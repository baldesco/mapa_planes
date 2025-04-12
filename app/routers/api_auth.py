# File: /app/routers/api_auth.py
# Final Version: Use get_db_with_header_token, remove debug logs

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from supabase import Client as SupabaseClient
from datetime import datetime, timezone, timedelta

from app.core.config import settings, logger
from app.models.auth import Token, UserCreate, UserInToken, PasswordResetRequest
from app.models.general import Msg
from app.db.setup import get_base_supabase_client
from app.auth.dependencies import (
    get_current_active_user,
    get_db,
    get_db_with_header_token,  # Use this dependency again
)
from app.auth import utils as auth_utils


router = APIRouter(prefix="/api/v1/auth", tags=["API - Authentication"])


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: SupabaseClient = Depends(get_base_supabase_client),
):
    """Handles user login via API, sets HttpOnly cookie with token."""
    logger.info(f"API Login attempt for user: {form_data.username}")
    try:
        auth_response = await asyncio.to_thread(
            db.auth.sign_in_with_password,
            {"email": form_data.username, "password": form_data.password},
        )
        if (
            not auth_response
            or not auth_response.session
            or not auth_response.session.access_token
        ):
            logger.warning(
                f"API Login failed for {form_data.username}: No session or token in response."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        access_token = auth_response.session.access_token
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="Lax",
            secure=settings.APP_ENV != "development",
            path="/",
        )
        logger.info(
            f"API Login successful for {form_data.username}, token set in cookie."
        )
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        status_code = status.HTTP_401_UNAUTHORIZED
        detail = "Incorrect email or password"
        logger.error(
            f"API Login error for {form_data.username}: {err_msg}", exc_info=False
        )
        if "Invalid login credentials" in err_msg:
            pass
        elif "Email not confirmed" in err_msg:
            detail = "Email not confirmed. Please check your inbox."
        elif "User not found" in err_msg:
            pass
        else:
            logger.error(
                f"Unexpected API login error for {form_data.username}", exc_info=True
            )
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            detail = "An internal error occurred during login."
        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/signup", response_model=Msg, status_code=status.HTTP_201_CREATED)
async def signup_user(
    user_in: UserCreate,
    db: SupabaseClient = Depends(get_base_supabase_client),
):
    """Handles new user registration via API."""
    logger.info(f"API Signup attempt for email: {user_in.email}")
    await auth_utils.create_supabase_user(user_data=user_in, db=db)
    return Msg(
        message="Signup successful. Please check your email for a confirmation link if required."
    )


@router.post("/request-password-reset", response_model=Msg)
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: SupabaseClient = Depends(get_base_supabase_client),
):
    """Initiates the password reset flow via API."""
    logger.info(f"API Password reset request for: {reset_data.email}")
    await auth_utils.initiate_supabase_password_reset(
        email=reset_data.email, db=db, request=request
    )
    return Msg(
        message="If an account exists for this email, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=Msg)
async def reset_password(
    request: Request,
    new_password: str = Form(..., min_length=8),
    db: SupabaseClient = Depends(get_db_with_header_token),
):
    """
    Sets a new password using the temporary session token provided in the
    Authorization header (obtained after clicking the email reset link).
    """
    user_email = "unknown"
    if hasattr(request.state, "user") and request.state.user:
        user_email = request.state.user.email

    logger.warning(
        f"API Attempting password update for user {user_email} via recovery flow (using header token)."
    )

    success = await auth_utils.confirm_supabase_password_reset(
        access_token="",  # Not used by the function anymore
        new_password=new_password,
        db=db,  # Pass the authenticated client
    )

    if success:
        logger.info(f"API Password successfully updated for user: {user_email}")
        return Msg(message="Password updated successfully.")
    else:
        logger.error(f"API Password update failed for user {user_email}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password update failed. The reset link may have expired, the password might not meet requirements, or the request was invalid.",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth_db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Logs the current user out via API by calling Supabase sign_out and clearing the cookie."""
    logger.info(f"API Logout request for user: {current_user.email}")
    try:
        await asyncio.to_thread(auth_db.auth.sign_out)
        logger.info(
            f"Supabase sign_out API call completed successfully for user: {current_user.email}"
        )
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        status_code = getattr(e, "status", None) or getattr(e, "status_code", None)
        if status_code == 401:
            logger.warning(
                f"Supabase sign_out failed (401), likely token already invalid for {current_user.email}. Proceeding with cookie clear."
            )
        else:
            logger.error(
                f"Error during Supabase sign_out call for {current_user.email}: {err_msg}",
                exc_info=True,
            )

    logger.info(f"Attempting to delete access_token cookie for {current_user.email}")
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=settings.APP_ENV != "development",
    )
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    expires_formatted = past_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    secure_flag = "; Secure" if settings.APP_ENV != "development" else ""
    manual_cookie_header = f"access_token=deleted; Path=/; Max-Age=0; Expires={expires_formatted}; HttpOnly; SameSite=Lax{secure_flag}"
    response.headers.append("Set-Cookie", manual_cookie_header)

    logger.info(
        f"Access token cookie cleared instruction sent for user: {current_user.email}"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserInToken)
async def read_users_me(
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Returns the basic information of the currently authenticated user via API."""
    return current_user
