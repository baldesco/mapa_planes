import asyncio  # Import asyncio
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from urllib.parse import urlencode
from supabase import Client as SupabaseClient

# Import helpers carefully to avoid new circular imports
from app.auth.dependencies import get_token_from_cookie
from app.db.setup import get_base_supabase_client  # Function to create client
from app.core.config import logger, settings


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware to handle authentication checks and redirects for page routes.
        """
        public_paths = [
            "/login",
            "/signup",
            "/static",
            "/docs",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        ]
        protected_page_paths = ["/"]

        request_path = request.url.path
        is_public = any(request_path.startswith(p) for p in public_paths)
        is_api = request_path.startswith("/api")
        is_protected_page = request_path in protected_page_paths

        if is_public or is_api:
            logger.debug(
                f"Middleware: Allowing public/API path {request_path} to proceed."
            )
            response = await call_next(request)
            return response

        if is_protected_page:
            token = await get_token_from_cookie(request)
            user = None
            should_redirect = False
            clear_cookie_on_response = False
            db_client: SupabaseClient | None = None

            if token:
                logger.debug(
                    f"Middleware: Found token for protected path {request_path}. Validating..."
                )
                try:
                    db_client = get_base_supabase_client()  # Get sync client instance
                    try:
                        logger.debug(
                            f"Middleware: Validating token {token[:10]}... via Supabase (sync in thread)"
                        )
                        # --- Use sync client in thread ---
                        auth_response = await asyncio.to_thread(
                            db_client.auth.get_user, token
                        )
                        # ---------------------------------

                        supabase_user_data = auth_response.user
                        if not supabase_user_data or not supabase_user_data.id:
                            logger.warning(
                                "Middleware: Supabase get_user returned no user/id for token."
                            )
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token session",
                            )

                        user = supabase_user_data
                        request.state.user = user  # Optional: make available
                        logger.debug(
                            f"Middleware: Token validated successfully for user {user.email}"
                        )

                    except Exception as validation_exc:
                        logger.warning(
                            f"Middleware: Token validation via Supabase failed: {validation_exc}"
                        )
                        # If Supabase client itself throws auth error (e.g., 401), map it
                        status_code = getattr(
                            validation_exc, "status_code", status.HTTP_401_UNAUTHORIZED
                        )
                        if not isinstance(status_code, int):  # Ensure it's an int
                            status_code = status.HTTP_401_UNAUTHORIZED
                        detail = getattr(
                            validation_exc, "message", "Token validation failed"
                        )
                        raise HTTPException(
                            status_code=status_code, detail=detail
                        ) from validation_exc

                except HTTPException as e:
                    logger.info(
                        f"Middleware: Token validation failed (HTTPException {e.status_code}). Path: {request_path}"
                    )
                    should_redirect = True
                    clear_cookie_on_response = True
                except Exception as e:
                    logger.error(
                        f"Middleware: Unexpected error during token validation for {request_path}: {e}",
                        exc_info=True,
                    )
                    should_redirect = True
                    clear_cookie_on_response = True

            else:
                logger.info(
                    f"Middleware: No token found for protected path {request_path}."
                )
                should_redirect = True

            if should_redirect:
                try:
                    login_url = request.url_for("serve_login_page")
                    query_params = urlencode({"reason": "session_expired"})
                    redirect_url = f"{login_url}?{query_params}"
                    response = RedirectResponse(
                        url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
                    )
                    if token or clear_cookie_on_response:
                        logger.info(
                            f"Middleware: Clearing cookie during redirect for path {request_path}"
                        )
                        response.delete_cookie(
                            "access_token",
                            path="/",
                            httponly=True,
                            samesite="Lax",
                            secure=settings.APP_ENV != "development",
                        )
                    return response
                except Exception as e:
                    logger.error(
                        f"Middleware: Failed to generate login URL for redirect: {e}"
                    )
                    return Response(
                        "Internal Server Error during redirect", status_code=500
                    )

        logger.debug(
            f"Middleware: Allowing request for path {request_path} to proceed."
        )
        response = await call_next(request)

        # This part might be redundant now if redirect clears cookie, but keep for safety?
        # if clear_cookie_on_response and token:
        #      logger.info(f"Middleware: Clearing invalid cookie on outgoing response for path {request_path}")
        #      response.delete_cookie(
        #          "access_token", path="/", httponly=True, samesite="Lax",
        #          secure=settings.APP_ENV != "development"
        #      )

        return response
