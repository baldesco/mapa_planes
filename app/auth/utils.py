import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Request
from supabase import Client as SupabaseClient
from urllib.parse import urljoin

# Import the specific error
from gotrue.errors import AuthApiError, AuthSessionMissingError

from app.core.config import settings, logger
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
                f"Supabase sign_up response indicates user might exist or other issue for email {user_data.email}. Response: {response}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists or requires confirmation.",
            )
        else:
            error_detail = "Unknown error during sign up."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
            )

    except HTTPException as http_exc:
        logger.warning(
            f"HTTP Exception during user sign up for {user_data.email}: {http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        logger.error(
            f"Error during Supabase user sign up for {user_data.email}: {err_msg}",
            exc_info=True,
        )
        detail = "Could not create user."
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "Password requires" in err_msg:
            detail = "Password does not meet requirements."
            status_code = status.HTTP_400_BAD_REQUEST
        elif "User already registered" in err_msg:
            detail = "Email already registered."
            status_code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=detail) from e


async def initiate_supabase_password_reset(
    email: str, db: SupabaseClient, request: Request
) -> bool:
    """Initiates a password reset request via Supabase Auth, specifying the redirect URL."""
    try:
        base_url = str(request.base_url)
        reset_url_object = request.url_for("serve_reset_password_page")
        reset_path_str = str(reset_url_object.path)
        redirect_url = urljoin(base_url, reset_path_str)
        logger.info(f"Password reset: Explicit redirect URL set to: {redirect_url}")

        logger.info(f"Initiating password reset for: {email}")
        await asyncio.to_thread(
            db.auth.reset_password_email, email, options={"redirect_to": redirect_url}
        )
        logger.info(
            f"Password reset email request sent successfully for: {email} (if user exists)."
        )
        return True
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        logger.error(
            f"Error initiating Supabase password reset for {email}: {err_msg}",
            exc_info=True,
        )
        return False


async def confirm_supabase_password_reset(
    access_token: str,  # Keep parameter for consistency, but it's not used
    new_password: str,
    db: SupabaseClient,  # Expect the *authenticated* client
) -> bool:
    """
    Confirms a password reset using the user's session token (obtained after clicking email link)
    and sets a new password via Supabase Auth.
    NOTE: This function assumes the `db` client is already authenticated with the
    session token obtained from the password recovery flow. The endpoint calling this
    needs to ensure that authentication state via the dependency.
    """
    try:
        logger.info("Attempting to update password using recovery session token.")
        # The db client passed here MUST be authenticated with the recovery token
        response = await asyncio.to_thread(
            db.auth.update_user,
            attributes={"password": new_password},
            # No jwt parameter here
        )

        if response and response.user:
            logger.info(
                f"Password successfully updated for user: {response.user.email}"
            )
            return True
        else:
            log_response = str(response)[:200] if response else "None"
            logger.error(
                f"Failed to update password using token. Response: {log_response}"
            )
            return False
    except AuthSessionMissingError as session_err:
        # Catch the specific error we've been seeing
        logger.critical(
            f"AuthSessionMissingError occurred during update_user: {session_err}",
            exc_info=True,
        )
        return False
    except AuthApiError as api_err:
        # Catch other potential API errors from Supabase
        logger.error(
            f"Supabase API Error during password update: {api_err.status} - {api_err.message}",
            exc_info=False,
        )
        return False
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        logger.error(
            f"Error confirming Supabase password reset: {err_msg}", exc_info=True
        )
        return False
