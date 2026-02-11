import logging

from maverick.storage import DatabaseError
from maverick.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class UserRepository:
    async def get_by_id(self, user_id: str) -> dict | None:
        sb = await get_supabase()
        try:
            result = await sb.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
        except Exception as e:
            logger.exception("Failed to get user profile by id")
            raise DatabaseError(str(e)) from e
        return dict(result.data) if result.data else None

    async def get_by_email(self, email: str) -> dict | None:
        sb = await get_supabase()
        try:
            result = await sb.table("profiles").select("*").eq("email", email).maybe_single().execute()
        except Exception as e:
            logger.exception("Failed to get user profile by email")
            raise DatabaseError(str(e)) from e
        return dict(result.data) if result.data else None

    async def ensure_profile(self, user_id: str, email: str) -> dict:
        """Create profile if it doesn't exist (fallback for trigger race condition)."""
        sb = await get_supabase()
        try:
            result = await (
                sb.table("profiles")
                .upsert(
                    {"id": user_id, "email": email, "credits": 0, "signup_bonus_granted": False},
                    on_conflict="id",
                )
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to ensure profile for user")
            raise DatabaseError(str(e)) from e
        return dict(result.data[0])

    async def grant_signup_bonus(self, user_id: str) -> bool:
        """Atomically grant signup bonus. Returns False if already granted."""
        sb = await get_supabase()
        try:
            result = await sb.rpc("grant_signup_bonus", {"p_user_id": user_id}).execute()
        except Exception as e:
            logger.exception("Failed to grant signup bonus")
            raise DatabaseError(str(e)) from e
        return result.data is True

    async def deduct_credit(self, user_id: str) -> bool:
        """Atomically deduct 1 credit. Returns False if insufficient."""
        sb = await get_supabase()
        try:
            result = await sb.rpc("deduct_credit", {"p_user_id": user_id}).execute()
        except Exception as e:
            logger.exception("Failed to deduct credit")
            raise DatabaseError(str(e)) from e
        return result.data is True

    async def add_credits(self, user_id: str, amount: int) -> None:
        sb = await get_supabase()
        try:
            await sb.rpc("add_credits", {"p_user_id": user_id, "p_amount": amount}).execute()
        except Exception as e:
            logger.exception("Failed to add credits")
            raise DatabaseError(str(e)) from e
