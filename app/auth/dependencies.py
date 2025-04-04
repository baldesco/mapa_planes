import asyncio
import uuid
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from supabase import Client as SupabaseClient
from supabase import AuthApiError  # Import specific Supabase error directly
from pydantic import ValidationError

from app.core.config import settings, logger
from app.models.auth import UserInToken
from app.db.setup import get_base_supabase_client


async def get_token_from_cookie(
    request: Request,
) -> str | None:
    """
    Custom dependency to extract the JWT from the 'access_token' cookie.
    Returns the raw token string or None if not found/malformed.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie:
        # logger.debug("get_token_from_cookie: No 'access_token' cookie found.")
        return None

    if token_cookie.lower().startswith("bearer "):
        parts = token_cookie.split(maxsplit=1)
        if len(parts) == 2 and parts[1]:
            raw_token = parts[1]
            # logger.debug(f"get_token_from_cookie: Extracted raw token from Bearer: {raw_token[:10]}...")
            return raw_token
        else:
            logger.warning(
                f"get_token_from_cookie: Malformed Bearer token in cookie: '{token_cookie}'"
            )
            return None
    else:
        logger.warning(
            f"get_token_from_cookie: Cookie value does not start with 'Bearer ': '{token_cookie}' - Treating as invalid."
        )
        return None


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
        logger.debug(
            f"get_current_user: Attempting validation for token {token[:10]}..."
        )
        response = await asyncio.to_thread(base_db.auth.get_user, token)
        user_data = response.user
        logger.debug(
            f"get_current_user: Supabase auth get_user response received. User ID: {user_data.id if user_data else 'None'}"
        )

        if not user_data or not user_data.id:
            logger.warning(
                "Token validation failed: Supabase get_user returned no user or user ID (session likely invalidated)."
            )
            raise credentials_exception

        try:
            current_user = UserInToken(id=user_data.id, email=user_data.email)
            logger.debug(f"Token validated successfully for user: {current_user.email}")
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
    logger.debug(f"get_current_active_user returning user: {current_user.email}")
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
        current_user = await get_current_user(token=token, base_db=db)
        return current_user
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        logger.error(
            f"Unexpected HTTPException in get_optional_current_user: {e.status_code} - {e.detail}",
            exc_info=False,
        )
        raise e
    except Exception as e:
        logger.error(
            f"Critical unexpected error in get_optional_current_user: {e}",
            exc_info=True,
        )
        return None


async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    request_client: SupabaseClient = Depends(get_base_supabase_client),
    current_user: UserInToken = Depends(get_current_active_user),
) -> SupabaseClient:
    """
    FastAPI dependency that provides a Supabase client instance configured
    to use the user's JWT token for RLS-enabled API calls.
    Requires user to be authenticated (enforced by current_user dependency).
    """
    if token is None:
        logger.error(
            "get_db: Reached dependency logic but token is None despite active user dependency."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (token missing)",
        )

    logger.debug(f"get_db: Configuring request client for user {current_user.email}...")
    auth_header = f"Bearer {token}"
    try:
        if hasattr(request_client, "postgrest") and hasattr(
            request_client.postgrest, "session"
        ):
            request_client.postgrest.session.headers["Authorization"] = auth_header
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
            elif hasattr(request_client.storage._client, "headers"):
                request_client.storage._client.headers["Authorization"] = auth_header
        # else: logger.debug("Storage client or its session not found for header setting.")

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


# logger.info("Auth Dependencies: User validation and authenticated 'get_db' dependency configured.")
