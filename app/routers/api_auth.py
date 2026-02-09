import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from supabase import Client as SupabaseClient, AuthApiError
from datetime import datetime, timezone, timedelta

from app.core.config import settings, logger
from app.models.auth import Token, UserCreate, UserInToken, PasswordResetRequest
from app.models.general import Msg
from app.db.setup import get_base_supabase_client
from app.auth.dependencies import (
    get_current_active_user,
    get_db,
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
        logger.info(f"API Login successful for user: {form_data.username}")
        return Token(access_token=access_token, token_type="bearer")
    except AuthApiError as api_error:
        err_msg = getattr(api_error, "message", str(api_error))
        status_code = getattr(api_error, "status", 401)
        detail = "Incorrect email or password"
        logger.error(
            f"API Login AuthApiError for {form_data.username}: {status_code} - {err_msg}",
            exc_info=False,
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
            status_code=status_code
            if isinstance(status_code, int)
            else status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from api_error
    except Exception as e:
        logger.error(
            f"Unexpected general error during API login for {form_data.username}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during login.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/signup", response_model=Msg, status_code=status.HTTP_201_CREATED)
async def signup_user(
    user_in: UserCreate,
    db: SupabaseClient = Depends(get_base_supabase_client),
):
    """Handles new user registration via API."""
    logger.info(f"API Signup attempt for email: {user_in.email}")
    await auth_utils.create_supabase_user(user_in, db=db)
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
    except AuthApiError as api_error:
        status_code = getattr(api_error, "status", None)
        if status_code == 401:
            logger.warning(
                f"Supabase sign_out failed (401), likely token already invalid for {current_user.email}."
            )
        else:
            logger.error(
                f"Error during Supabase sign_out call for {current_user.email}: {api_error.status} - {api_error.message}",
                exc_info=False,
            )
    except Exception as e:
        logger.error(
            f"Unexpected error during Supabase sign_out call for {current_user.email}: {e}",
            exc_info=True,
        )

    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=settings.APP_ENV != "development",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserInToken)
async def read_users_me(
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Returns the basic information of the currently authenticated user via API."""
    return current_user