import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status, UploadFile
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError  # type: ignore

from app.core.config import settings, logger
from app.models.visits import Visit, VisitCreate, VisitUpdate, VisitInDB
from app.models.places import PlaceStatus  # For updating place status

# Import the helper from crud.places or define a similar one here if preferred
from app.crud.places import _delete_storage_object


VISITS_TABLE = "visits"
PLACES_TABLE = "places"  # For updating place status


async def _update_parent_place_status(
    db: SupabaseClient, place_id: int, user_id: uuid.UUID
):
    """
    Updates the parent place's status based on its visits.
    Called after a visit is created, updated (review added), or deleted.
    """
    logger.info(
        f"CRUD Visits: Updating status for parent place {place_id} based on its visits."
    )
    try:
        visits_response = await asyncio.to_thread(
            db.table(VISITS_TABLE)
            .select("visit_datetime, rating, review_text, review_title")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))  # Ensure user owns the visits being checked
            .execute
        )

        if visits_response.error:
            logger.error(
                f"Failed to fetch visits for place {place_id} to update status: {visits_response.error.message}"
            )
            return

        visits_data = visits_response.data or []
        now_utc = datetime.now(timezone.utc)

        has_future_visits = any(
            datetime.fromisoformat(v["visit_datetime"].replace("Z", "+00:00"))
            >= now_utc
            for v in visits_data
        )

        new_status_val: PlaceStatus
        if has_future_visits:
            new_status_val = PlaceStatus.PENDING_SCHEDULED
        else:
            has_reviewed_past_visit = any(
                (
                    v.get("rating") is not None
                    or v.get("review_text")
                    or v.get("review_title")
                )
                and datetime.fromisoformat(v["visit_datetime"].replace("Z", "+00:00"))
                < now_utc
                for v in visits_data
            )
            if has_reviewed_past_visit:
                new_status_val = PlaceStatus.VISITED
            else:
                # If no future visits and no reviewed past visits, check current status of the place
                current_place_response = await asyncio.to_thread(
                    db.table(PLACES_TABLE)  # Query PLACES_TABLE
                    .select("status")
                    .eq("id", place_id)
                    .eq("user_id", str(user_id))
                    .single()
                    .execute
                )
                if (
                    current_place_response.data
                    and current_place_response.data.get("status")
                    == PlaceStatus.PENDING_PRIORITIZED.value
                ):
                    new_status_val = PlaceStatus.PENDING_PRIORITIZED
                else:
                    new_status_val = PlaceStatus.PENDING

        # Update the place status
        update_status_response = await asyncio.to_thread(
            db.table(PLACES_TABLE)  # Update PLACES_TABLE
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute
        )
        if update_status_response.error:
            logger.error(
                f"Failed to update status for place {place_id} to {new_status_val.value}: {update_status_response.error.message}"
            )
        else:
            logger.info(
                f"Parent Place {place_id} status updated to {new_status_val.value}."
            )

    except Exception as e:
        logger.error(
            f"Error in _update_parent_place_status for place {place_id}: {e}",
            exc_info=True,
        )


async def create_visit(
    db: SupabaseClient, visit_create: VisitCreate, user_id: uuid.UUID
) -> VisitInDB | None:
    logger.info(
        f"CRUD Visits: Creating new visit for place {visit_create.place_id} by user {user_id}"
    )
    try:
        visit_data = visit_create.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        visit_data["created_at"] = now_utc_iso
        visit_data["updated_at"] = now_utc_iso
        visit_data["user_id"] = str(user_id)
        # place_id is already in visit_create

        query = db.table(VISITS_TABLE).insert(visit_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            created_visit_data = response.data[0]
            validated_visit = VisitInDB(**created_visit_data)
            logger.info(
                f"CRUD Visits: Successfully created visit ID {validated_visit.id} for place {visit_create.place_id}"
            )
            # Update parent place status
            await _update_parent_place_status(
                db, place_id=visit_create.place_id, user_id=user_id
            )
            return validated_visit
        else:
            error_detail = "Visit insert failed"
            if hasattr(response, "error") and response.error:
                error_detail = response.error.message
            elif hasattr(response, "message"):
                error_detail = response.message
            logger.error(
                f"CRUD Visits: Failed to create visit for place {visit_create.place_id}: {error_detail}"
            )
            return None
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception creating visit for place {visit_create.place_id}: {e}",
            exc_info=True,
        )
        return None


async def get_visit_by_id(
    db: SupabaseClient, visit_id: int, user_id: uuid.UUID
) -> VisitInDB | None:
    logger.debug(f"CRUD Visits: Getting visit by ID: {visit_id} for user {user_id}")
    try:
        query = (
            db.table(VISITS_TABLE)
            .select("*")
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
            .maybe_single()
        )
        response: APIResponse = await asyncio.to_thread(query.execute)
        if response.data:
            return VisitInDB(**response.data)
        else:
            if hasattr(response, "error") and response.error:
                logger.error(
                    f"CRUD Visits: Error fetching visit {visit_id}: {response.error.message}"
                )
            else:
                logger.debug(
                    f"CRUD Visits: Visit ID {visit_id} not found for user {user_id}."
                )
            return None
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception in get_visit_by_id for ID {visit_id}: {e}",
            exc_info=True,
        )
        return None


async def get_visits_for_place(
    db: SupabaseClient, place_id: int, user_id: uuid.UUID
) -> List[Visit]:
    logger.debug(
        f"CRUD Visits: Fetching visits for place ID {place_id}, user {user_id}"
    )
    visits_list: List[Visit] = []
    try:
        query = (
            db.table(VISITS_TABLE)
            .select("*")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            for visit_data in response.data:
                try:
                    visits_list.append(Visit(**visit_data))
                except Exception as val_err:
                    logger.error(
                        f"CRUD Visits: Pydantic validation for visit data failed: {val_err}, data: {visit_data}"
                    )

        now = datetime.now(timezone.utc)
        future_visits = sorted(
            [v for v in visits_list if v.visit_datetime >= now],
            key=lambda v_item: v_item.visit_datetime,
        )
        past_visits = sorted(
            [v for v in visits_list if v.visit_datetime < now],
            key=lambda v_item: v_item.visit_datetime,
            reverse=True,
        )
        return future_visits + past_visits
    except Exception as e:
        logger.error(
            f"CRUD Visits: Error fetching visits for place {place_id}: {e}",
            exc_info=True,
        )
        return []


async def update_visit(
    db: SupabaseClient,
    visit_id: int,
    visit_update: VisitUpdate,
    user_id: uuid.UUID,
    place_id: int,  # Required to update parent place status
    db_service: Optional[SupabaseClient] = None,
    image_file: Optional[UploadFile] = None,
) -> VisitInDB | None:
    logger.info(
        f"CRUD Visits: Attempting to update visit ID {visit_id} for user {user_id}"
    )

    current_visit = await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)
    if not current_visit:
        logger.warning(
            f"CRUD Visits: Update failed. Visit ID {visit_id} not found or not owned by user {user_id}."
        )
        return None

    update_data_dict = visit_update.model_dump(
        exclude_unset=True, exclude_none=False
    )  # Keep explicit None for image_url

    # Handle image upload/removal for the visit
    old_image_url = current_visit.image_url
    new_image_url_from_payload = update_data_dict.get(
        "image_url"
    )  # This is if "image_url: null" is sent

    if image_file:  # New image uploaded
        if old_image_url and db_service:
            logger.info(
                f"CRUD Visits: Deleting old image '{old_image_url}' for visit {visit_id}"
            )
            await _delete_storage_object(old_image_url, db_service)

        file_extension = (
            os.path.splitext(image_file.filename)[1].lower()
            if image_file.filename
            else ".jpg"
        )
        # Basic validation for extension
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if file_extension not in allowed_extensions:
            file_extension = ".jpg"

        # Path: places/{user_id}/{place_id}/visits/{visit_id}/{uuid}.ext
        image_path_on_storage = f"places/{user_id}/{place_id}/visits/{visit_id}/{uuid.uuid4()}{file_extension}"
        content = await image_file.read()

        try:
            storage_from = db.storage.from_(
                settings.SUPABASE_BUCKET_NAME
            )  # User context for upload
            file_options = {
                "content-type": image_file.content_type or "application/octet-stream",
                "cache-control": "3600",
                "upsert": "false",
            }
            await asyncio.to_thread(
                storage_from.upload,
                path=image_path_on_storage,
                file=content,
                file_options=file_options,
            )
            public_url_response = await asyncio.to_thread(
                storage_from.get_public_url, image_path_on_storage
            )
            update_data_dict["image_url"] = (
                str(public_url_response) if public_url_response else None
            )
            if not update_data_dict["image_url"]:
                logger.error(
                    f"CRUD Visits: Image for visit {visit_id} uploaded, but failed to get public URL."
                )
                # Attempt to delete orphaned file
                if db_service:
                    await _delete_storage_object(image_path_on_storage, db_service)
                # Potentially raise error or return None if image upload was critical
        except Exception as img_e:
            logger.error(
                f"CRUD Visits: Failed to upload image for visit {visit_id}: {img_e}",
                exc_info=True,
            )
            # Do not proceed with update if image upload fails? Or update other fields? For now, continue.
            update_data_dict.pop(
                "image_url", None
            )  # Don't try to set a failed image_url

    elif (
        "image_url" in update_data_dict and new_image_url_from_payload is None
    ):  # Explicit request to remove image
        if old_image_url and db_service:
            logger.info(
                f"CRUD Visits: Explicitly removing image '{old_image_url}' for visit {visit_id}"
            )
            await _delete_storage_object(old_image_url, db_service)
        update_data_dict["image_url"] = None  # Ensure it's set to null in DB
    elif "image_url" in update_data_dict and new_image_url_from_payload is not None:
        # This case means image_url is being set directly, not via upload. Risky.
        # Usually, image_url is set by upload logic or cleared.
        # If we allow direct URL setting, ensure it's a valid URL. Pydantic model handles this.
        pass
    elif "image_url" not in update_data_dict and old_image_url:
        # image_url not in payload, keep existing one
        update_data_dict["image_url"] = old_image_url

    if not update_data_dict:  # No actual data to update after image handling
        logger.info(
            f"CRUD Visits: No data changes for visit {visit_id} after image processing."
        )
        # Still, update parent place status as visit_datetime might have changed if it was part of original payload
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return await get_visit_by_id(
            db=db, visit_id=visit_id, user_id=user_id
        )  # Return current state

    update_data_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        query_builder = (
            db.table(VISITS_TABLE)
            .update(update_data_dict)
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
        )
        response: APIResponse = await asyncio.to_thread(query_builder.execute)

        if not response.data and response.error:
            logger.error(
                f"CRUD Visits: Failed to update visit data for ID {visit_id}: {response.error.message}"
            )
            return None

        logger.info(f"CRUD Visits: Successfully updated visit ID {visit_id}")
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return await get_visit_by_id(
            db=db, visit_id=visit_id, user_id=user_id
        )  # Re-fetch to get latest

    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception updating visit ID {visit_id}: {e}",
            exc_info=True,
        )
        return None


async def delete_visit(
    db: SupabaseClient,
    visit_id: int,
    user_id: uuid.UUID,
    place_id: int,
    db_service: Optional[SupabaseClient] = None,
) -> bool:
    logger.warning(f"CRUD Visits: Deleting visit ID {visit_id} for user {user_id}")

    visit_to_delete = await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)
    if not visit_to_delete:
        logger.error(
            f"CRUD Visits: Delete failed. Visit ID {visit_id} not found or not owned by user {user_id}."
        )
        return False

    if visit_to_delete.image_url and db_service:
        logger.info(
            f"CRUD Visits: Deleting image '{visit_to_delete.image_url}' for visit {visit_id}"
        )
        await _delete_storage_object(visit_to_delete.image_url, db_service)

    try:
        query = (
            db.table(VISITS_TABLE)
            .delete()
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:  # Supabase delete returns the deleted records
            logger.info(f"CRUD Visits: Successfully deleted visit ID {visit_id}.")
            await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
            return True
        elif hasattr(response, "error") and response.error:
            logger.error(
                f"CRUD Visits: Error deleting visit {visit_id}: {response.error.message}"
            )
            return False
        else:  # No data and no error usually means record not found by the delete query
            logger.warning(
                f"CRUD Visits: Delete for visit {visit_id} affected 0 rows. Already deleted or RLS issue."
            )
            return False  # Consider it failed if no rows were confirmed deleted by this query

    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception deleting visit ID {visit_id}: {e}",
            exc_info=True,
        )
        return False
