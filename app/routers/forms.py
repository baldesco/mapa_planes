from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from supabase import AsyncClient

from app.auth.dependencies import get_current_active_user, get_db
from app.core.config import logger
from app.crud import places as crud_places
from app.db.setup import get_supabase_service_client
from app.models import places as models_places
from app.models.auth import UserInToken

# Using APIRouter even for non-API endpoints allows for better organization
router = APIRouter(tags=["Forms"])

# TODO: Implement flash messaging for user feedback after redirects.


@router.post("/places/", status_code=status.HTTP_303_SEE_OTHER)
async def handle_create_new_place_form(
    request: Request,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    # Form fields extracted using Form()
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    place_status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: str | None = Form(None),
    city: str | None = Form(None),
    country: str | None = Form(None),
    # Tags are not added on creation via this form
):
    """Handles the submission of the 'Add New Place' form from the main page."""
    logger.info(f"FORM Create place received for user {current_user.email}.")
    redirect_url = request.url_for("serve_root_page")
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
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
):
    """Handles status updates submitted from the map popup dropdown form."""
    # This endpoint remains unchanged as it only updates status
    logger.info(
        f"FORM Update status for place {place_id} to {new_status.value} by user {current_user.email}"
    )
    redirect_url = request.url_for("serve_root_page")
    place_update = models_places.PlaceUpdate(
        status=new_status, updated_at=datetime.now(UTC)
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
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    # --- Core Place Fields ---
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: models_places.PlaceCategory = Form(...),
    status_input: models_places.PlaceStatus = Form(..., alias="status"),
    address: str | None = Form(None),
    city: str | None = Form(None),
    country: str | None = Form(None),
    # --- Add tags input ---
    tags_input: str = Form("", description="Comma-separated list of tag names"),
):
    """Handles the submission of the 'Edit Place' form (core details + tags)."""
    logger.info(
        f"FORM Edit CORE place details & tags for ID {place_id} by user {current_user.email}. Tags Raw: '{tags_input}'"
    )
    redirect_url = request.url_for("serve_root_page")

    # Parse tags from the comma-separated input string
    # The JS library (Tagify) should ideally populate this input correctly.
    # We still clean it up here.
    tag_list: list[str] = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    logger.debug(f"FORM Parsed tags for update: {tag_list}")

    try:
        # Construct the update payload
        update_payload_dict = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "status": status_input,
            "address": address if address is not None else None,
            "city": city if city is not None else None,
            "country": country if country is not None else None,
            "updated_at": datetime.now(UTC),
            "tags": tag_list,  # Add the parsed tag list
        }

        # Use the PlaceUpdate model for validation
        place_update_data = models_places.PlaceUpdate(**update_payload_dict)

        # The CRUD function now handles tag updates
        updated_place = await crud_places.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_data,
            db=db,
            # No db_service needed here unless image logic was re-added
        )

        if updated_place is None:
            logger.error(
                f"FORM Failed to update core details/tags for place ID {place_id}, user {current_user.email}."
            )
            # TODO: Flash error: "Failed to save changes."
        else:
            logger.info(
                f"FORM Core details/tags for place ID {place_id} updated by user {current_user.email}."
            )
            # TODO: Flash success: "Place details updated."

    except ValidationError as e:
        logger.error(
            f"FORM Edit core details/tags validation error ID {place_id}, user {current_user.email}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error: "Invalid data submitted."
    except Exception as e:
        logger.error(
            f"FORM Unexpected error editing core details/tags for place ID {place_id}, user {current_user.email}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error: "An unexpected error occurred."

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# This endpoint remains unchanged as it only handles review/rating/image
@router.post("/places/{place_id}/review-image", status_code=status.HTTP_303_SEE_OTHER)
async def handle_add_review_image_form(
    request: Request,
    place_id: int,
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: AsyncClient | None = Depends(get_supabase_service_client),
    # Form fields for review/image
    review_title: str = Form(""),
    review_text: str = Form(""),
    rating: str | None = Form(None),
    image_file: UploadFile | None = File(None, alias="image"),
    remove_image: str | None = Form(None),  # Checkbox value 'yes'
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
                logger.warning(
                    f"Image upload function returned None for place {place_id}."
                )

        except HTTPException as http_exc:
            logger.error(
                f"Image upload failed for place {place_id}: {http_exc.status_code} - {http_exc.detail}"
            )
            update_failed = True
            # TODO: Flash message with http_exc.detail
        except Exception as e:
            logger.error(
                f"Unexpected error during image upload processing for place {place_id}: {e}",
                exc_info=True,
            )
            update_failed = True
            # TODO: Flash generic error message

    if update_failed:
        # TODO: Add flash message: "Image upload failed. Review details not saved."
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    # 2. Prepare and Execute Database Update for Review/Rating/Image URL
    try:
        valid_rating: int | None = None
        if rating is not None and rating.strip() != "":
            try:
                parsed_rating = int(rating)
                if 1 <= parsed_rating <= 5:
                    valid_rating = parsed_rating
                else:
                    logger.warning(
                        f"Invalid rating value '{rating}' (out of range 1-5) received for place {place_id}, setting to None."
                    )
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid rating value '{rating}' (not an integer) received for place {place_id}, setting to None."
                )

        update_payload = {
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "rating": valid_rating,
            "status": models_places.PlaceStatus.VISITED
            if (valid_rating or review_title or review_text or image_public_url)
            else None,
            "updated_at": datetime.now(UTC),
        }
        if update_payload["status"] is None:
            del update_payload["status"]

        if should_remove_image:
            update_payload["image_url"] = None
        elif image_public_url:
            update_payload["image_url"] = image_public_url

        # Exclude tags from this update, as it only handles review/image
        keys_to_check = ["review_title", "review", "rating", "image_url", "status"]
        has_changes = any(k in update_payload for k in keys_to_check)

        if not has_changes:
            logger.info(
                f"No review/rating/image changes submitted for place {place_id}."
            )
            # TODO: Flash info message: "No review details were changed."
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

        place_update_model = models_places.PlaceUpdate(
            **{
                k: v
                for k, v in update_payload.items()
                if v is not None or k == "image_url"
            }
        )

        # Use the standard update function, which will ignore the tags field if not present
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
    db: AsyncClient = Depends(get_db),
    current_user: UserInToken = Depends(get_current_active_user),
    db_service: AsyncClient | None = Depends(get_supabase_service_client),
):
    """Handles the submission of the delete confirmation from the map popup."""
    # No changes needed for tags here
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
