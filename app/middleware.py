from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from urllib.parse import urlencode
from supabase import AsyncClient

from app.auth.dependencies import get_token_from_cookie
from app.db.setup import get_base_supabase_client
from app.core.config import logger, settings
from app.models.auth import UserInToken


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Middleware to handle authentication checks and redirects for page routes.
        """
        request_path = request.url.path
        # logger.info(f"Middleware Dispatch: Received request for path: {request_path}") # Removed debug log

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
        # Check if the request path starts with any of the public paths
        is_public = any(request_path.startswith(p) for p in public_paths)

        is_api = request_path.startswith("/api")
        # Check if it's a protected page *or* any other non-public, non-API page
        is_protected_or_unknown_page = not is_public and not is_api

        if is_public or is_api:
            # logger.debug(f"Middleware: Allowing public/API path {request_path} to proceed.") # Removed debug log
            response = await call_next(request)
            return response

        # Logic applied to protected or unknown pages
        if is_protected_or_unknown_page:
            # logger.debug(f"Middleware: Checking auth for protected/unknown path {request_path}") # Removed debug log
            token = await get_token_from_cookie(request)
            user: UserInToken | None = None
            should_redirect = False
            clear_cookie_on_response = False
            db_client: AsyncClient | None = None

            if token:
                # logger.debug(f"Middleware: Found token for path {request_path}. Validating...") # Removed debug log
                try:
                    db_client = await get_base_supabase_client()
                    try:
                        # logger.debug(f"Middleware: Validating token {token[:10]}... via Supabase (async)") # Removed debug log
                        auth_response = await db_client.auth.get_user(token)

                        supabase_user_data = auth_response.user
                        if not supabase_user_data or not supabase_user_data.id:
                            logger.warning(
                                "Middleware: Supabase get_user returned no user/id for token."
                            )
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token session",
                            )

                        user = UserInToken(
                            id=supabase_user_data.id, email=supabase_user_data.email
                        )
                        request.state.user = user
                        # logger.debug(f"Middleware: Token validated successfully for user {user.email}") # Removed debug log

                    except Exception as validation_exc:
                        logger.warning(
                            f"Middleware: Token validation via Supabase failed: {validation_exc}"
                        )
                        status_code = getattr(
                            validation_exc, "status", None
                        ) or getattr(validation_exc, "status_code", None)
                        if (
                            not isinstance(status_code, int)
                            or status_code < 100
                            or status_code > 599
                        ):
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
                    clear_cookie_on_response = False

            else:
                logger.info(
                    f"Middleware: No token found for protected/unknown path {request_path}."
                )
                should_redirect = True

            if should_redirect:
                try:
                    login_url = request.url_for("serve_login_page")
                    query_params = urlencode({"reason": "session_expired"})
                    redirect_url = f"{login_url}?{query_params}"
                    # logger.info(f"Middleware: Redirecting to {redirect_url} from path {request_path}") # Removed debug log
                    response = RedirectResponse(
                        url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
                    )
                    if clear_cookie_on_response and token:
                        logger.info(
                            f"Middleware: Clearing invalid cookie during redirect for path {request_path}"
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
                        "Internal Server Error during redirect handling",
                        status_code=500,
                    )

        # logger.debug(f"Middleware: Allowing authenticated or public request for path {request_path} to proceed.") # Removed debug log
        response = await call_next(request)
        return response
