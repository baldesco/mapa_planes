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
from app.db.setup import get_db, get_supabase_service_client
from app.auth.dependencies import get_current_active_user
from app.core.config import logger

# Using APIRouter even for non-API endpoints allows for better organization
router = APIRouter(tags=["Forms"])

# TODO: Implement flash messaging for user feedback after redirects.
# Requires session middleware and template adjustments.


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
            # Rating/Review Title are not part of the basic add form
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
async def handle_edit_place_form(
    request: Request,
    place_id: int,
    db: SupabaseClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: Optional[SupabaseClient] = Depends(get_supabase_service_client),
    # Extract all fields from the edit form
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    rating: Optional[int] = Form(None),
    review_title: Optional[str] = Form(None),
    review_text: Optional[str] = Form(None),
    remove_image: Optional[str] = Form(None),  # Checkbox value is 'yes' if checked
):
    """Handles the submission of the main 'Edit Place' form."""
    logger.info(
        f"FORM Edit place submission for ID {place_id} by user {current_user.email}"
    )
    redirect_url = request.url_for("serve_root_page")

    try:
        # Construct the update payload carefully
        update_payload_dict = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "status": status_input,
            "address": address
            if address is not None
            else None,  # Allow empty string? No, map to None.
            "city": city if city is not None else None,
            "country": country if country is not None else None,
            "rating": rating,  # Pydantic handles None
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "updated_at": datetime.now(timezone.utc),
        }

        # Handle image removal intent
        if remove_image == "yes":
            update_payload_dict["image_url"] = (
                None  # Explicitly set to None for removal
            )
            logger.debug(f"Edit form signals removal of image for place {place_id}")

        # Create PlaceUpdate model, Pydantic excludes fields not explicitly set (unless None)
        place_update_data = models_places.PlaceUpdate(**update_payload_dict)

        updated_place = await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_data,
            db=db,
            db_service=db_service,  # Needed for image deletion if remove_image is checked
        )

        if updated_place is None:
            logger.error(
                f"FORM Failed to update place ID {place_id}, user {current_user.email}."
            )
            # TODO: Flash error: "Failed to save changes."
        else:
            logger.info(
                f"FORM Place ID {place_id} updated by user {current_user.email}."
            )
            # TODO: Flash success: "Place details updated."

    except ValidationError as e:
        logger.error(
            f"FORM Edit place validation error ID {place_id}, user {current_user.email}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error: "Invalid data submitted."
    except Exception as e:
        logger.error(
            f"FORM Unexpected error editing place ID {place_id}, user {current_user.email}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error: "An unexpected error occurred."

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


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
    rating: Optional[int] = Form(None),
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
        # We'll set image_url to None in the update payload later
    elif image_file and image_file.filename:
        logger.info(
            f"Processing image upload: {image_file.filename} for place {place_id}"
        )
        try:
            # Upload first, get URL
            image_public_url = await crud_places.upload_place_image(
                place_id=place_id, user_id=current_user.id, file=image_file, db=db
            )
            if image_public_url:
                logger.info(
                    f"Image uploaded successfully for place {place_id}, URL: {image_public_url}"
                )
            else:
                # Upload function failed internally (logged within crud)
                # TODO: Flash error: "Image upload failed."
                update_failed = True
        except HTTPException as http_exc:
            logger.error(
                f"Image upload failed for place {place_id}: {http_exc.status_code} - {http_exc.detail}"
            )
            # TODO: Flash error: f"Image upload failed: {http_exc.detail}"
            update_failed = True
        except Exception as e:
            logger.error(
                f"Unexpected error during image upload processing for place {place_id}: {e}",
                exc_info=True,
            )
            # TODO: Flash error: "An unexpected error occurred during image upload."
            update_failed = True

    # If upload failed, redirect immediately
    if update_failed:
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    # 2. Prepare and Execute Database Update
    try:
        update_payload = {
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "rating": rating,
            # Adding/editing review implies place was visited
            "status": models_places.PlaceStatus.VISITED,
            "updated_at": datetime.now(timezone.utc),
        }
        if should_remove_image:
            update_payload["image_url"] = None
        elif image_public_url:  # Only update URL if upload was successful
            update_payload["image_url"] = image_public_url

        # Create model only with fields that have changed or are being set
        place_update_model = models_places.PlaceUpdate(**update_payload)

        # Perform the update
        updated_place = await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_model,
            db=db,
            db_service=db_service,  # Needed if should_remove_image is true
        )

        if updated_place:
            logger.info(f"FORM Review/image details updated for place ID {place_id}.")
            # TODO: Flash success: "Review and image updated."
        else:
            logger.error(
                f"FORM Failed to update review/image details in DB for place ID {place_id}."
            )
            # This is tricky - image might be uploaded but DB failed. Orphaned image?
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
