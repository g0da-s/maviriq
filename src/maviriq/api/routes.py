import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sse_starlette.sse import EventSourceResponse

from pydantic import BaseModel as _BM

from maviriq.api.dependencies import (
    get_current_user,
    get_pipeline_runner,
    get_validation_repo,
)
from maviriq.api.stream_tokens import stream_token_store
from maviriq.models.schemas import (
    CreateValidationRequest,
    CreateValidationResponse,
    ValidationListResponse,
    ValidationRun,
    ValidationStatus,
)
from maviriq.pipeline import pubsub
from maviriq.config import settings
from maviriq.pipeline.runner import PipelineGraph
from maviriq.storage.credit_repository import CreditTransactionRepository
from maviriq.storage.repository import ValidationRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Store running pipelines
_running_pipelines: dict[str, asyncio.Task] = {}


class _IdeaCheck(_BM):
    is_valid: bool
    reason: str


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    """Transcribe audio via OpenAI Whisper API."""
    from maviriq.services.transcription import transcribe_audio

    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Transcription not configured")

    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25MB)")

    try:
        text = await transcribe_audio(contents, filename=file.filename or "recording.webm")
        return {"text": text}
    except Exception:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=502, detail="Transcription failed")


@router.get("/stats")
async def stats(
    repo: ValidationRepository = Depends(get_validation_repo),
) -> dict:
    """Public endpoint — no auth. Returns total completed validations."""
    count = await repo.count_completed()
    return {"ideas_analyzed": count}


@router.post("/validations", response_model=CreateValidationResponse)
async def create_validation(
    request: CreateValidationRequest,
    user: dict = Depends(get_current_user),
    runner: PipelineGraph = Depends(get_pipeline_runner),
) -> CreateValidationResponse:
    from maviriq.api.rate_limit import rate_limit_idea_check, rate_limit_validation

    # Lighter rate limit for the coherence check (20/hr)
    rate_limit_idea_check(user["id"])

    # LLM coherence check — runs before credit deduction
    from maviriq.services.llm import LLMService

    llm = LLMService()
    try:
        check = await llm.generate_structured(
            system_prompt=(
                "You decide whether user input is a coherent product, startup, or business idea. "
                "The input may be in Lithuanian or English — both are valid. "
                "Reject gibberish, random words, profanity-only inputs, or clearly non-idea text. "
                "Be lenient — vague or unusual ideas are fine. Only reject obvious garbage."
            ),
            user_prompt=request.idea,
            output_schema=_IdeaCheck,
            use_cheap_model=True,
        )
        if not check.is_valid:
            logger.info("LLM coherence check rejected idea from user %s", user["id"])
            raise HTTPException(status_code=422, detail=check.reason)
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "LLM idea check failed — rejecting to protect API costs", exc_info=True
        )
        raise HTTPException(
            status_code=503,
            detail="Validation service temporarily unavailable. Please try again in a moment.",
        )

    # Full validation rate limit — only counted for ideas that passed the check (5/hr)
    rate_limit_validation(user["id"])

    # Normalize idea — fix typos, grammar, abbreviations before pipeline
    from maviriq.services.input_validation import normalize_idea

    clean_idea = await normalize_idea(request.idea)
    if clean_idea != request.idea:
        logger.info(
            "Idea normalized for user %s: %r -> %r",
            user["id"],
            request.idea,
            clean_idea,
        )

    # Atomically deduct credit + record transaction in a single DB call
    txn_repo = CreditTransactionRepository()
    if not await txn_repo.deduct_credit_with_txn(user["id"], "validation"):
        logger.info("Insufficient credits for user %s", user["id"])
        raise HTTPException(status_code=402, detail="Insufficient credits")

    run_id = f"val_{uuid4().hex[:12]}"

    # Start pipeline in background — use cleaned idea for better research quality
    language = getattr(request, "language", "en") or "en"
    task = asyncio.create_task(
        _run_pipeline_background(run_id, clean_idea, runner, user_id=user["id"], language=language)
    )
    _running_pipelines[run_id] = task
    task.add_done_callback(lambda _: _running_pipelines.pop(run_id, None))

    return CreateValidationResponse(
        id=run_id,
        idea=request.idea,
        status=ValidationStatus.RUNNING,
        stream_url=f"/api/validations/{run_id}/stream",
    )


@router.post("/validations/{run_id}/stream-token")
async def create_stream_token(
    run_id: str,
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> dict:
    """Issue a short-lived, single-use token for connecting to an SSE stream."""
    run = await repo.get_for_user(run_id, user["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Validation not found")
    token = stream_token_store.create(user["id"], run_id)
    return {"token": token}


@router.get("/validations/{run_id}/stream")
async def stream_validation(
    run_id: str,
    token: str = "",
    repo: ValidationRepository = Depends(get_validation_repo),
):
    # Validate one-time stream token (not a JWT — short-lived, single-use)
    token_user_id = stream_token_store.consume(token, run_id) if token else None
    if not token_user_id:

        async def auth_error():
            yield {
                "event": "pipeline_error",
                "data": json.dumps({"error": "Not authenticated"}),
            }

        return EventSourceResponse(auth_error())

    async def event_generator():
        # Check if validation exists and belongs to user (ownership at DB level)
        run = await repo.get_for_user(run_id, token_user_id)
        if not run:
            yield {
                "event": "pipeline_error",
                "data": json.dumps({"error": "Validation not found"}),
            }
            return

        # If pipeline already finished, replay from DB and return
        if run.status in (ValidationStatus.COMPLETED, ValidationStatus.FAILED):
            async for evt in _replay_from_db(run):
                yield evt
            return

        # Subscribe for live events, then replay anything already in DB
        queue = pubsub.subscribe(run_id)
        try:
            # Replay agents that completed before we subscribed
            sent_agents: set[int] = set()
            agent_outputs = [
                (1, lambda r: r.pain_discovery),
                (2, lambda r: r.competitor_research),
                (3, lambda r: r.market_intelligence),
                (4, lambda r: r.graveyard_research),
                (5, lambda r: r.synthesis),
            ]
            run = await repo.get_for_user(run_id, token_user_id)
            if run:
                for agent_num, get_output in agent_outputs:
                    output = get_output(run)
                    if output is not None:
                        sent_agents.add(agent_num)
                        yield {
                            "event": "agent_completed",
                            "data": json.dumps(
                                {
                                    "agent": agent_num,
                                    "output": output.model_dump(),
                                }
                            ),
                        }

            # Stream live events from pubsub queue
            while True:
                event = await queue.get()
                if event is None:
                    break
                # Skip agent_completed events we already replayed
                if (
                    event.event == "agent_completed"
                    and event.data.get("agent") in sent_agents
                ):
                    continue
                yield {
                    "event": event.event,
                    "data": json.dumps(event.data),
                }
                if event.event in ("pipeline_completed", "pipeline_error"):
                    break
        finally:
            pubsub.unsubscribe(run_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/validations/{run_id}", response_model=ValidationRun)
async def get_validation(
    run_id: str,
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> ValidationRun:
    run = await repo.get_for_user(run_id, user["id"])
    if not run:
        raise HTTPException(status_code=404, detail="Validation not found")
    return run


@router.get("/validations", response_model=ValidationListResponse)
async def list_validations(
    page: int = Query(default=1, gt=0),
    per_page: int = Query(default=20, gt=0, le=100),
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> ValidationListResponse:
    items, total = await repo.list(page, per_page, user_id=user["id"])
    return ValidationListResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.delete("/validations/{run_id}")
async def delete_validation(
    run_id: str,
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> dict:
    # Cancel running pipeline if still active
    task = _running_pipelines.pop(run_id, None)
    if task and not task.done():
        task.cancel()

    deleted = await repo.delete_for_user(run_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Validation not found")
    return {"status": "deleted"}


async def _replay_from_db(run: ValidationRun):
    """Replay completed agent events from a finished run (for late-connecting clients)."""
    agent_outputs = [
        (1, run.pain_discovery),
        (2, run.competitor_research),
        (3, run.market_intelligence),
        (4, run.graveyard_research),
        (5, run.synthesis),
    ]
    for agent_num, output in agent_outputs:
        if output is not None:
            yield {
                "event": "agent_completed",
                "data": json.dumps(
                    {
                        "agent": agent_num,
                        "output": output.model_dump(),
                    }
                ),
            }

    if run.status == ValidationStatus.COMPLETED:
        yield {
            "event": "pipeline_completed",
            "data": json.dumps(
                {
                    "id": run.id,
                    "verdict": run.synthesis.verdict.value if run.synthesis else None,
                    "confidence": run.synthesis.confidence if run.synthesis else None,
                }
            ),
        }
    elif run.status == ValidationStatus.FAILED:
        yield {
            "event": "pipeline_error",
            "data": json.dumps({"error": "Processing failed. Please try again."}),
        }


async def _run_pipeline_background(
    run_id: str, idea: str, runner: PipelineGraph, user_id: str | None = None, language: str = "en"
):
    """Run pipeline in background. PipelineGraph.run() handles pubsub internally."""
    try:
        await runner.run(run_id, idea, user_id=user_id, language=language)
    except Exception:
        logger.exception(f"Background pipeline failed for {run_id}")
    finally:
        _running_pipelines.pop(run_id, None)
