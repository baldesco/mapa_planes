from fastapi import (
    APIRouter,
    Depends,
    Request,
    Query,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from supabase import Client as SupabaseClient

from app.core.config import logger
from app.models import places as models_places
from app.models.auth import UserInToken
from app.crud import places as crud_places
from app.auth.dependencies import (
    get_current_active_user,
    get_optional_current_user,
    get_db,
)

# Renamed function import to reflect change
from app.services.mapping import generate_map_html

# Templates directory setup
templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse, name="serve_root_page")
async def serve_root_page(
    request: Request,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    category_str: Optional[str] = Query(None, alias="category"),
    status_str: Optional[str] = Query(None, alias="status"),
):
    """Serves the main HTML page displaying the user's map and places."""
    logger.info(
        f"Request root page for user {current_user.email}. Filters: category='{category_str}', status='{status_str}'"
    )

    # Validate filters
    category: Optional[models_places.PlaceCategory] = None
    if category_str:
        try:
            category = models_places.PlaceCategory(category_str)
        except ValueError:
            logger.warning(f"Invalid category filter ignored: '{category_str}'.")
            category_str = None
    status_filter: Optional[models_places.PlaceStatus] = None
    if status_str:
        try:
            status_filter = models_places.PlaceStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status filter ignored: '{status_str}'.")
            status_str = None

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places = []
    try:
        places = await crud_places.get_places(
            db=db,
            user_id=current_user.id,
            category=category,
            status_filter=status_filter,
            limit=500,
            include_deleted=False,
        )
        logger.info(f"Fetched {len(places)} places for user {current_user.email}.")

        # Generate map HTML using the service function
        map_html_content = generate_map_html(  # Now only returns HTML
            places=places,
            request=request,
            category_filter=category,
            status_filter=status_filter,
        )

    except Exception as page_load_error:
        logger.error(
            f"Critical error generating map page: {page_load_error}", exc_info=True
        )
        map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded due to an internal error.</p>'

    # Prepare context
    context = {
        "request": request,
        "map_html": map_html_content,
        # Removed map_js_variable_name from context
        "places": places,
        "categories": [c.value for c in models_places.PlaceCategory],
        "statuses": [s.value for s in models_places.PlaceStatus],
        "current_category": category_str or None,
        "current_status": status_str or None,
        "user_email": current_user.email,
    }
    return templates.TemplateResponse("index.html", context)


@router.get("/login", response_class=HTMLResponse, name="serve_login_page")
async def serve_login_page(
    request: Request,
    reason: Optional[str] = Query(None),
    user: UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the login page. Redirects if user is logged in, unless forced."""
    if reason in ["logged_out", "session_expired", "password_reset_success"]:
        logger.debug(f"Displaying login page due to reason={reason}")
        return templates.TemplateResponse(
            "login.html", {"request": request, "reason": reason}
        )

    if user:
        logger.debug(
            f"User {user.email} already logged in, redirecting from /login to /"
        )
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse, name="serve_signup_page")
async def serve_signup_page(
    request: Request,
    user: UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the signup page. Redirects if user is already logged in."""
    if user:
        logger.debug(
            f"User {user.email} already logged in, redirecting from /signup to /"
        )
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get(
    "/request-password-reset",
    response_class=HTMLResponse,
    name="serve_request_password_reset_page",
)
async def serve_request_password_reset_page(
    request: Request,
    user: UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the page to request a password reset email."""
    if user:
        # Redirect logged-in users away from password reset
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        "request_password_reset.html", {"request": request}
    )


@router.get(
    "/reset-password",
    response_class=HTMLResponse,
    name="serve_reset_password_page",
)
async def serve_reset_password_page(request: Request):
    """
    Serves the page where the user enters their new password.
    This page is typically accessed via the link sent by Supabase.
    The token is expected in the URL fragment (#access_token=...) and handled by JS.
    """
    # No need to check for logged-in user here, as this flow uses a temporary token.
    # The JS will handle extracting the token from the URL fragment.
    logger.info("Serving reset password page. JS will handle token extraction.")
    return templates.TemplateResponse("reset_password.html", {"request": request})
