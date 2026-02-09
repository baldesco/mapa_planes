from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    status,
)
from fastapi.responses import RedirectResponse
from typing import Optional, List
from pydantic import ValidationError
from datetime import datetime, timezone
from supabase import Client as SupabaseClient

from app.crud import places as crud_places
from app.models import places as models_places
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.core.config import logger

router = APIRouter(tags=["Forms (Legacy/Fallback)"])

@router.post("/places/", status_code=status.HTTP_303_SEE_OTHER)
async def handle_create_new_place_form(
    request: Request,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    place_status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """
    Handles the legacy Add Place form via standard POST.
    Redirects to root, but the SPA-lite frontend is preferred.
    """
    redirect_url = request.url_for("serve_root_page")
    try:
        place_data = models_places.PlaceCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=place_status_input,
            address=address,
            city=city,
            country=country,
        )
        await crud_places.create_place(
            place=place_data, user_id=current_user.id, db=db
        )
    except (ValidationError, ValueError) as e:
        logger.error(f"Form submission error: {e}")
        
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/places/{place_id}/edit", status_code=status.HTTP_303_SEE_OTHER)
async def handle_edit_place_form(
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    tags_input: str = Form(""),
):
    """Handles legacy Edit Place form submission."""
    redirect_url = request.url_for("serve_root_page")
    tag_list: List[str] = [t.strip() for t in tags_input.split(",") if t.strip()]

    try:
        place_update = models_places.PlaceUpdate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=status_input,
            address=address,
            city=city,
            country=country,
            tags=tag_list
        )

        await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update,
            db=db
        )
    except ValidationError as e:
        logger.error(f"Form update error: {e}")

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/places/{place_id}/delete", status_code=status.HTTP_303_SEE_OTHER)
async def handle_delete_place_form(
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Handles legacy Delete Place confirmation."""
    await crud_places.delete_place(
        place_id=place_id, user_id=current_user.id, db=db
    )
    return RedirectResponse(url=request.url_for("serve_root_page"), status_code=status.HTTP_303_SEE_OTHER)