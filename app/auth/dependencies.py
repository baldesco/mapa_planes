import asyncio
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from supabase import Client as SupabaseClient, AuthApiError
from pydantic import ValidationError

from app.core.config import logger
from app.models.auth import UserInToken
from app.db.setup import get_base_supabase_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_token_from_header(
    token: str | None = Depends(oauth2_scheme),
) -> str | None:
    """Extracts the token from the Authorization header."""
    return token


async def get_token_from_cookie(request: Request) -> str | None:
    """Extracts the JWT from the 'access_token' cookie."""
    token_cookie = request.cookies.get("access_token")
    if not token_cookie:
        return None

    if token_cookie.lower().startswith("bearer "):
        parts = token_cookie.split(maxsplit=1)
        return parts[1] if len(parts) == 2 else None
    return token_cookie


async def get_current_user(
    token: str | None = Depends(get_token_from_cookie),
    base_db: SupabaseClient = Depends(get_base_supabase_client),
) -> UserInToken:
    """Validates the token via Supabase and returns user info."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        # supabase-py is synchronous for auth, so we wrap in a thread
        response = await asyncio.to_thread(base_db.auth.get_user, token)
        user_data = response.user

        if not user_data or not user_data.id:
            raise credentials_exception

        return UserInToken(id=user_data.id, email=user_data.email)

    except AuthApiError as api_error:
        logger.warning(f"Auth validation failed: {api_error.message}")
        raise credentials_exception
    except ValidationError:
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication.",
        )


async def get_current_active_user(
    current_user: UserInToken = Depends(get_current_user),
) -> UserInToken:
    """Ensures the user is valid (placeholder for is_active checks)."""
    return current_user


async def get_optional_current_user(
    request: Request,
    db: SupabaseClient = Depends(get_base_supabase_client),
) -> UserInToken | None:
    """Returns the current user if authenticated, else None."""
    try:
        token = await get_token_from_cookie(request)
        if token is None:
            return None
        return await get_current_user(token=token, base_db=db)
    except HTTPException:
        return None


async def get_db(
    token: str | None = Depends(get_token_from_cookie),
    request_client: SupabaseClient = Depends(get_base_supabase_client),
    current_user: UserInToken = Depends(get_current_active_user),
) -> SupabaseClient:
    """Configures a Supabase client with the user's JWT for RLS access."""
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Set the session on the client to ensure PostgREST/Storage use the user's JWT
        await asyncio.to_thread(
            request_client.auth.set_session, 
            access_token=token, 
            refresh_token=""
        )
    except Exception as e:
        logger.error(f"Error configuring authenticated client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure database client.",
        )

    return request_client


async def get_db_unvalidated(
    request_client: SupabaseClient = Depends(get_base_supabase_client),
) -> SupabaseClient:
    """Provides a base Supabase client without token validation."""
    return request_client