import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError

from app.core.config import settings, logger
from app.models.visits import Visit, VisitCreate, VisitUpdate, VisitInDB
from app.models.places import PlaceStatus

VISITS_TABLE = "visits"
PLACES_TABLE = "places"

async def _update_parent_place_status(db: SupabaseClient, place_id: int, user_id: uuid.UUID):
    """
    Recalculates and updates the status of a place based on its visits.
    Logic:
    1. If has future visits -> PENDING_SCHEDULED
    2. Else if has any past visit with a rating/review -> VISITED
    3. Else -> PENDING (or PENDING_PRIORITIZED if it was already that)
    """
    try:
        # Fetch all visits for this place
        v_query = db.table(VISITS_TABLE).select("visit_datetime, rating, review_text, review_title")\
            .eq("place_id", place_id).eq("user_id", str(user_id))
        v_res = await asyncio.to_thread(v_query.execute)
        visits = v_res.data or []
        
        now = datetime.now(timezone.utc)
        has_future = False
        has_reviewed_past = False

        for v in visits:
            v_dt = datetime.fromisoformat(v["visit_datetime"].replace("Z", "+00:00"))
            if v_dt >= now:
                has_future = True
                break
            if v.get("rating") or v.get("review_text") or v.get("review_title"):
                has_reviewed_past = True

        new_status = PlaceStatus.PENDING
        if has_future:
            new_status = PlaceStatus.PENDING_SCHEDULED
        elif has_reviewed_past:
            new_status = PlaceStatus.VISITED
        else:
            # Check if it was prioritized before reverting to plain pending
            p_query = db.table(PLACES_TABLE).select("status").eq("id", place_id).maybe_single()
            p_res = await asyncio.to_thread(p_query.execute)
            if p_res.data and p_res.data.get("status") == PlaceStatus.PENDING_PRIORITIZED:
                new_status = PlaceStatus.PENDING_PRIORITIZED

        await asyncio.to_thread(
            db.table(PLACES_TABLE)
            .update({"status": new_status.value, "updated_at": now.isoformat()})
            .eq("id", place_id)
            .execute
        )
    except Exception as e:
        logger.error(f"CRUD Visits: Status sync error for place {place_id}: {e}")

async def create_visit(db: SupabaseClient, visit_create: VisitCreate, user_id: uuid.UUID) -> VisitInDB | None:
    try:
        data = visit_create.model_dump(mode="json")
        now = datetime.now(timezone.utc).isoformat()
        data.update({"created_at": now, "updated_at": now, "user_id": str(user_id)})

        res = await asyncio.to_thread(
            db.table(VISITS_TABLE).insert(data, returning="representation").execute
        )
        if res.data:
            visit = VisitInDB(**res.data[0])
            await _update_parent_place_status(db, visit.place_id, user_id)
            return visit
        return None
    except Exception as e:
        logger.error(f"CRUD Visits: Create error: {e}")
        return None

async def get_visit_by_id(db: SupabaseClient, visit_id: int, user_id: uuid.UUID) -> VisitInDB | None:
    try:
        res = await asyncio.to_thread(
            db.table(VISITS_TABLE).select("*").eq("id", visit_id).eq("user_id", str(user_id)).maybe_single().execute
        )
        return VisitInDB(**res.data) if res.data else None
    except Exception as e:
        logger.error(f"CRUD Visits: Get error: {e}")
        return None

async def get_visits_for_place(db: SupabaseClient, place_id: int, user_id: uuid.UUID) -> List[Visit]:
    try:
        res = await asyncio.to_thread(
            db.table(VISITS_TABLE).select("*").eq("place_id", place_id).eq("user_id", str(user_id)).execute
        )
        # Sort logic: Soonest future first, then newest past
        visits = [Visit(**v) for v in res.data]
        now = datetime.now(timezone.utc)
        future = sorted([v for v in visits if v.visit_datetime >= now], key=lambda x: x.visit_datetime)
        past = sorted([v for v in visits if v.visit_datetime < now], key=lambda x: x.visit_datetime, reverse=True)
        return future + past
    except Exception as e:
        logger.error(f"CRUD Visits: List error: {e}")
        return []

async def update_visit(
    db: SupabaseClient, 
    visit_id: int, 
    visit_update: VisitUpdate, 
    user_id: uuid.UUID, 
    place_id: int,
    db_service: Optional[SupabaseClient] = None,
    image_file = None
) -> VisitInDB | None:
    try:
        current = await get_visit_by_id(db, visit_id, user_id)
        if not current: return None

        update_data = visit_update.model_dump(exclude_unset=True, exclude_none=False)
        
        if image_file:
            # Basic storage upload logic
            ext = image_file.filename.split('.')[-1] if '.' in image_file.filename else 'jpg'
            path = f"places/{user_id}/{place_id}/visits/{visit_id}/{uuid.uuid4()}.{ext}"
            content = await image_file.read()
            await asyncio.to_thread(db.storage.from_(settings.SUPABASE_BUCKET_NAME).upload, path, content)
            pub_url = db.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(path)
            update_data["image_url"] = str(pub_url)

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        res = await asyncio.to_thread(
            db.table(VISITS_TABLE).update(update_data).eq("id", visit_id).eq("user_id", str(user_id)).execute
        )
        
        await _update_parent_place_status(db, place_id, user_id)
        return await get_visit_by_id(db, visit_id, user_id)
    except Exception as e:
        logger.error(f"CRUD Visits: Update error: {e}")
        return None

async def delete_visit(db: SupabaseClient, visit_id: int, user_id: uuid.UUID, place_id: int, db_service: Optional[SupabaseClient] = None) -> bool:
    try:
        await asyncio.to_thread(
            db.table(VISITS_TABLE).delete().eq("id", visit_id).eq("user_id", str(user_id)).execute
        )
        await _update_parent_place_status(db, place_id, user_id)
        return True
    except Exception as e:
        logger.error(f"CRUD Visits: Delete error: {e}")
        return False