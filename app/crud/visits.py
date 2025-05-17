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
from app.crud.places import _delete_storage_object

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
        return  # Cannot proceed without visit data
    except Exception as e:
        logger.error(
            f"_update_parent_place_status: Unexpected error fetching visits for place {place_id}: {e}",
            exc_info=True,
        )
        return

    now_utc = datetime.now(timezone.utc)
    logger.debug(
        f"_update_parent_place_status: Current UTC time: {now_utc.isoformat()}"
    )
    logger.debug(
        f"_update_parent_place_status: Fetched {len(visits_data)} visits for place {place_id}: {visits_data}"
    )

    has_future_visits = False
    for v_data in visits_data:
        try:
            visit_dt_str = v_data["visit_datetime"]
            visit_dt = datetime.fromisoformat(visit_dt_str.replace("Z", "+00:00"))
            if visit_dt.tzinfo is None:
                visit_dt = visit_dt.replace(tzinfo=timezone.utc)

            logger.debug(
                f"_update_parent_place_status: Checking visit ID {v_data.get('id')}, datetime: {visit_dt.isoformat()}, Is future? {visit_dt >= now_utc}"
            )
            if visit_dt >= now_utc:
                has_future_visits = True
        except ValueError as ve:
            logger.error(
                f"Could not parse visit_datetime '{v_data.get('visit_datetime')}' for visit ID {v_data.get('id')}: {ve}"
            )
        except Exception as e_parse:
            logger.error(
                f"Error processing visit_datetime for visit {v_data.get('id')}: {v_data.get('visit_datetime')}. Error: {e_parse}"
            )

    logger.info(
        f"_update_parent_place_status: Place {place_id} - Has future visits? {has_future_visits}"
    )

    new_status_val: PlaceStatus
    if has_future_visits:
        new_status_val = PlaceStatus.PENDING_SCHEDULED
    else:
        has_reviewed_past_visit = False
        for v_data in visits_data:
            try:
                visit_dt_str = v_data["visit_datetime"]
                visit_dt = datetime.fromisoformat(visit_dt_str.replace("Z", "+00:00"))
                if visit_dt.tzinfo is None:
                    visit_dt = visit_dt.replace(tzinfo=timezone.utc)
                if (
                    v_data.get("rating") is not None
                    or v_data.get("review_text")
                    or v_data.get("review_title")
                ) and visit_dt < now_utc:
                    has_reviewed_past_visit = True
                    break
            except Exception:
                continue

        if has_reviewed_past_visit:
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
                if (
                    current_place_response.data
                    and current_place_response.data.get("status")
                    == PlaceStatus.PENDING_PRIORITIZED.value
                ):
                    new_status_val = PlaceStatus.PENDING_PRIORITIZED
                else:
                    new_status_val = PlaceStatus.PENDING
            except (
                APIError
            ) as e:  # Catch error if place itself not found (e.g. by single())
                logger.error(
                    f"_update_parent_place_status: APIError fetching current status for place {place_id}: {e.message}"
                )
                new_status_val = (
                    PlaceStatus.PENDING
                )  # Default if current status cannot be fetched
            except Exception as e:
                logger.error(
                    f"_update_parent_place_status: Unexpected error fetching current status for place {place_id}: {e}",
                    exc_info=True,
                )
                new_status_val = PlaceStatus.PENDING

    logger.info(
        f"_update_parent_place_status: Determined new status for place {place_id}: {new_status_val.value}"
    )

    try:
        update_query = (
            db.table(PLACES_TABLE)
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
        )
        update_status_response: APIResponse = await asyncio.to_thread(
            update_query.execute
        )
        # For update, data might be empty if returning=minimal (default) or if no rows matched.
        # An error would be an APIError exception.
        logger.info(
            f"_update_parent_place_status: Parent Place {place_id} status DB update processed. Data count: {len(update_status_response.data) if update_status_response.data else '0 (or minimal return)'}"
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

        if (
            response.data
        ):  # Insert with returning="representation" should have data on success
            created_visit_data = response.data[0]
            validated_visit = VisitInDB(**created_visit_data)
            logger.info(
                f"CRUD Visits: Successfully created visit ID {validated_visit.id} for place {visit_create.place_id}"
            )
            await _update_parent_place_status(
                db, place_id=visit_create.place_id, user_id=user_id
            )
            return validated_visit
        else:  # Should ideally be caught by APIError if insert fails due to DB constraint/RLS
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
        # If maybe_single() finds no data, response.data is None, no error is raised by default.
        logger.debug(
            f"CRUD Visits: Visit ID {visit_id} not found for user {user_id} (or RLS)."
        )
        return None
    except (
        APIError
    ) as e:  # Should catch if .single() was used and no row found, or other DB errors
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
        # No APIError means query was successful, even if it returned an empty list.

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
            logger.info(
                f"CRUD Visits: Deleting old image '{old_image_url}' for visit {visit_id}"
            )
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
            if not update_data_dict["image_url"]:
                logger.error(
                    f"CRUD Visits: Image for visit {visit_id} uploaded, but failed to get public URL."
                )
                if db_service:
                    await _delete_storage_object(image_path_on_storage, db_service)
        except Exception as img_e:  # Catch broad storage exceptions
            logger.error(
                f"CRUD Visits: Failed to upload image for visit {visit_id}: {img_e}",
                exc_info=True,
            )
            update_data_dict.pop(
                "image_url", None
            )  # Don't try to set a failed image_url

    elif "image_url" in update_data_dict and new_image_url_from_payload is None:
        if old_image_url and db_service:
            logger.info(
                f"CRUD Visits: Explicitly removing image '{old_image_url}' for visit {visit_id}"
            )
            await _delete_storage_object(old_image_url, db_service)
        update_data_dict["image_url"] = None
    elif "image_url" not in update_data_dict and old_image_url:
        update_data_dict["image_url"] = old_image_url

    meaningful_changes = {
        k: v for k, v in update_data_dict.items() if k != "updated_at"
    }
    if not meaningful_changes and not image_file:
        logger.info(
            f"CRUD Visits: No data changes for visit {visit_id}. Checking if status update needed due to date change."
        )
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
        # An update that matches no rows (e.g. RLS or wrong ID) will not raise APIError but response.data will be empty.
        # An actual DB error (constraint violation) WILL raise APIError.
        if not response.data:  # Check if any rows were actually updated
            logger.warning(
                f"CRUD Visits: Update for visit ID {visit_id} affected 0 rows. Visit may not exist or RLS issue."
            )
            # Re-fetch to confirm existence, if it exists, then no actual change was made or RLS.
            # If it doesn't exist, then this update effectively failed.
            check_visit = await get_visit_by_id(
                db=db, visit_id=visit_id, user_id=user_id
            )
            if not check_visit:
                return None  # Visit disappeared or was never there for this user

        logger.info(
            f"CRUD Visits: Successfully processed update for visit ID {visit_id}"
        )
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
        logger.error(
            f"CRUD Visits: Delete failed. Visit ID {visit_id} not found or not owned by user {user_id}."
        )
        return False  # Already gone or not accessible

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

        # If delete is successful and matches rows, response.data contains the deleted records.
        # If no rows match, response.data is empty, no error.
        if response.data:
            logger.info(f"CRUD Visits: Successfully deleted visit ID {visit_id}.")
            await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
            return True
        else:  # No data returned, means no rows matched the delete criteria (already deleted or RLS issue)
            logger.warning(
                f"CRUD Visits: Delete for visit {visit_id} affected 0 rows. Assuming already deleted or RLS issue."
            )
            # We should still update parent place status in case this call was to ensure it's gone
            await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
            return True  # Consider it "successfully gone"

    except APIError as e:
        logger.error(f"CRUD Visits: APIError deleting visit {visit_id}: {e.message}")
        return False
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception deleting visit ID {visit_id}: {e}",
            exc_info=True,
        )
        return False
