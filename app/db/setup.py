import asyncio
from fastapi import Depends, HTTPException, status, Request
from supabase import create_client, Client as SupabaseClient

from app.core.config import settings, logger
from app.models.auth import UserInToken  # Import the specific model needed
from app.auth.dependencies import (
    get_token_from_cookie,
    get_current_active_user,
)  # Import auth dependencies


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


# --- Primary 'get_db' dependency ---
async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    request_client: SupabaseClient = Depends(get_base_supabase_client),
    current_user: UserInToken = Depends(get_current_active_user),
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance configured
    to use the user's JWT token for RLS-enabled API calls.
    """
    if token is None:
        logger.error(
            "get_db: Reached dependency logic but token is None. This indicates an issue in dependency chain."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (token missing)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(
        f"get_db: Configuring request-specific Supabase client instance with Authorization header for user {current_user.email} using token {token[:10]}..."
    )
    auth_header = f"Bearer {token}"

    try:
        # Modify headers for PostgREST and Storage clients
        if hasattr(request_client, "postgrest") and hasattr(
            request_client.postgrest, "session"
        ):
            request_client.postgrest.session.headers["Authorization"] = auth_header
            logger.debug("Authorization header set for PostgREST client.")
        else:
            logger.warning(
                "Could not find request_client.postgrest.session to set auth header."
            )

        if hasattr(request_client, "storage") and hasattr(
            request_client.storage, "_client"
        ):
            if hasattr(request_client.storage._client, "session"):
                request_client.storage._client.session.headers["Authorization"] = (
                    auth_header
                )
                logger.debug("Authorization header set for Storage client.")
            elif hasattr(request_client.storage._client, "headers"):
                request_client.storage._client.headers["Authorization"] = auth_header
                logger.debug(
                    "Authorization header set for Storage client via .headers."
                )
        else:
            logger.debug("Storage client or its session not found for header setting.")

    except AttributeError as ae:
        logger.error(
            f"get_db: Failed to access internal session/headers to set auth token. Library structure might have changed. Error: {ae}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client for authenticated access (internal structure error).",
        )
    except Exception as e:
        logger.error(
            f"get_db: Unexpected error setting auth token on Supabase client: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client for authenticated access (unexpected error).",
        )

    return request_client


logger.info(
    "DB Setup: 'get_db' dependency configured to provide request-scoped, authenticated Supabase client."
)
