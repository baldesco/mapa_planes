import asyncio
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from urllib.parse import urlencode
from supabase import Client as SupabaseClient, AuthApiError

from app.auth.dependencies import get_token_from_cookie
from app.db.setup import get_base_supabase_client
from app.core.config import logger, settings
from app.models.auth import UserInToken


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware to handle authentication checks for protected page routes.
        API routes starting with /api/ are skipped as they are handled by 
        dependencies in the routers.
        """
        request_path = request.url.path

        public_paths = [
            "/login",
            "/signup",
            "/request-password-reset",
            "/reset-password",
            "/static",
            "/docs",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        ]
        
        is_public = any(request_path.startswith(p) for p in public_paths)
        is_api = request_path.startswith("/api")

        # Allow public paths and API calls to proceed to their respective handlers
        if is_public or is_api:
            return await call_next(request)

        # Protect all other page routes (e.g., the dashboard)
        token = await get_token_from_cookie(request)
        should_redirect = False
        clear_cookie = False

        if token:
            try:
                db_client = get_base_supabase_client()
                # Unified auth check using the official supabase client
                auth_response = await asyncio.to_thread(
                    db_client.auth.get_user, token
                )

                if auth_response.user and auth_response.user.id:
                    # Token is valid, attach user to request state
                    request.state.user = UserInToken(
                        id=auth_response.user.id, 
                        email=auth_response.user.email
                    )
                else:
                    should_redirect = True
                    clear_cookie = True

            except AuthApiError:
                # Specifically catch Supabase Auth errors (expired, invalid, etc.)
                should_redirect = True
                clear_cookie = True
            except Exception as e:
                logger.error(f"Middleware: Unexpected auth error: {e}")
                should_redirect = True
        else:
            should_redirect = True

        if should_redirect:
            login_url = request.url_for("serve_login_page")
            query_params = urlencode({"reason": "session_expired"})
            response = RedirectResponse(
                url=f"{login_url}?{query_params}", 
                status_code=status.HTTP_303_SEE_OTHER
            )
            if clear_cookie:
                response.delete_cookie(
                    "access_token",
                    path="/",
                    httponly=True,
                    samesite="Lax",
                    secure=settings.APP_ENV != "development",
                )
            return response

        return await call_next(request)