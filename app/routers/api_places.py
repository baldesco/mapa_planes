from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import List, Optional
from datetime import datetime, timezone
from supabase import Client as SupabaseClient
import uuid  # Import uuid

from app.crud import places as crud_places
from app.models import places as models_places
from app.models.auth import UserInToken

# Updated import for get_db
from app.auth.dependencies import get_current_active_user, get_db

# Import service client getter separately
from app.db.setup import get_supabase_service_client
from app.core.config import logger

router = APIRouter(prefix="/api/v1/places", tags=["API - Places"])


@router.get("/", response_model=List[models_places.Place])
async def list_places_api(
    category: Optional[models_places.PlaceCategory] = Query(None),
    status_filter: Optional[models_places.PlaceStatus] = Query(None, alias="status"),
    tags: Optional[str] = Query(
        None, description="Comma-separated list of tag names to filter by (match any)."
    ),  # Add tags filter
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to list places for the authenticated user, with optional filters including tags."""
    tag_list: Optional[List[str]] = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    logger.info(
        f"API List request for user {current_user.email}, Filters: cat={category}, status={status_filter}, tags={tag_list}, skip={skip}, limit={limit}"
    )
    places_db = await crud_places.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        tag_names=tag_list,  # Pass tag list to CRUD function
        skip=skip,
        limit=limit,
        include_deleted=False,
    )
    # The Place model now includes tags, so the response model handles it
    return places_db


@router.get("/{place_id}", response_model=models_places.Place)
async def get_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to retrieve a specific place by ID for the authenticated user."""
    logger.info(f"API Get place request: ID {place_id} by user {current_user.email}")
    db_place = await crud_places.get_place_by_id(
        place_id=place_id, user_id=current_user.id, db=db, include_deleted=False
    )
    if db_place is None:
        logger.warning(
            f"API Get place failed: Place ID {place_id} not found or not accessible by user {current_user.email}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or access denied",
        )
    # The Place model now includes tags, so the response model handles it
    return db_place


@router.put("/{place_id}", response_model=models_places.Place)
async def update_place_api(
    place_id: int,
    place_update: models_places.PlaceUpdate,  # This model now includes Optional[List[str]] for tags
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """API endpoint to update an existing place by ID for the authenticated user."""
    logger.info(
        f"API Update place request: ID {place_id} by user {current_user.email}. Payload tags: {place_update.tags}"
    )
    # Ensure updated_at is set if not provided in payload
    if place_update.updated_at is None:
        place_update.updated_at = datetime.now(timezone.utc)

    # The crud_places.update_place function now handles tag updates internally
    updated_place = await crud_places.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db,
        db_service=db_service,
    )
    if updated_place is None:
        # Check if the place exists at all for this user (even deleted) to give better error
        existing = await crud_places.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        detail = "Place not found or access denied."
        status_code = status.HTTP_404_NOT_FOUND
        if existing:
            detail = "Could not update place (it might be deleted or another issue occurred)."
            status_code = status.HTTP_400_BAD_REQUEST
            logger.error(
                f"API Update failed for existing place ID {place_id}, user {current_user.email}."
            )
        else:
            logger.warning(
                f"API Update failed: Place ID {place_id} not found for user {current_user.email}."
            )
        raise HTTPException(status_code=status_code, detail=detail)

    logger.info(
        f"API Place ID {place_id} updated successfully by user {current_user.email}."
    )
    # The Place response model includes tags
    return updated_place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """API endpoint to soft delete a specific place by ID for the authenticated user."""
    # No changes needed here, CASCADE DELETE handles place_tags associations
    logger.warning(
        f"API Soft Delete place request: ID {place_id} by user {current_user.email}"
    )
    success = await crud_places.delete_place(
        place_id=place_id, user_id=current_user.id, db=db, db_service=db_service
    )
    if not success:
        # Check if it failed because it doesn't exist or was already deleted
        existing = await crud_places.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        status_code = status.HTTP_404_NOT_FOUND
        detail = "Place not found or access denied."
        if existing and existing.deleted_at:
            logger.info(
                f"API Delete failed because place ID {place_id} was already deleted by user {current_user.email}."
            )
            detail = "Place already deleted."
        elif existing:
            logger.error(
                f"API Delete failed unexpectedly for existing place ID {place_id}, user {current_user.email}."
            )
            status_code = status.HTTP_400_BAD_REQUEST
            detail = "Place deletion failed."
        else:
            logger.warning(
                f"API Delete failed: Place ID {place_id} not found for user {current_user.email}."
            )
        raise HTTPException(status_code=status_code, detail=detail)

    # If successful, return No Content
    return Response(status_code=status.HTTP_204_NO_CONTENT)
