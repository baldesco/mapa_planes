"""Functions for database interactions (CRUD operations), primarily using Supabase."""

import uuid
import os
import asyncio
from datetime import datetime, timezone  # Import timezone
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from supabase import Client as SupabaseClient, create_client
from supabase.lib.client_options import ClientOptions
from postgrest import APIResponse

from .core.config import settings, logger
from .models import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
    PlaceCategory,
)

TABLE_NAME = "places"


async def create_place(place: PlaceCreate, db: SupabaseClient) -> PlaceInDB | None:
    """Creates a new place record in Supabase."""
    logger.info(f"CRUD: Attempting to create place: {place.name}")
    try:
        place_data = place.model_dump()
        now_utc = datetime.now(timezone.utc).isoformat()
        place_data.setdefault("created_at", now_utc)
        place_data.setdefault("updated_at", now_utc)
        place_data["deleted_at"] = None  # Explicitly set to null on creation

        query = db.table(TABLE_NAME).insert(place_data)
        response: APIResponse = await asyncio.to_thread(query.execute)
        logger.debug(f"Supabase insert response data: {response.data}")

        if response.data:
            created_place_data = response.data[0]
            validated_place = PlaceInDB(**created_place_data)
            logger.info(
                f"CRUD: Successfully created and validated place ID {validated_place.id}"
            )
            return validated_place
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", "Unknown error during insert"
            )
            logger.error(f"CRUD: Failed to create place '{place.name}': {error_detail}")
            return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in create_place for '{place.name}': {e}", exc_info=True
        )
        return None


async def get_places(
    db: SupabaseClient,
    category: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,  # Option to include deleted items if needed later
) -> List[PlaceInDB]:
    """Retrieves non-deleted places from Supabase, with filtering and pagination."""
    logger.info(
        f"CRUD: Fetching places. Category: {category}, Status: {status_filter}, Skip: {skip}, Limit: {limit}, IncludeDeleted: {include_deleted}"
    )
    places_validated = []
    try:
        query = db.table(TABLE_NAME).select("*").order("created_at", desc=True)

        # Filter by category and status
        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)

        # --- SOFT DELETE FILTER ---
        if not include_deleted:
            query = query.is_(
                "deleted_at", None
            )  # Only get rows where deleted_at is NULL

        final_query = query.range(skip, skip + limit - 1)
        response: APIResponse = await asyncio.to_thread(final_query.execute)

        if hasattr(response, "data") and response.data:
            logger.debug(
                f"CRUD: Received {len(response.data)} raw place records from Supabase."
            )
            for i, p_data in enumerate(response.data):
                try:
                    validated_place = PlaceInDB(**p_data)
                    places_validated.append(validated_place)
                except Exception as validation_error:
                    logger.error(
                        f"CRUD: Pydantic validation failed for place record #{i + 1}. Data: {p_data}. Error: {validation_error}",
                        exc_info=False,
                    )
            logger.info(
                f"CRUD: Successfully validated {len(places_validated)} place records."
            )

        elif hasattr(response, "error") and response.error:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", "Unknown Supabase error"
            )
            logger.error(f"CRUD: Error fetching places from Supabase: {error_detail}")
        elif not response.data:
            logger.debug("CRUD: No places found matching criteria or no data returned.")
        else:
            logger.warning(
                f"CRUD: Unexpected response structure from Supabase get_places: {response}"
            )

        return places_validated

    except Exception as e:
        logger.error(f"CRUD: Exception during get_places execution: {e}", exc_info=True)
        return []


async def get_place_by_id(
    place_id: int, db: SupabaseClient, include_deleted: bool = False
) -> PlaceInDB | None:
    """Retrieves a single non-deleted place by ID from Supabase."""
    logger.debug(
        f"CRUD: Getting place by ID: {place_id}, IncludeDeleted: {include_deleted}"
    )
    try:
        query = db.table(TABLE_NAME).select("*").eq("id", place_id)

        # --- SOFT DELETE FILTER ---
        if not include_deleted:
            query = query.is_("deleted_at", None)  # Add filter

        query = query.maybe_single()  # Apply maybe_single after all filters
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            validated_place = PlaceInDB(**response.data)
            logger.debug(f"CRUD: Found place ID {place_id}")
            return validated_place
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", None
            )
            if error_detail:
                logger.error(f"CRUD: Error fetching place {place_id}: {error_detail}")
            elif not include_deleted:
                logger.debug(f"CRUD: Place ID {place_id} not found or is deleted.")
            else:
                logger.debug(f"CRUD: Place ID {place_id} not found.")
            return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in get_place_by_id for ID {place_id}: {e}", exc_info=True
        )
        return None


async def update_place(
    place_id: int, place_update: PlaceUpdate, db: SupabaseClient
) -> PlaceInDB | None:
    """Updates an existing place in Supabase."""
    logger.info(f"CRUD: Attempting to update place ID {place_id}")
    try:
        # Ensure we don't try to update a deleted place unless explicitly allowed?
        # current_place = await get_place_by_id(place_id, db) # Check if it exists and isn't deleted
        # if not current_place:
        #     logger.warning(f"CRUD: Attempted to update non-existent or deleted place ID {place_id}.")
        #     return None
        # This check adds an extra DB call, might be omitted depending on requirements.

        update_data = place_update.model_dump(exclude_unset=True)
        if not update_data:
            logger.warning(f"CRUD: Update requested for place {place_id} with no data.")
            return await get_place_by_id(
                place_id, db
            )  # Return current state (if exists)

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Ensure we don't accidentally undelete via a normal update
        update_data.pop("deleted_at", None)

        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .is_(
                "deleted_at", None
            )  # Optionally ensure we only update non-deleted items
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            updated_place_data = response.data[0]
            validated_place = PlaceInDB(**updated_place_data)
            logger.info(f"CRUD: Successfully updated place ID {place_id}")
            return validated_place
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", None
            )
            if error_detail:
                logger.error(f"CRUD: Error updating place {place_id}: {error_detail}")
                return None
            else:
                logger.warning(
                    f"CRUD: Update for place {place_id} matched no rows (may not exist or is deleted)."
                )
                return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in update_place for ID {place_id}: {e}", exc_info=True
        )
        return None


async def upload_place_image(
    place_id: int, file: UploadFile, db: SupabaseClient
) -> str | None:
    """Uploads an image to Supabase Storage."""
    logger.info(
        f"CRUD: Uploading image for place ID {place_id}. Filename: {file.filename}"
    )
    if not settings.SUPABASE_BUCKET_NAME:
        logger.error("CRUD: Supabase bucket name not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image storage not configured.",
        )

    try:
        file_extension = (
            os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
        )
        if file_extension not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            file_extension = ".jpg"
        file_path_on_storage = f"places/{place_id}/{uuid.uuid4()}{file_extension}"

        content = await file.read()
        logger.debug(
            f"CRUD: Uploading {len(content)} bytes to bucket '{settings.SUPABASE_BUCKET_NAME}' path '{file_path_on_storage}'"
        )

        storage_from = db.storage.from_(settings.SUPABASE_BUCKET_NAME)
        upload_response = await asyncio.to_thread(
            storage_from.upload,
            path=file_path_on_storage,
            file=content,
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            },
        )
        logger.debug(
            f"CRUD: Supabase storage upload completed (response type: {type(upload_response)})."
        )

        # Getting public URL is synchronous
        public_url = storage_from.get_public_url(file_path_on_storage)

        if public_url:
            logger.info(
                f"CRUD: Image uploaded for place {place_id}. Public URL: {public_url}"
            )
            return public_url
        else:
            # This case is less likely if upload succeeded, but handle defensively
            logger.error(
                f"CRUD: Image uploaded for place {place_id}, but failed to get public URL."
            )
            return None
    except Exception as e:
        logger.error(
            f"CRUD: Error uploading image for place {place_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image: {e}",
        ) from e


# update_place_image_url is often implicitly handled by update_place now,
# but keep if direct URL updates are needed elsewhere.
# async def update_place_image_url(...) -> bool: ...


async def delete_place(place_id: int, db: SupabaseClient) -> bool:
    """Soft deletes a place by setting the deleted_at timestamp."""
    logger.warning(f"CRUD: Soft deleting place ID {place_id}.")
    # TODO: Consider deleting associated images from storage when soft deleting,
    # or have a separate cleanup process later.

    try:
        delete_time = datetime.now(timezone.utc).isoformat()
        update_data = {"deleted_at": delete_time}

        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .is_("deleted_at", None)  # Only soft delete if not already deleted
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            logger.info(f"CRUD: Successfully soft deleted place {place_id}.")
            return True
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", None
            )
            if error_detail:
                logger.error(
                    f"CRUD: Error soft deleting place {place_id}: {error_detail}"
                )
                return False
            else:
                # This means the place was already deleted or didn't exist
                logger.warning(
                    f"CRUD: Soft delete for place {place_id} affected no rows (already deleted or does not exist)."
                )
                # Consider if this should return True or False. False seems safer.
                return False

    except Exception as e:
        logger.error(
            f"CRUD: Exception in soft delete for ID {place_id}: {e}", exc_info=True
        )
        return False
