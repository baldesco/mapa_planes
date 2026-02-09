import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError

from app.core.config import settings, logger
from app.models.places import (
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    PlaceStatus,
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
    """Helper to delete an object from Supabase Storage."""
    if not path or not db_service:
        return False

    try:
        path_to_delete = path
        bucket_prefix = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET_NAME}/"
        
        if path.startswith(bucket_prefix):
            path_to_delete = path[len(bucket_prefix):]
        
        path_to_delete = path_to_delete.lstrip("/")
        storage_from = db_service.storage.from_(settings.SUPABASE_BUCKET_NAME)
        await asyncio.to_thread(storage_from.remove, [path_to_delete])
        return True
    except Exception as e:
        logger.error(f"CRUD: Storage deletion error: {e}")
        return False

async def _get_visits_for_place_ids(db: SupabaseClient, *, place_ids: List[int]) -> Dict[int, List[Visit]]:
    if not place_ids:
        return {}
    visits_by_place_id: Dict[int, List[Visit]] = {pid: [] for pid in place_ids}
    try:
        query = db.table(VISITS_TABLE).select("*").in_("place_id", place_ids)
        response: APIResponse = await asyncio.to_thread(query.execute)
        if response.data:
            for visit_data in response.data:
                pid = visit_data.get("place_id")
                if pid in visits_by_place_id:
                    visits_by_place_id[pid].append(Visit(**visit_data))
        
        # Sort: Future visits ascending, past visits descending
        now = datetime.now(timezone.utc)
        for pid in visits_by_place_id:
            v_list = visits_by_place_id[pid]
            future = sorted([v for v in v_list if v.visit_datetime >= now], key=lambda x: x.visit_datetime)
            past = sorted([v for v in v_list if v.visit_datetime < now], key=lambda x: x.visit_datetime, reverse=True)
            visits_by_place_id[pid] = future + past
            
        return visits_by_place_id
    except Exception as e:
        logger.error(f"CRUD: Error fetching visits: {e}")
        return visits_by_place_id

async def _get_tags_for_place_ids(db: SupabaseClient, *, place_ids: List[int]) -> Dict[int, List[Tag]]:
    if not place_ids:
        return {}
    tags_by_place_id: Dict[int, List[Tag]] = {pid: [] for pid in place_ids}
    try:
        query = db.table(PLACE_TAGS_TABLE).select("place_id, tags(*)").in_("place_id", place_ids)
        response: APIResponse = await asyncio.to_thread(query.execute)
        if response.data:
            for item in response.data:
                pid = item.get("place_id")
                tag_data = item.get("tags")
                if pid in tags_by_place_id and tag_data:
                    tags_by_place_id[pid].append(Tag(**tag_data))
        return tags_by_place_id
    except Exception as e:
        logger.error(f"CRUD: Error fetching tags: {e}")
        return tags_by_place_id

async def create_place(place: PlaceCreate, user_id: uuid.UUID, db: SupabaseClient) -> PlaceInDB | None:
    try:
        place_data = place.model_dump(mode="json", exclude_unset=True)
        now = datetime.now(timezone.utc).isoformat()
        place_data.update({"created_at": now, "updated_at": now, "user_id": str(user_id)})

        if place.latitude is not None and place.longitude is not None:
            place_data["timezone_iana"] = await get_timezone_from_coordinates(place.latitude, place.longitude)

        query = db.table(TABLE_NAME).insert(place_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            return PlaceInDB(**response.data[0], tags=[], visits=[])
        return None
    except Exception as e:
        logger.error(f"CRUD: Create place error: {e}")
        return None

async def get_places(db: SupabaseClient, user_id: uuid.UUID, **filters) -> List[Place]:
    try:
        query = db.table(TABLE_NAME).select("*").eq("user_id", str(user_id)).is_("deleted_at", None)
        
        if filters.get("category"):
            query = query.eq("category", filters["category"].value)
        if filters.get("status_filter"):
            query = query.eq("status", filters["status_filter"].value)

        response: APIResponse = await asyncio.to_thread(query.execute)
        if not response.data:
            return []

        place_ids = [p["id"] for p in response.data]
        tags_map = await _get_tags_for_place_ids(db, place_ids=place_ids)
        visits_map = await _get_visits_for_place_ids(db, place_ids=place_ids)

        return [
            Place(**p, tags=tags_map.get(p["id"], []), visits=visits_map.get(p["id"], []))
            for p in response.data
        ]
    except Exception as e:
        logger.error(f"CRUD: Get places error: {e}")
        return []

async def get_place_by_id(place_id: int, user_id: uuid.UUID, db: SupabaseClient, include_deleted: bool = False) -> Place | None:
    try:
        query = db.table(TABLE_NAME).select("*").eq("id", place_id).eq("user_id", str(user_id))
        if not include_deleted:
            query = query.is_("deleted_at", None)
        
        response: APIResponse = await asyncio.to_thread(query.maybe_single().execute)
        if not response.data:
            return None

        tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
        visits_dict = await _get_visits_for_place_ids(db, place_ids=[place_id])
        
        return Place(**response.data, tags=tags, visits=visits_dict.get(place_id, []))
    except Exception as e:
        logger.error(f"CRUD: Get place by ID error: {e}")
        return None

async def update_place(place_id: int, user_id: uuid.UUID, place_update: PlaceUpdate, db: SupabaseClient) -> Place | None:
    try:
        update_dict = place_update.model_dump(exclude_unset=True, exclude={"tags"})
        if "latitude" in update_dict or "longitude" in update_dict:
            update_dict["timezone_iana"] = await get_timezone_from_coordinates(
                update_dict.get("latitude"), update_dict.get("longitude")
            )
        
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await asyncio.to_thread(
            db.table(TABLE_NAME).update(update_dict).eq("id", place_id).eq("user_id", str(user_id)).execute
        )

        if place_update.tags is not None:
            current_tags = await crud_tags.get_tags_for_place(db=db, place_id=place_id)
            current_tag_names = {t.name for t in current_tags}
            desired_tag_names = {t.strip().lower() for t in place_update.tags if t.strip()}
            
            to_add = desired_tag_names - current_tag_names
            to_remove = current_tag_names - desired_tag_names
            
            for name in to_add:
                tag = await crud_tags.get_tag_by_name_for_user(db=db, name=name, user_id=user_id)
                if not tag: tag = await crud_tags.create_tag(db=db, name=name, user_id=user_id)
                if tag: await crud_tags.link_tags_to_place(db=db, place_id=place_id, tag_ids=[tag.id])
            
            if to_remove:
                tag_ids_to_remove = [t.id for t in current_tags if t.name in to_remove]
                await crud_tags.unlink_tags_from_place(db=db, place_id=place_id, tag_ids=tag_ids_to_remove)

        return await get_place_by_id(place_id, user_id, db)
    except Exception as e:
        logger.error(f"CRUD: Update place error: {e}")
        return None

async def delete_place(place_id: int, user_id: uuid.UUID, db: SupabaseClient, db_service: Optional[SupabaseClient] = None) -> bool:
    try:
        place = await get_place_by_id(place_id, user_id, db)
        if not place: return False

        if db_service:
            for v in place.visits:
                if v.image_url: await _delete_storage_object(v.image_url, db_service)

        await asyncio.to_thread(
            db.table(TABLE_NAME)
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", place_id)
            .eq("user_id", str(user_id))
            .execute
        )
        return True
    except Exception as e:
        logger.error(f"CRUD: Delete place error: {e}")
        return False