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
    This is created PER REQUEST and should be configured with auth token in get_db.
    """
    if not _supabase_url or not _supabase_key:
        logger.critical("Supabase URL or Anon Key not configured for base client.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core database config missing.",
        )
    try:
        # Create a new client instance for each request that needs it.
        # This instance will be customized with the user's token in get_db.
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

    # Check if it's already just the token (from JS fetch?) or Bearer token
    if token_cookie.lower().startswith("bearer "):
        parts = token_cookie.split(maxsplit=1)
        if len(parts) == 2 and parts[1]:
            raw_token = parts[1]
            logger.debug(
                f"get_token_from_cookie: Extracted raw token from Bearer: {raw_token[:10]}..."
            )
            return raw_token
        else:
            logger.warning(
                f"get_token_from_cookie: Malformed Bearer token in cookie: '{token_cookie}'"
            )
            return None
    elif token_cookie:
        # Assume it might be the raw token directly if not starting with Bearer
        # This depends on how the cookie was set (login endpoint sets "Bearer ...")
        logger.debug(
            f"get_token_from_cookie: Cookie found, assuming raw token: {token_cookie[:10]}..."
        )
        # Let's strictly enforce Bearer format set during login for clarity
        logger.warning(
            f"get_token_from_cookie: Cookie value does not start with 'Bearer ': '{token_cookie}' - Treating as invalid."
        )
        return None
    else:  # Should not happen if token_cookie is truthy, but for safety
        logger.warning(
            f"get_token_from_cookie: Unexpected cookie value state: '{token_cookie}'"
        )
        return None


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
        logger.info("get_current_user: No valid token provided via cookie.")
        raise credentials_exception

    try:
        logger.debug(
            f"Attempting to validate token from cookie with Supabase: {token[:10]}..."
        )
        # Use the base client instance just for this validation call
        # Pass the extracted token explicitly using the `jwt` parameter
        response = await asyncio.to_thread(base_db.auth.get_user, token)
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
        # Check common Supabase API error structures
        if hasattr(e, "details"):
            error_message = f"{error_message} Details: {e.details}"
        if hasattr(e, "status_code"):
            error_message = f"Status {e.status_code}: {error_message}"

        logger.error(
            f"Token validation error via Supabase client: {error_message}",
            exc_info=False,  # Usually don't need full stack trace for auth errors
        )
        # Distinguish common auth errors if possible
        if (
            "invalid JWT" in error_message.lower()
            or "token is expired" in error_message.lower()
            or "Unauthorized" in error_message  # Check for common phrases
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
    # Currently, just validates token existence and basic structure via get_current_user.
    logger.debug(f"get_current_active_user returning user: {current_user.email}")
    return current_user


# --- Primary 'get_db' dependency ---
# This dependency will now provide a Supabase client *authenticated with the user's token*
async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    # Depend on get_base_supabase_client to get a FRESH client instance per request
    request_client: SupabaseClient = Depends(get_base_supabase_client),
    # We need the validated user only to ensure auth happened, but use token directly
    current_user: models.UserInToken = Depends(get_current_active_user),
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance configured
    to use the user's JWT token (obtained from cookie and validated)
    for subsequent RLS-enabled API calls within the request scope.

    Raises 401 if the user is not authenticated (handled by Depends(get_current_active_user)).
    """
    if token is None:
        # This case should technically be caught by get_current_active_user dependency,
        # but adding a check here for robustness.
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
        # Modify the headers of the underlying httpx client session used by PostgREST
        # This relies on the internal structure of supabase-py v2+
        if hasattr(request_client, "postgrest") and hasattr(
            request_client.postgrest, "session"
        ):
            request_client.postgrest.session.headers["Authorization"] = auth_header
            logger.debug("Authorization header set for PostgREST client.")
        else:
            logger.warning(
                "Could not find request_client.postgrest.session to set auth header."
            )
            # Consider raising an error if PostgREST auth is critical and cannot be set

        # Also modify headers for the Storage client if it uses a separate session
        # Note: storage client structure might differ. Check supabase-py specifics if storage RLS fails.
        # Common pattern: client.storage._client.session or similar
        # Let's assume for now Storage might reuse headers or handle auth differently.
        # If storage operations fail auth, investigate here.
        # Example check (adjust based on actual library structure):
        if hasattr(request_client, "storage") and hasattr(
            request_client.storage, "_client"
        ):
            if hasattr(request_client.storage._client, "session"):
                request_client.storage._client.session.headers["Authorization"] = (
                    auth_header
                )
                logger.debug("Authorization header set for Storage client.")
            elif hasattr(
                request_client.storage._client, "headers"
            ):  # If headers are directly on the client
                request_client.storage._client.headers["Authorization"] = auth_header
                logger.debug(
                    "Authorization header set for Storage client via .headers."
                )

        # No explicit 'set_auth' method call needed anymore.
        # The modified client instance `request_client` is returned.

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
    "Primary 'get_db' dependency configured to provide request-scoped, authenticated Supabase client by modifying headers."
)

# --- Removed Local DB Setup ---
logger.info("Local SQLite database support has been removed.")


# --- Main execution block ---
if __name__ == "__main__":
    # Basic connectivity checks (can be useful)
    logger.info("Running database.py script directly for checks...")

    # Check base client creation
    try:
        base_client = get_base_supabase_client()
        logger.info(
            f"Successfully created a base Supabase client (anon key): {base_client}"
        )
        # Test basic anon connection (e.g., fetch public schema info - might require specific call)
        # logger.info("Attempting basic anon connection test...")
        # Example: list functions (might need specific permissions)
        # functions = await asyncio.to_thread(base_client.functions.list)
        # logger.info(f"Functions listed via anon client: {functions}")

    except HTTPException as http_exc:
        logger.error(
            f"HTTPException during base client check: {http_exc.status_code} - {http_exc.detail}"
        )
    except Exception as e:
        logger.error(f"Error creating/using base Supabase client: {e}", exc_info=True)

    # Check service client availability
    service_client = get_supabase_service_client()
    if service_client:
        logger.info(f"Supabase service client seems available: {service_client}")
        # Consider adding a basic test using the service client if needed, e.g., list users (admin required)
        # try:
        #    logger.info("Attempting basic service client test (list users)...")
        #    # This requires admin privileges setup in Supabase for the service key
        #    list_users_response = await asyncio.to_thread(service_client.auth.admin.list_users)
        #    logger.info(f"Service client listed users (count): {len(list_users_response.users)}")
        # except Exception as se:
        #    logger.error(f"Error testing service client (list users): {se}", exc_info=False)
    else:
        logger.warning(
            "Supabase service client is not available (check .env and logs)."
        )

    logger.info("database.py checks finished.")
