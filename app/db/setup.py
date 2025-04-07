import asyncio
from fastapi import Depends, HTTPException, status, Request
from supabase import create_client, Client as SupabaseClient

from app.core.config import settings, logger


# --- Supabase Client Setup ---
_supabase_url = settings.SUPABASE_URL
_supabase_key = settings.SUPABASE_KEY
_supabase_service_key = settings.SUPABASE_SERVICE_ROLE_KEY

# Store the base service client if configured
_base_service_client: SupabaseClient | None = None
if _supabase_url and _supabase_service_key:
    logger.info("Attempting to initialize Supabase base service client...")
    try:
        _base_service_client = create_client(_supabase_url, _supabase_service_key)
        logger.info("Supabase base service client initialized successfully.")
    except Exception as e:
        logger.error(
            f"Failed to initialize Supabase service client: {e}", exc_info=True
        )
        _base_service_client = None
else:
    logger.warning(
        "SUPABASE_SERVICE_ROLE_KEY not provided. Base service client not initialized."
    )


# --- Dependency Functions for FastAPI ---


def get_base_supabase_client() -> SupabaseClient:
    """
    Returns a base Supabase client initialized with the ANON key.
    This is created PER REQUEST and should be configured with auth token in get_db.
    """
    if not _supabase_url or not _supabase_key:
        logger.critical("Supabase URL or Anon Key not configured for base client.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core database config missing.",
        )
    try:
        client = create_client(_supabase_url, _supabase_key)
        logger.debug("Created new base Supabase client instance for request.")
        return client
    except Exception as e:
        logger.error(
            f"Failed to create base Supabase client instance: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize database client.",
        )


def get_supabase_service_client() -> SupabaseClient | None:
    """
    FastAPI dependency to get the initialized Supabase service client.
    Returns the shared instance if available, otherwise None. Use with caution.
    """
    if not _base_service_client:
        logger.warning(
            "Dependency Warning: Request for Supabase service client, but it's not available (key missing or init failed)."
        )
    return _base_service_client


logger.info("DB Setup: Base Supabase client getters configured.")
