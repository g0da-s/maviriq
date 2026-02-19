import logging

from maviriq.storage import DatabaseError
from maviriq.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class UserRepository:
    async def get_by_id(self, user_id: str) -> dict | None:
        sb = await get_supabase()
        try:
            result = (
                await sb.table("profiles")
                .select("*")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to get user profile by id")
            raise DatabaseError(str(e)) from e
        return dict(result.data) if result.data else None

    async def ensure_profile(self, user_id: str, email: str) -> dict:
        """Create profile if it doesn't exist (fallback for trigger race condition)."""
        sb = await get_supabase()
        try:
            result = await (
                sb.table("profiles")
                .upsert(
                    {
                        "id": user_id,
                        "email": email,
                        "credits": 0,
                        "signup_bonus_granted": False,
                    },
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
            result = await sb.rpc(
                "grant_signup_bonus", {"p_user_id": user_id}
            ).execute()
        except Exception as e:
            logger.exception("Failed to grant signup bonus")
            raise DatabaseError(str(e)) from e
        return result.data is True
