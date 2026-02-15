from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from supabase import AsyncClient, AuthApiError
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
    """
    return token


async def get_token_from_cookie(
    request: Request,
) -> str | None:
    """
    Custom dependency to extract the JWT from the 'access_token' cookie.
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
        return token_cookie


async def get_current_user(
    token: str | None = Depends(get_token_from_cookie),
    base_db: AsyncClient = Depends(get_base_supabase_client),
) -> UserInToken:
    """
    Dependency to validate the token from the cookie via Supabase asynchronously.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        response = await base_db.auth.get_user(token)
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
                f"Token validation error: Mapping failed. Error: {e}, Data: {user_data}",
                exc_info=True,
            )
            raise credentials_exception

    except AuthApiError as api_error:
        logger.warning(
            f"Supabase AuthApiError during token validation: {api_error.message}"
        )
        status_code = getattr(api_error, "status", status.HTTP_401_UNAUTHORIZED)
        if (
            status_code == 401
            or status_code == 403
            or "invalid JWT" in api_error.message.lower()
            or "token is expired" in api_error.message.lower()
            or "session from session_id claim" in api_error.message.lower()
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
    return current_user


async def get_optional_current_user(
    request: Request,
    db: AsyncClient = Depends(get_base_supabase_client),
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
            f"Unexpected HTTPException in get_optional_current_user: {e.status_code} - {e.detail}"
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
    request_client: AsyncClient = Depends(get_base_supabase_client),
    current_user: UserInToken = Depends(get_current_active_user),
) -> AsyncClient:
    """
    Provides an Async Supabase client configured with the user's JWT
    for RLS-enabled API calls.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (token missing)",
        )

    try:
        # Standard v2 way to configure auth for PostgREST sub-client
        request_client.postgrest.auth(token)

        # Update headers for Storage sub-client (v2 uses internal session client)
        if hasattr(request_client.storage, "session"):
            request_client.storage.session.headers.update(
                {"Authorization": f"Bearer {token}"}
            )
        elif hasattr(request_client.storage, "headers"):
            request_client.storage.headers.update({"Authorization": f"Bearer {token}"})

        # Set the session on the auth sub-client for scoped calls
        await request_client.auth.set_session(access_token=token, refresh_token="")

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


async def get_db_unvalidated(
    request_client: AsyncClient = Depends(get_base_supabase_client),
) -> AsyncClient:
    """
    Provides a base Supabase client without performing any token validation.
    """
    return request_client