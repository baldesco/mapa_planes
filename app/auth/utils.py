import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from supabase import Client as SupabaseClient

from app.core.config import settings, logger
from app.models.auth import UserCreate, SupabaseUser  # Use specific models


async def create_supabase_user(
    user_data: UserCreate, db: SupabaseClient
) -> SupabaseUser | None:
    """Registers a new user using Supabase Auth."""
    try:
        logger.info(f"Attempting to sign up user: {user_data.email}")
        # Run the synchronous sign_up call in a separate thread
        response = await asyncio.to_thread(
            db.auth.sign_up,
            {
                "email": user_data.email,
                "password": user_data.password,
            },
        )
        logger.debug(f"Supabase sign_up response: {response}")

        if response and response.user and response.user.id:
            logger.info(
                f"Successfully initiated sign up for user: {response.user.email} (ID: {response.user.id}). Confirmation may be required."
            )
            try:
                # Map Supabase response to our Pydantic model
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
                return None  # Signup might be ok, but we can't return typed obj
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


async def initiate_supabase_password_reset(email: str, db: SupabaseClient) -> bool:
    """Initiates a password reset request via Supabase Auth."""
    try:
        logger.info(f"Initiating password reset for: {email}")
        await asyncio.to_thread(db.auth.reset_password_email, email)
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
        # Don't reveal if email exists or not
        return False


async def confirm_supabase_password_reset(
    access_token: str, new_password: str, db: SupabaseClient
) -> bool:
    """
    Confirms a password reset using the user's session token (obtained after clicking email link)
    and sets a new password via Supabase Auth.
    NOTE: This function assumes the `db` client is already authenticated with the
    session token obtained from the password recovery flow. The endpoint calling this
    needs to ensure that authentication state.
    """
    try:
        logger.info("Attempting to update password using recovery session token.")
        # The db client passed here MUST be authenticated with the recovery token
        response = await asyncio.to_thread(
            db.auth.update_user,
            {"password": new_password},
        )

        logger.debug(f"Supabase update_user response for password reset: {response}")
        if response and response.user:
            logger.info(
                f"Password successfully updated for user: {response.user.email}"
            )
            return True
        else:
            logger.error(f"Failed to update password using token. Response: {response}")
            return False
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        logger.error(
            f"Error confirming Supabase password reset: {err_msg}", exc_info=True
        )
        return False
