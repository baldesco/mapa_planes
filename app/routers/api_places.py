from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import List, Optional
from datetime import datetime, timezone
from supabase import Client as SupabaseClient
import uuid

from app.crud import places as crud_places
from app.models import places as models_places
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.db.setup import get_supabase_service_client  # Kept for delete_place
from app.core.config import logger

router = APIRouter(prefix="/api/v1/places", tags=["API - Places"])


@router.post(
    "/", response_model=models_places.Place, status_code=status.HTTP_201_CREATED
)
async def create_new_place_api(
    place_in: models_places.PlaceCreate,  # PlaceCreate no longer has image_url, rating, review
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to create a new place for the authenticated user."""
    logger.info(
        f"API Create place request by user {current_user.email}: {place_in.name}"
    )
    created_place_in_db = await crud_places.create_place(
        place=place_in, user_id=current_user.id, db=db
    )
    if created_place_in_db is None:
        logger.error(
            f"API Create place failed for user {current_user.email}, place name: {place_in.name}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create place. Check data or RLS policies.",
        )
    # Fetch the full Place object which includes empty visits list by default
    full_created_place = await crud_places.get_place_by_id(
        place_id=created_place_in_db.id, user_id=current_user.id, db=db
    )
    if not full_created_place:  # Should not happen if creation succeeded
        # This case indicates an issue with get_place_by_id or data consistency
        logger.error(
            f"API Create place: Failed to retrieve place {created_place_in_db.id} after creation."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created place.",
        )
    return full_created_place


@router.get("/", response_model=List[models_places.Place])
async def list_places_api(
    category: Optional[models_places.PlaceCategory] = Query(None),
    status_filter: Optional[models_places.PlaceStatus] = Query(None, alias="status"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tag names"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to list places, now including their visits."""
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    logger.info(
        f"API List places request for user {current_user.email}, Filters: cat={category}, status={status_filter}, tags={tag_list}"
    )
    # crud_places.get_places now returns List[Place] which includes visits
    places_db = await crud_places.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        tag_names=tag_list,
        skip=skip,
        limit=limit,
    )
    return places_db


@router.get("/{place_id}", response_model=models_places.Place)
async def get_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to retrieve a specific place by ID, including its visits."""
    logger.info(f"API Get place request: ID {place_id} by user {current_user.email}")
    # crud_places.get_place_by_id now returns Place which includes visits
    db_place = await crud_places.get_place_by_id(
        place_id=place_id, user_id=current_user.id, db=db
    )
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or access denied",
        )
    return db_place


@router.put("/{place_id}", response_model=models_places.Place)
async def update_place_api(
    place_id: int,
    place_update: models_places.PlaceUpdate,  # PlaceUpdate no longer has image_url, rating, review
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(
        get_supabase_service_client
    ),  # Kept for crud_places.update_place if it needs it for other reasons (e.g. future main image deletion)
):
    """API endpoint to update an existing place."""
    logger.info(
        f"API Update place request: ID {place_id} by user {current_user.email}. Payload tags: {place_update.tags}"
    )
    if place_update.updated_at is None:  # Should always be set by client or here
        place_update.updated_at = datetime.now(timezone.utc)

    updated_place = await crud_places.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db,
        db_service=db_service,  # Pass db_service along
    )
    if updated_place is None:
        existing = await crud_places.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        detail = "Place not found or access denied."
        status_code = status.HTTP_404_NOT_FOUND
        if existing:
            detail = "Could not update place (it might be deleted or another issue occurred)."
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail)
    return updated_place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(
        get_supabase_service_client
    ),  # Required by delete_place for visit image cleanup
):
    """API endpoint to soft delete a place. Visits are hard deleted by CASCADE, visit images are attempted to be deleted."""
    logger.warning(
        f"API Soft Delete place request: ID {place_id} by user {current_user.email}"
    )
    success = await crud_places.delete_place(
        place_id=place_id, user_id=current_user.id, db=db, db_service=db_service
    )
    if not success:
        existing = await crud_places.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        status_code = status.HTTP_404_NOT_FOUND
        detail = "Place not found or access denied."
        if existing and existing.deleted_at:
            detail = "Place already deleted."
        elif existing:
            status_code = status.HTTP_400_BAD_REQUEST
            detail = "Place deletion failed."
        raise HTTPException(status_code=status_code, detail=detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
