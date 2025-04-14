from fastapi import (
    APIRouter,
    Depends,
    Request,
    Query,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any  # Import Dict, Any
from supabase import Client as SupabaseClient
import json  # Import json

from app.core.config import logger, settings
from app.models import places as models_places
from app.models import tags as models_tags  # Import tag models
from app.models.auth import UserInToken
from app.crud import places as crud_places
from app.crud import tags as crud_tags  # Import tag CRUD
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
    tags_str: Optional[str] = Query(None, alias="tags"),  # Add tags query param
):
    """Serves the main HTML page displaying the user's map and places."""
    logger.info(
        f"Request root page for user {current_user.email}. Filters: category='{category_str}', status='{status_str}', tags='{tags_str}'"
    )

    # --- Validate Filters ---
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

    current_tags_filter: List[str] = []
    if tags_str:
        current_tags_filter = [
            tag.strip().lower() for tag in tags_str.split(",") if tag.strip()
        ]
        logger.debug(f"Applying tag filter: {current_tags_filter}")

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places = []
    all_user_tags_for_js: List[Dict[str, Any]] = []  # Initialize for JS data

    try:
        # Fetch all tags for the current user
        all_user_tags_db = await crud_tags.get_tags_for_user(
            db=db, user_id=current_user.id
        )
        logger.info(
            f"Fetched {len(all_user_tags_db)} total tags for user {current_user.email}."
        )
        # ** FIX: Convert TagInDB objects to dicts for JSON serialization **
        all_user_tags_for_js = [tag.model_dump(mode="json") for tag in all_user_tags_db]

        # Fetch places, applying all filters including tags
        places = await crud_places.get_places(
            db=db,
            user_id=current_user.id,
            category=category,
            status_filter=status_filter,
            tag_names=current_tags_filter,
            limit=500,
            include_deleted=False,
        )
        logger.info(
            f"Fetched {len(places)} places for user {current_user.email} after filtering."
        )

        # Generate map HTML
        map_html_content = generate_map_html(
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
        places = []
        all_user_tags_for_js = []  # Ensure it's empty on error

    # Prepare context for the template
    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,
        "categories": [c.value for c in models_places.PlaceCategory],
        "statuses": [s.value for s in models_places.PlaceStatus],
        # Pass the JSON-serializable list of dicts
        "all_user_tags_json": json.dumps(all_user_tags_for_js),
        "current_category": category_str or None,
        "current_status": status_str or None,
        "current_tags_filter": current_tags_filter,
        "user_email": current_user.email,
    }
    return templates.TemplateResponse("index.html", context)


# --- Other page routes remain unchanged ---


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
    # Pass settings needed for Supabase JS client initialization
    return templates.TemplateResponse(
        "reset_password.html", {"request": request, "settings": settings}
    )
