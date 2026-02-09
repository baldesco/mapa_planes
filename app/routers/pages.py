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
from app.models.auth import UserInToken
from app.crud import places as crud_places
from app.crud import tags as crud_tags
from app.auth.dependencies import (
    get_current_active_user,
    get_optional_current_user,
    get_db,
)
from app.services.mapping import prepare_map_data

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse, name="serve_root_page")
async def serve_root_page(
    request: Request,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """
    Serves the main dashboard.
    Initial filters are handled client-side, but we hydrate the page with 
    the full list of places and tags to enable suggestion #1 and #2.
    """
    logger.info(f"Serving dashboard for user: {current_user.email}")

    places_list: List[models_places.Place] = []
    all_user_tags_for_js: List[Dict[str, Any]] = []
    map_data_json = "{}"

    try:
        # Fetch all tags to populate the filter suggestions
        all_user_tags_db = await crud_tags.get_tags_for_user(
            db=db, user_id=current_user.id
        )
        all_user_tags_for_js = [tag.model_dump(mode="json") for tag in all_user_tags_db]

        # Fetch all active places for the initial client-side state
        places_list = await crud_places.get_places(
            db=db,
            user_id=current_user.id,
            limit=1000, # Increased limit as filtering is now client-side
        )
        
        # Prepare data for map and sidebar state
        map_data = prepare_map_data(places=places_list)
        map_data_json = json.dumps(map_data)

    except Exception as e:
        logger.error(f"Error hydrating dashboard: {e}", exc_info=True)

    context = {
        "request": request,
        "map_data_json": map_data_json,
        "places": places_list,
        "categories": [c.value for c in models_places.PlaceCategory],
        "statuses": [s.value for s in models_places.PlaceStatus],
        "all_user_tags_json": json.dumps(all_user_tags_for_js),
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