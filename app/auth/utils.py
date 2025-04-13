import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Request
from supabase import Client as SupabaseClient
from urllib.parse import urljoin

# Import the specific error
from gotrue.errors import (
    AuthApiError,
    AuthSessionMissingError,
    AuthInvalidCredentialsError,
)

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
            logger.error(
                f"Unexpected Supabase sign_up response for {user_data.email}: {response}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
            )

    except HTTPException as http_exc:
        logger.warning(
            f"HTTP Exception during user sign up for {user_data.email}: {http_exc.detail}"
        )
        raise http_exc
    except AuthApiError as api_error:
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
    """Initiates a password reset request via Supabase Auth, specifying the redirect URL."""
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
        return True
    except AuthApiError as api_error:
        err_msg = getattr(api_error, "message", str(api_error))
        status_code = getattr(api_error, "status", 500)
        logger.error(
            f"Supabase AuthApiError initiating password reset for {email}: {status_code} - {err_msg}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error initiating Supabase password reset for {email}: {e}",
            exc_info=True,
        )
        return False


# REMOVED confirm_supabase_password_reset function as it's replaced


async def verify_recovery_and_update_password(
    recovery_token: str,
    recovery_type: str,
    new_password: str,
    db: SupabaseClient,  # Use the base client instance
) -> bool:
    """
    Verifies the recovery token using verify_otp and updates the password
    using the new session token obtained from successful verification.
    """
    if not recovery_token or not recovery_type:
        logger.error("verify_recovery: Missing token or type.")
        return False

    try:
        logger.info(f"Attempting to verify OTP/recovery token (type: {recovery_type}).")
        # Verify the token using verify_otp
        # Note: Email is often required for types other than 'recovery', but let's try without first.
        # If it fails requiring email, we'll need to add email to the reset form.
        verify_payload = {"token": recovery_token, "type": recovery_type}
        session_response = await asyncio.to_thread(db.auth.verify_otp, verify_payload)

        if (
            not session_response
            or not session_response.session
            or not session_response.user
        ):
            logger.error(
                f"verify_otp failed or returned invalid session. Response: {session_response}"
            )
            return False

        new_access_token = session_response.session.access_token
        user_email = session_response.user.email
        logger.info(f"Recovery token verified successfully for user: {user_email}")

        # Now update the password using the *new* access token from the verified session
        logger.info(
            f"Attempting password update for {user_email} using verified session token."
        )
        update_response = await asyncio.to_thread(
            db.auth.update_user,
            attributes={"password": new_password},
            jwt=new_access_token,  # Pass the NEW token explicitly
        )

        if update_response and update_response.user:
            logger.info(
                f"Password successfully updated for user: {update_response.user.email}"
            )
            return True
        else:
            log_response = str(update_response)[:200] if update_response else "None"
            logger.error(
                f"Password update failed after token verification. Unexpected update response: {log_response}"
            )
            return False

    except (AuthInvalidCredentialsError, AuthApiError) as api_err:
        # Catch specific errors from verify_otp or update_user
        err_msg = getattr(api_err, "message", str(api_err))
        status_code = getattr(api_err, "status", 500)
        if (
            "Token has expired or is invalid" in err_msg
            or status_code == 401
            or status_code == 403
        ):
            logger.warning(
                f"Recovery token verification failed: {status_code} - {err_msg}"
            )
        elif "Password requires" in err_msg or "weak password" in err_msg.lower():
            logger.warning(
                f"Password update failed (weak password): {status_code} - {err_msg}"
            )
        else:
            logger.error(
                f"Supabase API Error during recovery/update: {status_code} - {err_msg}",
                exc_info=False,
            )
        return False
    except Exception as e:
        # Catch other unexpected errors
        logger.error(
            f"Unexpected error during recovery verification or password update: {e}",
            exc_info=True,
        )
        return False
