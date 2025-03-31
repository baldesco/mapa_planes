"""Functions for database interactions (CRUD operations), primarily using Supabase."""

import uuid
import os
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from supabase import Client as SupabaseClient, create_client
from supabase.lib.client_options import (
    ClientOptions,
)
from postgrest import APIResponse

from .core.config import settings, logger
from .models import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
    PlaceCategory,
)

# Define the table name used in Supabase
TABLE_NAME = "places"


# --- Create Place ---
async def create_place(place: PlaceCreate, db: SupabaseClient) -> PlaceInDB | None:
    """Creates a new place record in Supabase."""
    logger.info(f"CRUD: Attempting to create place: {place.name}")
    try:
        place_data = place.model_dump()
        now = datetime.utcnow().isoformat()
        place_data.setdefault("created_at", now)
        place_data.setdefault("updated_at", now)

        query = db.table(TABLE_NAME).insert(place_data)
        response: APIResponse = await asyncio.to_thread(query.execute)

        logger.debug(f"Supabase insert response data: {response.data}")

        if response.data:
            created_place_data = response.data[0]
            # Validate the data returned from DB before returning
            validated_place = PlaceInDB(**created_place_data)
            logger.info(
                f"CRUD: Successfully created and validated place ID {validated_place.id}"
            )
            return validated_place
        else:
            # Attempt to log specific Supabase error if available in response structure
            # Supabase-py v2 might structure errors differently, adjust if needed
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", "Unknown error during insert"
            )
            logger.error(
                f"CRUD: Failed to create place '{place.name}' in Supabase: {error_detail}"
            )
            return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in create_place for '{place.name}': {e}", exc_info=True
        )
        return None


# --- Get Places ---
async def get_places(
    db: SupabaseClient,
    category: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,  # Renamed to avoid conflict
    skip: int = 0,
    limit: int = 100,
) -> List[PlaceInDB]:
    """Retrieves places from Supabase, with optional filtering and pagination."""
    logger.info(
        f"CRUD: Fetching places. Category: {category}, Status: {status_filter}, Skip: {skip}, Limit: {limit}"
    )
    places_validated = []
    try:
        query = db.table(TABLE_NAME).select("*").order("created_at", desc=True)

        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)  # Use renamed parameter

        final_query = query.range(skip, skip + limit - 1)
        response: APIResponse = await asyncio.to_thread(final_query.execute)

        if hasattr(response, "data") and response.data:
            logger.debug(
                f"CRUD: Received {len(response.data)} raw place records from Supabase."
            )
            for i, p_data in enumerate(response.data):
                try:
                    # Validate each place record with Pydantic
                    validated_place = PlaceInDB(**p_data)
                    places_validated.append(validated_place)
                except Exception as validation_error:
                    logger.error(
                        f"CRUD: Pydantic validation failed for place record #{i + 1}. Data: {p_data}. Error: {validation_error}",
                        exc_info=False,
                    )
                    # Optionally log full exc_info=True if needed for deep debugging
            logger.info(
                f"CRUD: Successfully validated {len(places_validated)} place records."
            )

        # Check for errors even if data is present (might be partial result?)
        # Adapt based on how Supabase returns errors alongside data
        elif hasattr(response, "error") and response.error:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", "Unknown Supabase error"
            )
            logger.error(f"CRUD: Error fetching places from Supabase: {error_detail}")
        elif not response.data:
            logger.debug("CRUD: No places found matching criteria or no data returned.")
        else:
            # Should not happen if hasattr checks pass, but good fallback
            logger.warning(
                f"CRUD: Unexpected response structure from Supabase get_places: {response}"
            )

        return places_validated  # Return only successfully validated places

    except Exception as e:
        # This catches errors in the asyncio.to_thread call or subsequent validation loop
        logger.error(f"CRUD: Exception during get_places execution: {e}", exc_info=True)
        return []  # Return empty list on major error


# --- Get Place By ID ---
async def get_place_by_id(place_id: int, db: SupabaseClient) -> PlaceInDB | None:
    """Retrieves a single place by its ID from Supabase."""
    logger.debug(f"CRUD: Getting place by ID: {place_id}")
    try:
        query = db.table(TABLE_NAME).select("*").eq("id", place_id).maybe_single()
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            validated_place = PlaceInDB(**response.data)
            logger.debug(f"CRUD: Found place ID {place_id}")
            return validated_place
        else:
            # Check for specific errors
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", None
            )
            if error_detail:
                logger.error(f"CRUD: Error fetching place {place_id}: {error_detail}")
            else:
                # This is expected if maybe_single() finds nothing
                logger.debug(f"CRUD: Place ID {place_id} not found.")
            return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in get_place_by_id for ID {place_id}: {e}", exc_info=True
        )
        return None


# --- Update Place ---
async def update_place(
    place_id: int, place_update: PlaceUpdate, db: SupabaseClient
) -> PlaceInDB | None:
    """Updates an existing place in Supabase."""
    logger.info(f"CRUD: Attempting to update place ID {place_id}")
    try:
        update_data = place_update.model_dump(exclude_unset=True)
        if not update_data:
            logger.warning(
                f"CRUD: Update requested for place {place_id} with no data. Returning current state."
            )
            # Need to call get_place_by_id asynchronously
            return await get_place_by_id(place_id, db)

        update_data["updated_at"] = datetime.utcnow().isoformat()

        query = db.table(TABLE_NAME).update(update_data).eq("id", place_id)
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
                # This happens if the .eq("id", place_id) didn't match any rows
                logger.warning(
                    f"CRUD: Update for place {place_id} matched no rows (may not exist)."
                )
                return None  # Place not found to update
    except Exception as e:
        logger.error(
            f"CRUD: Exception in update_place for ID {place_id}: {e}", exc_info=True
        )
        return None


# --- Upload Place Image ---
async def upload_place_image(
    place_id: int, file: UploadFile, db: SupabaseClient
) -> str | None:
    """Uploads an image to Supabase Storage and returns the public URL."""
    logger.info(
        f"CRUD: Uploading image for place ID {place_id}. Filename: {file.filename}"
    )
    if not settings.SUPABASE_BUCKET_NAME:
        logger.error(
            "CRUD: Supabase bucket name not configured (SUPABASE_BUCKET_NAME)."
        )
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

        content = await file.read()  # Reading file is already async, keep await
        logger.debug(
            f"CRUD: Uploading {len(content)} bytes to bucket '{settings.SUPABASE_BUCKET_NAME}' path '{file_path_on_storage}' content-type '{file.content_type}'"
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
        # Note: The structure of upload_response might vary; logging status_code might need adjustment
        # Check supabase-py docs for exact return type of storage.upload
        logger.debug(
            f"CRUD: Supabase storage upload completed (response type: {type(upload_response)}). Check logs or debugger for details."
            # f"CRUD: Supabase storage upload response status: {getattr(upload_response, 'status_code', 'N/A')}" # May not have status_code
        )

        # Getting the public URL is typically just string manipulation, likely doesn't need await or to_thread
        # If it *does* make a network call in some Supabase version, it would need to_thread as well.
        # Assume it's synchronous for now.
        public_url_response = storage_from.get_public_url(file_path_on_storage)

        if public_url_response:
            logger.info(
                f"CRUD: Image uploaded successfully for place {place_id}. Public URL obtained: {public_url_response}"
            )
            return public_url_response
        else:
            logger.error(
                f"CRUD: Image uploaded for place {place_id}, but failed to get public URL."
            )
            # Maybe attempt to remove the uploaded file if URL fails? More complex logic.
            return None

    except Exception as e:
        logger.error(
            f"CRUD: Error uploading image for place {place_id} to Supabase Storage: {e}",
            exc_info=True,
        )
        # Re-raise as HTTPException for the endpoint to handle
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image: {e}",
        ) from e


# --- Update Place Image URL (in DB) ---
async def update_place_image_url(
    place_id: int, image_url: str | None, db: SupabaseClient
) -> bool:
    """Updates the image_url field for a place in the database."""
    logger.info(f"CRUD: Updating image_url for place ID {place_id}.")
    try:
        update_data = {
            "image_url": image_url,
            "updated_at": datetime.utcnow().isoformat(),
        }
        query = db.table(TABLE_NAME).update(update_data).eq("id", place_id)
        # FIX: Use asyncio.to_thread for the synchronous execute() call
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            logger.info(f"CRUD: Successfully updated image_url for place {place_id}")
            return True
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", "Update failed"
            )
            logger.error(
                f"CRUD: Failed to update image_url for place {place_id}. Error: {error_detail}"
            )
            # Check if the error indicates the row wasn't found
            # This logic might depend on specific Supabase error codes/messages
            if "No rows found" in str(error_detail):  # Example check
                logger.warning(
                    f"CRUD: Place ID {place_id} not found during image URL update."
                )
            return False
    except Exception as e:
        logger.error(
            f"CRUD: Exception in update_place_image_url for ID {place_id}: {e}",
            exc_info=True,
        )
        return False


# --- Delete Place ---
async def delete_place(place_id: int, db: SupabaseClient) -> bool:
    """Deletes a place from Supabase. Returns True if successful."""
    logger.warning(
        f"CRUD: Attempting to delete place ID {place_id}. Image file deletion NOT YET IMPLEMENTED."
    )
    # TODO: Implement image deletion from storage before deleting DB record
    # This would involve listing files in the place's folder and calling storage delete, likely needing asyncio.to_thread

    try:
        query = db.table(TABLE_NAME).delete().eq("id", place_id)
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            logger.info(f"CRUD: Successfully deleted place {place_id} from database.")
            return True
        else:
            error_detail = getattr(response, "error", None) or getattr(
                response, "message", None
            )
            if error_detail:
                logger.error(f"CRUD: Error deleting place {place_id}: {error_detail}")
                return False
            else:
                # This likely means the .eq("id", place_id) matched no rows
                logger.warning(
                    f"CRUD: Delete command for place {place_id} affected no rows (might not exist)."
                )
                return False  # Indicate place wasn't found/deleted

    except Exception as e:
        logger.error(
            f"CRUD: Exception in delete_place for ID {place_id}: {e}", exc_info=True
        )
        return False
