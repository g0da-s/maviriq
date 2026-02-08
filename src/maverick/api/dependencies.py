import logging

import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from maverick.config import settings
from maverick.pipeline.runner import PipelineRunner
from maverick.storage.credit_repository import CreditTransactionRepository
from maverick.storage.repository import ValidationRepository
from maverick.storage.user_repository import UserRepository

logger = logging.getLogger(__name__)

_pipeline_runner: PipelineRunner | None = None
_validation_repo: ValidationRepository | None = None
_user_repo: UserRepository | None = None

security = HTTPBearer(auto_error=False)


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


def decode_supabase_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT. Returns the full payload or raises."""
    try:
        payload = pyjwt.decode(
            token,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
        return payload
    except pyjwt.PyJWTError as e:
        logger.error("JWT decode failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extract user from Supabase JWT, ensure profile exists, check signup bonus."""
    if cred is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_supabase_jwt(cred.credentials)
    user_id = payload.get("sub")
    email = payload.get("email", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no sub claim")

    email_confirmed = payload.get("email_confirmed_at") is not None

    repo = get_user_repo()
    profile = await repo.get_by_id(user_id)

    if not profile:
        profile = await repo.ensure_profile(user_id, email)

    # Grant signup bonus if email is verified and not yet granted
    if email_confirmed and not profile.get("signup_bonus_granted"):
        txn_repo = CreditTransactionRepository()
        granted = await repo.grant_signup_bonus(user_id)
        if granted:
            await txn_repo.record(user_id, 1, "signup_bonus")
        profile = await repo.get_by_id(user_id)

    return profile
