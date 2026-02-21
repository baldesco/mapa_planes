from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from supabase import AsyncClient

from app.auth.dependencies import get_current_active_user, get_db
from app.core.config import logger
from app.crud import places as crud_places
from app.db.setup import get_supabase_service_client
from app.models import places as models_places
from app.models.auth import UserInToken

router = APIRouter(prefix="/api/v1/places", tags=["API - Places"])


@router.post(
    "/", response_model=models_places.Place, status_code=status.HTTP_201_CREATED
)
async def create_new_place_api(
    place_in: models_places.PlaceCreate,
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
):
    """
    Creates a new place and returns the fully hydrated object (SPA-Lite ready).
    """
    logger.info(
        f"API Create place request by user {current_user.email}: {place_in.name}"
    )

    # crud_places.create_place now returns a fully hydrated Place object
    created_place = await crud_places.create_place(
        place=place_in, user_id=current_user.id, db=db
    )

    if created_place is None:
        logger.error(
            f"API Create place failed for user {current_user.email}, place name: {place_in.name}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create place. Check data or RLS policies.",
        )

    return created_place


@router.get("/", response_model=list[models_places.Place])
async def list_places_api(
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
    category: Annotated[models_places.PlaceCategory | None, Query()] = None,
    status_filter: Annotated[
        models_places.PlaceStatus | None, Query(alias="status")
    ] = None,
    tags: Annotated[
        str | None, Query(description="Comma-separated list of tag names")
    ] = None,
    q: Annotated[str | None, Query(description="Search query keyword")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    """API endpoint to list hydrated places, including their visits and tags."""
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    logger.info(
        f"API List places request for user {current_user.email}, Filters: cat={category}, status={status_filter}, tags={tag_list}, q={q}"
    )

    places_db = await crud_places.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        tag_names=tag_list,
        search_query=q,
        skip=skip,
        limit=limit,
    )
    return places_db


@router.get("/{place_id}", response_model=models_places.Place)
async def get_place_api(
    place_id: int,
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
):
    """API endpoint to retrieve a specific hydrated place by ID."""
    logger.info(f"API Get place request: ID {place_id} by user {current_user.email}")

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
    place_update: models_places.PlaceUpdate,
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
    db_service: Annotated[
        AsyncClient | None, Depends(get_supabase_service_client)
    ] = None,
):
    """
    Updates an existing place and returns the updated hydrated object (SPA-Lite ready).
    """
    logger.info(
        f"API Update place request: ID {place_id} by user {current_user.email}. Payload tags: {place_update.tags}"
    )

    if place_update.updated_at is None:
        place_update.updated_at = datetime.now(UTC)

    # crud_places.update_place returns the fully hydrated updated object
    updated_place = await crud_places.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db,
        db_service=db_service,
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
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
    db_service: Annotated[
        AsyncClient | None, Depends(get_supabase_service_client)
    ] = None,
):
    """API endpoint to soft delete a place. Cleanup happens in CRUD layer."""
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
