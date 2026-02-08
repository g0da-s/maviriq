from supabase import acreate_client, AsyncClient

from maverick.config import settings

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    """Get or create the async Supabase client (service_role for backend ops)."""
    global _client
    if _client is None:
        _client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client
