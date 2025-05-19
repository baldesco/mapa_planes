from fastapi import (
    APIRouter,
    Depends,
    Request,
    Query,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
from supabase import Client as SupabaseClient
import json

from app.core.config import logger, settings
from app.models import places as models_places
from app.models import tags as models_tags
from app.models.auth import UserInToken
from app.crud import places as crud_places
from app.crud import tags as crud_tags
from app.auth.dependencies import (
    get_current_active_user,
    get_optional_current_user,
    get_db,
)
from app.services.mapping import generate_map_html

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse, name="serve_root_page")
async def serve_root_page(
    request: Request,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    category_str: Optional[str] = Query(None, alias="category"),
    status_str: Optional[str] = Query(None, alias="status"),
    tags_str: Optional[str] = Query(None, alias="tags"),
):
    logger.info(
        f"Request root page for user {current_user.email}. Filters: category='{category_str}', status='{status_str}', tags='{tags_str}'"
    )

    category: Optional[models_places.PlaceCategory] = None
    if category_str:
        try:
            category = models_places.PlaceCategory(category_str)
        except ValueError:
            category_str = None  # Reset for context if invalid

    status_filter: Optional[models_places.PlaceStatus] = None
    if status_str:
        try:
            status_filter = models_places.PlaceStatus(status_str)
        except ValueError:
            status_str = None  # Reset for context if invalid

    current_tags_filter: List[str] = (
        [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()]
        if tags_str
        else []
    )

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places_list: List[models_places.Place] = []
    all_user_tags_for_js: List[Dict[str, Any]] = []

    try:
        all_user_tags_db = await crud_tags.get_tags_for_user(
            db=db, user_id=current_user.id
        )
        all_user_tags_for_js = [tag.model_dump(mode="json") for tag in all_user_tags_db]

        # crud_places.get_places now returns List[models_places.Place]
        # where each Place object contains its list of Visit objects.
        places_list = await crud_places.get_places(
            db=db,
            user_id=current_user.id,
            category=category,
            status_filter=status_filter,
            tag_names=current_tags_filter,
            limit=500,
        )
        logger.info(
            f"Fetched {len(places_list)} places for user {current_user.email} after filtering."
        )

        # generate_map_html will receive places with embedded visits.
        # It will need to be updated in a later phase to utilize this visit data for popups.
        map_html_content = generate_map_html(
            places=places_list,
            request=request,
            category_filter=category,
            status_filter=status_filter,
        )

    except Exception as page_load_error:
        logger.error(
            f"Critical error generating map page: {page_load_error}", exc_info=True
        )
        places_list = []
        all_user_tags_for_js = []

    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places_list,  # places_list now contains Place objects with their visits
        "categories": [c.value for c in models_places.PlaceCategory],
        "statuses": [
            s.value for s in models_places.PlaceStatus
        ],  # This enum is already updated
        "all_user_tags_json": json.dumps(all_user_tags_for_js),
        "current_category": category_str or None,
        "current_status": status_str or None,
        "current_tags_filter": current_tags_filter,
        "user_email": current_user.email,
    }
    return templates.TemplateResponse("index.html", context)


@router.get("/login", response_class=HTMLResponse, name="serve_login_page")
async def serve_login_page(
    request: Request,
    reason: Optional[str] = Query(None),
    user: UserInToken | None = Depends(get_optional_current_user),
):
    if reason in ["logged_out", "session_expired", "password_reset_success"]:
        return templates.TemplateResponse(
            "login.html", {"request": request, "reason": reason}
        )
    if user:
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse, name="serve_signup_page")
async def serve_signup_page(
    request: Request, user: UserInToken | None = Depends(get_optional_current_user)
):
    if user:
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
    request: Request, user: UserInToken | None = Depends(get_optional_current_user)
):
    if user:
        return RedirectResponse(
            url=request.url_for("serve_root_page"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        "request_password_reset.html", {"request": request}
    )


@router.get(
    "/reset-password", response_class=HTMLResponse, name="serve_reset_password_page"
)
async def serve_reset_password_page(request: Request):
    return templates.TemplateResponse(
        "reset_password.html", {"request": request, "settings": settings}
    )
