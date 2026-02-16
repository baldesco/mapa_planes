import os
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile
from supabase import AsyncClient

from app.core.config import logger, settings
from app.crud import tags as crud_tags
from app.models.places import (
    Place,
    PlaceCategory,
    PlaceCreate,
    PlaceStatus,
    PlaceUpdate,
)
from app.models.tags import Tag
from app.models.visits import Visit
from app.services.timezone_service import get_timezone_from_coordinates

TABLE_NAME = "places"
PLACE_TAGS_TABLE = "place_tags"
VISITS_TABLE = "visits"


async def _delete_storage_object(path: str, db_service: AsyncClient) -> bool:
    """
    Internal helper to delete an object from Supabase Storage asynchronously.
    Maintains original logic for path prefix stripping.
    """
    if not path:
        logger.warning(f"CRUD: Invalid or missing path for storage deletion: '{path}'")
        return False

    try:
        path_to_delete = path
        bucket_prefix_http = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/"
        bucket_prefix_storage_api = f"{settings.SUPABASE_BUCKET_NAME}/"

        if path.startswith(bucket_prefix_http):
            path_to_delete = path[len(bucket_prefix_http) :]
        elif path.startswith(bucket_prefix_storage_api):
            path_to_delete = path[len(bucket_prefix_storage_api) :]

        path_to_delete = path_to_delete.lstrip("/")

        if not path_to_delete:
            logger.warning(
                f"CRUD: Path became empty after stripping prefixes: original '{path}'"
            )
            return False

        logger.info(f"CRUD: Attempting to delete storage object: '{path_to_delete}'")
        # Native async storage call
        await db_service.storage.from_(settings.SUPABASE_BUCKET_NAME).remove(
            [path_to_delete]
        )
        return True
    except Exception as e:
        logger.error(
            f"CRUD: Exception during storage deletion of '{path}': {e}", exc_info=True
        )
        return False


async def _get_visits_for_place_ids(
    db: AsyncClient, *, place_ids: list[int]
) -> dict[int, list[Visit]]:
    """Fetches and sorts visits by ID asynchronously."""
    if not place_ids:
        return {}
    visits_by_place_id: dict[int, list[Visit]] = {pid: [] for pid in place_ids}
    try:
        response = (
            await db.table(VISITS_TABLE)
            .select("*")
            .in_("place_id", place_ids)
            .execute()
        )

        if response.data:
            for visit_data in response.data:
                pid = visit_data.get("place_id")
                if pid and pid in visits_by_place_id:
                    try:
                        visits_by_place_id[pid].append(Visit(**visit_data))
                    except Exception as validation_error:
                        logger.error(
                            f"CRUD Helper: Pydantic validation failed for visit {visit_data.get('id')}: {validation_error}"
                        )

        now = datetime.now(UTC)
        for pid_key in visits_by_place_id:
            future_visits = sorted(
                [v for v in visits_by_place_id[pid_key] if v.visit_datetime >= now],
                key=lambda v_item: v_item.visit_datetime,
            )
            past_visits = sorted(
                [v for v in visits_by_place_id[pid_key] if v.visit_datetime < now],
                key=lambda v_item: v_item.visit_datetime,
                reverse=True,
            )
            visits_by_place_id[pid_key] = future_visits + past_visits
        return visits_by_place_id
    except Exception as e:
        logger.error(
            f"CRUD Helper: Unexpected error fetching visits: {e}", exc_info=True
        )
        return visits_by_place_id


async def _get_tags_for_place_ids(
    db: AsyncClient, *, place_ids: list[int]
) -> dict[int, list[Tag]]:
    """Fetches tags for multiple places asynchronously."""
    if not place_ids:
        return {}
    tags_by_place_id: dict[int, list[Tag]] = {pid: [] for pid in place_ids}
    try:
        response = (
            await db.table(PLACE_TAGS_TABLE)
            .select("place_id, tags(*)")
            .in_("place_id", place_ids)
            .execute()
        )

        if response.data:
            for item in response.data:
                place_id_from_tag = item.get("place_id")
                tag_data = item.get("tags")
                if (
                    place_id_from_tag
                    and tag_data
                    and place_id_from_tag in tags_by_place_id
                ):
                    try:
                        tags_by_place_id[place_id_from_tag].append(Tag(**tag_data))
                    except Exception as validation_error:
                        logger.error(
                            f"CRUD Helper: Pydantic validation failed for tag: {validation_error}"
                        )

        for pid_key in tags_by_place_id:
            tags_by_place_id[pid_key].sort(key=lambda tag_item: tag_item.name)
        return tags_by_place_id
    except Exception as e:
        logger.error(f"CRUD Helper: Unexpected error fetching tags: {e}", exc_info=True)
        return tags_by_place_id


async def create_place(
    place: PlaceCreate, user_id: uuid.UUID, db: AsyncClient
) -> Place | None:
    """Creates a place and returns the fully hydrated Place object asynchronously."""
    logger.info(f"CRUD: Attempting to create place '{place.name}' for user {user_id}")
    try:
        place_data = place.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(UTC).isoformat()
        place_data["created_at"] = now_utc_iso
        place_data["updated_at"] = now_utc_iso
        place_data["deleted_at"] = None
        place_data["user_id"] = str(user_id)

        if (
            place.latitude is not None
            and place.longitude is not None
            and place.timezone_iana is None
        ):
            place_data["timezone_iana"] = await get_timezone_from_coordinates(
                place.latitude, place.longitude
            )

        response = await db.table(TABLE_NAME).insert(place_data).execute()

        if response.data:
            created_id = response.data[0].get("id")
            return await get_place_by_id(place_id=created_id, user_id=user_id, db=db)
        return None
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in create_place for '{place.name}': {e}",
            exc_info=True,
        )
        return None


async def get_places(
    db: AsyncClient,
    user_id: uuid.UUID,
    category: PlaceCategory | None = None,
    status_filter: PlaceStatus | None = None,
    tag_names: list[str] | None = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> list[Place]:
    """Fetches list of places with all relations asynchronously."""
    try:
        query = (
            db.table(TABLE_NAME)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
        )

        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)
        if not include_deleted:
            query = query.is_("deleted_at", None)

        # Note: Advanced tag filtering typically requires an inner join or RPC.
        # For parity, we execute the standard query and filter by tag_names in the hydration step if provided.
        response = await query.range(skip, skip + limit - 1).execute()
        place_data_list = response.data or []

        if not place_data_list:
            return []

        place_ids = [p.get("id") for p in place_data_list]
        tags_map = await _get_tags_for_place_ids(db=db, place_ids=place_ids)
        visits_map = await _get_visits_for_place_ids(db=db, place_ids=place_ids)

        places_validated: list[Place] = []
        for p_data in place_data_list:
            try:
                place_id = p_data.get("id")
                p_data["tags"] = tags_map.get(place_id, [])
                p_data["visits"] = visits_map.get(place_id, [])

                # Apply in-memory tag filter if requested
                if tag_names:
                    clean_filter = {t.strip().lower() for t in tag_names}
                    place_tag_names = {t.name.lower() for t in p_data["tags"]}
                    if not (clean_filter & place_tag_names):
                        continue

                places_validated.append(Place(**p_data))
            except Exception as validation_error:
                logger.error(
                    f"CRUD: Pydantic validation error for place ID {p_data.get('id')}: {validation_error}"
                )

        return places_validated
    except Exception as e:
        logger.error(f"CRUD: General Exception during get_places: {e}", exc_info=True)
        return []


async def get_place_by_id(
    place_id: int, user_id: uuid.UUID, db: AsyncClient, include_deleted: bool = False
) -> Place | None:
    """Fetches a single place with all relations asynchronously."""
    try:
        query = (
            db.table(TABLE_NAME)
            .select("*")
            .eq("id", place_id)
            .eq("user_id", str(user_id))
        )
        if not include_deleted:
            query = query.is_("deleted_at", None)

        response = await query.maybe_single().execute()

        if response.data:
            place_data = response.data
            place_data["tags"] = await crud_tags.get_tags_for_place(
                db=db, place_id=place_id
            )
            visits_map = await _get_visits_for_place_ids(db=db, place_ids=[place_id])
            place_data["visits"] = visits_map.get(place_id, [])
            return Place(**place_data)
        return None
    except Exception as e:
        logger.error(
            f"CRUD: Exception in get_place_by_id for ID {place_id}: {e}", exc_info=True
        )
        return None


async def update_place(
    place_id: int,
    user_id: uuid.UUID,
    place_update: PlaceUpdate,
    db: AsyncClient,
    db_service: AsyncClient | None = None,
) -> Place | None:
    """Updates a place and returns the fully hydrated Place object asynchronously."""
    logger.info(f"CRUD: Attempting to update place ID {place_id} for user {user_id}")

    current = await get_place_by_id(place_id=place_id, user_id=user_id, db=db)
    if not current:
        return None

    update_data = place_update.model_dump(
        exclude_unset=True, exclude_none=False, exclude={"tags"}
    )

    if "latitude" in update_data or "longitude" in update_data:
        new_lat = update_data.get("latitude", current.latitude)
        new_lon = update_data.get("longitude", current.longitude)
        if new_lat is not None and new_lon is not None:
            update_data["timezone_iana"] = await get_timezone_from_coordinates(
                new_lat, new_lon
            )

    if update_data:
        update_data["updated_at"] = datetime.now(UTC).isoformat()
        update_data.pop("deleted_at", None)
        await (
            db.table(TABLE_NAME)
            .update(update_data)
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )

    if place_update.tags is not None:
        try:
            current_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            current_tag_ids: set[int] = {tag.id for tag in current_tags}
            desired_tag_ids: set[int] = set()
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

            tags_to_add = list(desired_tag_ids - current_tag_ids)
            tags_to_remove = list(current_tag_ids - desired_tag_ids)
            if tags_to_add:
                await crud_tags.link_tags_to_place(
                    db=db, place_id=place_id, tag_ids=tags_to_add
                )
            if tags_to_remove:
                await crud_tags.unlink_tags_from_place(
                    db=db, place_id=place_id, tag_ids=tags_to_remove
                )
        except Exception as tag_err:
            logger.error(
                f"CRUD: Error updating tags for place {place_id}: {tag_err}",
                exc_info=True,
            )

    return await get_place_by_id(place_id=place_id, user_id=user_id, db=db)


async def delete_place(
    place_id: int,
    user_id: uuid.UUID,
    db: AsyncClient,
    db_service: AsyncClient | None = None,
) -> bool:
    """Soft deletes a place and cleans up assets asynchronously."""
    place_to_delete = await get_place_by_id(place_id=place_id, user_id=user_id, db=db)
    if not place_to_delete:
        return False

    if db_service and place_to_delete.visits:
        for visit_item in place_to_delete.visits:
            if visit_item.image_url:
                await _delete_storage_object(str(visit_item.image_url), db_service)

    try:
        delete_time = datetime.now(UTC).isoformat()
        response = (
            await db.table(TABLE_NAME)
            .update({"deleted_at": delete_time, "updated_at": delete_time})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        logger.error(
            f"CRUD: General Exception in soft delete for ID {place_id}: {e}",
            exc_info=True,
        )
        return False


async def _update_place_status_after_visit_change(
    db: AsyncClient, place_id: int, user_id: uuid.UUID
):
    """Recalculates place status based on visit dates and content asynchronously."""
    try:
        visits_response = (
            await db.table(VISITS_TABLE)
            .select("visit_datetime, rating, review_text, review_title")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )

        visits_data = visits_response.data or []
        now_utc = datetime.now(UTC)

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
                current_place_response = (
                    await db.table(TABLE_NAME)
                    .select("status")
                    .eq("id", place_id)
                    .eq("user_id", str(user_id))
                    .maybe_single()
                    .execute()
                )
                if (
                    current_place_response.data
                    and current_place_response.data.get("status")
                    == PlaceStatus.PENDING_PRIORITIZED.value
                ):
                    new_status_val = PlaceStatus.PENDING_PRIORITIZED
                else:
                    new_status_val = PlaceStatus.PENDING

        await (
            db.table(TABLE_NAME)
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as e:
        logger.error(
            f"Error in _update_place_status_after_visit_change: {e}", exc_info=True
        )


async def upload_place_image(
    place_id: int, user_id: uuid.UUID, file: UploadFile, db: AsyncClient
) -> str | None:
    """
    Uploads an image to Supabase Storage for a specific place and returns the public URL.
    """
    logger.info(
        f"CRUD: Uploading image '{file.filename}' for place {place_id}, user {user_id}"
    )
    try:
        # 1. Validate extension
        file_extension = (
            os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
        )
        allowed = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if file_extension not in allowed:
            file_extension = ".jpg"

        # 2. Prepare path
        storage_path = f"places/{user_id}/{place_id}/{uuid.uuid4()}{file_extension}"

        # 3. Read content and upload
        content = await file.read()
        storage_from = db.storage.from_(settings.SUPABASE_BUCKET_NAME)

        await storage_from.upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": file.content_type or "image/jpeg",
                "cache-control": "3600",
                "upsert": "false",
            },
        )

        # 4. Get and return public URL
        public_url_response = storage_from.get_public_url(storage_path)
        return str(public_url_response) if public_url_response else None

    except Exception as e:
        logger.error(
            f"CRUD: Exception uploading image for place {place_id}: {e}", exc_info=True
        )
        return None
