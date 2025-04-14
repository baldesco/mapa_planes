import asyncio
from fastapi import HTTPException, status, Request
from supabase import Client as SupabaseClient
from urllib.parse import urljoin

from gotrue.errors import AuthApiError

from app.core.config import logger
from app.models.auth import UserCreate, SupabaseUser


async def create_supabase_user(
    user_data: UserCreate, db: SupabaseClient
) -> SupabaseUser | None:
    """Registers a new user using Supabase Auth."""
    try:
        logger.info(f"Attempting to sign up user: {user_data.email}")
        response = await asyncio.to_thread(
            db.auth.sign_up,
            {
                "email": user_data.email,
                "password": user_data.password,
            },
        )

        if response and response.user and response.user.id:
            logger.info(
                f"Successfully initiated sign up for user: {response.user.email} (ID: {response.user.id}). Confirmation may be required."
            )
            try:
                # Map only necessary fields
                supabase_user = SupabaseUser(
                    id=response.user.id,
                    aud=response.user.aud,
                    role=response.user.role,
                    email=response.user.email,
                )
                return supabase_user
            except Exception as pydantic_error:
                logger.error(
                    f"Error mapping Supabase user response to Pydantic model: {pydantic_error}",
                    exc_info=True,
                )
                return None
        elif response and response.user and not response.user.id:
            logger.warning(
                f"Supabase sign_up response indicates user might exist or requires confirmation for email {user_data.email}."
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists or requires confirmation.",
            )
        else:
            error_detail = "Unknown error during sign up."
            logger.error(
                f"Unexpected Supabase sign_up response for {user_data.email}: {response}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
            )

    except HTTPException as http_exc:
        # Re-raise known HTTP exceptions
        logger.warning(
            f"HTTP Exception during user sign up for {user_data.email}: {http_exc.detail}"
        )
        raise http_exc
    except AuthApiError as api_error:
        # Handle specific Supabase API errors
        err_msg = getattr(api_error, "message", str(api_error))
        status_code = getattr(api_error, "status", 500)
        logger.error(
            f"Supabase AuthApiError during sign up for {user_data.email}: {status_code} - {err_msg}",
            exc_info=False,
        )
        detail = "Could not create user."
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "Password requires" in err_msg:
            detail = "Password does not meet requirements."
            http_status = status.HTTP_400_BAD_REQUEST
        elif "User already registered" in err_msg:
            detail = "Email already registered."
            http_status = status.HTTP_409_CONFLICT
        elif status_code == 429:
            detail = "Too many signup attempts. Please try again later."
            http_status = status.HTTP_429_TOO_MANY_REQUESTS
        raise HTTPException(status_code=http_status, detail=detail) from api_error
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            f"Unexpected error during Supabase user sign up for {user_data.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during signup.",
        ) from e


async def initiate_supabase_password_reset(
    email: str, db: SupabaseClient, request: Request
) -> bool:
    """Initiates a password reset request via Supabase Auth."""
    try:
        base_url = str(request.base_url)
        reset_url_object = request.url_for("serve_reset_password_page")
        reset_path_str = str(reset_url_object.path)
        redirect_url = urljoin(base_url.rstrip("/") + "/", reset_path_str.lstrip("/"))
        logger.info(f"Password reset: Explicit redirect URL set to: {redirect_url}")

        logger.info(f"Initiating password reset for: {email}")
        await asyncio.to_thread(
            db.auth.reset_password_email, email, options={"redirect_to": redirect_url}
        )
        logger.info(
            f"Password reset email request sent successfully for: {email} (if user exists)."
        )
        # Supabase returns 200 OK even if the user doesn't exist for security
        return True
    except AuthApiError as api_error:
        # Log API errors but don't expose details that reveal user existence
        err_msg = getattr(api_error, "message", str(api_error))
        status_code = getattr(api_error, "status", 500)
        logger.error(
            f"Supabase AuthApiError initiating password reset for {email}: {status_code} - {err_msg}",
            exc_info=False,
        )
        # Do not raise HTTPException here, always return True-like to the caller for security
        return False  # Indicate potential failure internally if needed
    except Exception as e:
        logger.error(
            f"Unexpected error initiating Supabase password reset for {email}: {e}",
            exc_info=True,
        )
        return False
