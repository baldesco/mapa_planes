"""Main FastAPI application file for Mapa Planes."""

import asyncio
import folium
import html  # For escaping HTML in popups
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Request,  # Ensure status is imported
    File,
    UploadFile,
    Form,
    Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# from fastapi.staticfiles import StaticFiles # Uncomment if needed
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError  # Using OpenCage
from typing import List, Optional
from pydantic import ValidationError  # Import for catching Pydantic errors

# Import local modules
from . import crud, models, database
from .core.config import settings, logger
from .models import PlaceCategory, PlaceStatus  # Keep PlaceStatus import
from .database import get_db  # Use the determined DB dependency

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
# app.mount("/static", StaticFiles(directory="static"), name="static") # Uncomment if needed

# --- Geocoding Setup (OpenCage) ---
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
        logger.error(
            "Geocoding skipped: OpenCage Geocoder not initialized (API Key missing?)."
        )
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
                # Extract details safely using .get()
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
                    f"OpenCage result found for '{address}', but missing/invalid geometry. Data: {best_result}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Geocoding found a location but lacks coordinate data.",
                )
        else:
            logger.warning(
                f"OpenCage geocoding failed: No results found for '{address}'"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Address not found."
            )

    except RateLimitExceededError:
        logger.error("OpenCage API rate limit exceeded.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Geocoding limit reached. Please try again later.",
        )
    except HTTPException as http_exc:
        # Explicitly re-raise known HTTPExceptions
        raise http_exc
    except Exception as e:
        logger.error(
            f"OpenCage geocoding unexpected error for '{address}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during geocoding.",
        )


# --- HTML Page Endpoint ---
@app.get("/", response_class=HTMLResponse, summary="Main Map Page")
async def read_root(
    request: Request,
    db=Depends(get_db),
    category: Optional[PlaceCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[PlaceStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
):
    """Serves the main HTML page displaying the map and places."""
    logger.info(
        f"Request for root page. Filters: category={category}, status={status_filter}"
    )
    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map data could not be loaded. Check server logs.</p>'
    places = []
    try:
        places = await crud.get_places(
            db=db, category=category, status_filter=status_filter, limit=500
        )
        logger.info(f"MAIN: Fetched {len(places)} validated places.")

        map_center = [4.7110, -74.0721]  # Bogota
        zoom_start = 12
        m = folium.Map(
            location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap"
        )

        marker_count = 0
        if places:
            for i, place in enumerate(places):
                logger.debug(
                    f"MAIN: Processing marker {i + 1}/{len(places)} for place ID {place.id}"
                )
                try:
                    # Validate essential data for marker
                    place_lat = place.latitude
                    place_lon = place.longitude
                    if not isinstance(place_lat, (int, float)) or not isinstance(
                        place_lon, (int, float)
                    ):
                        logger.warning(
                            f"MAIN: Skipping place ID {place.id} ('{getattr(place, 'name', 'N/A')}') due to invalid coordinates: Lat={place_lat}, Lon={place_lon}"
                        )
                        continue

                    # Prepare display data safely
                    place_name = html.escape(place.name or "Unnamed Place")
                    place_category = html.escape(
                        place.category.value if place.category else "N/A"
                    )
                    place_status = html.escape(
                        place.status.value if place.status else "N/A"
                    )
                    review = html.escape(place.review or "")
                    image_url = html.escape(
                        str(place.image_url or "")
                    )  # Ensure string for startswith

                    # Build popup HTML
                    popup_parts = [f"<h4>{place_name}</h4><p>"]
                    popup_parts.append(f"<b>Category:</b> {place_category}<br>")
                    popup_parts.append(f"<b>Status:</b> {place_status}<br>")
                    popup_parts.append(
                        f"<b>Coords:</b> ({place_lat:.5f}, {place_lon:.5f})<br>"
                    )
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
                    popup_parts.append("</p>")

                    if review:
                        popup_parts.append(
                            f"<p style='margin-top: 5px;'><b>Review:</b><br>{review[:150]}{'...' if len(review) > 150 else ''}</p>"
                        )
                    if image_url and image_url.startswith(("http://", "https://")):
                        popup_parts.append(
                            f'<img src="{image_url}" alt="{place_name}" style="max-width: 200px; max-height: 150px; margin-top: 5px; display: block;">'
                        )

                    # Status update form
                    popup_parts.append(f"""
                    <form action="{request.url_for("update_place_status_from_form_endpoint", place_id=place.id)}" method="post" style="margin-top: 10px;">
                         <label for="status-popup-{place.id}" style="font-size: 0.9em;">Change Status:</label><br>
                         <select name="status" id="status-popup-{place.id}" onchange="this.form.submit()" style="padding: 3px;">
                            <option value="{PlaceStatus.PENDING.value}" {"selected" if place.status == PlaceStatus.PENDING else ""}>Pending</option>
                            <option value="{PlaceStatus.PENDING_PRIORITIZED.value}" {"selected" if place.status == PlaceStatus.PENDING_PRIORITIZED else ""}>Prioritized</option>
                            <option value="{PlaceStatus.VISITED.value}" {"selected" if place.status == PlaceStatus.VISITED else ""}>Visited</option>
                         </select>
                         <noscript><button type="submit" style="margin-left: 5px;">Update</button></noscript>
                    </form>""")

                    popup_html = "".join(popup_parts)
                    color_map = {
                        PlaceStatus.VISITED: "green",
                        PlaceStatus.PENDING_PRIORITIZED: "orange",
                        PlaceStatus.PENDING: "blue",
                    }
                    marker_color = color_map.get(place.status, "gray")

                    folium.Marker(
                        location=[place_lat, place_lon],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{place_name} ({place_status})",
                        icon=folium.Icon(color=marker_color, icon="info-sign"),
                    ).add_to(m)
                    marker_count += 1

                except Exception as marker_error:
                    logger.error(
                        f"MAIN: Error processing marker for place ID {place.id}: {marker_error}",
                        exc_info=True,
                    )
                    # Continue to next marker

            logger.info(f"MAIN: Successfully added {marker_count} markers to the map.")
            map_html_content = m._repr_html_()  # Render HTML only if successful

        elif not places:
            logger.info("MAIN: No places found to display on map.")
            # Keep default map centered on Bogota
            map_html_content = m._repr_html_()  # Render the empty map

    except Exception as page_load_error:
        logger.error(
            f"MAIN: Critical error generating map page: {page_load_error}",
            exc_info=True,
        )
        # map_html_content retains the default error message

    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,
        "categories": [c.value for c in PlaceCategory],
        "statuses": [s.value for s in PlaceStatus],
        "current_category": category.value if category else None,
        "current_status": status_filter.value if status_filter else None,
        "attribution_html": "Geocoding by <a href='https://opencagedata.com/' target='_blank'>OpenCage</a>. Map data © <a href='https://openstreetmap.org/copyright' target='_blank'>OpenStreetMap</a> contributors & others.",
    }
    return templates.TemplateResponse("index.html", context)


# --- API Endpoints ---


@app.get("/geocode", response_model=models.GeocodeResult, summary="Geocode Address")
async def geocode_address_endpoint(
    address: str = Query(
        ..., min_length=3, description="Address or place name to geocode"
    ),
):
    """Geocodes an address string using OpenCage."""
    logger.info(f"API Geocoding request for: '{address}'")
    # perform_geocode raises appropriate HTTPExceptions on failure
    result = await perform_geocode(address)
    return result


# --- POST /places/ endpoint (Create Place) ---
@app.post("/places/", status_code=status.HTTP_303_SEE_OTHER, summary="Create New Place")
async def create_new_place_endpoint(
    request: Request,
    db=Depends(get_db),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    place_status_input: PlaceStatus = Form(..., alias="status"),  # RENAMED parameter
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Creates a new place from form data and redirects to the map."""
    logger.info(f"API Create place request (form): Name='{name}'")
    redirect_url = request.url_for("read_root")  # Define redirect URL once
    try:
        place_data = models.PlaceCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=place_status_input,  # Use RENAMED variable here
            address=address,
            city=city,
            country=country,
        )
    except ValidationError as validation_error:
        logger.error(
            f"API Create place validation error: {validation_error.errors()}",
            exc_info=False,
        )
        # TODO: Flash messages
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    created_place = await crud.create_place(place=place_data, db=db)
    if created_place is None:
        logger.error(
            f"Failed to create place '{place_data.name}' in DB after validation."
        )
    # TODO: Flash message
    else:
        logger.info(
            f"Place '{created_place.name}' created successfully (ID: {created_place.id})."
        )
        # TODO: Flash message

    # Correctly use the imported status module for the status code
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- Form Handling Endpoints (Update Status, Review, Upload Image) ---


@app.post(
    "/places/{place_id}/update-status",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Update Place Status",
)
async def update_place_status_from_form_endpoint(
    request: Request,
    place_id: int,
    new_status: PlaceStatus = Form(..., alias="status"),  # RENAMED parameter
    db=Depends(get_db),
):
    """Handles status update from the map popup form and redirects."""
    logger.info(f"API Update status request for place {place_id} to {new_status.value}")
    place_update = models.PlaceUpdate(status=new_status)  # Use RENAMED variable
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        logger.warning(f"Failed to update status or find place ID {place_id}.")
    else:
        logger.info(f"Status updated successfully for place ID {place_id}.")

    # Correctly use the imported status module for the status code
    return RedirectResponse(
        url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/review",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Add/Update Place Review",
)
async def add_update_review_endpoint(
    request: Request, place_id: int, review: str = Form(...), db=Depends(get_db)
):
    """Handles adding/updating a review from a form and redirects."""
    logger.info(f"API Add/Update review request for place ID {place_id}")
    place_update = models.PlaceUpdate(
        review=review.strip(), status=PlaceStatus.VISITED
    )  # Mark as visited
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        logger.warning(f"Failed to update review or find place ID {place_id}.")
    else:
        logger.info(f"Review updated successfully for place ID {place_id}.")
    return RedirectResponse(
        url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/upload-image/",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Upload Place Image",
)
async def upload_image_for_place_endpoint(
    request: Request, place_id: int, file: UploadFile = File(...), db=Depends(get_db)
):
    """Uploads an image for a place, saves URL, and redirects."""
    logger.info(
        f"API Image upload request for place ID {place_id}. Filename: {file.filename}"
    )
    redirect_url = request.url_for("read_root")

    db_place = await crud.get_place_by_id(place_id=place_id, db=db)
    if db_place is None:
        logger.warning(f"Place ID {place_id} not found for image upload.")
        # TODO: Flash message
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    try:
        image_url = await crud.upload_place_image(place_id=place_id, file=file, db=db)
    except HTTPException as e:
        logger.error(f"Image upload failed during storage operation: {e.detail}")
        # TODO: Flash message
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(
            f"Unexpected error during image upload for place {place_id}: {e}",
            exc_info=True,
        )
        # TODO: Flash message
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    if image_url:
        success = await crud.update_place_image_url(
            place_id=place_id, image_url=image_url, db=db
        )
        if not success:
            logger.error(
                f"Image uploaded ({image_url}), but failed to update DB for place {place_id}."
            )
            # TODO: Flash message
        else:
            logger.info(f"Image uploaded and DB updated for place {place_id}.")
            # TODO: Flash message
    else:
        logger.error(
            f"Image upload for place {place_id} completed but no URL was returned."
        )
        # TODO: Flash message

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- JSON API Endpoints ---


@app.get(
    "/api/places/",
    response_model=List[models.Place],
    summary="List Places (API)",
    tags=["API - Places"],
)
async def list_places_api(
    category: Optional[PlaceCategory] = Query(None),
    status_filter: Optional[PlaceStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    """API endpoint to get a list of places (JSON response)."""
    logger.info(
        f"API List places request: category={category}, status={status_filter}, skip={skip}, limit={limit}"
    )
    places_db = await crud.get_places(
        db=db, category=category, status_filter=status_filter, skip=skip, limit=limit
    )
    return [models.Place.model_validate(p) for p in places_db]


@app.get(
    "/api/places/{place_id}",
    response_model=models.Place,
    summary="Get Place Details (API)",
    tags=["API - Places"],
)
async def get_place_api(place_id: int, db=Depends(get_db)):
    """API endpoint to get details of a single place (JSON response)."""
    logger.info(f"API Get place request for ID {place_id}")
    db_place = await crud.get_place_by_id(place_id=place_id, db=db)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Place not found"
        )
    return models.Place.model_validate(db_place)


@app.delete(
    "/api/places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Place (API)",
    tags=["API - Places"],
)
async def delete_place_api(place_id: int, db=Depends(get_db)):
    """API endpoint to delete a place."""
    logger.info(f"API Delete place request for ID {place_id}")
    success = await crud.delete_place(place_id=place_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or could not be deleted",
        )
    return None  # Return No Content on success


@app.put(
    "/api/places/{place_id}",
    response_model=models.Place,
    summary="Update Place (API)",
    tags=["API - Places"],
)
async def update_place_api(
    place_id: int, place_update: models.PlaceUpdate, db=Depends(get_db)
):
    """API endpoint to update place details (JSON response)."""
    logger.info(
        f"API Update place request for ID {place_id} with data: {place_update.model_dump(exclude_unset=True)}"
    )
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        existing = await crud.get_place_by_id(place_id=place_id, db=db)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Place not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not update place",
            )
    logger.info(f"API Place ID {place_id} updated successfully.")
    return models.Place.model_validate(updated_place)


# --- Health Check ---
@app.get(
    "/health", status_code=status.HTTP_200_OK, summary="Health Check", tags=["System"]
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
