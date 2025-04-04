"""Utility functions related to authentication and authorization."""

import uuid
import asyncio  # Import asyncio
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from supabase import Client as SupabaseClient

from .core.config import settings, logger

# from .database import (
#     get_supabase_client,
#     get_supabase_service_client,
# )  # Import service client if needed for user management
from . import models


# Password hashing context (using bcrypt)
# Note: Supabase handles password hashing internally, so this might not be
# directly used unless you implement custom password checks outside Supabase.
# Keep it for potential future use or local password logic if needed.
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Password Hashing ---
# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Verifies a plain password against a hashed password."""
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password: str) -> str:
#     """Hashes a plain password."""
#     return pwd_context.hash(password)


# --- User Management Wrappers (using Supabase client) ---


async def create_supabase_user(
    user_data: models.UserCreate, db: SupabaseClient
) -> models.SupabaseUser | None:
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

        # Check response structure - successful sign-up usually returns user info
        if response and response.user and response.user.id:
            logger.info(
                f"Successfully initiated sign up for user: {response.user.email} (ID: {response.user.id}). Confirmation may be required."
            )
            # Map Supabase response to our Pydantic model (or return Supabase object directly)
            # Note: The Supabase client library might return slightly different structures. Adapt as needed.
            # Let's assume the essential fields are present for now.
            try:
                supabase_user = models.SupabaseUser(
                    id=response.user.id,
                    aud=response.user.aud,
                    role=response.user.role,
                    email=response.user.email,
                    # Map other fields if necessary
                )
                return supabase_user
            except Exception as pydantic_error:
                logger.error(
                    f"Error mapping Supabase user response to Pydantic model: {pydantic_error}",
                    exc_info=True,
                )
                # Still might be successful signup, but can't return typed object
                return None  # Or raise an internal error
        elif response and response.user and not response.user.id:
            logger.warning(
                f"Supabase sign_up response indicates user might exist or other issue for email {user_data.email}. Response: {response}"
            )
            # Supabase might return user without ID if email already exists but unconfirmed? Check GoTrue behavior.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists or requires confirmation.",
            )
        else:
            # Check for specific errors if the library provides them
            error_detail = "Unknown error during sign up."
            # This part depends heavily on how the supabase-py library surfaces errors
            # logger.error(f"Failed sign up response: {response}") # Log raw response
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
            )

    except HTTPException as http_exc:
        logger.warning(
            f"HTTP Exception during user sign up for {user_data.email}: {http_exc.detail}"
        )
        raise http_exc  # Re-raise known HTTP exceptions
    except Exception as e:
        # Catch potential API errors or other issues from the Supabase client
        err_msg = getattr(e, "message", str(e))
        logger.error(
            f"Error during Supabase user sign up for {user_data.email}: {err_msg}",
            exc_info=True,
        )
        detail = "Could not create user."
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        # Check for common Supabase errors (e.g., weak password, existing user)
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
        # Run the synchronous call in a separate thread
        await asyncio.to_thread(db.auth.reset_password_email, email)
        # This method often doesn't return detailed success/failure for security reasons
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
        # Don't reveal if email exists or not in error response to client
        # Simply return False or raise a generic error if needed by the endpoint
        return False


async def confirm_supabase_password_reset(
    access_token: str, new_password: str, db: SupabaseClient
) -> bool:
    """Confirms a password reset using the token from the user's session (obtained after clicking email link)
    and sets a new password via Supabase Auth."""
    # THIS FLOW IS TYPICALLY HANDLED BY SUPABASE UI/REDIRECTS.
    # Updating the password programmatically usually requires the user to be logged in
    # OR using a service role key for admin resets.
    # The more common flow for programmatic backend update is:
    # 1. User clicks link, gets redirected to your app with a code/token in URL.
    # 2. Your frontend exchanges this code for a session (token).
    # 3. With this new session token, the user can call an endpoint to update their password.

    # Let's implement the direct update assuming the user *is* authenticated with the reset token
    # This requires the `access_token` provided to `db.auth.update_user` to be the one obtained
    # from the password recovery flow.
    try:
        logger.info("Attempting to update password using recovery token.")
        # Run the synchronous call in a separate thread
        response = await asyncio.to_thread(
            db.auth.update_user,
            {"password": new_password},
            # If update_user needs the token explicitly, it would be passed here,
            # but usually, it relies on the client's set session.
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
        # Check for specific errors like expired token, etc.
        return False
