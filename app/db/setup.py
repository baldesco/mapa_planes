import asyncio
from fastapi import HTTPException, status
from supabase import create_client, Client as SupabaseClient

from app.core.config import settings, logger

# --- Supabase Configuration ---
_supabase_url = settings.SUPABASE_URL
_supabase_key = settings.SUPABASE_KEY
_supabase_service_key = settings.SUPABASE_SERVICE_ROLE_KEY

# Initialize the persistent Service Role client if keys are provided
# This client bypasses RLS and is used for admin tasks like storage cleanup
_base_service_client: SupabaseClient | None = None

if _supabase_url and _supabase_service_key:
    try:
        _base_service_client = create_client(_supabase_url, _supabase_service_key)
        logger.info("Supabase Service Role client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase service client: {e}")
else:
    logger.warning("SUPABASE_SERVICE_ROLE_KEY missing. Admin operations will be restricted.")


def get_base_supabase_client() -> SupabaseClient:
    """
    Creates a new Supabase client instance using the ANON key.
    This is used as a base for per-request authenticated clients.
    """
    if not _supabase_url or not _supabase_key:
        logger.critical("Supabase configuration missing (URL/Anon Key).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database configuration is missing.",
        )
    try:
        # Returns a fresh client instance
        return create_client(_supabase_url, _supabase_key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to database service.",
        )


def get_supabase_service_client() -> SupabaseClient | None:
    """
    Dependency to provide the Service Role client.
    Use with extreme caution: this client bypasses all Row Level Security.
    """
    return _base_service_client