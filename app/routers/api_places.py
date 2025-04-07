from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import List, Optional
from datetime import datetime, timezone
from supabase import Client as SupabaseClient

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
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: SupabaseClient = Depends(get_db),  # Uses updated get_db import
    current_user: UserInToken = Depends(get_current_active_user),
):
    """API endpoint to list places for the authenticated user, with optional filters."""
    logger.info(
        f"API List request for user {current_user.email}, Filters: cat={category}, status={status_filter}, skip={skip}, limit={limit}"
    )
    places_db = await crud_places.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
        include_deleted=False,  # API typically doesn't show deleted items
    )
    return places_db


@router.get("/{place_id}", response_model=models_places.Place)
async def get_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),  # Uses updated get_db import
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
    return db_place


@router.put("/{place_id}", response_model=models_places.Place)
async def update_place_api(
    place_id: int,
    place_update: models_places.PlaceUpdate,
    db: SupabaseClient = Depends(get_db),  # Uses updated get_db import
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """API endpoint to update an existing place by ID for the authenticated user."""
    logger.info(
        f"API Update place request: ID {place_id} by user {current_user.email}."
    )
    # Ensure updated_at is set if not provided in payload
    if place_update.updated_at is None:
        place_update.updated_at = datetime.now(timezone.utc)

    updated_place = await crud_places.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db,
        db_service=db_service,  # Pass service client for potential image deletion
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
            status_code = (
                status.HTTP_400_BAD_REQUEST
            )  # Or 404 if preferred not to reveal existence
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
    return updated_place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),  # Uses updated get_db import
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """API endpoint to soft delete a specific place by ID for the authenticated user."""
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
            # If already deleted, maybe return 204 still? Or 404/400? Let's stick to 404.
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
