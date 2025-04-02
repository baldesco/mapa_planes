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
from fastapi.staticfiles import StaticFiles
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError
from typing import List, Optional
from pydantic import ValidationError

from . import crud, models, database
from .core.config import settings, logger
from .models import PlaceCategory, PlaceStatus
from .database import get_db

app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Geocoder setup
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


# perform_geocode helper function
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


@app.get("/", response_class=HTMLResponse, summary="Main Map Page")
async def read_root(
    request: Request,
    db=Depends(get_db),
    category_str: Optional[str] = Query(None, alias="category"),
    status_str: Optional[str] = Query(None, alias="status"),
):
    """Serves the main HTML page displaying the map and non-deleted places."""
    logger.info(
        f"Request root page. Filters: category='{category_str}', status='{status_str}'"
    )

    category: Optional[PlaceCategory] = None
    if category_str:
        try:
            category = PlaceCategory(category_str)
        except ValueError:
            logger.warning(f"Invalid category filter: '{category_str}'.")
    status_filter: Optional[PlaceStatus] = None
    if status_str:
        try:
            status_filter = PlaceStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status filter: '{status_str}'.")
    logger.info(f"Processed Filters: category={category}, status={status_filter}")

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places = []
    try:
        places = await crud.get_places(
            db=db, category=category, status_filter=status_filter, limit=500
        )
        logger.info(f"MAIN: Fetched {len(places)} validated, non-deleted places.")

        map_center = [4.7110, -74.0721]
        zoom_start = 12
        m = folium.Map(
            location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap"
        )

        category_icons = {
            PlaceCategory.RESTAURANT: "utensils",
            PlaceCategory.PARK: "tree",
            PlaceCategory.ENTERTAINMENT: "film",
            PlaceCategory.SHOPPING: "shopping-cart",
            PlaceCategory.OTHER: "map-marker-alt",
        }
        default_icon = "info-circle"

        status_color_map = {
            PlaceStatus.VISITED: "green",
            PlaceStatus.PENDING_PRIORITIZED: "orange",
            PlaceStatus.PENDING: "blue",
        }
        default_color = "gray"

        marker_count = 0
        if places:
            for place in places:
                if (
                    place.latitude is None
                    or place.longitude is None
                    or place.status is None
                    or place.category is None
                ):
                    logger.warning(
                        f"MAIN: Skipping place ID {place.id} due to missing essential data."
                    )
                    continue

                try:
                    place_lat = place.latitude
                    place_lon = place.longitude
                    place_name = html.escape(place.name or "Unnamed Place")
                    place_category_enum = place.category
                    place_status_enum = place.status
                    place_category_val = place_category_enum.value
                    place_status_val = place_status_enum.value
                    review_title_raw = place.review_title
                    review_text_raw = place.review
                    review_title = html.escape(review_title_raw or "")
                    review_text = html.escape(review_text_raw or "")
                    image_url_str = str(place.image_url or "")
                    image_url_display = html.escape(image_url_str)

                    has_review_content = bool(review_text_raw or review_title_raw)
                    has_image = bool(
                        image_url_str
                        and image_url_str.startswith(("http://", "https://"))
                    )

                    popup_parts = [
                        f"<h4 style='margin-bottom: 8px;'>{place_name}</h4><div style='font-size: 0.9em; max-height: 200px; overflow-y: auto;'>"
                    ]
                    popup_parts.append(
                        f"<b>Category:</b> {html.escape(place_category_val)}<br>"
                    )
                    popup_parts.append(
                        f"<b>Status:</b> {html.escape(place_status_val)}<br>"
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

                    if has_review_content or has_image:
                        popup_parts.append(
                            "<hr style='margin: 5px 0; border-top-color: #eee;'>"
                        )
                        if review_title:
                            popup_parts.append(f"<b>Review:</b> {review_title}<br>")
                        if review_text:
                            snippet = review_text[:100] + (
                                "..." if len(review_text) > 100 else ""
                            )
                            popup_parts.append(f"<i>{snippet}</i>")
                        elif has_image:
                            popup_parts.append(
                                f'<img src="{image_url_display}" alt="{place_name}" style="max-width: 100px; max-height: 75px; margin-top: 5px; display: block; border-radius: 4px;">'
                            )

                    popup_parts.append("</div>")

                    popup_parts.append(
                        "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px; display: flex; flex-wrap: wrap; gap: 5px;'>"
                    )

                    status_form_url = request.url_for(
                        "update_place_status_from_form_endpoint", place_id=place.id
                    )
                    popup_parts.append(f"""
                    <form action="{status_form_url}" method="post" style="display: inline-block; margin-right: 5px;" target="_top">
                         <select name="status" onchange="this.form.submit()" title="Change Status">
                            <option value="{PlaceStatus.PENDING.value}" {"selected" if place_status_enum == PlaceStatus.PENDING else ""}>Pending</option>
                            <option value="{PlaceStatus.PENDING_PRIORITIZED.value}" {"selected" if place_status_enum == PlaceStatus.PENDING_PRIORITIZED else ""}>Prioritized</option>
                            <option value="{PlaceStatus.VISITED.value}" {"selected" if place_status_enum == PlaceStatus.VISITED else ""}>Visited</option>
                         </select>
                         <noscript><button type="submit">Update</button></noscript>
                    </form>""")

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
                        "review_title": review_title_raw,
                        "review": review_text_raw,
                        "image_url": image_url_str,
                        "created_at": place.created_at.isoformat()
                        if place.created_at
                        else None,
                        "updated_at": place.updated_at.isoformat()
                        if place.updated_at
                        else None,
                        "deleted_at": place.deleted_at.isoformat()
                        if place.deleted_at
                        else None,
                    }
                    js_object_string = json.dumps(place_data_for_js)
                    escaped_js_string_for_html_attr = html.escape(
                        js_object_string, quote=True
                    )

                    popup_parts.append(
                        f'<button type="button" onclick="window.parent.showEditPlaceForm(\'{escaped_js_string_for_html_attr}\')" title="Edit Place Details">Edit</button>'
                    )

                    if has_review_content or has_image:
                        popup_parts.append(
                            f'<button type="button" onclick="window.parent.showSeeReviewModal(\'{escaped_js_string_for_html_attr}\')" title="See Review / Image">See Review</button>'
                        )
                    else:
                        popup_parts.append(
                            # Pass the already escaped string, JS will parse it
                            f'<button type="button" onclick="window.parent.showReviewForm(\'{escaped_js_string_for_html_attr}\')" title="Add Review / Image">Add Review</button>'
                        )

                    delete_form_url = request.url_for(
                        "delete_place_from_form_endpoint", place_id=place.id
                    )
                    popup_parts.append(f"""
                    <form action="{delete_form_url}" method="post" target="_top" style="display: inline-block;" onsubmit="return confirm('Are you sure you want to delete this place?');">
                        <button type="submit" title="Delete Place">Delete</button>
                    </form>""")

                    popup_parts.append("</div>")
                    popup_html = "".join(popup_parts)

                    marker_color = status_color_map.get(
                        place_status_enum, default_color
                    )
                    marker_icon = category_icons.get(place_category_enum, default_icon)

                    folium.Marker(
                        location=[place_lat, place_lon],
                        popup=folium.Popup(popup_html, max_width=350),
                        tooltip=f"{place_name} ({html.escape(place_status_val)})",
                        icon=folium.Icon(
                            color=marker_color, icon=marker_icon, prefix="fa"
                        ),
                    ).add_to(m)
                    marker_count += 1
                except Exception as marker_error:
                    logger.error(
                        f"MAIN: Error processing marker for place ID {place.id}: {marker_error}",
                        exc_info=True,
                    )

            logger.info(f"MAIN: Successfully added {marker_count} markers.")
            map_html_content = m._repr_html_()
        else:
            logger.info("MAIN: No places found to display on map.")
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
        "current_category": category_str or None,
        "current_status": status_str or None,
        "attribution_html": "Geocoding by <a href='https://opencagedata.com/' target='_blank'>OpenCage</a>. Map data © <a href='https://openstreetmap.org/copyright' target='_blank'>OpenStreetMap</a> contributors.",
    }
    return templates.TemplateResponse("index.html", context)


# --- API Endpoints ---


# GET /geocode
@app.get("/geocode", response_model=models.GeocodeResult, summary="Geocode Address")
async def geocode_address_endpoint(address: str = Query(..., min_length=3)):
    logger.info(f"API Geocoding request for: '{address}'")
    result = await perform_geocode(address)
    return result


# --- Form Handling Endpoints ---


# POST /places/
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
    form_data = await request.form()
    logger.info(f"API Create place form received data: {dict(form_data)}")
    redirect_url = request.url_for("read_root")
    try:
        if latitude is None or longitude is None:
            logger.error(
                "API Create place error: Latitude or Longitude missing in form data."
            )
            # TODO: Add flash message feedback
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

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
        logger.info(f"API Create place validated data: {place_data.model_dump()}")

    except ValidationError as e:
        logger.error(
            f"API Create place Pydantic validation error: {e.errors()}", exc_info=False
        )
        # TODO: Flash message error
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(
            f"API Create place unexpected error before CRUD: {e}", exc_info=True
        )
        # TODO: Flash message error
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    created_place = await crud.create_place(place=place_data, db=db)

    if created_place is None:
        logger.error(
            f"Failed to create place '{place_data.name}' in DB (CRUD operation failed). Check Supabase schema and logs."
        )
        # TODO: Flash error
    else:
        logger.info(f"Place '{created_place.name}' created (ID: {created_place.id}).")
        # TODO: Flash success

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# POST /places/{place_id}/update-status
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
    logger.info(f"API Update status form for place {place_id} to {new_status.value}")
    place_update = models.PlaceUpdate(status=new_status)
    updated_place = await crud.update_place(
        place_id=place_id, place_update=place_update, db=db
    )
    if updated_place is None:
        logger.warning(f"Failed to update status/find place ID {place_id}.")
        # TODO: Flash error
    else:
        logger.info(f"Status updated for place ID {place_id}.")
        # TODO: Flash success
    return RedirectResponse(
        url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


# POST /places/{place_id}/edit
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
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    status_input: PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    logger.info(f"API Edit place form submission for ID {place_id}, Name='{name}'")
    redirect_url = request.url_for("read_root")
    try:
        place_update_data = models.PlaceUpdate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=status_input,
            address=address,
            city=city,
            country=country,
        )
        updated_place = await crud.update_place(
            place_id=place_id, place_update=place_update_data, db=db
        )
        if updated_place is None:
            logger.error(f"Failed to update place ID {place_id} via edit form.")
            # TODO: Flash error
        else:
            logger.info(f"Place ID {place_id} updated via edit form.")
            # TODO: Flash success
    except ValidationError as e:
        logger.error(
            f"API Edit place validation error ID {place_id}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error
    except Exception as e:
        logger.error(
            f"API Unexpected error editing place ID {place_id}: {e}", exc_info=True
        )
        # TODO: Flash generic error
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# POST /places/{place_id}/review-image
@app.post(
    "/places/{place_id}/review-image",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Add/Update Review and Image",
)
async def add_review_image_endpoint(
    request: Request,
    place_id: int,
    db=Depends(get_db),
    review_title: str = Form(""),
    review_text: str = Form(""),
    image_file: Optional[UploadFile] = File(None, alias="image"),
):
    logger.info(
        f"API Review/Image form for ID {place_id}. Title: '{review_title[:20]}...', Image provided: {image_file is not None and image_file.filename}"
    )
    redirect_url = request.url_for("read_root")
    image_public_url = None

    if image_file and image_file.filename:
        try:
            logger.info(
                f"Attempting image upload for place {place_id}, filename: {image_file.filename}"
            )
            image_public_url = await crud.upload_place_image(
                place_id=place_id, file=image_file, db=db
            )
            if image_public_url:
                logger.info(f"Image uploaded successfully for place {place_id}.")
            else:
                logger.error(
                    f"Image upload OK but no URL returned for place {place_id}."
                )
        except HTTPException as http_exc:
            logger.error(
                f"Image upload failed for place {place_id}: {http_exc.status_code} - {http_exc.detail}"
            )
            # TODO: Flash message image upload error
        except Exception as e:
            logger.error(
                f"Unexpected error during image upload for place {place_id}: {e}",
                exc_info=True,
            )
            # TODO: Flash message generic image upload error

    try:
        update_payload = {
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "status": PlaceStatus.VISITED,
        }
        if image_public_url:
            update_payload["image_url"] = image_public_url

        place_update_model = models.PlaceUpdate(**update_payload)
        logger.debug(
            f"Prepared update model for place {place_id}: {place_update_model.model_dump()}"
        )

        updated_place = await crud.update_place(
            place_id=place_id, place_update=place_update_model, db=db
        )

        if updated_place:
            logger.info(
                f"Review/image/status details updated successfully for place ID {place_id}."
            )
            # TODO: Flash overall success
        else:
            logger.error(
                f"Failed to update review/image/status details in DB for place ID {place_id} (CRUD returned None)."
            )
            # TODO: Flash update failure

    except ValidationError as e:
        logger.error(
            f"API Review/Image Pydantic validation error ID {place_id}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error
    except Exception as e:
        logger.error(
            f"API Unexpected error saving review/image details ID {place_id}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# POST /places/{place_id}/delete (Soft Delete)
@app.post(
    "/places/{place_id}/delete",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Handle Delete Place Form (Soft Delete)",
)
async def delete_place_from_form_endpoint(
    request: Request, place_id: int, db=Depends(get_db)
):
    """Handles soft deletion of a place triggered by a form."""
    logger.warning(f"API Soft Delete request (form) for place ID {place_id}")
    redirect_url = request.url_for("read_root")
    success = await crud.delete_place(place_id=place_id, db=db)
    if not success:
        logger.error(f"Failed to soft delete place ID {place_id} via form.")
        # TODO: Flash error
    else:
        logger.info(f"Place ID {place_id} soft deleted via form.")
        # TODO: Flash success
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- JSON API Endpoints ---
# GET /api/places/
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


# GET /api/places/{place_id}
@app.get("/api/places/{place_id}", response_model=models.Place, tags=["API - Places"])
async def get_place_api(place_id: int, db=Depends(get_db)):
    logger.info(f"API Get place: ID {place_id}")
    db_place = await crud.get_place_by_id(place_id=place_id, db=db)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Place not found or deleted"
        )
    return models.Place.model_validate(db_place)


# DELETE /api/places/{place_id} (Soft Delete)
@app.delete(
    "/api/places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["API - Places"],
)
async def delete_place_api(place_id: int, db=Depends(get_db)):
    """API endpoint to soft delete a place."""
    logger.info(f"API Soft Delete place: ID {place_id}")
    success = await crud.delete_place(place_id=place_id, db=db)
    if not success:
        existing = await crud.get_place_by_id(
            place_id=place_id, db=db, include_deleted=True
        )
        status_code = (
            status.HTTP_404_NOT_FOUND if not existing else status.HTTP_400_BAD_REQUEST
        )
        detail = (
            "Place not found"
            if not existing
            else "Place already deleted or delete failed"
        )
        raise HTTPException(status_code=status_code, detail=detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# PUT /api/places/{place_id}
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
        existing = await crud.get_place_by_id(
            place_id=place_id, db=db, include_deleted=True
        )
        detail = (
            "Place not found"
            if not existing
            else "Could not update place (possibly deleted or error)"
        )
        status_code = (
            status.HTTP_404_NOT_FOUND if not existing else status.HTTP_400_BAD_REQUEST
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
