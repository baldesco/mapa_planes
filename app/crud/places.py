import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set
from fastapi import UploadFile, HTTPException, status
from supabase import Client as SupabaseClient
from supabase.lib.client_options import ClientOptions
from postgrest import APIResponse, APIError

from app.core.config import settings, logger
from app.models.places import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
    PlaceCategory,
)

# Import tag models and crud functions
from app.models.tags import Tag, TagInDB
from app.crud import tags as crud_tags


TABLE_NAME = "places"
PLACE_TAGS_TABLE = "place_tags"  # Define junction table name


async def _delete_storage_object(path: str, db_service: SupabaseClient):
    """Internal helper to delete an object from Supabase Storage using service client."""
    if not path or not path.startswith("places/"):
        logger.warning(f"CRUD: Invalid or missing path for storage deletion: '{path}'")
        return False
    if not db_service:
        logger.error("CRUD: Service client not available for storage deletion.")
        return False

    try:
        path_to_delete = path.lstrip("/")
        logger.info(
            f"CRUD: Attempting to delete storage object: '{path_to_delete}' using service client."
        )
        storage_from = db_service.storage.from_(settings.SUPABASE_BUCKET_NAME)

        delete_task = asyncio.to_thread(storage_from.remove, [path_to_delete])
        response = await delete_task
        logger.debug(
            f"CRUD: Storage deletion response for '{path_to_delete}': {response}"
        )

        if response and isinstance(response, list) and len(response) > 0:
            logger.info(
                f"CRUD: Successfully deleted storage object: '{path_to_delete}'"
            )
            return True
        elif response is None or (isinstance(response, list) and len(response) == 0):
            logger.warning(
                f"CRUD: Storage deletion command executed for '{path_to_delete}', but response suggests no object was deleted. Response: {response}"
            )
            return False
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


async def _get_tags_for_place_ids(
    db: SupabaseClient, *, place_ids: List[int]
) -> Dict[int, List[Tag]]:
    """Internal helper to fetch tags for a list of place IDs."""
    if not place_ids:
        return {}

    logger.debug(f"CRUD Helper: Fetching tags for place IDs: {place_ids}")
    tags_by_place_id: Dict[int, List[Tag]] = {pid: [] for pid in place_ids}
    try:
        query = (
            db.table(PLACE_TAGS_TABLE)
            .select("place_id, tags(*)")
            .in_("place_id", place_ids)
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            for item in response.data:
                place_id = item.get("place_id")
                tag_data = item.get("tags")
                if place_id and tag_data and place_id in tags_by_place_id:
                    try:
                        tag_obj = Tag(**tag_data)
                        tags_by_place_id[place_id].append(tag_obj)
                    except Exception as validation_error:
                        logger.error(
                            f"CRUD Helper: Pydantic validation failed for tag record for place {place_id}. Data: {tag_data}. Error: {validation_error}",
                            exc_info=False,
                        )

        elif hasattr(response, "error") and response.error:
            logger.error(
                f"CRUD Helper: Error fetching tags for places {place_ids}: {response.error.message}"
            )

        for pid in tags_by_place_id:
            tags_by_place_id[pid].sort(key=lambda tag: tag.name)

        return tags_by_place_id

    except APIError as e:
        logger.error(
            f"CRUD Helper: APIError fetching tags for places {place_ids}: {e.message}",
            exc_info=False,
        )
        return tags_by_place_id
    except Exception as e:
        logger.error(
            f"CRUD Helper: Unexpected error fetching tags for places {place_ids}: {e}",
            exc_info=True,
        )
        return tags_by_place_id


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
        place_data["user_id"] = str(user_id)

        if place.rating is not None:
            place_data["rating"] = place.rating

        logger.debug(f"CRUD: Data being sent to Supabase insert: {place_data}")

        query = db.table(TABLE_NAME).insert(place_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)
        logger.debug(f"Supabase insert response data: {response.data}")

        if response.data:
            created_place_data = response.data[0]
            validated_place = PlaceInDB(**created_place_data, tags=[])
            logger.info(
                f"CRUD: Successfully created and validated place ID {validated_place.id} for user {user_id}"
            )
            return validated_place
        else:
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
    tag_names: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> List[PlaceInDB]:
    """Retrieves non-deleted places for a specific user from Supabase, with optional filters including tags."""
    logger.info(
        f"CRUD: Fetching places for user {user_id}. Category: {category}, Status: {status_filter}, Tags: {tag_names}, Skip: {skip}, Limit: {limit}, IncludeDeleted: {include_deleted}"
    )
    places_validated = []
    try:
        # Determine select statement based on whether tag filtering is needed
        select_statement = "*"
        perform_tag_join_in_select = False
        clean_tag_names = []
        if tag_names:
            clean_tag_names = [t.strip().lower() for t in tag_names if t.strip()]
            if clean_tag_names:
                # Need the join in select to apply the filter
                select_statement = "*, place_tags!inner(tags!inner(name))"
                perform_tag_join_in_select = True
                logger.debug(f"CRUD: Applying tag filter for names: {clean_tag_names}")

        # Build the base query
        query = (
            db.table(TABLE_NAME).select(select_statement).order("created_at", desc=True)
        )
        query = query.eq("user_id", str(user_id))

        # Apply standard filters
        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)
        if not include_deleted:
            query = query.is_("deleted_at", None)

        # Conditionally apply tag filter using the joined path
        if clean_tag_names:
            query = query.in_("place_tags.tags.name", clean_tag_names)

        # Apply range and execute
        final_query = query.range(skip, skip + limit - 1)
        response: APIResponse = await asyncio.to_thread(final_query.execute)

        place_data_list = []
        if hasattr(response, "data") and response.data:
            place_data_list = response.data
            logger.debug(
                f"CRUD: Received {len(place_data_list)} raw place records for user {user_id}."
            )
        elif hasattr(response, "error") and response.error:
            error_detail = getattr(response.error, "message", str(response.error))
            logger.error(
                f"CRUD: Error fetching places for user {user_id}: {error_detail}"
            )
            return []
        elif not response.data:
            logger.debug(f"CRUD: No places found for user {user_id} matching criteria.")
            return []
        else:
            logger.warning(
                f"CRUD: Unexpected response structure from Supabase get_places for user {user_id}: {response}"
            )
            return []

        # Fetch Tags separately for all retrieved places
        place_ids = [p_data.get("id") for p_data in place_data_list if p_data.get("id")]
        tags_map = {}
        if place_ids:
            tags_map = await _get_tags_for_place_ids(db=db, place_ids=place_ids)

        # Validate and Combine
        for i, p_data in enumerate(place_data_list):
            try:
                place_id = p_data.get("id")
                if not place_id:
                    continue

                if uuid.UUID(p_data.get("user_id")) != user_id:
                    logger.warning(
                        f"CRUD: RLS Mismatch? Fetched place ID {place_id} belongs to another user. Skipping."
                    )
                    continue

                # Remove the join data only if we performed the join in the select
                if perform_tag_join_in_select:
                    p_data.pop("place_tags", None)

                place_tags = tags_map.get(place_id, [])
                p_data_with_tags = {**p_data, "tags": place_tags}

                validated_place = PlaceInDB(**p_data_with_tags)
                places_validated.append(validated_place)
            except Exception as validation_error:
                logger.error(
                    f"CRUD: Pydantic validation failed for place record #{i + 1} for user {user_id}. Data: {p_data}. Error: {validation_error}",
                    exc_info=False,
                )
        logger.info(
            f"CRUD: Successfully validated {len(places_validated)} place records (with tags) for user {user_id}."
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
    """Retrieves a single place by ID for a specific user from Supabase, including its tags."""
    logger.debug(
        f"CRUD: Getting place by ID: {place_id} for user {user_id}, IncludeDeleted: {include_deleted}"
    )
    try:
        query = (
            db.table(TABLE_NAME)
            .select("*")
            .eq("id", place_id)
            .eq("user_id", str(user_id))
        )

        if not include_deleted:
            query = query.is_("deleted_at", None)

        query = query.maybe_single()
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            place_data = response.data
            if uuid.UUID(place_data.get("user_id")) != user_id:
                logger.error(
                    f"CRUD: RLS Mismatch? Fetched place ID {place_id} belongs to another user ({place_data.get('user_id')}), requested by {user_id}."
                )
                return None

            place_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            place_data_with_tags = {**place_data, "tags": place_tags}
            validated_place = PlaceInDB(**place_data_with_tags)

            logger.debug(
                f"CRUD: Found place ID {place_id} (with tags) for user {user_id}"
            )
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
    """Updates an existing place for a specific user in Supabase, including handling tags."""
    logger.info(f"CRUD: Attempting to update place ID {place_id} for user {user_id}")

    # --- 1. Fetch Current Place ---
    current_place_check = await get_place_by_id(
        place_id=place_id, user_id=user_id, db=db, include_deleted=False
    )
    if not current_place_check:
        logger.warning(
            f"CRUD: Update failed. Place ID {place_id} not found or does not belong to user {user_id}."
        )
        deleted_check = await get_place_by_id(
            place_id=place_id, user_id=user_id, db=db, include_deleted=True
        )
        if deleted_check and deleted_check.deleted_at:
            logger.warning(f"CRUD: Update failed. Place ID {place_id} is deleted.")
        return None

    old_image_url = current_place_check.image_url

    # --- 2. Prepare Place Data Update ---
    update_data = place_update.model_dump(
        mode="json", exclude_unset=True, exclude_none=False, exclude={"tags"}
    )
    should_remove_image = (
        "image_url" in update_data and update_data["image_url"] is None
    )
    has_place_data_changes = bool(update_data)

    if has_place_data_changes:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data.pop("deleted_at", None)

        if place_update.rating is not None:
            update_data["rating"] = place_update.rating
        elif "rating" in update_data and update_data["rating"] is None:
            pass

        if should_remove_image:
            logger.info(f"CRUD: Explicit request to remove image for place {place_id}.")
            update_data["image_url"] = None
        elif "image_url" not in update_data and old_image_url:
            update_data.pop("image_url", None)
            logger.debug(
                f"CRUD: image_url not in update payload, keeping existing: {old_image_url}"
            )

        logger.debug(
            f"CRUD: Data being sent to Supabase update for ID {place_id} (user {user_id}): {update_data}"
        )

        # --- 3. Execute Place Table Update ---
        try:
            query = (
                db.table(TABLE_NAME)
                .update(update_data)
                .eq("id", place_id)
                .eq("user_id", str(user_id))
                .is_("deleted_at", None)
            )
            response: APIResponse = await asyncio.to_thread(query.execute)

            if not response.data:
                error_detail = "Update failed (0 rows affected), possibly RLS violation, place not found for user, or no actual data changed."
                if hasattr(response, "error") and response.error:
                    error_detail = getattr(
                        response.error, "message", str(response.error)
                    )
                logger.error(
                    f"CRUD: Failed to update place data for ID {place_id}, user {user_id}: {error_detail}"
                )
                refetched = await get_place_by_id(
                    place_id=place_id, user_id=user_id, db=db
                )
                if not refetched:
                    logger.error(
                        f"CRUD: Place ID {place_id} seems to have disappeared during update."
                    )
                    return None
                else:
                    logger.warning(
                        f"CRUD: Place ID {place_id} update affected 0 rows, but place exists. Data might be identical."
                    )
                    if not (hasattr(response, "error") and response.error):
                        pass
                    else:
                        return None

            logger.info(
                f"CRUD: Successfully updated core place data for ID {place_id}, user {user_id} (Affected rows: {len(response.data)})"
            )

            if should_remove_image and old_image_url:
                logger.info(
                    f"CRUD: Post-update: Deleting old image '{old_image_url}' from storage."
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

        except APIError as e:
            logger.error(
                f"CRUD: PostgREST APIError updating place data for user {user_id}, place {place_id}: {e.message}",
                exc_info=False,
            )
            return None
        except Exception as e:
            logger.error(
                f"CRUD: General Exception updating place data for user {user_id}, ID {place_id}: {e}",
                exc_info=True,
            )
            return None

    # --- 4. Handle Tag Updates ---
    if place_update.tags is not None:
        logger.info(
            f"CRUD: Updating tags for place {place_id}. Desired tags: {place_update.tags}"
        )
        try:
            current_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            current_tag_ids: Set[int] = {tag.id for tag in current_tags}
            logger.debug(
                f"CRUD: Current tag IDs for place {place_id}: {current_tag_ids}"
            )

            desired_tag_ids: Set[int] = set()
            for tag_name in place_update.tags:
                clean_name = tag_name.strip().lower()
                if not clean_name:
                    continue

                tag = await crud_tags.get_tag_by_name_for_user(
                    db=db, name=clean_name, user_id=user_id
                )
                if not tag:
                    tag = await crud_tags.create_tag(
                        db=db, name=clean_name, user_id=user_id
                    )

                if tag and tag.id:
                    desired_tag_ids.add(tag.id)
                else:
                    logger.error(
                        f"CRUD: Failed to find or create tag '{clean_name}' for user {user_id} during place update."
                    )

            logger.debug(
                f"CRUD: Desired tag IDs for place {place_id}: {desired_tag_ids}"
            )

            tags_to_add = list(desired_tag_ids - current_tag_ids)
            tags_to_remove = list(current_tag_ids - desired_tag_ids)

            link_success = True
            unlink_success = True
            if tags_to_add:
                logger.debug(f"CRUD: Linking tags {tags_to_add} to place {place_id}")
                link_success = await crud_tags.link_tags_to_place(
                    db=db, place_id=place_id, tag_ids=tags_to_add
                )
            if tags_to_remove:
                logger.debug(
                    f"CRUD: Unlinking tags {tags_to_remove} from place {place_id}"
                )
                unlink_success = await crud_tags.unlink_tags_from_place(
                    db=db, place_id=place_id, tag_ids=tags_to_remove
                )

            if not link_success or not unlink_success:
                logger.error(
                    f"CRUD: Failed to fully update tag associations for place {place_id}."
                )

        except Exception as tag_update_error:
            logger.error(
                f"CRUD: Error processing tag updates for place {place_id}: {tag_update_error}",
                exc_info=True,
            )

    # --- 5. Fetch Final Place Data ---
    final_updated_place = await get_place_by_id(
        place_id=place_id, user_id=user_id, db=db
    )
    if final_updated_place:
        logger.info(f"CRUD: Update process complete for place ID {place_id}.")
        return final_updated_place
    else:
        logger.error(
            f"CRUD: Failed to re-fetch place ID {place_id} after update operations."
        )
        return None


async def upload_place_image(
    place_id: int, user_id: uuid.UUID, file: UploadFile, db: SupabaseClient
) -> str | None:
    """Uploads an image to Supabase Storage under the user's path."""
    # No changes needed for tags
    logger.info(
        f"CRUD: Uploading image for place ID {place_id}, user {user_id}. Filename: {file.filename}"
    )
    if not settings.SUPABASE_BUCKET_NAME:
        logger.error("CRUD: Supabase bucket name not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image storage not configured.",
        )

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

        public_url = None
        try:
            logger.debug(
                f"CRUD: Attempting to get public URL for: {file_path_on_storage}"
            )
            get_url_task = asyncio.to_thread(
                storage_from.get_public_url, file_path_on_storage
            )
            public_url = await get_url_task
            logger.debug(
                f"CRUD: get_public_url returned: {public_url} (Type: {type(public_url)})"
            )
        except Exception as url_error:
            logger.error(
                f"CRUD: Uploaded '{file_path_on_storage}', but failed get_public_url for user {user_id}: {url_error}",
                exc_info=True,
            )
            return None

        if public_url and isinstance(public_url, str) and public_url.startswith("http"):
            logger.info(
                f"CRUD: Image uploaded and public URL obtained for user {user_id}, place {place_id}: {public_url}"
            )
            return public_url
        else:
            logger.error(
                f"CRUD: Image possibly uploaded for user {user_id}, place {place_id}, but get_public_url returned invalid data: {public_url}"
            )
            return None

    except HTTPException as http_exc:
        raise http_exc
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

    place_to_delete = await get_place_by_id(
        place_id=place_id, user_id=user_id, db=db, include_deleted=False
    )
    if not place_to_delete:
        logger.error(
            f"CRUD: Soft delete failed. Place ID {place_id} not found or not owned by user {user_id}."
        )
        already_deleted = await get_place_by_id(
            place_id=place_id, user_id=user_id, db=db, include_deleted=True
        )
        if already_deleted and already_deleted.deleted_at:
            logger.info(
                f"CRUD: Soft delete request for place {place_id} which is already deleted."
            )
            return True
        return False

    old_image_url = place_to_delete.image_url

    try:
        delete_time = datetime.now(timezone.utc)
        place_delete_update = PlaceUpdate(
            deleted_at=delete_time, updated_at=delete_time
        )
        update_data = place_delete_update.model_dump(
            mode="json", exclude_unset=True, exclude={"tags"}
        )

        logger.debug(
            f"CRUD: Data for soft delete ID {place_id} (user {user_id}): {update_data}"
        )

        query = (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .is_("deleted_at", None)
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
            logger.warning(
                f"CRUD: Soft delete for place {place_id} (user {user_id}) affected no rows. Place might have been deleted concurrently."
            )
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
