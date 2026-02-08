import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from maverick.api.dependencies import get_current_user, get_user_repo
from maverick.api.rate_limit import rate_limit_auth, rate_limit_register
from maverick.models.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from maverick.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from maverick.storage.credit_repository import CreditTransactionRepository
from maverick.storage.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        credits=user["credits"],
        created_at=user.get("created_at", ""),
    )


@router.post("/register", response_model=AuthResponse)
async def register(
    request: Request,
    req: RegisterRequest,
    repo: UserRepository = Depends(get_user_repo),
) -> AuthResponse:
    rate_limit_auth(request)
    rate_limit_register(request)
    existing = await repo.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(req.password)
    user = await repo.create(email=req.email, password_hash=hashed)

    txn_repo = CreditTransactionRepository()
    await txn_repo.record(user["id"], 1, "signup_bonus")

    token = create_access_token(user["id"])
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    req: LoginRequest,
    repo: UserRepository = Depends(get_user_repo),
) -> AuthResponse:
    rate_limit_auth(request)
    user = await repo.get_by_email(req.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user["id"])
    return AuthResponse(token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)
