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

from app.core.config import logger
from app.models import places as models_places
from app.models.auth import UserInToken
from app.crud import places as crud_places
from app.db.setup import get_db
from app.auth.dependencies import get_current_active_user, get_optional_current_user
from app.services.mapping import generate_map_html

# Templates directory setup
templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse, name="serve_root_page")
async def serve_root_page(
    request: Request,
    db: Depends(get_db),  # Use the authenticated DB client
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
            category_str = None  # Clear invalid filter for context
    status_filter: Optional[models_places.PlaceStatus] = None
    if status_str:
        try:
            status_filter = models_places.PlaceStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status filter ignored: '{status_str}'.")
            status_str = None  # Clear invalid filter for context

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places = []
    try:
        # Fetch places using CRUD function
        places = await crud_places.get_places(
            db=db,
            user_id=current_user.id,
            category=category,
            status_filter=status_filter,
            limit=500,  # Consider making limit configurable or paginated
            include_deleted=False,
        )
        logger.info(f"Fetched {len(places)} places for user {current_user.email}.")

        # Generate map HTML using the mapping service
        map_html_content = generate_map_html(
            places=places,
            request=request,  # Pass request for URL generation within map
            category_filter=category,
            status_filter=status_filter,
        )

    except Exception as page_load_error:
        logger.error(
            f"Critical error generating map page for user {current_user.email}: {page_load_error}",
            exc_info=True,
        )
        # Use default error message if map generation fails
        map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded due to an internal error.</p>'

    # Prepare context for the template
    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,  # Pass places data if needed elsewhere in template (e.g., list view)
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
    # Use optional user dependency to check if already logged in
    user: UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the login page. Redirects if user is logged in, unless forced."""
    # If specifically redirected from logout or session expired, force show login
    if reason in ["logged_out", "session_expired"]:
        logger.debug(f"Displaying login page due to reason={reason}")
        return templates.TemplateResponse(
            "login.html", {"request": request, "reason": reason}
        )

    # Otherwise, if user is already logged in, redirect to main page
    if user:
        logger.debug(
            f"User {user.email} already logged in, redirecting from /login to /"
        )
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # User not logged in and not forced, show the login template
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
