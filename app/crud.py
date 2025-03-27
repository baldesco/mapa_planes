"""Functions for database interactions (CRUD operations), primarily using Supabase."""

import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from supabase import Client as SupabaseClient, create_client
from .core.config import settings, logger
from .models import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
    PlaceCategory,
    Place,
)

# Define the table name used in Supabase
TABLE_NAME = "places"


async def create_place(place: PlaceCreate, db: SupabaseClient) -> PlaceInDB | None:
    """Creates a new place record in Supabase."""
    try:
        place_data = place.model_dump()
        # Timestamps are best handled by DB defaults (if set up) or triggers
        # Manually setting them here if DB doesn't auto-set created_at/updated_at
        now = datetime.utcnow().isoformat()
        place_data.setdefault("created_at", now)  # Set if not present
        place_data.setdefault("updated_at", now)  # Set if not present

        response = await db.table(TABLE_NAME).insert(place_data).execute()
        logger.debug(f"Supabase insert response data: {response.data}")

        if response.data:
            created_place_data = response.data[0]
            return PlaceInDB(**created_place_data)
        else:
            # Supabase errors might be in response.error or raise exception depending on client version/config
            error_msg = getattr(response, "error", {}).get(
                "message", "Unknown error during insert"
            )
            logger.error(f"Failed to create place in Supabase: {error_msg}")
            return None
    except Exception as e:
        logger.error(f"Exception in create_place: {e}", exc_info=True)
        # Re-raise or handle specific exceptions if needed
        return None


async def get_places(
    db: SupabaseClient,
    category: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,  # Renamed to avoid conflict
    skip: int = 0,
    limit: int = 100,
) -> List[PlaceInDB]:
    """Retrieves places from Supabase, with optional filtering and pagination."""
    try:
        query = db.table(TABLE_NAME).select("*").order("created_at", desc=True)

        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)  # Use renamed parameter

        # Apply pagination using range
        response = await query.range(skip, skip + limit - 1).execute()
        logger.debug(f"Supabase select response count: {len(response.data)}")

        if response.data:
            # Validate data against Pydantic model
            places = [PlaceInDB(**p) for p in response.data]
            return places
        else:
            error_msg = getattr(response, "error", {}).get("message")
            if error_msg:
                logger.error(f"Error fetching places from Supabase: {error_msg}")
            # It's okay if no data is found, return empty list
            return []
    except Exception as e:
        logger.error(f"Exception in get_places: {e}", exc_info=True)
        return []  # Return empty list on error


async def get_place_by_id(place_id: int, db: SupabaseClient) -> PlaceInDB | None:
    """Retrieves a single place by its ID from Supabase."""
    try:
        response = (
            await db.table(TABLE_NAME)
            .select("*")
            .eq("id", place_id)
            .maybe_single()
            .execute()
        )
        logger.debug(f"Supabase select single response data: {response.data}")

        if response.data:
            return PlaceInDB(**response.data)
        else:
            error_msg = getattr(response, "error", {}).get("message")
            if error_msg:
                logger.error(f"Error fetching place {place_id}: {error_msg}")
            # maybe_single() returns None if not found, which is expected
            return None
    except Exception as e:
        logger.error(
            f"Exception in get_place_by_id for ID {place_id}: {e}", exc_info=True
        )
        return None


async def update_place(
    place_id: int, place_update: PlaceUpdate, db: SupabaseClient
) -> PlaceInDB | None:
    """Updates an existing place in Supabase."""
    try:
        update_data = place_update.model_dump(
            exclude_unset=True
        )  # Only include fields provided
        if not update_data:
            logger.warning(f"Update requested for place {place_id} with no data.")
            return await get_place_by_id(
                place_id, db
            )  # Return current state if nothing to update

        # Ensure updated_at is set (if DB trigger isn't used)
        update_data["updated_at"] = datetime.utcnow().isoformat()

        response = (
            await db.table(TABLE_NAME).update(update_data).eq("id", place_id).execute()
        )
        logger.debug(f"Supabase update response data: {response.data}")

        if response.data:
            updated_place_data = response.data[0]
            return PlaceInDB(**updated_place_data)
        else:
            # Check if it was a "not found" situation or other error
            error_msg = getattr(response, "error", {}).get("message")
            if error_msg:
                logger.error(f"Error updating place {place_id}: {error_msg}")
                return None  # Indicate update failure
            else:
                # If data is empty and no error, it likely means the ID didn't match
                logger.warning(f"Update for place {place_id} matched no rows.")
                return None  # Indicate place not found
    except Exception as e:
        logger.error(f"Exception in update_place for ID {place_id}: {e}", exc_info=True)
        return None


async def upload_place_image(
    place_id: int, file: UploadFile, db: SupabaseClient
) -> str | None:
    """Uploads an image to Supabase Storage and returns the public URL."""
    if not settings.SUPABASE_BUCKET_NAME:
        logger.error("Supabase bucket name not configured (SUPABASE_BUCKET_NAME).")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image storage not configured.",
        )

    try:
        # Generate a unique filename to prevent overwrites
        file_extension = (
            os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
        )
        if file_extension not in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
        ]:  # Basic validation
            file_extension = ".jpg"  # Default extension
        # Path within the bucket
        file_path_on_storage = f"places/{place_id}/{uuid.uuid4()}{file_extension}"

        content = await file.read()
        logger.info(
            f"Attempting to upload {len(content)} bytes to bucket '{settings.SUPABASE_BUCKET_NAME}' at path '{file_path_on_storage}' with content-type '{file.content_type}'"
        )

        # Upload using supabase-py async client
        upload_response = await db.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=file_path_on_storage,
            file=content,
            file_options={
                "content-type": file.content_type or "application/octet-stream"
            },
        )
        # Note: Supabase client might change response structure. Check its docs/behavior.
        # Assuming success if no exception. Check response if available.
        logger.debug(
            f"Supabase storage upload response status: {getattr(upload_response, 'status_code', 'N/A')}"
        )

        # Get the public URL - this requires the bucket to be public
        # and appropriate storage policies to be set in Supabase UI.
        public_url_response = db.storage.from_(
            settings.SUPABASE_BUCKET_NAME
        ).get_public_url(file_path_on_storage)

        if public_url_response:
            logger.info(
                f"Image uploaded for place {place_id}. Public URL: {public_url_response}"
            )
            return public_url_response
        else:
            # This case might occur if URL generation fails for some reason
            logger.error(
                f"Image uploaded for place {place_id}, but failed to get public URL."
            )
            return None  # Indicate failure to get URL

    except Exception as e:
        # Catch specific Supabase storage errors if possible
        logger.error(
            f"Error uploading image for place {place_id} to Supabase Storage: {e}",
            exc_info=True,
        )
        # Re-raise as HTTPException?
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image: {e}",
        ) from e


async def update_place_image_url(
    place_id: int, image_url: str | None, db: SupabaseClient
) -> bool:
    """Updates the image_url field for a place in the database."""
    try:
        update_data = {
            "image_url": image_url,  # Can be None to clear the URL
            "updated_at": datetime.utcnow().isoformat(),
        }
        response = (
            await db.table(TABLE_NAME).update(update_data).eq("id", place_id).execute()
        )

        if response.data:
            logger.info(f"Successfully updated image_url for place {place_id}")
            return True
        else:
            error_msg = getattr(response, "error", {}).get("message")
            logger.error(
                f"Failed to update image_url for place {place_id}. Error: {error_msg}"
            )
            return False
    except Exception as e:
        logger.error(
            f"Exception in update_place_image_url for ID {place_id}: {e}", exc_info=True
        )
        return False


async def delete_place(place_id: int, db: SupabaseClient) -> bool:
    """Deletes a place from Supabase. Returns True if successful."""
    # TODO: Add logic to delete the associated image from Supabase Storage
    # place = await get_place_by_id(place_id, db)
    # if place and place.image_url:
    #    try:
    #        # Parse path from URL and call db.storage.from_(...).remove([path])
    #        pass # Implement image deletion logic
    #    except Exception as e:
    #        logger.error(f"Failed to delete image for place {place_id}: {e}")
    #        # Proceed with DB deletion anyway? Or handle error?

    try:
        response = await db.table(TABLE_NAME).delete().eq("id", place_id).execute()
        logger.debug(f"Supabase delete response data: {response.data}")

        if response.data:
            logger.info(f"Successfully deleted place {place_id}")
            return True
        else:
            error_msg = getattr(response, "error", {}).get("message")
            if error_msg:
                logger.error(f"Error deleting place {place_id}: {error_msg}")
                return False
            else:
                # Empty data might mean row wasn't found
                logger.warning(
                    f"Delete command for place {place_id} affected no rows (might not exist)."
                )
                return False  # Indicate place wasn't found/deleted

    except Exception as e:
        logger.error(f"Exception in delete_place for ID {place_id}: {e}", exc_info=True)
        return False
