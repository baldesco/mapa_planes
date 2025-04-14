import asyncio
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from supabase import Client as SupabaseClient
from supabase import AuthApiError
from pydantic import ValidationError

from app.core.config import logger
from app.models.auth import UserInToken
from app.db.setup import get_base_supabase_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_token_from_header(
    token: str | None = Depends(oauth2_scheme),
) -> str | None:
    """
    Dependency to extract the token from the Authorization header.
    Returns the raw token string or None if not found.
    """
    return token


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
        return token_cookie


async def get_current_user(
    token: str | None = Depends(get_token_from_cookie),
    base_db: SupabaseClient = Depends(get_base_supabase_client),
) -> UserInToken:
    """
    Dependency to validate the token from the cookie via Supabase and return user info.
    Raises 401 if token is missing, invalid, or validation fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        response = await asyncio.to_thread(base_db.auth.get_user, token)
        user_data = response.user

        if not user_data or not user_data.id:
            logger.warning(
                "Token validation failed: Supabase get_user returned no user or user ID."
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
            # Log other API errors but raise a generic internal server error
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
    # Placeholder for future checks (e.g., is_active flag)
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
        # Only suppress 401, re-raise others
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
    current_user: UserInToken = Depends(
        get_current_active_user
    ),  # Ensures user is authenticated
) -> SupabaseClient:
    """
    Provides a Supabase client configured with the user's JWT token (from cookie)
    for RLS-enabled API calls. Requires authentication.
    """
    if token is None:
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

        # Set session for auth client as well
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


# Dependency used for password reset where auth relies on implicit Supabase cookie
async def get_db_unvalidated(
    request_client: SupabaseClient = Depends(get_base_supabase_client),
) -> SupabaseClient:
    """
    Provides a base Supabase client without performing any token validation.
    """
    # The Supabase library should pick up the necessary session cookie automatically
    # when db.auth.update_user is called in the endpoint using this client.
    return request_client
