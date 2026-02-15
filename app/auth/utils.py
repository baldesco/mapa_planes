from supabase import AsyncClient, AuthApiError
from urllib.parse import urljoin
from fastapi import HTTPException, status, Request

from app.core.config import logger
from app.models.auth import UserCreate, SupabaseUser


async def create_supabase_user(
    user_data: UserCreate, db: AsyncClient
) -> SupabaseUser | None:
    """Registers a new user using Supabase Auth asynchronously."""
    try:
        logger.info(f"Attempting to sign up user: {user_data.email}")
        
        # Native async sign_up call in Supabase-py v2
        response = await db.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
            }
        )

        if response and response.user and response.user.id:
            logger.info(
                f"Successfully initiated sign up for user: {response.user.email} (ID: {response.user.id})."
            )
            try:
                return SupabaseUser(
                    id=response.user.id,
                    aud=response.user.aud,
                    role=response.user.role,
                    email=response.user.email,
                )
            except Exception as pydantic_error:
                logger.error(
                    f"Error mapping Supabase user response: {pydantic_error}",
                    exc_info=True,
                )
                return None
        elif response and response.user and not response.user.id:
            logger.warning(
                f"Supabase sign_up response indicates user might exist or requires confirmation for {user_data.email}."
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists or requires confirmation.",
            )
        else:
            logger.error(f"Unexpected Supabase sign_up response for {user_data.email}: {response}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown error during sign up."
            )

    except HTTPException as http_exc:
        raise http_exc
    except AuthApiError as api_error:
        err_msg = api_error.message
        status_code = getattr(api_error, "status", 500)
        logger.error(
            f"Supabase AuthApiError during sign up for {user_data.email}: {status_code} - {err_msg}"
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
        logger.error(
            f"Unexpected error during Supabase user sign up for {user_data.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during signup.",
        ) from e


async def initiate_supabase_password_reset(
    email: str, db: AsyncClient, request: Request
) -> bool:
    """Initiates a password reset request via Supabase Auth asynchronously."""
    try:
        base_url = str(request.base_url)
        reset_url_object = request.url_for("serve_reset_password_page")
        reset_path_str = str(reset_url_object.path)
        redirect_url = urljoin(base_url.rstrip("/") + "/", reset_path_str.lstrip("/"))
        
        logger.info(f"Initiating password reset for: {email} with redirect: {redirect_url}")
        
        # Native async reset_password_email call
        await db.auth.reset_password_email(email, options={"redirect_to": redirect_url})
        
        logger.info(f"Password reset email request sent successfully for: {email}")
        return True
    except AuthApiError as api_error:
        logger.error(
            f"Supabase AuthApiError initiating password reset for {email}: {api_error.message}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error initiating Supabase password reset for {email}: {e}",
            exc_info=True,
        )
        return False