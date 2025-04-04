from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    UploadFile,
    File,
    HTTPException,
    status,
)
from fastapi.responses import RedirectResponse
from typing import Optional
from pydantic import ValidationError
from datetime import datetime, timezone
from supabase import Client as SupabaseClient

from app.crud import places as crud_places
from app.models import places as models_places
from app.models.auth import UserInToken
from app.auth.dependencies import get_current_active_user, get_db
from app.db.setup import get_supabase_service_client
from app.core.config import logger

# Using APIRouter even for non-API endpoints allows for better organization
router = APIRouter(tags=["Forms"])

# TODO: Implement flash messaging for user feedback after redirects.


@router.post("/places/", status_code=status.HTTP_303_SEE_OTHER)
async def handle_create_new_place_form(
    request: Request,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    # Form fields extracted using Form()
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    place_status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Handles the submission of the 'Add New Place' form from the main page."""
    logger.info(f"FORM Create place received for user {current_user.email}.")
    redirect_url = request.url_for("serve_root_page")  # Use named route from pages.py
    try:
        place_data = models_places.PlaceCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=place_status_input,
            address=address,
            city=city,
            country=country,
        )
    except (ValidationError, ValueError) as e:
        logger.error(
            f"FORM Create place validation error for user {current_user.email}: {e}",
            exc_info=False,
        )
        # TODO: Add flash message: "Invalid data submitted."
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    created_place = await crud_places.create_place(
        place=place_data, user_id=current_user.id, db=db
    )

    if created_place is None:
        logger.error(
            f"FORM Failed to create place '{place_data.name}' for user {current_user.email} in DB."
        )
        # TODO: Add flash message: "Failed to save the new place."
    else:
        logger.info(
            f"FORM Place '{created_place.name}' (ID: {created_place.id}) created for user {current_user.email}."
        )
        # TODO: Add flash message: f"Place '{created_place.name}' added successfully!"

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/places/{place_id}/update-status", status_code=status.HTTP_303_SEE_OTHER)
async def handle_update_place_status_form(
    request: Request,
    place_id: int,
    new_status: models_places.PlaceStatus = Form(..., alias="status"),
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Handles status updates submitted from the map popup dropdown form."""
    logger.info(
        f"FORM Update status for place {place_id} to {new_status.value} by user {current_user.email}"
    )
    redirect_url = request.url_for("serve_root_page")
    place_update = models_places.PlaceUpdate(
        status=new_status, updated_at=datetime.now(timezone.utc)
    )
    updated_place = await crud_places.update_place(
        place_id=place_id, user_id=current_user.id, place_update=place_update, db=db
    )

    if updated_place is None:
        logger.warning(
            f"FORM Failed to update status for place ID {place_id}, user {current_user.email}."
        )
        # TODO: Add flash message: "Failed to update status."
    else:
        logger.info(
            f"FORM Status updated for place ID {place_id} by user {current_user.email}."
        )
        # TODO: Add flash message: "Status updated." (Maybe too noisy?)

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/places/{place_id}/edit", status_code=status.HTTP_303_SEE_OTHER)
async def handle_edit_place_form(  # Renamed for clarity
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    # db_service is only needed if image handling were here, remove if not needed
    # db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
    # --- Core Place Fields Only ---
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    # --- REMOVED review/rating/image fields ---
    # rating: Optional[int] = Form(None),
    # review_title: Optional[str] = Form(None),
    # review_text: Optional[str] = Form(None),
    # remove_image: Optional[str] = Form(None),
):
    """Handles the submission of the 'Edit Place' form (core details only)."""
    logger.info(
        f"FORM Edit CORE place details for ID {place_id} by user {current_user.email}"
    )
    redirect_url = request.url_for("serve_root_page")

    try:
        # Construct the update payload with only core fields
        update_payload_dict = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "status": status_input,
            "address": address if address is not None else None,
            "city": city if city is not None else None,
            "country": country if country is not None else None,
            "updated_at": datetime.now(timezone.utc),
        }

        place_update_data = models_places.PlaceUpdate(**update_payload_dict)

        updated_place = await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_data,
            db=db,
            # No db_service needed here unless image logic was re-added
        )

        if updated_place is None:
            logger.error(
                f"FORM Failed to update core details for place ID {place_id}, user {current_user.email}."
            )
            # TODO: Flash error: "Failed to save changes."
        else:
            logger.info(
                f"FORM Core details for place ID {place_id} updated by user {current_user.email}."
            )
            # TODO: Flash success: "Place details updated."

    except ValidationError as e:
        logger.error(
            f"FORM Edit core details validation error ID {place_id}, user {current_user.email}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error: "Invalid data submitted."
    except Exception as e:
        logger.error(
            f"FORM Unexpected error editing core details for place ID {place_id}, user {current_user.email}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error: "An unexpected error occurred."

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# This endpoint remains unchanged as it already handles review/rating/image
@router.post("/places/{place_id}/review-image", status_code=status.HTTP_303_SEE_OTHER)
async def handle_add_review_image_form(
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
    # Form fields for review/image
    review_title: str = Form(""),
    review_text: str = Form(""),
    rating: Optional[int] = Form(None),  # Keep rating here
    image_file: Optional[UploadFile] = File(None, alias="image"),
    remove_image: Optional[str] = Form(None),  # Checkbox value 'yes'
):
    """Handles the submission of the review and image form."""
    logger.info(
        f"FORM Review/Image submission for ID {place_id} by user {current_user.email}."
    )
    redirect_url = request.url_for("serve_root_page")
    image_public_url = None
    should_remove_image = remove_image == "yes"
    update_failed = False

    # 1. Handle Image Upload/Removal Intent
    if should_remove_image:
        logger.info(
            f"Review form signals removal of existing image for place {place_id}"
        )
    elif image_file and image_file.filename:
        logger.info(
            f"Processing image upload: {image_file.filename} for place {place_id}"
        )
        try:
            image_public_url = await crud_places.upload_place_image(
                place_id=place_id, user_id=current_user.id, file=image_file, db=db
            )
            if image_public_url:
                logger.info(
                    f"Image uploaded successfully for place {place_id}, URL: {image_public_url}"
                )
            else:
                update_failed = True
        except HTTPException as http_exc:
            logger.error(
                f"Image upload failed for place {place_id}: {http_exc.status_code} - {http_exc.detail}"
            )
            update_failed = True
        except Exception as e:
            logger.error(
                f"Unexpected error during image upload processing for place {place_id}: {e}",
                exc_info=True,
            )
            update_failed = True

    if update_failed:
        # TODO: Add flash message: "Image upload failed. Review details not saved."
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    # 2. Prepare and Execute Database Update for Review/Rating/Image URL
    try:
        # IMPORTANT: Check if rating is empty string and convert to None
        # FastAPI/Pydantic might handle this, but being explicit is safer
        valid_rating = rating
        if isinstance(rating, str) and rating.strip() == "":
            valid_rating = None
        elif rating is not None:
            try:
                # Ensure it's a valid integer if provided
                valid_rating = int(rating)
                if not (1 <= valid_rating <= 5):
                    raise ValueError("Rating out of range")
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid rating value '{rating}' received for place {place_id}, setting to None."
                )
                valid_rating = None  # Set to None if invalid conversion

        update_payload = {
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "rating": valid_rating,  # Use validated rating
            "status": models_places.PlaceStatus.VISITED,  # Assume visited if adding review
            "updated_at": datetime.now(timezone.utc),
        }
        if should_remove_image:
            update_payload["image_url"] = None
        elif image_public_url:
            update_payload["image_url"] = image_public_url

        # Only proceed if there's actually something to update
        # (excluding status and updated_at which are always set)
        has_changes = any(
            k in update_payload
            for k in ["review_title", "review", "rating", "image_url"]
        )
        if not has_changes:
            logger.info(
                f"No review/rating/image changes submitted for place {place_id}."
            )
            # TODO: Flash info message: "No review details were changed."
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

        place_update_model = models_places.PlaceUpdate(**update_payload)

        updated_place = await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_model,
            db=db,
            db_service=db_service,
        )

        if updated_place:
            logger.info(f"FORM Review/image details updated for place ID {place_id}.")
            # TODO: Flash success: "Review details updated."
        else:
            logger.error(
                f"FORM Failed to update review/image details in DB for place ID {place_id}."
            )
            # TODO: Flash failure: "Failed to save review details."

    except ValidationError as e:
        logger.error(
            f"FORM Review/Image Pydantic validation error ID {place_id}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error: "Invalid data submitted for review."
    except Exception as e:
        logger.error(
            f"FORM Unexpected error saving review/image details ID {place_id}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error: "An unexpected error occurred while saving the review."

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/places/{place_id}/delete", status_code=status.HTTP_303_SEE_OTHER)
async def handle_delete_place_form(
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
):
    """Handles the submission of the delete confirmation from the map popup."""
    logger.warning(
        f"FORM Soft Delete request for place ID {place_id} by user {current_user.email}"
    )
    redirect_url = request.url_for("serve_root_page")
    success = await crud_places.delete_place(
        place_id=place_id, user_id=current_user.id, db=db, db_service=db_service
    )

    if not success:
        logger.error(
            f"FORM Failed to soft delete place ID {place_id} for user {current_user.email}."
        )
        # TODO: Flash error: "Failed to delete place."
    else:
        logger.info(
            f"FORM Place ID {place_id} soft deleted by user {current_user.email}."
        )
        # TODO: Flash success: "Place deleted."

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
