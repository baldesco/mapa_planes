import asyncio
import uuid
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from supabase import Client as SupabaseClient
from pydantic import ValidationError

from app.core.config import settings, logger
from app.models.auth import UserInToken  # Import specific model
from app.db.setup import get_base_supabase_client  # Import base client getter


async def get_token_from_cookie(
    request: Request,
) -> str | None:
    """
    Custom dependency to extract the JWT from the 'access_token' cookie.
    Returns the raw token string or None if not found/malformed.
    """
    token_cookie = request.cookies.get("access_token")
    if not token_cookie:
        logger.debug("get_token_from_cookie: No 'access_token' cookie found.")
        return None

    # Expect "Bearer <token>" format set during login
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
    Raises 401 if token is missing, invalid, or validation fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        logger.info("get_current_user: No valid token provided via cookie.")
        raise credentials_exception

    try:
        logger.debug(
            f"Attempting to validate token from cookie with Supabase: {token[:10]}..."
        )
        # Use the base client instance (anon key) just for this validation call
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

        # Extract necessary info and validate with Pydantic model
        try:
            if not user_data.id or not user_data.email:
                logger.error(
                    f"Token validation error: Supabase user object missing id or email. Data: {user_data}"
                )
                raise credentials_exception

            current_user = UserInToken(id=user_data.id, email=user_data.email)
            logger.debug(f"Token validated successfully for user: {current_user.email}")
            return current_user
        except (ValidationError, AttributeError) as e:
            logger.error(
                f"Token validation error: Could not map Supabase user to UserInToken model. Error: {e}, Data: {user_data}",
                exc_info=True,
            )
            raise credentials_exception

    except Exception as e:
        error_message = getattr(e, "message", str(e))
        if hasattr(e, "details"):
            error_message = f"{error_message} Details: {e.details}"
        if hasattr(e, "status_code"):
            error_message = f"Status {e.status_code}: {error_message}"

        logger.error(
            f"Token validation error via Supabase client: {error_message}",
            exc_info=False,
        )
        # Distinguish common auth errors if possible
        if (
            "invalid JWT" in error_message.lower()
            or "token is expired" in error_message.lower()
            or "Unauthorized" in error_message
            or (hasattr(e, "status_code") and e.status_code == 401)
        ):
            raise credentials_exception
        else:
            logger.error(
                f"Unexpected error during Supabase token validation: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication.",
            ) from e


async def get_current_active_user(
    current_user: UserInToken = Depends(get_current_user),
) -> UserInToken:
    """
    Ensures the user retrieved from the token is valid (currently just checks presence).
    Placeholder for future checks like is_active, etc.
    """
    # Currently, validation happens in get_current_user. This is a pass-through.
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
            logger.debug("get_optional_current_user: No token found in cookie.")
            return None
        # Reuse the main validation dependency, but catch the 401 exception
        current_user = await get_current_user(token=token, base_db=db)
        logger.debug(f"get_optional_current_user: Found user {current_user.email}")
        return current_user
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            logger.debug("get_optional_current_user: Token invalid or expired (401).")
            return None
        # Re-raise unexpected HTTP exceptions
        logger.error(
            f"Unexpected HTTPException in get_optional_current_user: {e.status_code} - {e.detail}",
            exc_info=False,
        )
        raise e
    except Exception as e:
        # Catch any other unexpected errors during optional user retrieval
        logger.error(
            f"Critical unexpected error in get_optional_current_user: {e}",
            exc_info=True,
        )
        # Depending on policy, you might want to return None or raise 500
        # Returning None is safer for endpoints that can work anonymously
        return None
