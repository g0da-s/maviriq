import logging

from httpx import Timeout
from supabase import acreate_client, AsyncClient, AsyncClientOptions

from maviriq.config import settings
from maviriq.storage import DatabaseError

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None

_SUPABASE_TIMEOUT = Timeout(30.0, connect=10.0)


async def get_supabase() -> AsyncClient:
    """Get or create the async Supabase client (service_role for backend ops)."""
    global _client
    if _client is None:
        try:
            _client = await acreate_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
                options=AsyncClientOptions(
                    postgrest_client_timeout=_SUPABASE_TIMEOUT,
                    storage_client_timeout=30,
                ),
            )
        except Exception as e:
            logger.exception("Failed to initialize Supabase client")
            raise DatabaseError(str(e)) from e
    return _client
