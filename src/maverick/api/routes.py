import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from maverick.api.dependencies import get_current_user, get_pipeline_runner, get_validation_repo
from maverick.models.schemas import (
    CreateValidationRequest,
    CreateValidationResponse,
    ValidationListResponse,
    ValidationRun,
    ValidationStatus,
)
from maverick.pipeline import pubsub
from maverick.pipeline.runner import PipelineRunner
from maverick.storage.credit_repository import CreditTransactionRepository
from maverick.storage.repository import ValidationRepository
from maverick.storage.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Store running pipelines
_running_pipelines: dict[str, asyncio.Task] = {}


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/validations", response_model=CreateValidationResponse)
async def create_validation(
    request: CreateValidationRequest,
    user: dict = Depends(get_current_user),
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> CreateValidationResponse:
    # Deduct credit
    user_repo = UserRepository()
    if not await user_repo.deduct_credit(user["id"]):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    txn_repo = CreditTransactionRepository()
    await txn_repo.record(user["id"], -1, "validation")

    run_id = f"val_{uuid4().hex[:12]}"

    # Start pipeline in background
    task = asyncio.create_task(
        _run_pipeline_background(run_id, request.idea, runner, user_id=user["id"])
    )
    _running_pipelines[run_id] = task
    task.add_done_callback(lambda _: _running_pipelines.pop(run_id, None))

    return CreateValidationResponse(
        id=run_id,
        idea=request.idea,
        status=ValidationStatus.RUNNING,
        stream_url=f"/api/validations/{run_id}/stream",
    )


@router.get("/validations/{run_id}/stream")
async def stream_validation(
    run_id: str,
    token: str = "",
    repo: ValidationRepository = Depends(get_validation_repo),
):
    # EventSource can't send Authorization headers, so accept token as query param
    from maverick.api.dependencies import decode_supabase_jwt

    token_user_id = None
    if token:
        try:
            payload = decode_supabase_jwt(token)
            token_user_id = payload.get("sub")
        except Exception:
            pass
    if not token_user_id:
        async def auth_error():
            yield {"event": "error", "data": json.dumps({"error": "Not authenticated"})}
        return EventSourceResponse(auth_error())

    async def event_generator():
        # Check if validation exists and belongs to user
        run = await repo.get(run_id)
        if not run or run.user_id != token_user_id:
            yield {
                "event": "error",
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
                (1, "Pain & User Discovery", lambda r: r.pain_discovery),
                (2, "Competitor Research", lambda r: r.competitor_research),
                (3, "Viability Analysis", lambda r: r.viability),
                (4, "Synthesis & Verdict", lambda r: r.synthesis),
            ]
            run = await repo.get(run_id)
            if run:
                for agent_num, agent_name, get_output in agent_outputs:
                    output = get_output(run)
                    if output is not None:
                        sent_agents.add(agent_num)
                        yield {
                            "event": "agent_completed",
                            "data": json.dumps({
                                "agent": agent_num,
                                "name": agent_name,
                                "output": output.model_dump(),
                            }),
                        }

            # Stream live events from pubsub queue
            while True:
                event = await queue.get()
                if event is None:
                    break
                # Skip agent_completed events we already replayed
                if event.event == "agent_completed" and event.data.get("agent") in sent_agents:
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
    run = await repo.get(run_id)
    if not run or run.user_id != user["id"]:
        raise HTTPException(status_code=404, detail="Validation not found")
    return run


@router.get("/validations", response_model=ValidationListResponse)
async def list_validations(
    page: int = 1,
    per_page: int = 20,
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> ValidationListResponse:
    items, total = await repo.list(page, per_page, user_id=user["id"])
    return ValidationListResponse(items=items, total=total, page=page, per_page=per_page)


@router.delete("/validations/{run_id}")
async def delete_validation(
    run_id: str,
    user: dict = Depends(get_current_user),
    repo: ValidationRepository = Depends(get_validation_repo),
) -> dict:
    # Verify ownership
    run = await repo.get(run_id)
    if not run or run.user_id != user["id"]:
        raise HTTPException(status_code=404, detail="Validation not found")

    # Cancel running pipeline if still active
    task = _running_pipelines.pop(run_id, None)
    if task and not task.done():
        task.cancel()
    await repo.delete(run_id)
    return {"status": "deleted"}


async def _replay_from_db(run: ValidationRun):
    """Replay completed agent events from a finished run (for late-connecting clients)."""
    agent_outputs = [
        (1, "Pain & User Discovery", run.pain_discovery),
        (2, "Competitor Research", run.competitor_research),
        (3, "Viability Analysis", run.viability),
        (4, "Synthesis & Verdict", run.synthesis),
    ]
    for agent_num, agent_name, output in agent_outputs:
        if output is not None:
            yield {
                "event": "agent_completed",
                "data": json.dumps({
                    "agent": agent_num,
                    "name": agent_name,
                    "output": output.model_dump(),
                }),
            }

    if run.status == ValidationStatus.COMPLETED:
        yield {
            "event": "pipeline_completed",
            "data": json.dumps({
                "id": run.id,
                "verdict": run.synthesis.verdict.value if run.synthesis else None,
                "confidence": run.synthesis.confidence if run.synthesis else None,
            }),
        }
    elif run.status == ValidationStatus.FAILED:
        yield {
            "event": "pipeline_error",
            "data": json.dumps({"error": run.error}),
        }


async def _run_pipeline_background(
    run_id: str, idea: str, runner: PipelineRunner, user_id: str | None = None
):
    """Run pipeline in background, publishing SSE events via pubsub."""
    try:
        async for event in runner.run(run_id, idea, user_id=user_id):
            pubsub.publish(run_id, event)
    except Exception as e:
        logger.exception(f"Background pipeline failed for {run_id}")
    finally:
        pubsub.publish(run_id, None)  # Signal stream end
        _running_pipelines.pop(run_id, None)
