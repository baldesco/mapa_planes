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
from .database import get_supabase_service_client  # Import service client getter

# Dependency Injection for service client (used for admin tasks like deleting other users' storage if needed)
# Note: Regular CRUD operations should work with the standard client due to RLS.
# Service client is mainly for bypassing RLS if absolutely necessary or for specific admin actions.
# Let's try to use the standard client first and only use service client for specific cross-user/RLS-bypass needs.


TABLE_NAME = "places"


async def _delete_storage_object(path: str, db_service: SupabaseClient):
    """Internal helper to delete an object from Supabase Storage using service client."""
    if not path or not path.startswith("places/"):  # Basic check
        logger.warning(f"CRUD: Invalid or missing path for storage deletion: '{path}'")
        return False
    if not db_service:
        logger.error("CRUD: Service client not available for storage deletion.")
        # Decide if this should raise an error or just fail silently
        return False

    try:
        # Storage paths usually don't start with '/', remove if present
        path_to_delete = path.lstrip("/")
        logger.info(
            f"CRUD: Attempting to delete storage object: '{path_to_delete}' using service client."
        )
        storage_from = db_service.storage.from_(settings.SUPABASE_BUCKET_NAME)

        # Run the blocking delete call in a separate thread
        delete_task = asyncio.to_thread(storage_from.remove, [path_to_delete])
        response = await delete_task
        logger.debug(
            f"CRUD: Storage deletion response for '{path_to_delete}': {response}"
        )

        # Check response structure - successful deletion might return list with deleted item details
        if response and isinstance(response, list) and len(response) > 0:
            # You might want more specific checks based on the actual response structure
            logger.info(
                f"CRUD: Successfully deleted storage object: '{path_to_delete}'"
            )
            return True
        elif response is None or (isinstance(response, list) and len(response) == 0):
            # Might occur if file didn't exist or other issues
            logger.warning(
                f"CRUD: Storage deletion command executed for '{path_to_delete}', but response suggests no object was deleted (or API changed). Response: {response}"
            )
            return False  # Consider if this is success or failure based on intent
        else:
            logger.error(
                f"CRUD: Unexpected response during storage deletion for '{path_to_delete}': {response}"
            )
            return False

    except APIError as storage_api_error:
        err_msg = getattr(storage_api_error, "message", str(storage_api_error))
        logger.error(
            f"CRUD: Storage APIError during deletion of '{path}': {err_msg}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: General Exception during storage deletion of '{path}': {e}",
            exc_info=True,
        )
        return False


async def create_place(
    place: PlaceCreate, user_id: uuid.UUID, db: SupabaseClient
) -> PlaceInDB | None:
    """Creates a new place record in Supabase, associated with a user."""
    logger.info(f"CRUD: Attempting to create place '{place.name}' for user {user_id}")
    try:
        place_data = place.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        place_data["created_at"] = now_utc_iso
        place_data["updated_at"] = now_utc_iso
        place_data["deleted_at"] = None
        place_data["user_id"] = str(user_id)  # Add user ID

        # Rating should be included if provided in PlaceCreate
        if place.rating is not None:
            place_data["rating"] = place.rating

        logger.debug(f"CRUD: Data being sent to Supabase insert: {place_data}")

        # RLS Policy 'INSERT ... WITH CHECK (auth.uid() = user_id)' should enforce ownership
        query = db.table(TABLE_NAME).insert(place_data)
        response: APIResponse = await asyncio.to_thread(query.execute)
        logger.debug(f"Supabase insert response data: {response.data}")

        if response.data:
            created_place_data = response.data[0]
            validated_place = PlaceInDB(**created_place_data)
            logger.info(
                f"CRUD: Successfully created and validated place ID {validated_place.id} for user {user_id}"
            )
            return validated_place
        else:
            # Handle potential RLS failure or other insert issues
            error_detail = "Insert failed, possibly RLS violation or DB error."
            if hasattr(response, "error") and response.error:
                error_detail = getattr(response.error, "message", str(response.error))
            elif hasattr(response, "message") and response.message:
                error_detail = response.message
            logger.error(
                f"CRUD: Failed to create place '{place.name}' for user {user_id}: {error_detail}"
            )
            return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in create_place for user {user_id}, place '{place.name}': {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in create_place for user {user_id}, place '{place.name}': {e}",
            exc_info=True,
        )
        return None


async def get_places(
    db: SupabaseClient,
    user_id: uuid.UUID,
    category: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> List[PlaceInDB]:
    """Retrieves non-deleted places for a specific user from Supabase."""
    logger.info(
        f"CRUD: Fetching places for user {user_id}. Category: {category}, Status: {status_filter}, Skip: {skip}, Limit: {limit}, IncludeDeleted: {include_deleted}"
    )
    places_validated = []
    try:
        # RLS Policy 'SELECT ... USING (auth.uid() = user_id)' should automatically filter by user
        query = db.table(TABLE_NAME).select("*").order("created_at", desc=True)
        # Explicit user_id filter (belt-and-suspenders, or if RLS isn't active/correct)
        query = query.eq("user_id", str(user_id))

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
                f"CRUD: Received {len(response.data)} raw place records for user {user_id}."
            )
            for i, p_data in enumerate(response.data):
                try:
                    # Ensure user_id from DB matches the requested user_id before validating
                    if uuid.UUID(p_data.get("user_id")) != user_id:
                        logger.warning(
                            f"CRUD: RLS Mismatch? Fetched place ID {p_data.get('id')} belongs to another user. Skipping."
                        )
                        continue
                    validated_place = PlaceInDB(**p_data)
                    places_validated.append(validated_place)
                except Exception as validation_error:
                    logger.error(
                        f"CRUD: Pydantic validation failed for place record #{i + 1} for user {user_id}. Data: {p_data}. Error: {validation_error}",
                        exc_info=False,
                    )
            logger.info(
                f"CRUD: Successfully validated {len(places_validated)} place records for user {user_id}."
            )

        elif hasattr(response, "error") and response.error:
            error_detail = getattr(response.error, "message", str(response.error))
            logger.error(
                f"CRUD: Error fetching places for user {user_id}: {error_detail}"
            )
        elif not response.data:
            logger.debug(f"CRUD: No places found for user {user_id} matching criteria.")
        else:
            logger.warning(
                f"CRUD: Unexpected response structure from Supabase get_places for user {user_id}: {response}"
            )

        return places_validated

    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError during get_places for user {user_id}: {e.message}",
            exc_info=False,
        )
        return []
    except Exception as e:
        logger.error(
            f"CRUD: General Exception during get_places for user {user_id}: {e}",
            exc_info=True,
        )
        return []


async def get_place_by_id(
    place_id: int, user_id: uuid.UUID, db: SupabaseClient, include_deleted: bool = False
) -> PlaceInDB | None:
    """Retrieves a single place by ID for a specific user from Supabase."""
    logger.debug(
        f"CRUD: Getting place by ID: {place_id} for user {user_id}, IncludeDeleted: {include_deleted}"
    )
    try:
        # RLS Policy should enforce ownership, but we add explicit user_id check
        query = (
            db.table(TABLE_NAME)
            .select("*")
            .eq("id", place_id)
            .eq("user_id", str(user_id))
        )

        if not include_deleted:
            query = query.is_("deleted_at", None)

        query = query.maybe_single()  # Expect 0 or 1 result
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            # Double-check user_id before validation (paranoia)
            if uuid.UUID(response.data.get("user_id")) != user_id:
                logger.error(
                    f"CRUD: RLS Mismatch? Fetched place ID {place_id} belongs to another user ({response.data.get('user_id')}), requested by {user_id}."
                )
                return None
            validated_place = PlaceInDB(**response.data)
            logger.debug(f"CRUD: Found place ID {place_id} for user {user_id}")
            return validated_place
        else:
            error_detail = None
            if hasattr(response, "error") and response.error:
                error_detail = getattr(response.error, "message", str(response.error))

            if error_detail:
                logger.error(
                    f"CRUD: Error fetching place {place_id} for user {user_id}: {error_detail}"
                )
            else:
                # Check if it exists at all (ignoring user filter temporarily - requires careful RLS or service key)
                # basic_check = await db.table(TABLE_NAME).select("id, user_id").eq("id", place_id).maybe_single().execute()
                # if basic_check.data: logger.debug(f"CRUD: Place ID {place_id} exists but does not belong to user {user_id} or is deleted (if not included).")
                # else: logger.debug(f"CRUD: Place ID {place_id} not found at all.")
                logger.debug(
                    f"CRUD: Place ID {place_id} not found for user {user_id} or is deleted (if not included)."
                )
            return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in get_place_by_id for user {user_id}, place {place_id}: {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in get_place_by_id for user {user_id}, ID {place_id}: {e}",
            exc_info=True,
        )
        return None


async def update_place(
    place_id: int,
    user_id: uuid.UUID,
    place_update: PlaceUpdate,
    db: SupabaseClient,
    db_service: SupabaseClient | None = None,
) -> PlaceInDB | None:
    """Updates an existing place for a specific user in Supabase."""
    logger.info(f"CRUD: Attempting to update place ID {place_id} for user {user_id}")
    # Fetch current place to check ownership and get old image URL if needed
    current_place = await get_place_by_id(
        place_id=place_id, user_id=user_id, db=db, include_deleted=False
    )
    if not current_place:
        logger.warning(
            f"CRUD: Update failed. Place ID {place_id} not found or does not belong to user {user_id}."
        )
        # Check if it exists but is deleted
        deleted_check = await get_place_by_id(
            place_id=place_id, user_id=user_id, db=db, include_deleted=True
        )
        if deleted_check and deleted_check.deleted_at:
            logger.warning(f"CRUD: Update failed. Place ID {place_id} is deleted.")
        return None  # Not found or not owned/deleted

    old_image_url = current_place.image_url

    try:
        update_data = place_update.model_dump(
            mode="json", exclude_unset=True, exclude_none=False
        )  # Keep explicit None for image_url
        # If image_url is explicitly set to None in the update, it means remove the image.
        should_remove_image = (
            "image_url" in update_data and update_data["image_url"] is None
        )

        if not update_data:
            logger.warning(
                f"CRUD: Update requested for place {place_id} (user {user_id}) with no data fields."
            )
            return current_place  # No changes requested

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data.pop("deleted_at", None)  # Prevent accidental undelete via update

        # Ensure rating is included if present in the update model
        if place_update.rating is not None:
            update_data["rating"] = place_update.rating
        elif "rating" in update_data and update_data["rating"] is None:
            # Allow explicitly setting rating to null if needed, otherwise exclude if not set
            pass  # Explicitly setting to null is allowed by model
        # else:
        # update_data.pop("rating", None) # Remove if not explicitly set? Or let DB handle default/existing?

        # Handle image removal intent
        if should_remove_image:
            logger.info(f"CRUD: Explicit request to remove image for place {place_id}.")
            # Ensure the database field is set to null
            update_data["image_url"] = None
        elif "image_url" not in update_data and old_image_url:
            # If image_url is not in the payload, keep the existing one.
            # We don't want to accidentally remove it if the field wasn't sent.
            update_data.pop(
                "image_url", None
            )  # Remove from update payload if not present
            logger.debug(
                f"CRUD: image_url not in update payload, keeping existing: {old_image_url}"
            )

        logger.debug(
            f"CRUD: Data being sent to Supabase update for ID {place_id} (user {user_id}): {update_data}"
        )

        # RLS Policy 'UPDATE ... USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)' enforces ownership
        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .eq("user_id", str(user_id))  # Explicit user check
            .is_("deleted_at", None)  # Can only update non-deleted places
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            updated_place_data = response.data[0]
            validated_place = PlaceInDB(**updated_place_data)
            logger.info(
                f"CRUD: Successfully updated place ID {place_id} for user {user_id}"
            )

            # --- Delete old image from storage AFTER successful DB update ---
            if should_remove_image and old_image_url:
                logger.info(
                    f"CRUD: Post-update: Deleting old image '{old_image_url}' from storage."
                )
                # Extract path from URL (this is fragile, assumes Supabase public URL structure)
                try:
                    # Example URL: https://<project_ref>.supabase.co/storage/v1/object/public/place-images/places/<user_id>/<place_id>/<uuid>.jpg
                    # Need to extract: places/<user_id>/<place_id>/<uuid>.jpg
                    url_prefix = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/"
                    if old_image_url.startswith(url_prefix):
                        image_path = old_image_url[len(url_prefix) :]
                        # Deletion might require service client if RLS on storage is strict
                        if db_service:
                            deleted = await _delete_storage_object(
                                image_path, db_service
                            )
                            if not deleted:
                                logger.error(
                                    f"CRUD: Failed to delete image '{image_path}' from storage for place {place_id} (user {user_id}). Manual cleanup may be needed."
                                )
                        else:
                            logger.warning(
                                f"CRUD: Cannot delete image '{image_path}' for place {place_id} (user {user_id}) as service client is not available."
                            )
                    else:
                        logger.warning(
                            f"CRUD: Could not parse image path from old URL: {old_image_url}"
                        )
                except Exception as img_del_err:
                    logger.error(
                        f"CRUD: Error during old image deletion logic for place {place_id}: {img_del_err}",
                        exc_info=True,
                    )

            return validated_place
        else:
            # Handle potential RLS failure or other update issues
            error_detail = "Update failed, possibly RLS violation, place not found for user, or DB error."
            if hasattr(response, "error") and response.error:
                error_detail = getattr(response.error, "message", str(response.error))
            logger.error(
                f"CRUD: Failed to update place ID {place_id} for user {user_id}: {error_detail}"
            )
            # Re-fetch to confirm status (optional, adds overhead)
            # existing = await get_place_by_id(place_id, user_id, db, include_deleted=True)
            # if not existing: logger.warning(f"CRUD Update Fail Detail: Place {place_id} not found for user {user_id}.")
            # elif existing.deleted_at: logger.warning(f"CRUD Update Fail Detail: Place {place_id} is deleted.")
            # else: logger.warning(f"CRUD Update Fail Detail: Place {place_id} found, update affected 0 rows (RLS/no change/DB issue).")
            return None
    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in update_place for user {user_id}, place {place_id}: {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in update_place for user {user_id}, ID {place_id}: {e}",
            exc_info=True,
        )
        return None


async def upload_place_image(
    place_id: int, user_id: uuid.UUID, file: UploadFile, db: SupabaseClient
) -> str | None:
    """Uploads an image to Supabase Storage under the user's path."""
    logger.info(
        f"CRUD: Uploading image for place ID {place_id}, user {user_id}. Filename: {file.filename}"
    )
    if not settings.SUPABASE_BUCKET_NAME:
        logger.error("CRUD: Supabase bucket name not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image storage not configured.",
        )

    # Ensure the place exists and belongs to the user before uploading
    place = await get_place_by_id(place_id=place_id, user_id=user_id, db=db)
    if not place:
        logger.error(
            f"CRUD: Upload failed. Place ID {place_id} not found or doesn't belong to user {user_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or access denied.",
        )

    try:
        file_extension = (
            os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
        )
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if file_extension not in allowed_extensions:
            logger.warning(
                f"CRUD: Invalid image ext '{file_extension}' for place {place_id}. Defaulting to .jpg"
            )
            file_extension = ".jpg"

        # Define user-specific path: places/{user_id}/{place_id}/{uuid}.ext
        file_path_on_storage = (
            f"places/{user_id}/{place_id}/{uuid.uuid4()}{file_extension}"
        )
        content = await file.read()
        logger.debug(
            f"CRUD: Uploading {len(content)} bytes to bucket '{settings.SUPABASE_BUCKET_NAME}' path '{file_path_on_storage}' for user {user_id}"
        )

        storage_from = db.storage.from_(settings.SUPABASE_BUCKET_NAME)
        file_options = {
            "content-type": file.content_type or "application/octet-stream",
            "cache-control": "3600",
            "upsert": "false",
        }

        try:
            # RLS Policy 'INSERT ... WITH CHECK (folder is places/{auth.uid()}/...)' enforces this
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
            err_msg = getattr(storage_api_error, "message", str(storage_api_error))
            logger.error(
                f"CRUD: Storage APIError during upload for user {user_id}, place {place_id}, path {file_path_on_storage}: {err_msg}",
                exc_info=False,
            )
            detail_msg = f"Storage error during upload: {err_msg}"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            if "security policy" in err_msg.lower() or "Unauthorized" in err_msg:
                detail_msg = f"Storage permission denied. Check Supabase Storage RLS policies for bucket '{settings.SUPABASE_BUCKET_NAME}'."
                status_code = status.HTTP_403_FORBIDDEN
            elif "exists" in err_msg.lower() and not file_options.get("upsert"):
                detail_msg = f"File already exists at path '{file_path_on_storage}' and upsert is false."
                status_code = status.HTTP_409_CONFLICT
            raise HTTPException(
                status_code=status_code, detail=detail_msg
            ) from storage_api_error
        except Exception as upload_err:
            logger.error(
                f"CRUD: Unexpected error during storage upload call for user {user_id}, place {place_id}: {upload_err}",
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
            public_url = await get_url_task  # Directly returns the string URL
            logger.debug(
                f"CRUD: get_public_url returned: {public_url} (Type: {type(public_url)})"
            )
        except Exception as url_error:
            logger.error(
                f"CRUD: Uploaded '{file_path_on_storage}', but failed get_public_url for user {user_id}: {url_error}",
                exc_info=True,
            )
            # Return None, but the file *is* uploaded. Might need cleanup logic later.
            return None

        # --- Validate and Return URL ---
        if public_url and isinstance(public_url, str) and public_url.startswith("http"):
            logger.info(
                f"CRUD: Image uploaded and public URL obtained for user {user_id}, place {place_id}: {public_url}"
            )
            # --- Update place record with the new image URL ---
            # This ideally happens *after* upload succeeds. Consider atomicity.
            image_update_payload = PlaceUpdate(
                image_url=public_url, updated_at=datetime.now(timezone.utc)
            )
            updated_place_record = await update_place(
                place_id=place_id,
                user_id=user_id,
                place_update=image_update_payload,
                db=db,
            )
            if not updated_place_record:
                logger.error(
                    f"CRUD: Image uploaded to {public_url}, BUT failed to update database record for place {place_id}!"
                )
                # Maybe delete the orphaned image? Requires service client likely.
                return None  # Indicate failure despite upload

            return public_url
        else:
            logger.error(
                f"CRUD: Image possibly uploaded for user {user_id}, place {place_id}, but get_public_url returned invalid data: {public_url}"
            )
            return None

    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions from checks or upload
    except Exception as e:
        logger.error(
            f"CRUD: General error in upload_place_image logic for user {user_id}, place {place_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not upload image due to an internal error.",
        ) from e


async def delete_place(
    place_id: int,
    user_id: uuid.UUID,
    db: SupabaseClient,
    db_service: SupabaseClient | None = None,
) -> bool:
    """Soft deletes a place for a specific user by setting the deleted_at timestamp."""
    logger.warning(f"CRUD: Soft deleting place ID {place_id} for user {user_id}.")

    # Optional: Fetch place first to get image URL for later deletion
    place_to_delete = await get_place_by_id(
        place_id=place_id, user_id=user_id, db=db, include_deleted=False
    )
    if not place_to_delete:
        logger.error(
            f"CRUD: Soft delete failed. Place ID {place_id} not found or not owned by user {user_id}."
        )
        # Check if already deleted
        already_deleted = await get_place_by_id(
            place_id=place_id, user_id=user_id, db=db, include_deleted=True
        )
        if already_deleted and already_deleted.deleted_at:
            logger.info(
                f"CRUD: Soft delete request for place {place_id} which is already deleted."
            )
            return True  # Treat as success if already deleted
        return False

    old_image_url = place_to_delete.image_url

    try:
        delete_time = datetime.now(timezone.utc)
        place_delete_update = PlaceUpdate(
            deleted_at=delete_time, updated_at=delete_time
        )
        update_data = place_delete_update.model_dump(mode="json", exclude_unset=True)

        logger.debug(
            f"CRUD: Data for soft delete ID {place_id} (user {user_id}): {update_data}"
        )

        # RLS Policy for UPDATE enforces ownership
        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .eq("user_id", str(user_id))  # Explicit user check
            .is_("deleted_at", None)  # Only soft delete if not already deleted
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if hasattr(response, "error") and response.error:
            error_detail = getattr(response.error, "message", str(response.error))
            logger.error(
                f"CRUD: Error soft deleting place {place_id} for user {user_id}: {error_detail}"
            )
            return False
        elif response.data:
            logger.info(
                f"CRUD: Successfully soft deleted place {place_id} for user {user_id}."
            )
            # --- Optionally delete associated image from storage ---
            if old_image_url:
                logger.info(
                    f"CRUD: Post-soft-delete: Deleting associated image '{old_image_url}' from storage."
                )
                try:
                    url_prefix = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/"
                    if old_image_url.startswith(url_prefix):
                        image_path = old_image_url[len(url_prefix) :]
                        if db_service:
                            deleted = await _delete_storage_object(
                                image_path, db_service
                            )
                            if not deleted:
                                logger.warning(
                                    f"CRUD: Failed to delete image '{image_path}' from storage after soft delete of place {place_id}."
                                )
                        else:
                            logger.warning(
                                f"CRUD: Cannot delete image '{image_path}' after soft delete of place {place_id} as service client is not available."
                            )
                    else:
                        logger.warning(
                            f"CRUD: Could not parse image path from old URL for deletion: {old_image_url}"
                        )
                except Exception as img_del_err:
                    logger.error(
                        f"CRUD: Error during image deletion after soft delete of place {place_id}: {img_del_err}",
                        exc_info=True,
                    )

            return True
        else:
            # This case means the query executed but affected 0 rows.
            # Since we checked existence beforehand, this likely means it was deleted between the check and the update.
            logger.warning(
                f"CRUD: Soft delete for place {place_id} (user {user_id}) affected no rows. Place might have been deleted concurrently."
            )
            # Re-check if it's now deleted
            final_check = await get_place_by_id(
                place_id=place_id, user_id=user_id, db=db, include_deleted=True
            )
            if final_check and final_check.deleted_at:
                logger.info(
                    f"CRUD: Confirmed place {place_id} (user {user_id}) is now soft deleted (likely concurrent)."
                )
                return True
            else:
                logger.error(
                    f"CRUD: Soft delete for place {place_id} (user {user_id}) failed unexpectedly (0 rows affected, not deleted)."
                )
                return False

    except APIError as e:
        logger.error(
            f"CRUD: PostgREST APIError in soft delete for user {user_id}, place {place_id}: {e.message}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in soft delete for user {user_id}, ID {place_id}: {e}",
            exc_info=True,
        )
        return False
