"""Supabase client initialization."""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Get Supabase client instance (cached singleton).

    Returns:
        Supabase client configured with service role key

    Raises:
        Exception: If client initialization fails
    """
    try:
        settings = get_settings()
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Supabase client: {e}") from e
