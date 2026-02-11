import logging

from fastapi import APIRouter, Depends

from maviriq.api.dependencies import get_current_user
from maviriq.models.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        credits=user["credits"],
        created_at=str(user.get("created_at", "")),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)
