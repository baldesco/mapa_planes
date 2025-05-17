from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Response,  # Added Response import
)
from typing import List, Optional
from supabase import Client as SupabaseClient
import uuid
import json  # Added json import
from datetime import datetime  # Added datetime import

from app.crud import visits as crud_visits
from app.crud import places as crud_places
from app.models import visits as models_visits
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.db.setup import get_supabase_service_client
from app.core.config import logger

router = APIRouter(prefix="/api/v1", tags=["API - Visits"])


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
    place = await crud_places.get_place_by_id(
        db=db, place_id=place_id, user_id=current_user.id
    )
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent place not found or access denied.",
        )

    if visit_in.place_id != place_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path place_id and payload place_id mismatch.",
        )

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


@router.get("/places/{place_id}/visits", response_model=List[models_visits.Visit])
async def list_visits_for_place(
    place_id: int,
    db: SupabaseClient = Depends(get_db),
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
    db: SupabaseClient = Depends(get_db),
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
    visit_datetime: Optional[datetime] = Form(None),  # Ensure datetime is imported
    review_title: Optional[str] = Form(None),
    review_text: Optional[str] = Form(None),
    rating: Optional[int] = Form(None),
    reminder_enabled: Optional[bool] = Form(None),
    # Expect reminder_offsets_hours as a list of integers directly from the form if possible,
    # or handle JSON string if client sends it that way.
    # For simplicity with Form, let's assume client might send multiple form fields for this
    # or a single comma-separated string. If JSON string is preferred:
    reminder_offsets_hours_str: Optional[str] = Form(
        None, alias="reminder_offsets_hours"
    ),  # e.g., "12,24,48" or JSON "[12,24,48]"
    image_url_action: Optional[str] = Form(
        None, description="'remove' to delete image, or keep empty"
    ),
    image_file: Optional[UploadFile] = File(None, alias="image"),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
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

    parsed_offsets: Optional[List[int]] = None
    if reminder_offsets_hours_str is not None:
        try:
            # Attempt to parse as JSON array first
            if reminder_offsets_hours_str.startswith(
                "["
            ) and reminder_offsets_hours_str.endswith("]"):
                offsets_list = json.loads(reminder_offsets_hours_str)
            else:  # Try parsing as comma-separated string
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
            parsed_offsets = offsets_list
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format for reminder_offsets_hours (expected comma-separated integers or JSON array): {e}",
            )

    if parsed_offsets is not None:  # Only add to payload if successfully parsed
        update_payload_dict["reminder_offsets_hours"] = parsed_offsets
    elif (
        reminder_offsets_hours_str == ""
    ):  # Explicitly empty string means clear the offsets
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not update visit."
        )
    return models_visits.Visit(**updated_visit.model_dump())


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_visit(
    visit_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete visit."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
