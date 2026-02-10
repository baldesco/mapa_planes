import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set, Any
from fastapi import (
    UploadFile,
    HTTPException,
    status,
)
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError  # type: ignore

from app.core.config import settings, logger
from app.models.places import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
    PlaceCategory,
    Place,
)
from app.models.tags import Tag
from app.crud import tags as crud_tags
from app.models.visits import Visit
from app.services.timezone_service import get_timezone_from_coordinates


TABLE_NAME = "places"
PLACE_TAGS_TABLE = "place_tags"
VISITS_TABLE = "visits"


async def _delete_storage_object(path: str, db_service: SupabaseClient) -> bool:
    """
    Internal helper to delete an object from Supabase Storage using service client.
    Maintains original logic for path prefix stripping and error handling.
    """
    if not path:
        logger.warning(f"CRUD: Invalid or missing path for storage deletion: '{path}'")
        return False
    if not db_service:
        logger.error("CRUD: Service client not available for storage deletion.")
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
            logger.warning(f"CRUD: Path became empty after stripping prefixes: original '{path}'")
            return False

        logger.info(f"CRUD: Attempting to delete storage object: '{path_to_delete}' using service client.")
        storage_from = db_service.storage.from_(settings.SUPABASE_BUCKET_NAME)

        delete_task = asyncio.to_thread(storage_from.remove, [path_to_delete])
        response_list = await delete_task
        logger.debug(f"CRUD: Storage deletion response for '{path_to_delete}': {response_list}")

        if response_list and isinstance(response_list, list) and len(response_list) > 0:
            response_item = response_list[0]
            if response_item.get("error"):
                logger.error(f"CRUD: Storage deletion failed for '{path_to_delete}'. Error: {response_item.get('message', response_item.get('error'))}")
                if "NotFound" in str(response_item.get("error")):
                    return True
                return False
            return True
        elif isinstance(response_list, list) and len(response_list) == 0:
            return True
        else:
            return False
    except APIError as storage_api_error:
        err_msg = getattr(storage_api_error, "message", str(storage_api_error))
        status_code = getattr(storage_api_error, "status", "Unknown")
        if status_code == 404 or (isinstance(err_msg, str) and "not found" in err_msg.lower()):
            return True
        return False
    except Exception as e:
        logger.error(f"CRUD: General Exception during storage deletion of '{path}': {e}", exc_info=True)
        return False


async def _get_visits_for_place_ids(
    db: SupabaseClient, *, place_ids: List[int]
) -> Dict[int, List[Visit]]:
    """Original logic: Fetches and sorts visits by ID."""
    if not place_ids:
        return {}
    visits_by_place_id: Dict[int, List[Visit]] = {pid: [] for pid in place_ids}
    try:
        query = db.table(VISITS_TABLE).select("*").in_("place_id", place_ids)
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            for visit_data in response.data:
                place_id_from_visit = visit_data.get("place_id")
                if place_id_from_visit and place_id_from_visit in visits_by_place_id:
                    try:
                        visit_obj = Visit(**visit_data)
                        visits_by_place_id[place_id_from_visit].append(visit_obj)
                    except Exception as validation_error:
                        logger.error(f"CRUD Helper: Pydantic validation failed for visit {visit_data.get('id')}: {validation_error}")
        elif hasattr(response, "error") and response.error:
            logger.error(f"CRUD Helper: Error fetching visits for places {place_ids}: {response.error.message}")

        now = datetime.now(timezone.utc)
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
        logger.error(f"CRUD Helper: Unexpected error fetching visits for places {place_ids}: {e}", exc_info=True)
        return visits_by_place_id


async def _get_tags_for_place_ids(
    db: SupabaseClient, *, place_ids: List[int]
) -> Dict[int, List[Tag]]:
    """Original logic: Fetches tags for multiple places."""
    if not place_ids:
        return {}
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
                place_id_from_tag = item.get("place_id")
                tag_data = item.get("tags")
                if (
                    place_id_from_tag
                    and tag_data
                    and place_id_from_tag in tags_by_place_id
                ):
                    try:
                        tag_obj = Tag(**tag_data)
                        tags_by_place_id[place_id_from_tag].append(tag_obj)
                    except Exception as validation_error:
                        logger.error(f"CRUD Helper: Pydantic validation failed for tag: {validation_error}")
        elif hasattr(response, "error") and response.error:
            logger.error(f"CRUD Helper: Error fetching tags for places {place_ids}: {response.error.message}")

        for pid_key in tags_by_place_id:
            tags_by_place_id[pid_key].sort(key=lambda tag_item: tag_item.name)
        return tags_by_place_id
    except Exception as e:
        logger.error(f"CRUD Helper: Unexpected error fetching tags for places {place_ids}: {e}", exc_info=True)
        return tags_by_place_id


async def create_place(
    place: PlaceCreate, user_id: uuid.UUID, db: SupabaseClient
) -> Place | None:
    """
    Creates a place and returns the fully hydrated Place object.
    Updated to support SPA-Lite updates.
    """
    logger.info(f"CRUD: Attempting to create place '{place.name}' for user {user_id}")
    try:
        place_data = place.model_dump(mode="json", exclude_unset=True)
        now_utc_iso = datetime.now(timezone.utc).isoformat()
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

        query = db.table(TABLE_NAME).insert(place_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            created_place_data = response.data[0]
            logger.info(f"CRUD: Successfully created place ID {created_place_data.get('id')} for user {user_id}")
            # Re-fetch to return fully hydrated object (visits, tags) for the SPA frontend
            return await get_place_by_id(place_id=created_place_data.get("id"), user_id=user_id, db=db)
        else:
            error_detail = "Insert failed"
            if hasattr(response, "error") and response.error:
                error_detail = response.error.message
            logger.error(f"CRUD: Failed to create place '{place.name}': {error_detail}")
            return None
    except Exception as e:
        logger.error(f"CRUD: General Exception in create_place for '{place.name}': {e}", exc_info=True)
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
) -> List[Place]:
    """Original logic: Fetches list of places with all relations."""
    logger.info(f"CRUD: Fetching places for user {user_id}. Filters: cat={category}, status={status_filter}")
    try:
        select_statement = "*"
        perform_tag_join_in_select = False
        clean_tag_names = []
        if tag_names:
            clean_tag_names = [t.strip().lower() for t in tag_names if t.strip()]
            if clean_tag_names:
                select_statement = "*, place_tags!inner(tags!inner(name))"
                perform_tag_join_in_select = True

        query = db.table(TABLE_NAME).select(select_statement).order("created_at", desc=True)
        query = query.eq("user_id", str(user_id))

        if category:
            query = query.eq("category", category.value)
        if status_filter:
            query = query.eq("status", status_filter.value)
        if not include_deleted:
            query = query.is_("deleted_at", None)
        if clean_tag_names:
            query = query.in_("place_tags.tags.name", clean_tag_names)

        final_query = query.range(skip, skip + limit - 1)
        response: APIResponse = await asyncio.to_thread(final_query.execute)

        place_data_list = response.data if hasattr(response, "data") and response.data else []

        if not place_data_list:
            if hasattr(response, "error") and response.error:
                logger.error(f"CRUD: Error fetching places: {response.error.message}")
            return []

        place_ids = [p_data_item.get("id") for p_data_item in place_data_list if p_data_item.get("id")]
        tags_map = await _get_tags_for_place_ids(db=db, place_ids=place_ids)
        visits_map = await _get_visits_for_place_ids(db=db, place_ids=place_ids)

        places_validated: List[Place] = []
        for p_data_item in place_data_list:
            try:
                place_id = p_data_item.get("id")
                if not place_id or uuid.UUID(p_data_item.get("user_id")) != user_id:
                    continue
                if perform_tag_join_in_select:
                    p_data_item.pop("place_tags", None)

                p_data_item["tags"] = tags_map.get(place_id, [])
                p_data_item["visits"] = visits_map.get(place_id, [])
                
                places_validated.append(Place(**p_data_item))
            except Exception as validation_error:
                logger.error(f"CRUD: Pydantic validation error for place ID {p_data_item.get('id')}: {validation_error}")

        return places_validated
    except Exception as e:
        logger.error(f"CRUD: General Exception during get_places for user {user_id}: {e}", exc_info=True)
        return []


async def get_place_by_id(
    place_id: int, user_id: uuid.UUID, db: SupabaseClient, include_deleted: bool = False
) -> Place | None:
    """Original logic: Fetches a single place with all relations."""
    logger.debug(f"CRUD: Getting place by ID: {place_id} for user {user_id}")
    try:
        query = db.table(TABLE_NAME).select("*").eq("id", place_id).eq("user_id", str(user_id))
        if not include_deleted:
            query = query.is_("deleted_at", None)
        query = query.maybe_single()
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            place_data = response.data
            if uuid.UUID(place_data.get("user_id")) != user_id:
                return None

            place_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            visits_map = await _get_visits_for_place_ids(db=db, place_ids=[place_id])
            
            place_data["tags"] = place_tags
            place_data["visits"] = visits_map.get(place_id, [])
            
            return Place(**place_data)
        else:
            if hasattr(response, "error") and response.error:
                logger.error(f"CRUD: Error fetching place {place_id}: {response.error.message}")
            return None
    except Exception as e:
        logger.error(f"CRUD: General Exception in get_place_by_id for ID {place_id}: {e}", exc_info=True)
        return None


async def update_place(
    place_id: int,
    user_id: uuid.UUID,
    place_update: PlaceUpdate,
    db: SupabaseClient,
    db_service: SupabaseClient | None = None,
) -> Place | None:
    """
    Updates a place and returns the fully hydrated Place object.
    Updated to support SPA-Lite updates.
    """
    logger.info(f"CRUD: Attempting to update place ID {place_id} for user {user_id}")

    current_place_check = await get_place_by_id(place_id=place_id, user_id=user_id, db=db)
    if not current_place_check:
        logger.warning(f"CRUD: Update failed. Place ID {place_id} not found.")
        return None

    update_data_dict = place_update.model_dump(exclude_unset=True, exclude_none=False, exclude={"tags"})

    if "latitude" in update_data_dict or "longitude" in update_data_dict:
        new_lat = update_data_dict.get("latitude", current_place_check.latitude)
        new_lon = update_data_dict.get("longitude", current_place_check.longitude)
        if new_lat is not None and new_lon is not None:
            update_data_dict["timezone_iana"] = await get_timezone_from_coordinates(new_lat, new_lon)
        else:
            update_data_dict["timezone_iana"] = None

    if update_data_dict:
        update_data_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_data_dict.pop("deleted_at", None)

        try:
            query_builder = (
                db.table(TABLE_NAME)
                .update(update_data_dict)
                .eq("id", place_id)
                .eq("user_id", str(user_id))
                .is_("deleted_at", None)
            )
            response: APIResponse = await asyncio.to_thread(query_builder.execute)

            if not response.data and hasattr(response, "error") and response.error:
                logger.error(f"CRUD: Failed to update place ID {place_id}: {response.error.message}")
                return None
        except Exception as e:
            logger.error(f"CRUD: Exception updating place data for ID {place_id}: {e}", exc_info=True)
            return None

    if place_update.tags is not None:
        try:
            current_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            current_tag_ids: Set[int] = {tag.id for tag in current_tags}
            desired_tag_ids: Set[int] = set()
            for tag_name in place_update.tags:
                clean_name = tag_name.strip().lower()
                if not clean_name:
                    continue
                tag = await crud_tags.get_tag_by_name_for_user(db=db, name=clean_name, user_id=user_id)
                if not tag:
                    tag = await crud_tags.create_tag(db=db, name=clean_name, user_id=user_id)
                if tag and tag.id:
                    desired_tag_ids.add(tag.id)

            tags_to_add = list(desired_tag_ids - current_tag_ids)
            tags_to_remove = list(current_tag_ids - desired_tag_ids)
            if tags_to_add:
                await crud_tags.link_tags_to_place(db=db, place_id=place_id, tag_ids=tags_to_add)
            if tags_to_remove:
                await crud_tags.unlink_tags_from_place(db=db, place_id=place_id, tag_ids=tags_to_remove)
        except Exception as tag_err:
            logger.error(f"CRUD: Error updating tags for place {place_id}: {tag_err}", exc_info=True)

    return await get_place_by_id(place_id=place_id, user_id=user_id, db=db)


async def delete_place(
    place_id: int,
    user_id: uuid.UUID,
    db: SupabaseClient,
    db_service: SupabaseClient | None = None,
) -> bool:
    """Soft deletes a place. Cascade hard deletes visits, storage helper cleans images."""
    logger.warning(f"CRUD: Soft deleting place ID {place_id} for user {user_id}.")
    place_to_delete = await get_place_by_id(place_id=place_id, user_id=user_id, db=db)
    if not place_to_delete:
        return False

    if db_service and place_to_delete.visits:
        for visit_item in place_to_delete.visits:
            if visit_item.image_url:
                await _delete_storage_object(str(visit_item.image_url), db_service)

    try:
        delete_time = datetime.now(timezone.utc).isoformat()
        query = (
            db.table(TABLE_NAME)
            .update({"deleted_at": delete_time, "updated_at": delete_time})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .is_("deleted_at", None)
        )
        response: APIResponse = await asyncio.to_thread(query.execute)
        return bool(response.data)
    except Exception as e:
        logger.error(f"CRUD: General Exception in soft delete for place ID {place_id}: {e}", exc_info=True)
        return False


async def _update_place_status_after_visit_change(
    db: SupabaseClient, place_id: int, user_id: uuid.UUID
):
    """Original helper: Recalculates status based on visit dates and content."""
    try:
        visits_response = await asyncio.to_thread(
            db.table(VISITS_TABLE)
            .select("visit_datetime, rating, review_text, review_title")
            .eq("place_id", place_id)
            .eq("user_id", str(user_id))
            .execute
        )

        if hasattr(visits_response, "error") and visits_response.error:
            return

        visits_data = visits_response.data or []
        now_utc = datetime.now(timezone.utc)

        has_future_visits = any(
            datetime.fromisoformat(v["visit_datetime"].replace("Z", "+00:00")) >= now_utc
            for v in visits_data
        )

        new_status_val: PlaceStatus
        if has_future_visits:
            new_status_val = PlaceStatus.PENDING_SCHEDULED
        else:
            has_reviewed_past_visit = any(
                (v.get("rating") is not None or v.get("review_text") or v.get("review_title"))
                and datetime.fromisoformat(v["visit_datetime"].replace("Z", "+00:00")) < now_utc
                for v in visits_data
            )
            if has_reviewed_past_visit:
                new_status_val = PlaceStatus.VISITED
            else:
                current_place_response = await asyncio.to_thread(
                    db.table(TABLE_NAME).select("status").eq("id", place_id).eq("user_id", str(user_id)).single().execute
                )
                if current_place_response.data and current_place_response.data.get("status") == PlaceStatus.PENDING_PRIORITIZED.value:
                    new_status_val = PlaceStatus.PENDING_PRIORITIZED
                else:
                    new_status_val = PlaceStatus.PENDING

        await asyncio.to_thread(
            db.table(TABLE_NAME)
            .update({"status": new_status_val.value, "updated_at": now_utc.isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute
        )
    except Exception as e:
        logger.error(f"Error in _update_place_status_after_visit_change: {e}", exc_info=True)