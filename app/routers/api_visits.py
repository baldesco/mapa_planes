from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Response,
)
from typing import List, Optional
from supabase import Client as SupabaseClient
import uuid
import json
import re
from datetime import datetime, timezone, timedelta

from ics import Calendar, Event
from ics.alarm import DisplayAlarm
import pytz

from app.crud import visits as crud_visits
from app.crud import places as crud_places
from app.models import visits as models_visits
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.db.setup import get_supabase_service_client
from app.core.config import logger

router = APIRouter(prefix="/api/v1", tags=["API - Visits & Calendar"])


@router.post(
    "/places/{place_id}/visits",
    response_model=models_visits.Visit,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_visit_for_place(
    place_id: int,
    visit_in: models_visits.VisitCreate,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Creates a new visit. Triggers a place status update internally."""
    place = await crud_places.get_place_by_id(
        db=db, place_id=place_id, user_id=current_user.id
    )
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent place not found or access denied.",
        )

    if visit_in.place_id != place_id:
        visit_in.place_id = place_id

    created_visit = await crud_visits.create_visit(
        db=db, visit_create=visit_in, user_id=current_user.id
    )
    if created_visit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create visit."
        )

    return models_visits.Visit(**created_visit.model_dump())


@router.get("/places/{place_id}/visits", response_model=List[models_visits.Visit])
async def list_visits_for_place(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Returns all visits for a specific place, sorted by date."""
    visits_list = await crud_visits.get_visits_for_place(
        db=db, place_id=place_id, user_id=current_user.id
    )
    return visits_list


@router.put("/visits/{visit_id}", response_model=models_visits.Visit)
async def update_existing_visit(
    visit_id: int,
    visit_datetime: Optional[datetime] = Form(None),
    review_title: Optional[str] = Form(None),
    review_text: Optional[str] = Form(None),
    rating: Optional[int] = Form(None),
    image_url_action: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None, alias="image_file"),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """Updates a visit, review, or image. Returns the updated visit object."""
    existing_visit = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if not existing_visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or access denied.",
        )

    update_payload = {}
    if visit_datetime is not None:
        update_payload["visit_datetime"] = visit_datetime
    if review_title is not None:
        update_payload["review_title"] = review_title.strip()
    if review_text is not None:
        update_payload["review_text"] = review_text.strip()
    if rating is not None:
        update_payload["rating"] = rating
    if image_url_action == "remove":
        update_payload["image_url"] = None

    visit_update_model = models_visits.VisitUpdate(**update_payload)

    updated_visit = await crud_visits.update_visit(
        db=db,
        visit_id=visit_id,
        visit_update=visit_update_model,
        user_id=current_user.id,
        place_id=existing_visit.place_id,
        db_service=db_service,
        image_file=image_file if image_file and image_file.filename else None,
    )

    if updated_visit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update visit.",
        )
    return models_visits.Visit(**updated_visit.model_dump())


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_visit(
    visit_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """Deletes a visit. Triggers place status re-calculation."""
    visit_to_delete = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if not visit_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or access denied.",
        )

    success = await crud_visits.delete_visit(
        db=db,
        visit_id=visit_id,
        user_id=current_user.id,
        place_id=visit_to_delete.place_id,
        db_service=db_service,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete visit.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/visits/{visit_id}/calendar_event", response_class=Response)
async def generate_calendar_event_for_visit(
    visit_id: int,
    customization_data: models_visits.CalendarEventCustomization,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Generates an RFC 5545 (.ics) file for the visit."""
    visit = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found.")

    place = await crud_places.get_place_by_id(
        db=db, place_id=visit.place_id, user_id=current_user.id
    )
    
    visit_dt_utc = visit.visit_datetime.replace(tzinfo=timezone.utc)
    duration = timedelta(**{customization_data.duration_unit: customization_data.duration_value})

    cal = Calendar()
    event = Event()
    event.name = customization_data.event_name
    event.begin = visit_dt_utc
    event.end = visit_dt_utc + duration
    event.location = f"{place.name}, {place.address}" if place.address else place.name
    
    if place.timezone_iana:
        try:
            local_tz = pytz.timezone(place.timezone_iana)
            event.begin = visit_dt_utc.astimezone(local_tz)
            event.end = (visit_dt_utc + duration).astimezone(local_tz)
        except:
            pass

    cal.events.add(event)
    
    return Response(
        content=cal.serialize(),
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=visit.ics"},
    )