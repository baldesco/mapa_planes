"""Main FastAPI application file for Mapa Planes."""

import asyncio
import folium
import html
import json
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Request,
    File,
    UploadFile,
    Form,
    Query,
    Response,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError
from typing import List, Optional
from pydantic import ValidationError

# Import local modules
from . import crud, models, database
from .core.config import settings, logger
from .models import PlaceCategory, PlaceStatus
from .database import get_db

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")

# --- Geocoding Setup ---
if not settings.OPENCAGE_API_KEY:
    logger.critical("OPENCAGE_API_KEY is not set. Geocoding endpoint will fail.")
    geocoder = None
else:
    try:
        geocoder = OpenCageGeocode(settings.OPENCAGE_API_KEY)
        logger.info("OpenCage Geocoder initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize OpenCage Geocoder: {e}", exc_info=True)
        geocoder = None


# --- Helper Functions ---
async def perform_geocode(address: str) -> models.GeocodeResult | None:
    """Performs geocoding using OpenCage Geocoder. Raises HTTPException on failure."""
    if not geocoder:
        logger.error("Geocoding skipped: OpenCage Geocoder not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service is not configured.",
        )
    try:
        logger.debug(f"Geocoding address with OpenCage: '{address}'")
        results = await asyncio.to_thread(
            geocoder.geocode,
            address,
            key=settings.OPENCAGE_API_KEY,
            language="es",
            countrycode="co",
            limit=1,
            no_annotations=1,
            timeout=10,
        )
        if results and len(results):
            best_result = results[0]
            components = best_result.get("components", {})
            geometry = best_result.get("geometry", {})
            formatted_address = best_result.get("formatted")
            if geometry and "lat" in geometry and "lng" in geometry:
                city = components.get(
                    "city",
                    components.get(
                        "town",
                        components.get("village", components.get("state_district")),
                    ),
                )
                country = components.get("country")
                road = components.get("road")
                house_number = components.get("house_number")
                neighbourhood = components.get("neighbourhood")
                street_address_parts = filter(None, [house_number, road, neighbourhood])
                street_address = ", ".join(street_address_parts)
                result = models.GeocodeResult(
                    latitude=geometry["lat"],
                    longitude=geometry["lng"],
                    address=street_address or None,
                    city=city,
                    country=country,
                    display_name=formatted_address,
                )
                logger.debug(f"OpenCage geocoding successful: {formatted_address}")
                return result
            else:
                logger.warning(
                    f"OpenCage result missing geometry for '{address}'. Data: {best_result}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Geocoding lacks coordinate data.",
                )
        else:
            logger.warning(f"OpenCage geocoding failed: No results for '{address}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Address not found."
            )
    except RateLimitExceededError:
        logger.error("OpenCage API rate limit exceeded.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Geocoding limit reached.",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"OpenCage geocoding unexpected error for '{address}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during geocoding.",
        )


# --- HTML Page Endpoint ---
@app.get("/", response_class=HTMLResponse, summary="Main Map Page")
async def read_root(
    request: Request,
    db=Depends(get_db),
    category_str: Optional[str] = Query(
        None, alias="category", description="Filter by category"
    ),
    status_str: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
):
    """Serves the main HTML page displaying the map and places."""
    logger.info(
        f"Request for root page. Raw Filters: category='{category_str}', status='{status_str}'"
    )

    # --- Process filter strings into Enums ---
    category: Optional[PlaceCategory] = None
    if category_str:
        try:
            category = PlaceCategory(category_str)
        except ValueError:
            logger.warning(f"Invalid category filter: '{category_str}'. Ignoring.")
    status_filter: Optional[PlaceStatus] = None
    if status_str:
        try:
            status_filter = PlaceStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status filter: '{status_str}'. Ignoring.")
    logger.info(f"Processed Filters: category={category}, status={status_filter}")
    # --- End Filter Processing ---

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map data could not be loaded.</p>'
    places = []
    try:
        places = await crud.get_places(
            db=db, category=category, status_filter=status_filter, limit=500
        )
        logger.info(f"MAIN: Fetched {len(places)} validated places.")

        map_center = [4.7110, -74.0721]
        zoom_start = 12
        m = folium.Map(
            location=map_center, zoom_start=zoom_start, tiles="CartoDB positron"
        )  # Use a lighter tile

        # --- Icon Mapping ---
        category_icons = {
            PlaceCategory.RESTAURANT: "cutlery",
            PlaceCategory.PARK: "tree-conifer",  # FontAwesome 5 free name
            PlaceCategory.ENTERTAINMENT: "film",
            PlaceCategory.SHOPPING: "shopping-cart",
            PlaceCategory.OTHER: "map-marker",
        }
        default_icon = "info-sign"  # Fallback

        marker_count = 0
        if places:
            for place in places:
                logger.debug(f"MAIN: Processing marker for place ID {place.id}")
                try:
                    place_lat = place.latitude
                    place_lon = place.longitude
                    if not isinstance(place_lat, (int, float)) or not isinstance(
                        place_lon, (int, float)
                    ):
                        logger.warning(
                            f"MAIN: Skipping place ID {place.id} invalid coords: {place_lat}, {place_lon}"
                        )
                        continue

                    place_name = html.escape(place.name or "Unnamed Place")
                    place_category_enum = place.category
                    place_category_val = getattr(place_category_enum, "value", "N/A")
                    place_status_enum = place.status
                    place_status_val = getattr(place_status_enum, "value", "N/A")

                    place_category_display = html.escape(place_category_val)
                    place_status_display = html.escape(place_status_val)
                    review_title = html.escape(place.review_title or "")
                    review_text = html.escape(place.review or "")
                    image_url_str = str(place.image_url or "")
                    image_url_display = html.escape(image_url_str)

                    # --- Popup HTML Generation ---
                    popup_parts = [
                        f"<h4 style='margin-bottom: 8px;'>{place_name}</h4><div style='font-size: 0.9em; max-height: 200px; overflow-y: auto;'>"
                    ]  # Added style
                    popup_parts.append(f"<b>Category:</b> {place_category_display}<br>")
                    popup_parts.append(f"<b>Status:</b> {place_status_display}<br>")

                    address_info = ", ".join(
                        filter(
                            None,
                            [
                                html.escape(place.address or ""),
                                html.escape(place.city or ""),
                                html.escape(place.country or ""),
                            ],
                        )
                    )
                    if address_info:
                        popup_parts.append(f"<b>Address:</b> {address_info}<br>")

                    # Display Review Title and Text if they exist
                    if review_title:
                        popup_parts.append(
                            f"<p style='margin-top: 5px;'><b>Review Title:</b><br>{review_title}</p>"
                        )
                    if review_text:
                        review_snippet = review_text[:150] + (
                            "..." if len(review_text) > 150 else ""
                        )
                        popup_parts.append(
                            f"<p style='margin-top: 5px;'><b>Review:</b><br>{review_snippet}</p>"
                        )

                    if image_url_str and image_url_str.startswith(
                        ("http://", "https://")
                    ):
                        popup_parts.append(
                            f'<img src="{image_url_display}" alt="{place_name}" style="max-width: 200px; max-height: 150px; margin-top: 5px; display: block; border-radius: 4px;">'
                        )

                    popup_parts.append("</div>")  # Close scrollable div

                    # --- Actions Section ---
                    popup_parts.append(
                        "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px; display: flex; flex-wrap: wrap; gap: 5px;'>"
                    )  # Flex container

                    # Status Change Form (kept similar)
                    current_status = (
                        place_status_enum if place_status_enum else PlaceStatus.PENDING
                    )
                    status_form_url = request.url_for(
                        "update_place_status_from_form_endpoint", place_id=place.id
                    )
                    popup_parts.append(f"""
                    <form action="{status_form_url}" method="post" style="display: inline-block; margin-right: 5px;">
                         <select name="status" onchange="this.form.submit()" title="Change Status" style="padding: 3px 5px; font-size: 0.85em; border-radius: 3px;">
                            <option value="{PlaceStatus.PENDING.value}" {"selected" if current_status == PlaceStatus.PENDING else ""}>Pending</option>
                            <option value="{PlaceStatus.PENDING_PRIORITIZED.value}" {"selected" if current_status == PlaceStatus.PENDING_PRIORITIZED else ""}>Prioritized</option>
                            <option value="{PlaceStatus.VISITED.value}" {"selected" if current_status == PlaceStatus.VISITED else ""}>Visited</option>
                         </select>
                    </form>""")

                    # Edit Button (Triggers JS)
                    # Pass necessary data safely escaped for JS context
                    place_data_for_js = {
                        "id": place.id,
                        "name": place.name,
                        "latitude": place.latitude,
                        "longitude": place.longitude,
                        "category": place_category_val,
                        "status": place_status_val,
                        "address": place.address,
                        "city": place.city,
                        "country": place.country,
                        "review_title": place.review_title,
                        "review": place.review,  # Pass review data too
                    }
                    # Use json.dumps for robust JS string conversion
                    js_data_arg = html.escape(json.dumps(place_data_for_js), quote=True)
                    popup_parts.append(
                        f'<button onclick=\'showEditForm({js_data_arg})\' title="Edit Place" style="padding: 3px 8px; font-size: 0.85em; background-color: #f0ad4e; color: white; border: none; border-radius: 3px; cursor: pointer;">Edit</button>'
                    )

                    # Add/Edit Review Button (Triggers JS)
                    popup_parts.append(
                        f'<button onclick=\'showReviewForm({js_data_arg})\' title="Add/Edit Review & Image" style="padding: 3px 8px; font-size: 0.85em; background-color: #5bc0de; color: white; border: none; border-radius: 3px; cursor: pointer;">Review</button>'
                    )

                    # Delete Button (Simple Form POST)
                    delete_form_url = request.url_for(
                        "delete_place_from_form_endpoint", place_id=place.id
                    )
                    popup_parts.append(f"""
                    <form action="{delete_form_url}" method="post" style="display: inline-block;" onsubmit="return confirm('Are you sure you want to delete {html.escape(place_name)}?');">
                        <button type="submit" title="Delete Place" style="padding: 3px 8px; font-size: 0.85em; background-color: #d9534f; color: white; border: none; border-radius: 3px; cursor: pointer;">Delete</button>
                    </form>""")

                    popup_parts.append("</div>")  # Close actions div
                    # --- End Actions ---

                    popup_html = "".join(popup_parts)

                    # --- Marker Icon and Color ---
                    status_color_map = {
                        PlaceStatus.VISITED: "green",
                        PlaceStatus.PENDING_PRIORITIZED: "orange",
                        PlaceStatus.PENDING: "blue",
                    }
                    marker_color = status_color_map.get(current_status, "gray")
                    marker_icon = category_icons.get(place_category_enum, default_icon)

                    folium.Marker(
                        location=[place_lat, place_lon],
                        popup=folium.Popup(
                            popup_html, max_width=350
                        ),  # Slightly wider popup
                        tooltip=f"{place_name} ({place_status_display})",
                        icon=folium.Icon(
                            color=marker_color, icon=marker_icon, prefix="fa"
                        ),  # Use FontAwesome prefix
                    ).add_to(m)
                    marker_count += 1
                except Exception as marker_error:
                    logger.error(
                        f"MAIN: Error processing marker for place ID {place.id}: {marker_error}",
                        exc_info=True,
                    )

            logger.info(f"MAIN: Successfully added {marker_count} markers.")
            map_html_content = m._repr_html_()
        elif not places:
            logger.info("MAIN: No places found to display.")
            map_html_content = m._repr_html_()

    except Exception as page_load_error:
        logger.error(
            f"MAIN: Critical error generating map page: {page_load_error}",
            exc_info=True,
        )

    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,
        "categories": [c.value for c in PlaceCategory],
        "statuses": [s.value for s in PlaceStatus],
        "current_category": category_str if category_str else None,
        "current_status": status_str if status_str else None,
        "attribution_html": "Geocoding by <a href='https://opencagedata.com/' target='_blank'>OpenCage</a>. Map data © <a href='https://openstreetmap.org/copyright' target='_blank'>OpenStreetMap</a> contributors.",
    }
    return templates.TemplateResponse("index.html", context)


# --- API Endpoints ---
@app.get("/geocode", response_model=models.GeocodeResult, summary="Geocode Address")
async def geocode_address_endpoint(address: str = Query(..., min_length=3)):
    """Geocodes an address string using OpenCage."""
    logger.info(f"API Geocoding request for: '{address}'")
    result = await perform_geocode(address)
    return result


# --- Form Handling Endpoints ---


@app.post("/places/", status_code=status.HTTP_303_SEE_OTHER, summary="Create New Place")
async def create_new_place_endpoint(
    request: Request,
    db=Depends(get_db),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    place_status_input: PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Creates a new place from form data and redirects."""
    logger.info(f"API Create place request (form): Name='{name}'")
    redirect_url = request.url_for("read_root")
    try:
        place_data = models.PlaceCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=place_status_input,
            address=address,
            city=city,
            country=country,
        )
    except ValidationError as validation_error:
        logger.error(
            f"API Create place validation error: {validation_error.errors()}",
            exc_info=False,
        )
        # TODO: Flash message error
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    created_place = await crud.create_place(place=place_data, db=db)
    if created_place is None:
        logger.error(
            f"Failed to create place '{place_data.name}' in DB."
        )  # TODO: Flash message error
    else:
        logger.info(
            f"Place '{created_place.name}' created (ID: {created_place.id})."
        )  # TODO: Flash message success
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/places/{place_id}/update-status",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Update Place Status",
)
async def update_place_status_from_form_endpoint(
    request: Request,
    place_id: int,
    new_status: PlaceStatus = Form(..., alias="status"),
    db=Depends(get_db),
):
    """Handles status update from the map popup form and redirects."""
    logger.info(f"API Update status request for place {place_id} to {new_status.value}")
    place_update = models.PlaceUpdate(status=new_status)
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        logger.warning(
            f"Failed to update status/find place ID {place_id}."
        )  # TODO: Flash message error
    else:
        logger.info(
            f"Status updated for place ID {place_id}."
        )  # TODO: Flash message success
    return RedirectResponse(
        url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/edit",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Handle Edit Place Form",
)
async def edit_place_from_form_endpoint(
    request: Request,
    place_id: int,
    db=Depends(get_db),
    name: str = Form(...),
    latitude: float = Form(
        ...
    ),  # Assume coords are passed from form (potentially updated by geocoder)
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    status: PlaceStatus = Form(...),
    address: Optional[str] = Form(None),  # Address from form
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Handles submission of the edit place form."""
    logger.info(f"API Edit place form submission for ID {place_id}, Name='{name}'")
    redirect_url = request.url_for("read_root")

    try:
        # Create PlaceUpdate model from form data
        place_update_data = models.PlaceUpdate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=status,
            address=address,
            city=city,
            country=country,
            # review/image fields are not part of this form
        )

        updated_place = await crud.update_place(
            place_id=place_id, place_update=place_update_data, db=db
        )

        if updated_place is None:
            logger.error(f"Failed to update place ID {place_id} via edit form.")
            # TODO: Flash message error
        else:
            logger.info(f"Place ID {place_id} updated successfully via edit form.")
            # TODO: Flash message success

    except ValidationError as validation_error:
        logger.error(
            f"API Edit place validation error for ID {place_id}: {validation_error.errors()}",
            exc_info=False,
        )
        # TODO: Flash message validation error
    except Exception as e:
        logger.error(
            f"API Unexpected error editing place ID {place_id}: {e}", exc_info=True
        )
        # TODO: Flash message generic error

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/places/{place_id}/review-image",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Add/Update Review and Image",
)
async def add_review_image_endpoint(
    request: Request,
    place_id: int,
    db=Depends(get_db),
    review_title: str = Form(""),  # Allow empty title
    review_text: str = Form(""),  # Allow empty text
    image_file: Optional[UploadFile] = File(None, alias="image"),  # Use alias
):
    """Handles review text and optional image upload from a form."""
    logger.info(
        f"API Review/Image submission for place ID {place_id}. Title: '{review_title[:20]}...', Has Image: {image_file is not None}"
    )
    redirect_url = request.url_for("read_root")
    image_public_url = None

    # 1. Upload Image if provided
    if image_file and image_file.filename:
        try:
            logger.info(
                f"Attempting image upload for place {place_id}, filename: {image_file.filename}"
            )
            image_public_url = await crud.upload_place_image(
                place_id=place_id, file=image_file, db=db
            )
            if image_public_url:
                logger.info(
                    f"Image uploaded for place {place_id}, URL: {image_public_url}"
                )
                # TODO: Flash message image success
            else:
                logger.error(
                    f"Image upload completed for place {place_id} but no URL returned."
                )
                # TODO: Flash message image URL failure
        except HTTPException as e:
            logger.error(f"Image upload failed for place {place_id}: {e.detail}")
            # TODO: Flash message image upload error (e.detail)
            # Decide if we should proceed without image or stop
            # For now, let's proceed to update text fields anyway
        except Exception as e:
            logger.error(
                f"Unexpected error during image upload for place {place_id}: {e}",
                exc_info=True,
            )
            # TODO: Flash message generic image error
            # Proceed with text update

    # 2. Update Review Text and Image URL in DB
    try:
        place_update_data = models.PlaceUpdate(
            review_title=review_title.strip() if review_title else None,
            review=review_text.strip() if review_text else None,
            # Only include image_url if upload was successful (or if clearing it intentionally)
            # Here we assume we always want to set it if upload happened
            # image_url=image_public_url # This might overwrite if upload failed but we proceeded
        )
        # If an image was successfully uploaded, ensure its URL is in the update data
        if image_public_url:
            place_update_data.image_url = image_public_url

        # Also mark as visited when adding review/image
        place_update_data.status = PlaceStatus.VISITED

        logger.debug(
            f"Updating place {place_id} with review/image data: {place_update_data.model_dump(exclude_unset=True)}"
        )

        updated_place = await crud.update_place(
            place_id=place_id, place_update=place_update_data, db=db
        )

        if updated_place is None:
            # This could happen if the place ID is invalid OR if the update itself failed in DB
            logger.error(
                f"Failed to update review/image details for place ID {place_id}."
            )
            # TODO: Flash message DB update error
        else:
            logger.info(
                f"Review/image details updated successfully for place ID {place_id}."
            )
            # TODO: Flash message combined success (or separate for text/image)

    except ValidationError as validation_error:
        logger.error(
            f"API Review/Image validation error for ID {place_id}: {validation_error.errors()}",
            exc_info=False,
        )
        # TODO: Flash message validation error
    except Exception as e:
        logger.error(
            f"API Unexpected error saving review/image details for ID {place_id}: {e}",
            exc_info=True,
        )
        # TODO: Flash message generic error

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- NEW: Delete Place Form Handler ---
@app.post(
    "/places/{place_id}/delete",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Handle Delete Place Form",
)
async def delete_place_from_form_endpoint(
    request: Request, place_id: int, db=Depends(get_db)
):
    """Handles deletion of a place triggered by a form."""
    logger.warning(f"API Delete request (form) for place ID {place_id}")
    redirect_url = request.url_for("read_root")

    success = await crud.delete_place(place_id=place_id, db=db)

    if not success:
        logger.error(f"Failed to delete place ID {place_id} via form.")
        # TODO: Flash message error (place not found or deletion failed)
    else:
        logger.info(f"Place ID {place_id} deleted successfully via form.")
        # TODO: Flash message success

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- JSON API Endpoints ---


@app.get("/api/places/", response_model=List[models.Place], tags=["API - Places"])
async def list_places_api(
    category: Optional[PlaceCategory] = Query(None),
    status_filter: Optional[PlaceStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    logger.info(
        f"API List: category={category}, status={status_filter}, skip={skip}, limit={limit}"
    )
    places_db = await crud.get_places(
        db=db, category=category, status_filter=status_filter, skip=skip, limit=limit
    )
    return [models.Place.model_validate(p) for p in places_db]


@app.get("/api/places/{place_id}", response_model=models.Place, tags=["API - Places"])
async def get_place_api(place_id: int, db=Depends(get_db)):
    logger.info(f"API Get place: ID {place_id}")
    db_place = await crud.get_place_by_id(place_id=place_id, db=db)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Place not found"
        )
    return models.Place.model_validate(db_place)


@app.delete(
    "/api/places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["API - Places"],
)
async def delete_place_api(place_id: int, db=Depends(get_db)):
    logger.info(f"API Delete place: ID {place_id}")
    success = await crud.delete_place(place_id=place_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or delete failed",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # Explicit Response for 204


@app.put("/api/places/{place_id}", response_model=models.Place, tags=["API - Places"])
async def update_place_api(
    place_id: int, place_update: models.PlaceUpdate, db=Depends(get_db)
):
    logger.info(
        f"API Update place: ID {place_id} Data: {place_update.model_dump(exclude_unset=True)}"
    )
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        existing = await crud.get_place_by_id(place_id=place_id, db=db)
        detail = "Place not found" if not existing else "Could not update place"
        status_code = (
            status.HTTP_404_NOT_FOUND
            if not existing
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=detail)
    logger.info(f"API Place ID {place_id} updated.")
    return models.Place.model_validate(updated_place)


# --- Health Check ---
@app.get(
    "/health", status_code=status.HTTP_200_OK, summary="Health Check", tags=["System"]
)
async def health_check():
    return {"status": "ok"}
