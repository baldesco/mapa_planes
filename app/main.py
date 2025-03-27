"""Main FastAPI application file for Mapa Planes."""

import asyncio
import folium
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
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from typing import List, Optional

# Import local modules
from . import crud, models, database
from .core.config import settings, logger
from .models import PlaceCategory, PlaceStatus
from .database import get_db  # Use the determined DB dependency

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
)

# Mount static files (optional, if you have CSS/JS files)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# --- Geocoding Setup ---
# IMPORTANT: Ensure GEOCODING_USER_AGENT is set correctly in .env
if (
    not settings.GEOCODING_USER_AGENT
    or "your_email@example.com" in settings.GEOCODING_USER_AGENT
):
    logger.critical(
        "GEOCODING_USER_AGENT is not set properly. Geocoding requests may be blocked."
    )
    # You might want to exit or disable geocoding here if the agent isn't set

geolocator = Nominatim(user_agent=settings.GEOCODING_USER_AGENT)
# Apply rate limiting (1 req/sec for Nominatim's free tier)
geocode_limited = RateLimiter(
    geolocator.geocode, min_delay_seconds=1.1, error_wait_seconds=5.0
)
# reverse_limited = RateLimiter(geolocator.reverse, min_delay_seconds=1.1) # If reverse geocoding needed


# --- Helper Functions ---
async def perform_geocode(address: str) -> models.GeocodeResult | None:
    """Performs geocoding using Nominatim in a thread pool executor."""
    try:
        logger.debug(f"Geocoding address: '{address}'")
        # Run synchronous geopy call in background thread
        location = await asyncio.to_thread(
            geocode_limited, address, addressdetails=True, timeout=10
        )  # Add timeout

        if location and location.raw.get("address"):
            addr = location.raw["address"]
            # Prioritize specific city tags, fall back to others
            city = addr.get(
                "city", addr.get("town", addr.get("village", addr.get("county")))
            )
            # Construct a simple street address if road is available
            street = addr.get("road")
            house_number = addr.get("house_number")
            full_address = (
                f"{house_number} {street}" if house_number and street else street
            )

            result = models.GeocodeResult(
                latitude=location.latitude,
                longitude=location.longitude,
                address=full_address
                or location.address.split(",")[0],  # Fallback address part
                city=city,
                country=addr.get("country"),
                display_name=location.address,  # Full display name
            )
            logger.debug(f"Geocoding successful: {result.display_name}")
            return result
        elif location:  # Found coords but no address details
            logger.debug(
                f"Geocoding found coordinates but limited details for: {location.address}"
            )
            return models.GeocodeResult(
                latitude=location.latitude,
                longitude=location.longitude,
                display_name=location.address,
            )
        else:
            logger.warning(f"Geocoding failed: No location found for '{address}'")
            return None
    except Exception as e:
        logger.error(f"Geocoding error for '{address}': {e}", exc_info=True)
        return None  # Return None on any exception


# --- HTML Page Endpoint ---
@app.get("/", response_class=HTMLResponse, summary="Main Map Page")
async def read_root(
    request: Request,
    db=Depends(get_db),  # Use the configured DB dependency
    category: Optional[PlaceCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[PlaceStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
):
    """Serves the main HTML page displaying the map and places."""
    logger.info(
        f"Request for root page. Filters: category={category}, status={status_filter}"
    )
    places = await crud.get_places(
        db=db, category=category, status_filter=status_filter, limit=500
    )  # Increased limit

    # Default map center: Bogota, Colombia
    map_center = [4.7110, -74.0721]
    zoom_start = 12

    # Create Folium map
    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")

    # Add markers to the map
    for place in places:
        # Build popup HTML content
        popup_parts = [
            f"<h4>{place.name}</h4>",
            f"<p><b>Category:</b> {place.category.value}<br>",
            f"<b>Status:</b> {place.status.value}<br>",
            f"<b>Coords:</b> ({place.latitude:.5f}, {place.longitude:.5f})<br>",
        ]
        address_info = ", ".join(
            filter(None, [place.address, place.city, place.country])
        )
        if address_info:
            popup_parts.append(f"<b>Address:</b> {address_info}<br>")
        popup_parts.append("</p>")  # End main details paragraph

        if place.review:
            popup_parts.append(
                f"<p style='margin-top: 5px;'><b>Review:</b><br>{place.review[:150]}{'...' if len(place.review) > 150 else ''}</p>"
            )
        if place.image_url:
            popup_parts.append(
                f'<img src="{place.image_url}" alt="{place.name}" style="max-width: 200px; max-height: 150px; margin-top: 5px; display: block;">'
            )

        # Status update form inside popup
        popup_parts.append(f"""
        <form action="/places/{place.id}/update-status" method="post" style="margin-top: 10px;">
             <label for="status-popup-{place.id}" style="font-size: 0.9em;">Change Status:</label><br>
             <select name="status" id="status-popup-{place.id}" onchange="this.form.submit()" style="padding: 3px;">
                <option value="{PlaceStatus.PENDING.value}" {"selected" if place.status == PlaceStatus.PENDING else ""}>Pending</option>
                <option value="{PlaceStatus.PENDING_PRIORITIZED.value}" {"selected" if place.status == PlaceStatus.PENDING_PRIORITIZED else ""}>Prioritized</option>
                <option value="{PlaceStatus.VISITED.value}" {"selected" if place.status == PlaceStatus.VISITED else ""}>Visited</option>
             </select>
             <noscript><button type="submit" style="margin-left: 5px;">Update</button></noscript>
        </form>
        """)
        # TODO: Add link/button to trigger review/image edit (maybe via JS modal)

        popup_html = "".join(popup_parts)

        # Determine marker color based on status
        color_map = {
            PlaceStatus.VISITED: "green",
            PlaceStatus.PENDING_PRIORITIZED: "orange",
            PlaceStatus.PENDING: "blue",
        }
        marker_color = color_map.get(
            place.status, "gray"
        )  # Default gray if status unknown

        folium.Marker(
            location=[place.latitude, place.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{place.name} ({place.status.value})",  # Hover text
            icon=folium.Icon(
                color=marker_color, icon="info-sign"
            ),  # Use standard icons
        ).add_to(m)

    # Render map HTML
    map_html_content = m._repr_html_()

    # Prepare context for Jinja2 template
    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,  # Pass places data if needed elsewhere in template
        "categories": [c.value for c in PlaceCategory],  # For filter dropdown
        "statuses": [s.value for s in PlaceStatus],  # For filter dropdown
        "current_category": category.value if category else None,
        "current_status": status_filter.value if status_filter else None,
        "nominatim_attribution": "Map data © <a href='https://openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
    }

    return templates.TemplateResponse("index.html", context)


# --- API Endpoints ---


@app.get("/geocode", response_model=models.GeocodeResult, summary="Geocode Address")
async def geocode_address_endpoint(
    address: str = Query(
        ..., min_length=3, description="Address or place name to geocode"
    ),
):
    """Geocodes an address string using Nominatim."""
    logger.info(f"API Geocoding request for: '{address}'")
    result = await perform_geocode(address)
    if result:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find coordinates for the address: '{address}'. Try being more specific.",
        )


@app.post("/places/", status_code=status.HTTP_303_SEE_OTHER, summary="Create New Place")
async def create_new_place_endpoint(
    request: Request,  # Needed for form parsing if not using Pydantic model directly
    db=Depends(get_db),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    status: PlaceStatus = Form(...),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Creates a new place from form data and redirects to the map."""
    logger.info(f"API Create place request (form): Name='{name}'")
    place_data = models.PlaceCreate(
        name=name,
        latitude=latitude,
        longitude=longitude,
        category=category,
        status=status,
        address=address,
        city=city,
        country=country,
    )

    created_place = await crud.create_place(place=place_data, db=db)

    if created_place is None:
        # TODO: Implement flash messages or other ways to show errors on redirect
        logger.error(f"Failed to create place '{place_data.name}' in DB.")
        # Redirecting anyway, but ideally show an error message
        # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create place")
    else:
        logger.info(
            f"Place '{created_place.name}' created successfully (ID: {created_place.id})."
        )

    # Redirect back to the main map page
    return RedirectResponse(
        url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/update-status",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Update Place Status",
)
async def update_place_status_from_form_endpoint(
    place_id: int,
    status: PlaceStatus = Form(...),  # Get status from form data
    db=Depends(get_db),
):
    """Handles status update from the form in the map popup and redirects."""
    logger.info(f"API Update status request for place {place_id} to {status.value}")
    place_update = models.PlaceUpdate(status=status)
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )

    if updated_place is None:
        # Place not found or error updating
        # TODO: Add flash message on redirect
        logger.warning(f"Failed to update status or find place ID {place_id}.")
    else:
        logger.info(f"Status updated successfully for place ID {place_id}.")

    # Redirect back to the main map page (consider preserving filters via query params)
    return RedirectResponse(
        url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/review",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Add/Update Place Review",
)
async def add_update_review_endpoint(
    place_id: int, review: str = Form(...), db=Depends(get_db)
):
    """Handles adding/updating a review from a form and redirects."""
    logger.info(f"API Add/Update review request for place ID {place_id}")
    # Set status to 'visited' when adding/updating review
    place_update = models.PlaceUpdate(review=review, status=PlaceStatus.VISITED)
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )

    if updated_place is None:
        logger.warning(f"Failed to update review or find place ID {place_id}.")
        # TODO: Flash message
    else:
        logger.info(f"Review updated successfully for place ID {place_id}.")

    return RedirectResponse(
        url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/upload-image/",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Upload Place Image",
)
async def upload_image_for_place_endpoint(
    place_id: int,
    file: UploadFile = File(..., description="Image file for the place"),
    db=Depends(get_db),
):
    """Uploads an image for a place, saves URL, and redirects."""
    logger.info(
        f"API Image upload request for place ID {place_id}. Filename: {file.filename}"
    )

    # 1. Check if place exists
    db_place = await crud.get_place_by_id(place_id=place_id, db=db)
    if db_place is None:
        logger.warning(f"Place ID {place_id} not found for image upload.")
        # TODO: Flash message
        return RedirectResponse(
            url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
        )  # Redirect even on error

    # 2. Upload image to Storage
    try:
        image_url = await crud.upload_place_image(place_id=place_id, file=file, db=db)
    except HTTPException as e:
        logger.error(f"Image upload failed during storage operation: {e.detail}")
        # TODO: Flash message
        return RedirectResponse(
            url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        logger.error(f"Unexpected error during image upload: {e}", exc_info=True)
        # TODO: Flash message
        return RedirectResponse(
            url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
        )

    # 3. Update the place record with the image URL
    if image_url:
        success = await crud.update_place_image_url(
            place_id=place_id, image_url=image_url, db=db
        )
        if not success:
            logger.error(
                f"Image uploaded ({image_url}), but failed to update DB for place {place_id}."
            )
            # TODO: Flash message / Consider cleanup of uploaded image if DB fails
        else:
            logger.info(f"Image uploaded and DB updated for place {place_id}.")
            # TODO: Flash success message
    else:
        # This case might happen if upload_place_image returns None but doesn't raise Exception
        logger.error(
            f"Image upload for place {place_id} seemed to succeed but no URL was returned."
        )
        # TODO: Flash message

    return RedirectResponse(
        url=app.url_path_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.get(
    "/places/",
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
    return [
        models.Place.model_validate(p) for p in places_db
    ]  # Convert PlaceInDB to Place


@app.get(
    "/places/{place_id}",
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
    "/places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Place (API)",
    tags=["API - Places"],
)
async def delete_place_api(place_id: int, db=Depends(get_db)):
    """API endpoint to delete a place."""
    logger.info(f"API Delete place request for ID {place_id}")
    success = await crud.delete_place(place_id=place_id, db=db)
    if not success:
        # Check if it existed first to return 404 if appropriate
        # db_place = await crud.get_place_by_id(place_id=place_id, db=db) # Avoid extra call unless needed
        # Assume failure means not found or internal error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or could not be deleted",
        )
    # No content to return on successful delete
    return None


@app.put(
    "/places/{place_id}",
    response_model=models.Place,
    summary="Update Place (API)",
    tags=["API - Places"],
)
async def update_place_api(
    place_id: int, place_update: models.PlaceUpdate, db=Depends(get_db)
):
    """API endpoint to update a place details (JSON response)."""
    logger.info(
        f"API Update place request for ID {place_id} with data: {place_update.model_dump(exclude_unset=True)}"
    )
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        # Could be 404 or 500
        existing = await crud.get_place_by_id(
            place_id=place_id, db=db
        )  # Check if it exists
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


@app.get(
    "/health", status_code=status.HTTP_200_OK, summary="Health Check", tags=["System"]
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# --- Optional: Startup event ---
# @app.on_event("startup")
# async def on_startup():
#    # Perform tasks on startup, e.g., initial DB checks
#    if database.IS_LOCAL_SQLITE and database.local_engine:
#        logger.info("Running startup: Ensuring local tables exist.")
#        database.create_local_tables()
#    # Could also test Supabase connection here
