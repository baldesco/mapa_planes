"""Functions for database interactions (CRUD operations), primarily using Supabase."""

import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from supabase import Client as SupabaseClient
from supabase.lib.client_options import ClientOptions
from postgrest import APIResponse, APIError

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
        place_data = place.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        place_data.setdefault("created_at", now_utc_iso)
        place_data.setdefault("updated_at", now_utc_iso)
        place_data["deleted_at"] = None

        logger.debug(f"CRUD: Data being sent to Supabase insert: {place_data}")
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
            error_detail = "Unknown error during insert"
            if hasattr(response, "error") and response.error:
                error_detail = (
                    response.error.message
                    if hasattr(response.error, "message")
                    else str(response.error)
                )
            elif hasattr(response, "message") and response.message:
                error_detail = response.message
            logger.error(f"CRUD: Failed to create place '{place.name}': {error_detail}")
            return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in create_place for '{place.name}': {e.message} (Code: {e.code}, Details: {e.details}, Hint: {e.hint})",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in create_place for '{place.name}': {e}",
            exc_info=True,
        )
        return None


async def get_places(
    db: SupabaseClient,
    category: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> List[PlaceInDB]:
    """Retrieves non-deleted places from Supabase, with filtering and pagination."""
    logger.info(
        f"CRUD: Fetching places. Category: {category}, Status: {status_filter}, Skip: {skip}, Limit: {limit}, IncludeDeleted: {include_deleted}"
    )
    places_validated = []
    try:
        query = db.table(TABLE_NAME).select("*").order("created_at", desc=True)

        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)

        if not include_deleted:
            query = query.is_("deleted_at", None)

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
            error_detail = (
                response.error.message
                if hasattr(response.error, "message")
                else str(response.error)
            )
            logger.error(f"CRUD: Error fetching places from Supabase: {error_detail}")
        elif not response.data:
            logger.debug("CRUD: No places found matching criteria or no data returned.")
        else:
            logger.warning(
                f"CRUD: Unexpected response structure from Supabase get_places: {response}"
            )

        return places_validated

    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError during get_places: {e.message}", exc_info=False
        )
        return []
    except Exception as e:
        logger.error(
            f"CRUD: General Exception during get_places execution: {e}", exc_info=True
        )
        return []


async def get_place_by_id(
    place_id: int, db: SupabaseClient, include_deleted: bool = False
) -> PlaceInDB | None:
    """Retrieves a single place by ID from Supabase."""
    logger.debug(
        f"CRUD: Getting place by ID: {place_id}, IncludeDeleted: {include_deleted}"
    )
    try:
        query = db.table(TABLE_NAME).select("*").eq("id", place_id)

        if not include_deleted:
            query = query.is_("deleted_at", None)

        query = query.maybe_single()
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            validated_place = PlaceInDB(**response.data)
            logger.debug(f"CRUD: Found place ID {place_id}")
            return validated_place
        else:
            error_detail = None
            if hasattr(response, "error") and response.error:
                error_detail = (
                    response.error.message
                    if hasattr(response.error, "message")
                    else str(response.error)
                )

            if error_detail:
                logger.error(f"CRUD: Error fetching place {place_id}: {error_detail}")
            elif not include_deleted:
                logger.debug(f"CRUD: Place ID {place_id} not found or is deleted.")
            else:
                logger.debug(f"CRUD: Place ID {place_id} not found.")
            return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in get_place_by_id for {place_id}: {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in get_place_by_id for ID {place_id}: {e}",
            exc_info=True,
        )
        return None


async def update_place(
    place_id: int, place_update: PlaceUpdate, db: SupabaseClient
) -> PlaceInDB | None:
    """Updates an existing place in Supabase."""
    logger.info(f"CRUD: Attempting to update place ID {place_id}")
    try:
        update_data = place_update.model_dump(mode="json", exclude_unset=True)

        if not update_data:
            logger.warning(
                f"CRUD: Update requested for place {place_id} with no data fields set in the model."
            )
            return await get_place_by_id(place_id, db)

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data.pop("deleted_at", None)

        logger.debug(
            f"CRUD: Data being sent to Supabase update for ID {place_id}: {update_data}"
        )

        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .is_("deleted_at", None)
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            updated_place_data = response.data[0]
            validated_place = PlaceInDB(**updated_place_data)
            logger.info(f"CRUD: Successfully updated place ID {place_id}")
            return validated_place
        else:
            error_detail = None
            if hasattr(response, "error") and response.error:
                error_detail = (
                    response.error.message
                    if hasattr(response.error, "message")
                    else str(response.error)
                )

            if error_detail:
                logger.error(f"CRUD: Error updating place {place_id}: {error_detail}")
                return None
            else:
                existing = await get_place_by_id(place_id, db, include_deleted=True)
                if not existing:
                    logger.warning(
                        f"CRUD: Update for place {place_id} failed: Place not found."
                    )
                elif existing.deleted_at:
                    logger.warning(
                        f"CRUD: Update for place {place_id} failed: Place is deleted."
                    )
                else:
                    logger.warning(
                        f"CRUD: Update for place {place_id} affected no rows or resulted in no change (or RLS issue)."
                    )
                return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in update_place for {place_id}: {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in update_place for ID {place_id}: {e}",
            exc_info=True,
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
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if file_extension not in allowed_extensions:
            logger.warning(
                f"CRUD: Invalid image extension '{file_extension}' for place {place_id}. Defaulting to .jpg"
            )
            file_extension = ".jpg"

        file_path_on_storage = f"places/{place_id}/{uuid.uuid4()}{file_extension}"
        content = await file.read()
        logger.debug(
            f"CRUD: Uploading {len(content)} bytes to bucket '{settings.SUPABASE_BUCKET_NAME}' path '{file_path_on_storage}'"
        )

        storage_from = db.storage.from_(settings.SUPABASE_BUCKET_NAME)

        file_options = {
            "content-type": file.content_type or "application/octet-stream",
            "cache-control": "3600",
            "upsert": "false",  # Set to "true" to allow overwriting
        }

        try:
            # Run the blocking upload call in a separate thread
            upload_task = asyncio.to_thread(
                storage_from.upload,
                path=file_path_on_storage,
                file=content,
                file_options=file_options,
            )
            await upload_task
            logger.debug(
                f"CRUD: Supabase storage upload call completed for path {file_path_on_storage}."
            )
        except APIError as storage_api_error:
            err_msg = (
                storage_api_error.message
                if hasattr(storage_api_error, "message")
                else str(storage_api_error)
            )
            logger.error(
                f"CRUD: Storage APIError during upload for place {place_id}, path {file_path_on_storage}: {err_msg}",
                exc_info=False,
            )

            if "security policy" in err_msg.lower():
                detail_msg = f"Storage permission denied. Check Supabase Storage RLS policies for bucket '{settings.SUPABASE_BUCKET_NAME}'."
                status_code = status.HTTP_403_FORBIDDEN
            elif "exists" in err_msg.lower() and not file_options.get("upsert"):
                detail_msg = f"File already exists at path '{file_path_on_storage}' and upsert is false."
                status_code = status.HTTP_409_CONFLICT
            else:
                detail_msg = f"Storage error during upload: {err_msg}"
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(
                status_code=status_code,
                detail=detail_msg,
            ) from storage_api_error
        except Exception as upload_err:
            logger.error(
                f"CRUD: Unexpected error during storage upload call for place {place_id}: {upload_err}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error during image upload.",
            ) from upload_err

        # --- Get Public URL ---
        public_url = None
        try:
            logger.debug(
                f"CRUD: Attempting to get public URL for: {file_path_on_storage}"
            )
            get_url_task = asyncio.to_thread(
                storage_from.get_public_url, file_path_on_storage
            )
            public_url_response = await get_url_task
            public_url = public_url_response
            logger.debug(
                f"CRUD: get_public_url returned: {public_url} (Type: {type(public_url)})"
            )
        except Exception as url_error:
            logger.error(
                f"CRUD: Uploaded {file_path_on_storage}, but failed during get_public_url: {url_error}",
                exc_info=True,
            )
            return None

        # --- Validate and Return URL ---
        if public_url and isinstance(public_url, str) and public_url.startswith("http"):
            logger.info(
                f"CRUD: Image uploaded and public URL obtained for place {place_id}: {public_url}"
            )
            return public_url
        else:
            logger.error(
                f"CRUD: Image possibly uploaded for place {place_id}, but get_public_url returned invalid data: {public_url}"
            )
            return None

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"CRUD: General error in upload_place_image logic for place {place_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not upload image due to an internal error.",
        ) from e


async def delete_place(place_id: int, db: SupabaseClient) -> bool:
    """Soft deletes a place by setting the deleted_at timestamp."""
    logger.warning(f"CRUD: Soft deleting place ID {place_id}.")

    try:
        delete_time_iso = datetime.now(timezone.utc).isoformat()
        place_delete_update = PlaceUpdate(
            deleted_at=delete_time_iso, updated_at=delete_time_iso
        )
        update_data = place_delete_update.model_dump(mode="json", exclude_unset=True)

        logger.debug(f"CRUD: Data for soft delete ID {place_id}: {update_data}")

        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .is_("deleted_at", None)
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if hasattr(response, "error") and response.error:
            error_detail = (
                response.error.message
                if hasattr(response.error, "message")
                else str(response.error)
            )
            logger.error(f"CRUD: Error soft deleting place {place_id}: {error_detail}")
            return False
        elif response.data:
            logger.info(f"CRUD: Successfully soft deleted place {place_id}.")
            return True
        else:
            existing = await get_place_by_id(place_id, db, include_deleted=True)
            if not existing:
                logger.warning(
                    f"CRUD: Soft delete for place {place_id} failed: Place not found."
                )
            elif existing.deleted_at:
                logger.info(
                    f"CRUD: Successfully soft deleted place {place_id} (confirmed via re-fetch)."
                )
                return True
            else:
                logger.warning(
                    f"CRUD: Soft delete for place {place_id} affected no rows and record not deleted (unknown reason, possibly RLS)."
                )
            return False

    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in soft delete for {place_id}: {e.message}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in soft delete for ID {place_id}: {e}",
            exc_info=True,
        )
        return False
