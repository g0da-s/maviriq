from maverick.pipeline.runner import PipelineRunner
from maverick.storage.repository import ValidationRepository

_pipeline_runner: PipelineRunner | None = None
_validation_repo: ValidationRepository | None = None


def get_pipeline_runner() -> PipelineRunner:
    global _pipeline_runner
    if _pipeline_runner is None:
        _pipeline_runner = PipelineRunner()
    return _pipeline_runner


def get_validation_repo() -> ValidationRepository:
    global _validation_repo
    if _validation_repo is None:
        _validation_repo = ValidationRepository()
    return _validation_repo
