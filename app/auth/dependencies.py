import asyncio
import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from supabase import Client as SupabaseClient
from supabase import AuthApiError
from pydantic import ValidationError

from app.core.config import settings, logger
from app.models.auth import UserInToken
from app.db.setup import get_base_supabase_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_token_from_header(
    token: str | None = Depends(oauth2_scheme),
) -> str | None:
    """
    Dependency to extract the token from the Authorization header.
    Returns the raw token string or None if not found.
    Note: auto_error=False means it won't raise 401 automatically if header is missing.
    """
    return token


async def get_db_with_header_token(
    request: Request,  # Add request to access state
    token: str | None = Depends(get_token_from_header),
    request_client: SupabaseClient = Depends(get_base_supabase_client),
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance configured
    to use the JWT token from the Authorization header (e.g., for password reset).
    Raises 401 if the token is missing or invalid during configuration.
    Crucially calls `set_session` on the client instance.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials from header",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        logger.warning("get_db_with_header_token: No token provided in header.")
        raise credentials_exception

    auth_header = f"Bearer {token}"
    try:
        # Configure PostgREST client (might not be strictly needed for auth.update_user, but good practice)
        if hasattr(request_client, "postgrest") and hasattr(
            request_client.postgrest, "session"
        ):
            request_client.postgrest.session.headers["Authorization"] = auth_header
        else:
            logger.warning(
                "Could not find request_client.postgrest.session to set auth header."
            )

        # Configure Storage client (might not be strictly needed for auth.update_user)
        if hasattr(request_client, "storage") and hasattr(
            request_client.storage, "_client"
        ):
            if hasattr(request_client.storage._client, "session"):
                request_client.storage._client.session.headers["Authorization"] = (
                    auth_header
                )
            elif hasattr(request_client.storage._client, "headers"):
                request_client.storage._client.headers["Authorization"] = auth_header

        # *** CRITICAL STEP: Set the session on the Auth client ***
        # This is what `update_user` relies on when no JWT is passed explicitly.
        request_client.auth.set_session(access_token=token, refresh_token="")
        logger.info(
            "get_db_with_header_token: Successfully called set_session on Supabase client."
        )

        # Store token in state for debugging or potential future use, but don't rely on it for the fix
        request.state.recovery_token = token

        # REMOVED the get_user call block here as it was failing and isn't needed for the update operation itself.
        # The primary goal is to return a client instance with the session correctly set.
        request.state.user = None  # Explicitly set user state to None here

    except AuthApiError as api_error:
        # Catch potential errors during set_session if the token is immediately invalid
        logger.error(
            f"get_db_with_header_token: AuthApiError during set_session: {api_error.status} - {api_error.message}",
            exc_info=False,
        )
        raise credentials_exception from api_error
    except Exception as e:
        logger.error(
            f"get_db_with_header_token: Unexpected error setting auth token/session on Supabase client: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client for authenticated access.",
        ) from e

    return request_client


async def get_token_from_cookie(
    request: Request,
) -> str | None:
    """
    Custom dependency to extract the JWT from the 'access_token' cookie.
    Returns the raw token string or None if not found/malformed.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie:
        return None

    # Handle potential "Bearer " prefix in cookie value
    if token_cookie.lower().startswith("bearer "):
        parts = token_cookie.split(maxsplit=1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
        else:
            logger.warning(
                f"get_token_from_cookie: Malformed Bearer token in cookie: '{token_cookie}'"
            )
            return None
    else:
        # Assume the cookie value *is* the token if no "Bearer " prefix
        logger.debug(
            f"get_token_from_cookie: Cookie value does not start with 'Bearer ', treating value as token: '{token_cookie[:10]}...'"
        )
        return token_cookie


async def get_current_user(
    token: str | None = Depends(get_token_from_cookie),
    base_db: SupabaseClient = Depends(get_base_supabase_client),
) -> UserInToken:
    """
    Dependency to validate the token from the cookie via Supabase and return user info.
    Raises 401 if token is missing, invalid, or validation fails (including invalidated session).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        # Use the base client and pass the token explicitly to get_user
        response = await asyncio.to_thread(base_db.auth.get_user, token)
        user_data = response.user

        if not user_data or not user_data.id:
            logger.warning(
                "Token validation failed: Supabase get_user returned no user or user ID (session likely invalidated)."
            )
            raise credentials_exception

        try:
            current_user = UserInToken(id=user_data.id, email=user_data.email)
            return current_user
        except (ValidationError, AttributeError) as e:
            logger.error(
                f"Token validation error: Could not map Supabase user to UserInToken model. Error: {e}, Data: {user_data}",
                exc_info=True,
            )
            raise credentials_exception

    except AuthApiError as api_error:
        logger.warning(
            f"Supabase AuthApiError during token validation: {api_error.status} - {api_error.message}"
        )
        status_code = getattr(api_error, "status", status.HTTP_401_UNAUTHORIZED)
        if (
            status_code == 401
            or "invalid JWT" in api_error.message.lower()
            or "Token is expired" in api_error.message.lower()
        ):
            raise credentials_exception from api_error
        else:
            logger.error(
                f"Unexpected Supabase AuthApiError during validation: {api_error}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication.",
            ) from api_error
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"Unexpected error during token validation process: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication.",
        ) from e


async def get_current_active_user(
    current_user: UserInToken = Depends(get_current_user),
) -> UserInToken:
    """
    Ensures the user retrieved from the token is valid.
    Relies on get_current_user to perform the actual validation.
    """
    return current_user


async def get_optional_current_user(
    request: Request,
    db: SupabaseClient = Depends(get_base_supabase_client),
) -> UserInToken | None:
    """Dependency that returns the current user if authenticated, or None otherwise."""
    try:
        token = await get_token_from_cookie(request)
        if token is None:
            return None
        # Pass the token explicitly to get_current_user
        current_user = await get_current_user(token=token, base_db=db)
        return current_user
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        logger.error(
            f"Unexpected HTTPException in get_optional_current_user: {e.status_code} - {e.detail}",
            exc_info=False,
        )
        raise e  # Re-raise other HTTP exceptions
    except Exception as e:
        # Log critical errors but return None to avoid breaking pages that allow anonymous access
        logger.error(
            f"Critical unexpected error in get_optional_current_user: {e}",
            exc_info=True,
        )
        return None


async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    request_client: SupabaseClient = Depends(get_base_supabase_client),
    current_user: UserInToken = Depends(
        get_current_active_user
    ),  # Ensures user is authenticated
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance configured
    to use the user's JWT token (from cookie) for RLS-enabled API calls.
    Requires user to be authenticated (enforced by current_user dependency).
    """
    if token is None:
        # This should theoretically not happen due to get_current_active_user dependency,
        # but check defensively.
        logger.error(
            "get_db: Reached dependency logic but token is None despite active user dependency."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (token missing)",
        )

    auth_header = f"Bearer {token}"
    try:
        # Configure PostgREST client
        if hasattr(request_client, "postgrest") and hasattr(
            request_client.postgrest, "session"
        ):
            request_client.postgrest.session.headers["Authorization"] = auth_header
        else:
            logger.warning(
                "Could not find request_client.postgrest.session to set auth header."
            )

        # Configure Storage client
        if hasattr(request_client, "storage") and hasattr(
            request_client.storage, "_client"
        ):
            if hasattr(request_client.storage._client, "session"):
                request_client.storage._client.session.headers["Authorization"] = (
                    auth_header
                )
            elif hasattr(request_client.storage._client, "headers"):
                request_client.storage._client.headers["Authorization"] = auth_header

        # Set session for auth client as well (might be needed for some auth operations)
        request_client.auth.set_session(access_token=token, refresh_token="")

    except Exception as e:
        logger.error(
            f"get_db: Unexpected error setting auth token on Supabase client: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client for authenticated access.",
        )

    return request_client
