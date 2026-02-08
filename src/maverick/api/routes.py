import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from maverick.api.dependencies import get_pipeline_runner, get_validation_repo
from maverick.models.schemas import (
    CreateValidationRequest,
    CreateValidationResponse,
    ValidationListResponse,
    ValidationRun,
    ValidationStatus,
)
from maverick.pipeline.runner import PipelineRunner
from maverick.storage.repository import ValidationRepository

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
    runner: PipelineRunner = Depends(get_pipeline_runner),
) -> CreateValidationResponse:
    run_id = f"val_{uuid4().hex[:12]}"

    # Start pipeline in background
    task = asyncio.create_task(_run_pipeline_background(run_id, request.idea, runner))
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
    repo: ValidationRepository = Depends(get_validation_repo),
):
    async def event_generator():
        # Check if validation exists
        run = await repo.get(run_id)
        if not run:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Validation not found"}),
            }
            return

        # Track which agent completions we've already sent
        sent_agents: set[int] = set()

        # Detect already-completed agents from a prior load
        agent_outputs = [
            (1, "Pain & User Discovery", lambda r: r.pain_discovery),
            (2, "Competitor Research", lambda r: r.competitor_research),
            (3, "Viability Analysis", lambda r: r.viability),
            (4, "Synthesis & Verdict", lambda r: r.synthesis),
        ]

        while True:
            run = await repo.get(run_id)
            if not run:
                break

            # Emit completion events for any agent that has output we haven't sent yet
            for agent_num, agent_name, get_output in agent_outputs:
                if agent_num not in sent_agents:
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

            # Check if done
            if run.status == ValidationStatus.COMPLETED:
                yield {
                    "event": "pipeline_completed",
                    "data": json.dumps({
                        "id": run.id,
                        "verdict": run.synthesis.verdict.value if run.synthesis else None,
                        "confidence": run.synthesis.confidence if run.synthesis else None,
                    }),
                }
                break
            elif run.status == ValidationStatus.FAILED:
                yield {
                    "event": "pipeline_error",
                    "data": json.dumps({"error": run.error}),
                }
                break

            # Poll every 2 seconds
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@router.get("/validations/{run_id}", response_model=ValidationRun)
async def get_validation(
    run_id: str, repo: ValidationRepository = Depends(get_validation_repo)
) -> ValidationRun:
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Validation not found")
    return run


@router.get("/validations", response_model=ValidationListResponse)
async def list_validations(
    page: int = 1,
    per_page: int = 20,
    repo: ValidationRepository = Depends(get_validation_repo),
) -> ValidationListResponse:
    items, total = await repo.list(page, per_page)
    return ValidationListResponse(items=items, total=total, page=page, per_page=per_page)


@router.delete("/validations/{run_id}")
async def delete_validation(
    run_id: str, repo: ValidationRepository = Depends(get_validation_repo)
) -> dict:
    # Cancel running pipeline if still active
    task = _running_pipelines.pop(run_id, None)
    if task and not task.done():
        task.cancel()
    deleted = await repo.delete(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Validation not found")
    return {"status": "deleted"}


async def _run_pipeline_background(run_id: str, idea: str, runner: PipelineRunner):
    """Run pipeline in background, discarding SSE events."""
    try:
        async for _ in runner.run(run_id, idea):
            pass  # Discard events, they're streamed via /stream endpoint
    except Exception as e:
        logger.exception(f"Background pipeline failed for {run_id}")
    finally:
        _running_pipelines.pop(run_id, None)
