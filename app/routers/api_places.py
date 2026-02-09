from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import List, Optional
from supabase import Client as SupabaseClient
import uuid

from app.crud import places as crud_places
from app.models import places as models_places
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.db.setup import get_supabase_service_client
from app.core.config import logger

router = APIRouter(prefix="/api/v1/places", tags=["API - Places"])


@router.post(
    "/", response_model=models_places.Place, status_code=status.HTTP_201_CREATED
)
async def create_new_place_api(
    place_in: models_places.PlaceCreate,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """
    Creates a new place and returns the full object including nested relations.
    Used by addPlaceForm.js for SPA-lite updates.
    """
    logger.info(f"API: Creating place '{place_in.name}' for {current_user.email}")
    
    created_place_db = await crud_places.create_place(
        place=place_in, user_id=current_user.id, db=db
    )
    
    if not created_place_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create place. Check data constraints or RLS."
        )

    # Fetch full place to include empty visits/tags arrays for the frontend state
    full_place = await crud_places.get_place_by_id(
        place_id=created_place_db.id, user_id=current_user.id, db=db
    )
    return full_place


@router.get("/", response_model=List[models_places.Place])
async def list_places_api(
    category: Optional[models_places.PlaceCategory] = Query(None),
    status_filter: Optional[models_places.PlaceStatus] = Query(None, alias="status"),
    tags: Optional[str] = Query(None, description="Comma-separated tag names"),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """
    Returns a list of places. 
    While the frontend now filters client-side, this remains for initial state sync.
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    places = await crud_places.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        tag_names=tag_list,
        limit=1000
    )
    return places


@router.get("/{place_id}", response_model=models_places.Place)
async def get_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Fetches a single place with all its metadata and visits."""
    place = await crud_places.get_place_by_id(
        place_id=place_id, user_id=current_user.id, db=db
    )
    if not place:
        raise HTTPException(status_code=404, detail="Place not found.")
    return place


@router.put("/{place_id}", response_model=models_places.Place)
async def update_place_api(
    place_id: int,
    place_update: models_places.PlaceUpdate,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """
    Updates place details (including tags).
    Returns the updated object to allow the frontend to update its local store.
    """
    logger.info(f"API: Updating place {place_id} for {current_user.email}")
    
    updated_place = await crud_places.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db
    )
    
    if not updated_place:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Place not found or update failed."
        )
    return updated_place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place_api(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """
    Performs a soft-delete on a place and handles image cleanup via service role.
    Frontend uses the 204 response to remove the item from local state.
    """
    logger.warning(f"API: Deleting place {place_id} for {current_user.email}")
    
    success = await crud_places.delete_place(
        place_id=place_id, 
        user_id=current_user.id, 
        db=db, 
        db_service=db_service
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete place."
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)