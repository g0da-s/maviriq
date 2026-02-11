import logging

from supabase import acreate_client, AsyncClient

from maviriq.config import settings
from maviriq.storage import DatabaseError

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    """Get or create the async Supabase client (service_role for backend ops)."""
    global _client
    if _client is None:
        try:
            _client = await acreate_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
            )
        except Exception as e:
            logger.exception("Failed to initialize Supabase client")
            raise DatabaseError(str(e)) from e
    return _client
