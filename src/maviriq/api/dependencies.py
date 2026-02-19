import logging

import jwt as pyjwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from maviriq.config import settings
from maviriq.pipeline.runner import PipelineGraph
from maviriq.storage.credit_repository import CreditTransactionRepository
from maviriq.storage.repository import ValidationRepository
from maviriq.storage.user_repository import UserRepository
from maviriq.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=3600,
        )
    return _jwks_client


_pipeline_runner: PipelineGraph | None = None
_validation_repo: ValidationRepository | None = None
_user_repo: UserRepository | None = None

security = HTTPBearer(auto_error=False)


def get_pipeline_runner() -> PipelineGraph:
    global _pipeline_runner
    if _pipeline_runner is None:
        _pipeline_runner = PipelineGraph()
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
    """Decode and verify a Supabase JWT using the JWKS public key."""
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    except Exception:
        logger.exception("JWKS key fetch failed")
        raise HTTPException(
            status_code=503, detail="Authentication service temporarily unavailable"
        )

    try:
        payload = pyjwt.decode(
            token,
            signing_key.key,
            audience="authenticated",
            algorithms=["ES256"],
            leeway=10,
        )
        return payload
    except pyjwt.PyJWTError:
        logger.warning("JWT decode failed for token")
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

    repo = get_user_repo()
    profile = await repo.get_by_id(user_id)

    if not profile:
        profile = await repo.ensure_profile(user_id, email)

    # Grant signup bonus if email is verified and not yet granted
    if not profile.get("signup_bonus_granted"):
        sb = await get_supabase()
        auth_user = await sb.auth.admin.get_user_by_id(user_id)
        if auth_user and auth_user.user and auth_user.user.email_confirmed_at:
            txn_repo = CreditTransactionRepository()
            granted = await repo.grant_signup_bonus(user_id)
            if granted:
                await txn_repo.record(user_id, 1, "signup_bonus")
            profile = await repo.get_by_id(user_id)

    return profile
