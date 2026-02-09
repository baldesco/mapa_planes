import uuid
import asyncio
from typing import List, Optional
from supabase import Client as SupabaseClient
from postgrest import APIResponse

from app.core.config import logger
from app.models.tags import TagInDB

TAGS_TABLE = "tags"
PLACE_TAGS_TABLE = "place_tags"

async def get_tag_by_name_for_user(
    db: SupabaseClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Retrieves a specific tag by name (case-insensitive) for a user."""
    clean_name = name.strip().lower()
    if not clean_name:
        return None
    try:
        query = db.table(TAGS_TABLE).select("*")\
            .eq("user_id", str(user_id))\
            .eq("name", clean_name)\
            .maybe_single()
        
        response: APIResponse = await asyncio.to_thread(query.execute)
        if response.data:
            return TagInDB(**response.data)
        return None
    except Exception as e:
        logger.error(f"CRUD Tags: Get by name error: {e}")
        return None

async def create_tag(
    db: SupabaseClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Creates a new tag for a user."""
    clean_name = name.strip().lower()
    if not clean_name:
        return None

    try:
        tag_data = {"name": clean_name, "user_id": str(user_id)}
        query = db.table(TAGS_TABLE).insert(tag_data, returning="representation")
        response: APIResponse = await asyncio.to_thread(query.execute)

        if response.data:
            return TagInDB(**response.data[0])
        
        # Check if failed because it already exists
        return await get_tag_by_name_for_user(db=db, name=clean_name, user_id=user_id)
    except Exception as e:
        logger.error(f"CRUD Tags: Create error: {e}")
        return None

async def get_tags_for_user(
    db: SupabaseClient, *, user_id: uuid.UUID, query: Optional[str] = None
) -> List[TagInDB]:
    """Retrieves all tags for a user, optionally filtered by name."""
    try:
        select_query = db.table(TAGS_TABLE).select("*").eq("user_id", str(user_id))
        if query:
            select_query = select_query.ilike("name", f"%{query.strip().lower()}%")

        response: APIResponse = await asyncio.to_thread(select_query.order("name").execute)
        return [TagInDB(**tag_data) for tag_data in response.data] if response.data else []
    except Exception as e:
        logger.error(f"CRUD Tags: Get for user error: {e}")
        return []

async def link_tags_to_place(
    db: SupabaseClient, *, place_id: int, tag_ids: List[int]
) -> bool:
    """Associates tags with a place."""
    if not tag_ids:
        return True
    try:
        records = [{"place_id": place_id, "tag_id": tid} for tid in tag_ids]
        await asyncio.to_thread(
            db.table(PLACE_TAGS_TABLE).insert(records, returning="minimal").execute
        )
        return True
    except Exception as e:
        logger.error(f"CRUD Tags: Link error: {e}")
        return False

async def unlink_tags_from_place(
    db: SupabaseClient, *, place_id: int, tag_ids: List[int]
) -> bool:
    """Removes tag associations from a place."""
    if not tag_ids:
        return True
    try:
        await asyncio.to_thread(
            db.table(PLACE_TAGS_TABLE).delete()\
                .eq("place_id", place_id)\
                .in_("tag_id", tag_ids)\
                .execute
        )
        return True
    except Exception as e:
        logger.error(f"CRUD Tags: Unlink error: {e}")
        return False

async def get_tags_for_place(db: SupabaseClient, *, place_id: int) -> List[TagInDB]:
    """Retrieves all tags associated with a specific place."""
    try:
        query = db.table(PLACE_TAGS_TABLE).select("tags(*)").eq("place_id", place_id)
        response: APIResponse = await asyncio.to_thread(query.execute)
        
        tags = []
        if response.data:
            for item in response.data:
                if item.get("tags"):
                    tags.append(TagInDB(**item["tags"]))
        
        return sorted(tags, key=lambda x: x.name)
    except Exception as e:
        logger.error(f"CRUD Tags: Get for place error: {e}")
        return []