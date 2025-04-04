import os
import uuid
import asyncio
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from supabase import create_client, Client as SupabaseClient

# Add AsyncClient for explicit async operations if needed later
# from supabase_async import create_client as create_async_client, AsyncClient
from pydantic import ValidationError

# Ensure config is loaded correctly
try:
    from .core.config import settings, logger
    from . import models  # Import models for token validation
except ImportError:
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from app.core.config import settings, logger
    import app.models as models


# --- Supabase Client Setup ---
# Store the base URL and anon key
_supabase_url = settings.SUPABASE_URL
_supabase_key = settings.SUPABASE_KEY
_supabase_service_key = settings.SUPABASE_SERVICE_ROLE_KEY

# Store the base service client if configured
_base_service_client: SupabaseClient | None = None
if _supabase_url and _supabase_service_key:
    logger.info("Attempting to initialize Supabase base service client...")
    try:
        # Use options to prevent auto-refreshing token for service client
        _base_service_client = create_client(
            _supabase_url,
            _supabase_service_key,
            #  options=ClientOptions(auto_refresh_token=False, persist_session=False)
            # ClientOptions seems removed or changed in recent versions, handle manually if needed
        )
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
    This should NOT be used for authenticated RLS calls directly.
    """
    if not _supabase_url or not _supabase_key:
        logger.critical("Supabase URL or Anon Key not configured for base client.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core database config missing.",
        )
    # Create a new instance per request? Or reuse a global one?
    # For ANON key, reusing might be fine, but let's create new for safety/clarity
    # Note: Creating client on every request might add overhead. Consider optimizing later if needed.
    try:
        client = create_client(_supabase_url, _supabase_key)
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
    Returns the shared instance if available, otherwise None.
    """
    # Return the pre-initialized client
    if not _base_service_client:
        logger.warning(
            "Dependency Warning: Request for Supabase service client, but it's not available (key missing or init failed)."
        )
    return _base_service_client


# --- Authentication Dependencies ---


async def get_token_from_cookie(
    request: Request,
) -> str | None:  # Return None if not found
    """
    Custom dependency to extract the JWT from the 'access_token' cookie.
    Returns the raw token string or None if not found/malformed.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie:
        logger.debug("get_token_from_cookie: No 'access_token' cookie found.")
        return None

    parts = token_cookie.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        logger.warning(
            f"get_token_from_cookie: Malformed 'access_token' cookie value: '{token_cookie}'"
        )
        return None  # Treat malformed as not found

    raw_token = parts[1]
    logger.debug(f"get_token_from_cookie: Extracted raw token: {raw_token[:10]}...")
    return raw_token


async def get_current_user(
    # Depend on the token extractor returning Optional[str]
    token: str | None = Depends(get_token_from_cookie),
    # Use the base client for validation initially
    base_db: SupabaseClient = Depends(get_base_supabase_client),
) -> models.UserInToken:
    """
    Dependency to validate the token from the cookie and return the current user's basic info.
    Raises 401 if token is missing, invalid, or validation fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",  # Keep generic for security
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        logger.info("get_current_user: No token provided via cookie.")
        raise credentials_exception

    try:
        logger.debug(
            f"Attempting to validate token from cookie with Supabase: {token[:10]}..."
        )
        # Use the base client instance just for this validation call
        response = await asyncio.to_thread(base_db.auth.get_user, jwt=token)
        user_data = response.user
        logger.debug(
            f"Supabase auth get_user response received. User ID: {user_data.id if user_data else 'None'}"
        )

        if not user_data:
            logger.warning(
                "Token validation failed: Supabase get_user returned no user."
            )
            raise credentials_exception

        # Extract necessary info
        try:
            if not user_data.id or not user_data.email:
                logger.error(
                    f"Token validation error: Supabase user object missing id or email. Data: {user_data}"
                )
                raise credentials_exception

            current_user = models.UserInToken(id=user_data.id, email=user_data.email)
            logger.debug(f"Token validated successfully for user: {current_user.email}")
            return current_user
        except (ValidationError, AttributeError) as e:
            logger.error(
                f"Token validation error: Could not map Supabase user to UserInToken model. Error: {e}, Data: {user_data}",
                exc_info=True,
            )
            raise credentials_exception

    except Exception as e:  # Catch broader exceptions during the auth call
        # Log potential gotrue errors more specifically
        error_message = getattr(e, "message", str(e))
        logger.error(
            f"Token validation error via Supabase client: {error_message}",
            exc_info=False,
        )
        # Distinguish common auth errors if possible
        if (
            "invalid JWT" in error_message.lower()
            or "token is expired" in error_message.lower()
        ):
            raise credentials_exception  # Keep the same 401 for standard auth errors
        else:  # Raise 500 for unexpected errors during validation
            logger.error(
                f"Unexpected error during Supabase token validation: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication.",
            ) from e


async def get_current_active_user(
    current_user: models.UserInToken = Depends(get_current_user),
) -> models.UserInToken:
    """Ensures the user retrieved from the token is valid"""
    # Placeholder for future checks like is_active, etc.
    logger.debug(f"get_current_active_user returning user: {current_user.email}")
    return current_user


# --- Primary 'get_db' dependency ---
# This dependency will now provide a Supabase client *authenticated with the user's token*
async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    base_client: SupabaseClient = Depends(get_base_supabase_client),  # Get base client
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance
    authenticated with the user's JWT token from the cookie.
    Raises 401 if the user is not authenticated.
    """
    if token is None:
        logger.warning(
            "get_db: Attempted to get authenticated DB client without token."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set the JWT for the client instance for this request scope
    # This modifies the 'Authorization' header used for subsequent PostgREST calls
    logger.debug(f"get_db: Setting auth header for token {token[:10]}...")
    try:
        # The set_auth method might have changed; typically, you modify headers.
        # Let's manually set the header on the underlying httpx client's session
        # This depends on internal structure but is often necessary.
        # Alternative: Create a *new* client instance with the token? More overhead.
        # base_client.rest.session.headers["Authorization"] = f"Bearer {token}" # Example - check library specifics

        # Simpler approach often intended by libraries: `set_session` (might require refresh token)
        # or just passing the auth header manually to each request if needed.

        # Let's try the intended library way first: modify the client's state
        # This might implicitly set headers for Postgrest calls made with this `base_client` instance
        # within the request scope. We rely on `get_current_user` running first to validate.
        base_client.auth.set_auth(
            token
        )  # Assuming this works as intended for subsequent calls
        # If set_auth doesn't work, you might need to pass headers explicitly in CRUD:
        # e.g., db.table(...).select(...).execute(headers={"Authorization": f"Bearer {token}"}) -> less ideal

    except Exception as e:
        logger.error(
            f"get_db: Failed to set auth token on Supabase client: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client for authenticated access.",
        )

    return base_client


logger.info(
    "Primary 'get_db' dependency configured to provide authenticated Supabase client."
)


# --- Removed Local DB Setup ---
logger.info("Local SQLite database support has been removed.")

# --- Main execution block ---
# (Keep if useful for basic connectivity checks of anon/service clients)
if __name__ == "__main__":
    # ... (rest of the __main__ block can remain as is) ...
    pass
