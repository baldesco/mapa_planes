import json
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytz
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from ics import Calendar, Event
from ics.alarm import DisplayAlarm
from supabase import AsyncClient

from app.auth.dependencies import get_current_active_user, get_db
from app.core.config import logger
from app.crud import places as crud_places
from app.crud import visits as crud_visits
from app.db.setup import get_supabase_service_client
from app.models import visits as models_visits
from app.models.auth import UserInToken

router = APIRouter(prefix="/api/v1", tags=["API - Visits & Calendar"])


@router.post(
    "/places/{place_id}/visits",
    response_model=models_visits.Visit,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_visit_for_place(
    place_id: int,
    visit_in: models_visits.VisitCreate,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    place = await crud_places.get_place_by_id(
        db=db, place_id=place_id, user_id=current_user.id
    )
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent place not found or access denied.",
        )

    if visit_in.place_id != place_id:
        logger.warning(
            f"Payload place_id {visit_in.place_id} differs from path place_id {place_id}. Using path."
        )
        visit_in.place_id = place_id

    logger.info(
        f"API Create visit request for place {place_id} by user {current_user.email}"
    )

    created_visit = await crud_visits.create_visit(
        db=db, visit_create=visit_in, user_id=current_user.id
    )
    if created_visit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create visit."
        )

    return models_visits.Visit(**created_visit.model_dump())


@router.get("/places/{place_id}/visits", response_model=list[models_visits.Visit])
async def list_visits_for_place(
    place_id: int,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    place = await crud_places.get_place_by_id(
        db=db, place_id=place_id, user_id=current_user.id
    )
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or access denied.",
        )

    logger.info(f"API List visits for place {place_id}, user {current_user.email}")
    visits_list = await crud_visits.get_visits_for_place(
        db=db, place_id=place_id, user_id=current_user.id
    )
    return visits_list


@router.get("/visits/{visit_id}", response_model=models_visits.Visit)
async def get_visit_details(
    visit_id: int,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    logger.info(f"API Get visit request: ID {visit_id} by user {current_user.email}")
    visit = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if visit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or access denied.",
        )
    return models_visits.Visit(**visit.model_dump())


@router.put("/visits/{visit_id}", response_model=models_visits.Visit)
async def update_existing_visit(
    visit_id: int,
    visit_datetime: datetime | None = Form(None),
    review_title: str | None = Form(None),
    review_text: str | None = Form(None),
    rating: int | None = Form(None),
    reminder_enabled: bool | None = Form(None),
    reminder_offsets_hours_str: str | None = Form(
        None, alias="reminder_offsets_hours"
    ),
    image_url_action: str | None = Form(
        None, description="'remove' to delete image, or keep empty"
    ),
    image_file: UploadFile | None = File(None, alias="image_file"),
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: AsyncClient | None = Depends(get_supabase_service_client),
):
    logger.info(f"API Update visit request: ID {visit_id} by user {current_user.email}")

    existing_visit = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if not existing_visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or access denied.",
        )

    update_payload_dict = {}
    if visit_datetime is not None:
        update_payload_dict["visit_datetime"] = visit_datetime
    if review_title is not None:
        update_payload_dict["review_title"] = review_title
    if review_text is not None:
        update_payload_dict["review_text"] = review_text
    if rating is not None:
        update_payload_dict["rating"] = rating
    if reminder_enabled is not None:
        update_payload_dict["reminder_enabled"] = reminder_enabled

    parsed_offsets: list[int] | None = None
    if reminder_offsets_hours_str is not None:
        try:
            if reminder_offsets_hours_str.strip().startswith(
                "["
            ) and reminder_offsets_hours_str.strip().endswith("]"):
                offsets_list = json.loads(reminder_offsets_hours_str)
            elif reminder_offsets_hours_str.strip() == "":
                offsets_list = []
            else:
                offsets_list = [
                    int(s.strip())
                    for s in reminder_offsets_hours_str.split(",")
                    if s.strip()
                ]

            if not (
                isinstance(offsets_list, list)
                and all(isinstance(i, int) for i in offsets_list)
            ):
                raise ValueError("reminder_offsets_hours must be a list of integers.")
            parsed_offsets = offsets_list if offsets_list else None
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format for reminder_offsets_hours: {e}",
            )

    if parsed_offsets is not None:
        update_payload_dict["reminder_offsets_hours"] = parsed_offsets
    elif reminder_offsets_hours_str == "":
        update_payload_dict["reminder_offsets_hours"] = None

    if image_url_action == "remove":
        update_payload_dict["image_url"] = None

    try:
        visit_update_model = models_visits.VisitUpdate(**update_payload_dict)
    except Exception as pydantic_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid update data: {pydantic_error}",
        )

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
        check_visit = await crud_visits.get_visit_by_id(
            db=db, visit_id=visit_id, user_id=current_user.id
        )
        if not check_visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visit not found or access denied after update attempt.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update visit. Data might be invalid or unchanged.",
        )
    return models_visits.Visit(**updated_visit.model_dump())


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_visit(
    visit_id: int,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: AsyncClient | None = Depends(get_supabase_service_client),
):
    logger.warning(
        f"API Delete visit request: ID {visit_id} by user {current_user.email}"
    )

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
        check_again = await crud_visits.get_visit_by_id(
            db=db, visit_id=visit_id, user_id=current_user.id
        )
        if check_again:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete visit.",
            )
        else:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/visits/{visit_id}/calendar_event", response_class=Response)
async def generate_calendar_event_for_visit(
    visit_id: int,
    customization_data: models_visits.CalendarEventCustomization,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    logger.info(f"API: Generating ICS for visit {visit_id}, user {current_user.email}")

    visit = await crud_visits.get_visit_by_id(
        db=db, visit_id=visit_id, user_id=current_user.id
    )
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or access denied.",
        )

    place = await crud_places.get_place_by_id(
        db=db, place_id=visit.place_id, user_id=current_user.id
    )
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated place not found."
        )

    visit_dt_utc = visit.visit_datetime
    if visit_dt_utc.tzinfo is None:
        visit_dt_utc = visit_dt_utc.replace(tzinfo=UTC)

    duration_delta = timedelta()
    if customization_data.duration_unit == "minutes":
        duration_delta = timedelta(minutes=customization_data.duration_value)
    elif customization_data.duration_unit == "hours":
        duration_delta = timedelta(hours=customization_data.duration_value)
    elif customization_data.duration_unit == "days":
        duration_delta = timedelta(days=customization_data.duration_value)

    event_dt_end_utc = visit_dt_utc + duration_delta

    cal = Calendar()
    event = Event()
    event.uid = f"{visit.id}-{uuid.uuid4()}@mapaplanes.app"
    event.name = customization_data.event_name

    description_parts = [f"Visit to {place.name}."]
    if visit.review_title:
        description_parts.append(f"Note: {visit.review_title}")
    event.description = "\n".join(description_parts)

    location_parts = []
    if place.name:
        location_parts.append(place.name)
    if place.address:
        location_parts.append(place.address)
    if place.city:
        location_parts.append(place.city)
    if place.country:
        location_parts.append(place.country)
    event.location = ", ".join(filter(None, location_parts))

    if place.latitude is not None and place.longitude is not None:
        event.geo = (place.latitude, place.longitude)

    if place.timezone_iana:
        try:
            local_tz = pytz.timezone(place.timezone_iana)
            event.begin = visit_dt_utc.astimezone(local_tz)
            event.end = event_dt_end_utc.astimezone(local_tz)
        except pytz.UnknownTimeZoneError:
            logger.warning(
                f"Unknown timezone_iana '{place.timezone_iana}' for place {place.id}. Defaulting event to UTC."
            )
            event.begin = visit_dt_utc
            event.end = event_dt_end_utc
    else:
        event.begin = visit_dt_utc
        event.end = event_dt_end_utc

    if customization_data.remind_1_day_before:
        alarm = DisplayAlarm(
            trigger=timedelta(days=-1), display_text=f"Reminder: {event.name}"
        )
        event.alarms.append(alarm)
    if customization_data.remind_2_hours_before:
        alarm = DisplayAlarm(
            trigger=timedelta(hours=-2), display_text=f"Reminder: {event.name}"
        )
        event.alarms.append(alarm)
    if customization_data.remind_15_mins_before:
        alarm = DisplayAlarm(
            trigger=timedelta(minutes=-15), display_text=f"Reminder: {event.name}"
        )
        event.alarms.append(alarm)

    cal.events.add(event)
    ics_content = cal.serialize()

    place_name_part = "".join(c if c.isalnum() else "_" for c in place.name[:30])
    place_name_part = re.sub(r"_+", "_", place_name_part)
    place_name_part = place_name_part.strip("_")
    if not place_name_part:
        place_name_part = "event_details"

    base_filename = f"mapa_planes_visit_{visit.id}_{place_name_part}"
    if base_filename.endswith("_"):
        base_filename = base_filename.rstrip("_")

    final_filename = f"{base_filename}.ics"

    final_filename = re.sub(r"[ \.]+$", "", final_filename)

    content_disposition_header = f"attachment; filename={final_filename}"

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": content_disposition_header},
    )
