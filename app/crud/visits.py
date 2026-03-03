import os
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile

from app.core.config import logger, settings
from app.crud.places import _delete_storage_object  # Using helper from places CRUD
from app.models.places import PlaceStatus
from app.models.visits import Visit, VisitCreate, VisitInDB, VisitPhoto, VisitUpdate
from supabase import AsyncClient

VISITS_TABLE = "visits"
PLACES_TABLE = "places"
VISIT_PHOTOS_TABLE = "visit_photos"


async def _update_parent_place_status(
    db: AsyncClient, place_id: int, user_id: uuid.UUID
):
    logger.info(
        f"CRUD Visits: Updating status for parent place {place_id} based on its visits."
    )
    visits_data = []
    try:
        visits_response = (
            await db.table(VISITS_TABLE)
            .select("id, visit_datetime, rating, review_text, review_title")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        visits_data = visits_response.data or []
    except Exception as e:
        logger.error(
            f"_update_parent_place_status: Unexpected error fetching visits for place {place_id}: {e}",
            exc_info=True,
        )
        return

    now_utc = datetime.now(UTC)

    has_future_visits = False
    for v_data in visits_data:
        try:
            visit_dt_str = v_data["visit_datetime"]
            visit_dt = datetime.fromisoformat(visit_dt_str.replace("Z", "+00:00"))
            if visit_dt.tzinfo is None:
                visit_dt = visit_dt.replace(tzinfo=UTC)
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
                    visit_dt = visit_dt.replace(tzinfo=UTC)

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
                current_place_response = (
                    await db.table(PLACES_TABLE)
                    .select("status")
                    .eq("id", place_id)
                    .eq("user_id", str(user_id))
                    .single()
                    .execute()
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
        await (
            db.table(PLACES_TABLE)
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        logger.info(
            f"Place {place_id} status update to {new_status_val.value} processed by DB."
        )
    except Exception as e:
        logger.error(
            f"_update_parent_place_status: Unexpected error updating status for place {place_id}: {e}",
            exc_info=True,
        )


async def create_visit(
    db: AsyncClient, visit_create: VisitCreate, user_id: uuid.UUID
) -> VisitInDB | None:
    logger.info(
        f"CRUD Visits: Creating new visit for place {visit_create.place_id} by user {user_id}"
    )
    try:
        visit_data = visit_create.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(UTC).isoformat()
        visit_data["created_at"] = now_utc_iso
        visit_data["updated_at"] = now_utc_iso
        visit_data["user_id"] = str(user_id)

        response = await db.table(VISITS_TABLE).insert(visit_data).execute()

        if response.data:
            created_visit_data = response.data[0]
            visit_id = created_visit_data["id"]

            # Backwards Compatibility: Sync image_url to visit_photos table
            if created_visit_data.get("image_url"):
                await add_visit_photo(
                    db=db,
                    visit_id=visit_id,
                    user_id=user_id,
                    image_url=created_visit_data["image_url"],
                )

            validated_visit = await get_visit_by_id(
                db=db, visit_id=visit_id, user_id=user_id
            )
            logger.info(
                f"CRUD Visits: Successfully created visit ID {visit_id} for place {visit_create.place_id}"
            )
            await _update_parent_place_status(
                db, place_id=visit_create.place_id, user_id=user_id
            )
            return validated_visit
        else:
            logger.error(
                f"CRUD Visits: Failed to create visit for place {visit_create.place_id} - no data returned."
            )
            return None
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception creating visit for place {visit_create.place_id}: {e}",
            exc_info=True,
        )
        return None


async def get_visit_by_id(
    db: AsyncClient, visit_id: int, user_id: uuid.UUID
) -> VisitInDB | None:
    try:
        response = (
            await db.table(VISITS_TABLE)
            .select("*")
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        if response.data:
            visit_data = response.data
            # Fetch photos
            try:
                photos_response = (
                    await db.table(VISIT_PHOTOS_TABLE)
                    .select("*")
                    .eq("visit_id", visit_id)
                    .order("is_main", desc=True)
                    .order("created_at", desc=False)
                    .execute()
                )
                visit_data["photos"] = photos_response.data or []
            except Exception as photo_err:
                logger.error(
                    f"CRUD Visits: Error fetching photos for visit {visit_id}: {photo_err}. Continuing without photos."
                )
                visit_data["photos"] = []
            return VisitInDB(**visit_data)
        return None
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception in get_visit_by_id for ID {visit_id}: {e}",
            exc_info=True,
        )
        return None


async def get_visits_for_place(
    db: AsyncClient, place_id: int, user_id: uuid.UUID
) -> list[Visit]:
    visits_list: list[Visit] = []
    try:
        response = (
            await db.table(VISITS_TABLE)
            .select("*")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        if response.data:
            visit_ids = [v["id"] for v in response.data]
            photos_by_visit = {}
            try:
                # Fetch all photos for these visits in one go
                photos_response = (
                    await db.table(VISIT_PHOTOS_TABLE)
                    .select("*")
                    .in_("visit_id", visit_ids)
                    .order("is_main", desc=True)
                    .order("created_at", desc=False)
                    .execute()
                )

                for photo in photos_response.data or []:
                    vid = photo["visit_id"]
                    if vid not in photos_by_visit:
                        photos_by_visit[vid] = []
                    photos_by_visit[vid].append(photo)
            except Exception as photo_err:
                logger.error(
                    f"CRUD Visits: Error fetching photos for visits: {photo_err}. Continuing without photos."
                )

            for visit_data in response.data:
                try:
                    visit_data["photos"] = photos_by_visit.get(visit_data["id"], [])
                    visits_list.append(Visit(**visit_data))
                except Exception as val_err:
                    logger.error(
                        f"CRUD Visits: Pydantic validation for visit data failed: {val_err}, data: {visit_data}"
                    )

        now = datetime.now(UTC)
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
    db: AsyncClient,
    visit_id: int,
    visit_update: VisitUpdate,
    user_id: uuid.UUID,
    place_id: int,
    db_service: AsyncClient | None = None,
    image_file: UploadFile | None = None,
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
            await storage_from.upload(
                path=image_path_on_storage,
                file=content,
                file_options=file_options,
            )
            public_url_response = await storage_from.get_public_url(
                image_path_on_storage
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

    update_data_dict["updated_at"] = datetime.now(UTC).isoformat()

    try:
        await (
            db.table(VISITS_TABLE)
            .update(update_data_dict)
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        logger.info(f"CRUD Visits: Update for visit ID {visit_id} processed by DB.")

        # Backwards Compatibility: Sync image_url change to visit_photos table
        # If image_url was updated/removed via the classic field, we want to reflect it.
        if "image_url" in update_data_dict:
            new_val = update_data_dict["image_url"]
            if new_val:
                # Add it as a photo if it doesn't exist already (best effort)
                existing_photos = (
                    await db.table(VISIT_PHOTOS_TABLE)
                    .select("*")
                    .eq("visit_id", visit_id)
                    .eq("image_url", new_val)
                    .execute()
                )
                if not existing_photos.data:
                    await add_visit_photo(
                        db=db, visit_id=visit_id, user_id=user_id, image_url=new_val
                    )
            else:
                # If image_url was cleared, we might want to clear the 'orphaned' photo record too?
                # This depends on if we want to treat the first photo in visit_photos as the legacy image_url.
                # For now, let's keep it simple: legacy field is a "main" photo.
                pass

        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception updating visit ID {visit_id}: {e}",
            exc_info=True,
        )
        return None


async def delete_visit(
    db: AsyncClient,
    visit_id: int,
    user_id: uuid.UUID,
    place_id: int,
    db_service: AsyncClient | None = None,
) -> bool:
    logger.warning(f"CRUD Visits: Deleting visit ID {visit_id} for user {user_id}")
    visit_to_delete = await get_visit_by_id(db=db, visit_id=visit_id, user_id=user_id)
    if not visit_to_delete:
        logger.info(
            f"CRUD Visits: Visit ID {visit_id} not found for user {user_id}, assuming already deleted or not accessible."
        )
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return True

    # 1. Cleanup photos in storage and DB
    if visit_to_delete.photos:
        for photo in visit_to_delete.photos:
            if db_service:
                await _delete_storage_object(str(photo.image_url), db_service)

        # Note: cascading delete in DB handles visit_photos records,
        # but we could explicitly delete them if we wanted to be sure.

    # 2. Cleanup legacy image_url
    if visit_to_delete.image_url and db_service:
        await _delete_storage_object(str(visit_to_delete.image_url), db_service)

    try:
        response = (
            await db.table(VISITS_TABLE)
            .delete()
            .eq("id", visit_id)
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            logger.info(f"CRUD Visits: Successfully deleted visit ID {visit_id}.")
        else:
            logger.warning(
                f"CRUD Visits: Delete for visit {visit_id} affected 0 rows. Assuming already gone or RLS."
            )

        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return True
    except Exception as e:
        logger.error(
            f"CRUD Visits: General Exception deleting visit ID {visit_id}: {e}",
            exc_info=True,
        )
        await _update_parent_place_status(db, place_id=place_id, user_id=user_id)
        return False


async def add_visit_photo(
    db: AsyncClient,
    visit_id: int,
    user_id: uuid.UUID,
    image_url: str,
    storage_path: str | None = None,
    is_main: bool = False,
) -> VisitPhoto | None:
    try:
        data = {
            "visit_id": visit_id,
            "user_id": str(user_id),
            "image_url": image_url,
            "storage_path": storage_path,
            "is_main": is_main,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        response = await db.table(VISIT_PHOTOS_TABLE).insert(data).execute()
        if response.data:
            return VisitPhoto(**response.data[0])
        return None
    except Exception as e:
        logger.error(
            f"CRUD Visits: Error adding photo to visit {visit_id}: {e}", exc_info=True
        )
        return None


async def delete_visit_photo(
    db: AsyncClient,
    photo_id: int,
    user_id: uuid.UUID,
    db_service: AsyncClient | None = None,
) -> bool:
    try:
        # Fetch photo to get storage path
        response = (
            await db.table(VISIT_PHOTOS_TABLE)
            .select("*")
            .eq("id", photo_id)
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        if not response.data:
            return False

        photo_data = response.data
        if db_service:
            await _delete_storage_object(photo_data["image_url"], db_service)

        await db.table(VISIT_PHOTOS_TABLE).delete().eq("id", photo_id).execute()
        return True
    except Exception as e:
        logger.error(
            f"CRUD Visits: Error deleting photo {photo_id}: {e}", exc_info=True
        )
        return False


async def set_main_photo(
    db: AsyncClient, visit_id: int, photo_id: int, user_id: uuid.UUID
) -> bool:
    try:
        # 1. Reset all photos for this visit to is_main=False
        await (
            db.table(VISIT_PHOTOS_TABLE)
            .update({"is_main": False})
            .eq("visit_id", visit_id)
            .eq("user_id", str(user_id))
            .execute()
        )

        # 2. Set the target photo to is_main=True
        response = (
            await db.table(VISIT_PHOTOS_TABLE)
            .update({"is_main": True})
            .eq("id", photo_id)
            .eq("visit_id", visit_id)
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            # 3. Sync to visits.image_url for backward compatibility
            main_photo_url = response.data[0]["image_url"]
            await (
                db.table(VISITS_TABLE)
                .update(
                    {
                        "image_url": main_photo_url,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", visit_id)
                .execute()
            )
            return True
        return False
    except Exception as e:
        logger.error(
            f"CRUD Visits: Error setting main photo {photo_id}: {e}", exc_info=True
        )
        return False
