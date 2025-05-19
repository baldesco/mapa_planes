import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError  # type: ignore

from app.core.config import settings, logger
from app.models.visits import Visit, VisitCreate, VisitUpdate, VisitInDB
from app.models.places import PlaceStatus
from app.crud.places import _delete_storage_object  # Using helper from places CRUD

VISITS_TABLE = "visits"
PLACES_TABLE = "places"


async def _update_parent_place_status(
    db: SupabaseClient, place_id: int, user_id: uuid.UUID
):
    logger.info(
        f"CRUD Visits: Updating status for parent place {place_id} based on its visits."
    )
    visits_data = []
    try:
        visits_query = (
            db.table(VISITS_TABLE)
            .select("id, visit_datetime, rating, review_text, review_title")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
        )
        visits_response: APIResponse = await asyncio.to_thread(visits_query.execute)
        visits_data = visits_response.data or []
    except APIError as e:
        logger.error(
            f"_update_parent_place_status: APIError fetching visits for place {place_id}: {e.message}"
        )
        return
    except Exception as e:
        logger.error(
            f"_update_parent_place_status: Unexpected error fetching visits for place {place_id}: {e}",
            exc_info=True,
        )
        return

    now_utc = datetime.now(timezone.utc)

    has_future_visits = False
    for v_data in visits_data:
        try:
            visit_dt_str = v_data["visit_datetime"]
            visit_dt = datetime.fromisoformat(visit_dt_str.replace("Z", "+00:00"))
            if visit_dt.tzinfo is None:
                visit_dt = visit_dt.replace(tzinfo=timezone.utc)
            if visit_dt >= now_utc:
                has_future_visits = True
                break
        except ValueError as ve:
            logger.warning(
                f"Could not parse visit_datetime '{v_data.get('visit_datetime')}' for visit ID {v_data.get('id')}: {ve}"
            )
        except Exception as e_parse:
            logger.warning(
                f"Error processing visit_datetime for visit {v_data.get('id')}: {v_data.get('visit_datetime')}. Error: {e_parse}"
            )

    new_status_val: PlaceStatus
    if has_future_visits:
        new_status_val = PlaceStatus.PENDING_SCHEDULED
    else:
        has_reviewed_past_or_present_visit = False
        for v_data in visits_data:
            try:
                visit_dt_str = v_data["visit_datetime"]
                visit_dt = datetime.fromisoformat(visit_dt_str.replace("Z", "+00:00"))
                if visit_dt.tzinfo is None:
                    visit_dt = visit_dt.replace(tzinfo=timezone.utc)

                is_reviewed = (
                    v_data.get("rating") is not None
                    or v_data.get("review_text")
                    or v_data.get("review_title")
                )

                if is_reviewed and visit_dt < now_utc:
                    has_reviewed_past_or_present_visit = True
                    break
            except Exception:  # Skip if date unparseable or other issues
                continue

        if has_reviewed_past_or_present_visit:
            new_status_val = PlaceStatus.VISITED
        else:
            try:
                current_place_query = (
                    db.table(PLACES_TABLE)
                    .select("status")
                    .eq("id", place_id)
                    .eq("user_id", str(user_id))
                    .single()
                )
                current_place_response: APIResponse = await asyncio.to_thread(
                    current_place_query.execute
                )
                current_status_str = (
                    current_place_response.data.get("status")
                    if current_place_response.data
                    else None
                )

                if current_status_str == PlaceStatus.PENDING_PRIORITIZED.value:
                    new_status_val = PlaceStatus.PENDING_PRIORITIZED
                else:
                    new_status_val = PlaceStatus.PENDING
            except (
                APIError
            ) as e:  # Catches error if .single() finds no row or multiple rows
                logger.error(
                    f"_update_parent_place_status: APIError fetching current status for place {place_id} to revert: {e.message}"
                )
                new_status_val = PlaceStatus.PENDING
            except Exception as e:
                logger.error(
                    f"_update_parent_place_status: Unexpected error fetching current status for place {place_id} to revert: {e}",
                    exc_info=True,
                )
                new_status_val = PlaceStatus.PENDING

    logger.info(
        f"Place {place_id}: Determined final new status: {new_status_val.value}"
    )

    try:
        update_query = (
            db.table(PLACES_TABLE)
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
        )
        await asyncio.to_thread(
            update_query.execute
        )  # No need to check response.data for simple update
        logger.info(
            f"Place {place_id} status update to {new_status_val.value} processed by DB."
        )
    except APIError as e:
        logger.error(
            f"_update_parent_place_status: APIError updating status for place {place_id} to {new_status_val.value}: {e.message}"
        )
    except Exception as e:
        logger.error(
            f"_update_parent_place_status: Unexpected error updating status for place {place_id}: {e}",
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

        query = db.table(VISITS_TABLE).insert(visit_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            created_visit_data = response.data[0]
            validated_visit = VisitInDB(**created_visit_data)
            logger.info(
                f"CRUD Visits: Successfully created visit ID {validated_visit.id} for place {visit_create.place_id}"
            )
            await _update_parent_place_status(
                db, place_id=visit_create.place_id, user_id=user_id
            )
            return validated_visit
        else:
            logger.error(
                f"CRUD Visits: Failed to create visit for place {visit_create.place_id} - no data returned and no APIError raised."
            )
            return None
    except APIError as e:
        logger.error(
            f"CRUD Visits: APIError creating visit for place {visit_create.place_id}: {e.message} (Code: {e.code}, Details: {e.details})"
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
        return None
    except APIError as e:
        logger.error(
            f"CRUD Visits: APIError in get_visit_by_id for ID {visit_id}: {e.message}"
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
    except APIError as e:
        logger.error(
            f"CRUD Visits: APIError fetching visits for place {place_id}: {e.message}"
        )
        return []
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
    place_id: int,
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

    update_data_dict = visit_update.model_dump(exclude_unset=True, exclude_none=False)
    old_image_url = current_visit.image_url
    new_image_url_from_payload = update_data_dict.get("image_url")

    if image_file:
        if old_image_url and db_service:
            await _delete_storage_object(old_image_url, db_service)

        file_extension = (
            os.path.splitext(image_file.filename)[1].lower()
            if image_file.filename
            else ".jpg"
        )
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if file_extension not in allowed_extensions:
            file_extension = ".jpg"
        image_path_on_storage = f"places/{user_id}/{place_id}/visits/{visit_id}/{uuid.uuid4()}{file_extension}"
        content = await image_file.read()
        try:
            storage_from = db.storage.from_(settings.SUPABASE_BUCKET_NAME)
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
            if not update_data_dict["image_url"] and db_service:
                logger.error(
                    f"CRUD Visits: Image for visit {visit_id} uploaded, but failed to get public URL. Deleting orphaned file."
                )
                await _delete_storage_object(image_path_on_storage, db_service)
        except Exception as img_e:
            logger.error(
                f"CRUD Visits: Failed to upload image for visit {visit_id}: {img_e}",
                exc_info=True,
            )
            update_data_dict.pop("image_url", None)
    elif "image_url" in update_data_dict and new_image_url_from_payload is None:
        if old_image_url and db_service:
            await _delete_storage_object(old_image_url, db_service)
        update_data_dict["image_url"] = None
    elif "image_url" not in update_data_dict and old_image_url:
        update_data_dict["image_url"] = old_image_url

    meaningful_changes = {
        k: v for k, v in update_data_dict.items() if k != "updated_at"
    }
    if not meaningful_changes and not image_file:
        if (
            visit_update.visit_datetime is not None
            and visit_update.visit_datetime != current_visit.visit_datetime
        ):
            await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)

    update_data_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        query_builder = (
            db.table(VISITS_TABLE)
            .update(update_data_dict)
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
        )
        response: APIResponse = await asyncio.to_thread(query_builder.execute)
        # For supabase-py v2, update with default returning="minimal" returns an empty list in response.data on success.
        # An error (like RLS violation if no rows matched for this user) would typically raise APIError.
        # If 0 rows were updated because data was identical, it's still a "successful" DB operation.
        logger.info(f"CRUD Visits: Update for visit ID {visit_id} processed by DB.")

        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)
    except APIError as e:
        logger.error(f"CRUD Visits: APIError updating visit ID {visit_id}: {e.message}")
        return None
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
        logger.info(
            f"CRUD Visits: Visit ID {visit_id} not found for user {user_id}, assuming already deleted or not accessible."
        )
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return True

    if visit_to_delete.image_url and db_service:
        await _delete_storage_object(visit_to_delete.image_url, db_service)

    try:
        query = (
            db.table(VISITS_TABLE)
            .delete()
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        # If delete is successful and matches rows, response.data contains the deleted records.
        # If no rows match (already deleted or RLS), response.data is empty.
        if response.data:
            logger.info(f"CRUD Visits: Successfully deleted visit ID {visit_id}.")
        else:
            logger.warning(
                f"CRUD Visits: Delete for visit {visit_id} affected 0 rows (no data returned from DB). Assuming already gone or RLS."
            )

        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return True
    except APIError as e:
        logger.error(f"CRUD Visits: APIError deleting visit {visit_id}: {e.message}")
        # Attempt status update even on error as a safeguard, though it might also fail
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return False
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception deleting visit ID {visit_id}: {e}",
            exc_info=True,
        )
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return False
