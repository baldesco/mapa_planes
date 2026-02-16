from fastapi import HTTPException, status
from supabase import AsyncClient, create_async_client

from app.core.config import logger, settings

# --- Supabase Client Setup ---
_supabase_url = settings.SUPABASE_URL
_supabase_key = settings.SUPABASE_KEY
_supabase_service_key = settings.SUPABASE_SERVICE_ROLE_KEY

# Store the base service client if configured
_base_service_client: AsyncClient | None = None


async def init_service_client() -> None:
    """
    Initializes the Supabase base service client asynchronously.
    Called during the first request for the service client or app startup.
    """
    global _base_service_client
    if _supabase_url and _supabase_service_key and _base_service_client is None:
        logger.info("Attempting to initialize Supabase async base service client...")
        try:
            _base_service_client = await create_async_client(
                _supabase_url, _supabase_service_key
            )
            logger.info("Supabase async base service client initialized successfully.")
        except Exception as e:
            logger.error(
                f"Failed to initialize Supabase service client: {e}", exc_info=True
            )
            _base_service_client = None
    elif not _supabase_service_key:
        logger.warning(
            "SUPABASE_SERVICE_ROLE_KEY not provided. Base service client not initialized."
        )


async def get_base_supabase_client() -> AsyncClient:
    """
    Returns a base Supabase client initialized with the ANON key.
    This is created PER REQUEST and is configured with the user auth token in get_db.
    """
    if not _supabase_url or not _supabase_key:
        logger.critical("Supabase URL or Anon Key not configured for base client.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core database config missing.",
        )
    try:
        # Per request client creation for proper JWT scope handling
        client = await create_async_client(_supabase_url, _supabase_key)
        logger.debug("Created new async base Supabase client instance for request.")
        return client
    except Exception as e:
        logger.error(
            f"Failed to create base Supabase client instance: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize database client.",
        ) from None


async def get_supabase_service_client() -> AsyncClient | None:
    """
    FastAPI dependency to get the initialized Supabase service client.
    Returns the shared instance if available, otherwise None.
    """
    if not _base_service_client and _supabase_service_key:
        await init_service_client()

    if not _base_service_client:
        logger.warning(
            "Dependency Warning: Request for Supabase service client, but it's not available (key missing or init failed)."
        )
    return _base_service_client


logger.info("DB Setup: Async Supabase client getters configured.")
