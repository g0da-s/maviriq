from fastapi import Header, HTTPException

from maverick.pipeline.runner import PipelineRunner
from maverick.services.auth import decode_access_token
from maverick.storage.repository import ValidationRepository
from maverick.storage.user_repository import UserRepository

_pipeline_runner: PipelineRunner | None = None
_validation_repo: ValidationRepository | None = None
_user_repo: UserRepository | None = None


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


def get_user_repo() -> UserRepository:
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    repo = get_user_repo()
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
