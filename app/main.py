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
    APIRouter,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError
from typing import List, Optional
from pydantic import ValidationError
from datetime import datetime, timezone

from . import crud, models, database, auth_utils
from .core.config import settings, logger
from .models import (
    PlaceCategory,
    PlaceStatus,
    UserInToken,
    UserCreate,
    Token,
    Msg,
    PasswordResetRequest,
)

# Import necessary dependencies from database
from .database import (
    get_db,
    get_current_active_user,
    get_token_from_cookie,  # Needed for optional user check
    get_supabase_service_client,  # Need this dependency for some operations
    get_base_supabase_client,  # Need this for non-authenticated routes
)

# --- App Initialization ---
app = FastAPI(
    title="Mapa Planes",
    description="A web app to manage and map places to visit.",
    version="1.0.0",
)

# --- CORS Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS
        ],  # Ensure stripping whitespace
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.BACKEND_CORS_ORIGINS}")

# --- Static Files and Templates ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Geocoder Setup ---
geocoder: OpenCageGeocode | None = None
if not settings.OPENCAGE_API_KEY:
    logger.warning(
        "OPENCAGE_API_KEY is not set. Geocoding endpoint will be unavailable."
    )
else:
    try:
        geocoder = OpenCageGeocode(settings.OPENCAGE_API_KEY)
        logger.info("OpenCage Geocoder initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenCage Geocoder: {e}", exc_info=True)


# --- Helper Functions ---
async def perform_geocode(address: str) -> models.GeocodeResult | None:
    """Performs geocoding using OpenCage Geocoder. Raises HTTPException on failure."""
    if not geocoder:
        logger.error("Geocoding skipped: OpenCage Geocoder not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service is not configured or API key missing.",
        )
    try:
        logger.debug(f"Geocoding address with OpenCage: '{address}'")
        # Use asyncio.to_thread for the blocking geocode call
        results = await asyncio.to_thread(
            geocoder.geocode,
            address,
            key=settings.OPENCAGE_API_KEY,
            language="es",  # Optional: prioritize Spanish results
            countrycode="co",  # Optional: limit to Colombia
            limit=1,
            no_annotations=1,
            timeout=15,  # Add timeout
        )

        if results and len(results):
            best_result = results[0]
            components = best_result.get("components", {})
            geometry = best_result.get("geometry", {})
            formatted_address = best_result.get("formatted")

            if geometry and "lat" in geometry and "lng" in geometry:
                # Extract relevant address components
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
                # Construct a street address if possible
                street_address_parts = filter(None, [house_number, road, neighbourhood])
                street_address = ", ".join(street_address_parts)

                result = models.GeocodeResult(
                    latitude=geometry["lat"],
                    longitude=geometry["lng"],
                    address=street_address or None,  # Use constructed address or None
                    city=city,
                    country=country,
                    display_name=formatted_address,  # Full formatted address
                )
                logger.debug(f"OpenCage geocoding successful: {formatted_address}")
                return result
            else:
                logger.warning(
                    f"OpenCage result missing geometry for '{address}'. Data: {best_result}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Geocoding result lacks coordinate data.",
                )
        else:
            logger.warning(f"OpenCage geocoding failed: No results for '{address}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found by geocoder.",
            )
    except RateLimitExceededError:
        logger.error("OpenCage API rate limit exceeded.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Geocoding limit reached. Please try again later.",
        )
    except HTTPException as http_exc:
        raise http_exc  # Re-raise known HTTP exceptions
    except (
        asyncio.TimeoutError
    ):  # Catch potential timeouts from to_thread if geocoder takes too long
        logger.error(f"OpenCage geocoding timed out for address: '{address}'")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Geocoding request timed out.",
        )
    except Exception as e:
        logger.error(
            f"OpenCage geocoding unexpected error for '{address}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during geocoding.",
        )


# --- Authentication Check Dependency (Optional, for pages) ---
async def get_optional_current_user(
    request: Request,
    # Use the base client (anon key) for user validation as it doesn't need RLS
    db: database.SupabaseClient = Depends(database.get_base_supabase_client),
) -> models.UserInToken | None:
    """Dependency that returns the current user if authenticated, or None otherwise."""
    try:
        token = await get_token_from_cookie(request)  # Reuse cookie logic
        if token is None:
            logger.debug("get_optional_current_user: No token found in cookie.")
            return None
        # Use get_current_user logic directly but return None on 401
        # Pass the base_db explicitly here, as get_current_user depends on it
        current_user = await database.get_current_user(token=token, base_db=db)
        logger.debug(f"get_optional_current_user: Found user {current_user.email}")
        return current_user
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            logger.debug("get_optional_current_user: Token invalid or expired (401).")
            return None
        logger.error(
            f"Unexpected HTTPException in get_optional_current_user: {e.status_code} - {e.detail}",
            exc_info=False,
        )
        return None  # Treat other errors as not logged in for safety
    except Exception as e:
        logger.error(
            f"Critical unexpected error in get_optional_current_user: {e}",
            exc_info=True,
        )
        return None


# --- Root Endpoint (Map Page) ---
@app.get("/", response_class=HTMLResponse, summary="Main Map Page")
async def read_root(
    request: Request,
    # Use the authenticated get_db for data fetching
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    category_str: Optional[str] = Query(None, alias="category"),
    status_str: Optional[str] = Query(None, alias="status"),
):
    """Serves the main HTML page displaying the user's map and places."""
    logger.info(
        f"Request root page for user {current_user.email}. Filters: category='{category_str}', status='{status_str}'"
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

    map_html_content = '<p style="color: red; text-align: center; padding: 20px;">Map could not be loaded.</p>'
    places = []
    try:
        places = await crud.get_places(
            db=db,
            user_id=current_user.id,
            category=category,
            status_filter=status_filter,
            limit=500,  # Consider pagination
        )
        logger.info(
            f"MAIN: Fetched {len(places)} places for user {current_user.email}."
        )

        # Default map center (Bogotá)
        map_center = [4.7110, -74.0721]
        zoom_start = 12
        # Attempt to center map based on existing places if available
        if places:
            valid_coords = [
                (p.latitude, p.longitude)
                for p in places
                if p.latitude is not None and p.longitude is not None
            ]
            if valid_coords:
                avg_lat = sum(lat for lat, lon in valid_coords) / len(valid_coords)
                avg_lon = sum(lon for lat, lon in valid_coords) / len(valid_coords)
                map_center = [avg_lat, avg_lon]
                # Simple zoom adjustment based on number of places (very basic)
                if len(valid_coords) > 50:
                    zoom_start = 10
                elif len(valid_coords) > 10:
                    zoom_start = 11

        m = folium.Map(
            location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap"
        )

        # Icon and Color Mappings
        category_icons = {
            PlaceCategory.RESTAURANT: "utensils",
            PlaceCategory.PARK: "tree",
            PlaceCategory.ENTERTAINMENT: "film",
            PlaceCategory.SHOPPING: "shopping-cart",
            PlaceCategory.TRIP: "plane",
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
                # Basic validation before attempting to create marker
                if (
                    place.latitude is None
                    or place.longitude is None
                    or place.status is None
                    or place.category is None
                ):
                    logger.warning(
                        f"MAIN: Skipping place ID {place.id} ('{place.name}') due to missing essential data (lat/lon/status/category)."
                    )
                    continue

                try:
                    # Extract data with defaults/escaping
                    place_lat, place_lon = place.latitude, place.longitude
                    place_name = html.escape(place.name or "Unnamed Place")
                    place_category_enum = place.category
                    place_status_enum = place.status
                    review_title_raw = place.review_title
                    review_text_raw = place.review
                    image_url_str = str(place.image_url or "")
                    rating = place.rating

                    # Prepare data object for JS (used in popup buttons)
                    place_data_for_js = {
                        "id": place.id,
                        "name": place.name,  # Use original name for JS
                        "latitude": place.latitude,
                        "longitude": place.longitude,
                        "category": place_category_enum.value,
                        "status": place_status_enum.value,
                        "address": place.address,
                        "city": place.city,
                        "country": place.country,
                        "review_title": review_title_raw,
                        "review": review_text_raw,
                        "image_url": image_url_str,
                        "rating": rating,
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
                    # Safely escape the JSON string for use in an HTML attribute
                    js_object_string = json.dumps(place_data_for_js)
                    escaped_js_string_for_html_attr = html.escape(
                        js_object_string, quote=True
                    )

                    # Build Popup HTML dynamically
                    popup_parts = [
                        f"<h4 style='margin-bottom: 8px;'>{place_name}</h4>",
                        "<div style='font-size: 0.9em; max-height: 250px; overflow-y: auto;'>",  # Add scroll for long content
                    ]
                    # Category and Status
                    popup_parts.append(
                        f"<b>Category:</b> {html.escape(place_category_enum.value.replace('_', ' ').title())}<br>"
                    )
                    popup_parts.append(
                        f"<b>Status:</b> {html.escape(place_status_enum.value.replace('_', ' ').title())}<br>"
                    )

                    # Rating (display stars)
                    if rating:
                        stars_html = "".join(
                            [
                                '<i class="fas fa-star" style="color: #FFD700;"></i>'
                                for _ in range(rating)
                            ]
                        )
                        stars_html += "".join(
                            [
                                '<i class="far fa-star" style="color: #ccc;"></i>'
                                for _ in range(5 - rating)
                            ]
                        )
                        popup_parts.append(f"<b>Rating:</b> {stars_html}<br>")

                    # Address
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

                    # Review and Image section
                    has_review_content = bool(
                        review_text_raw or review_title_raw or rating
                    )
                    has_image = bool(image_url_str and image_url_str.startswith("http"))
                    if has_review_content or has_image:
                        popup_parts.append(
                            "<hr style='margin: 5px 0; border-top-color: #eee;'>"
                        )
                        if review_title_raw:
                            popup_parts.append(
                                f"<b>Review:</b> {html.escape(review_title_raw)}<br>"
                            )
                        if review_text_raw:
                            # Show snippet, full review in modal
                            snippet = html.escape(review_text_raw[:100]) + (
                                "..." if len(review_text_raw) > 100 else ""
                            )
                            popup_parts.append(f"<i>{snippet}</i><br>")
                        if has_image:
                            # Show thumbnail in popup
                            popup_parts.append(
                                f'<img src="{html.escape(image_url_str)}" alt="{place_name}" style="max-width: 100px; max-height: 75px; margin-top: 5px; display: block; border-radius: 4px; cursor: pointer;" onclick="window.parent.showImageOverlay(event)">'
                            )  # Added onclick for overlay

                    popup_parts.append("</div>")  # End scrollable div

                    # Action Buttons Section
                    popup_parts.append(
                        "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px; display: flex; flex-wrap: wrap; gap: 5px;'>"
                    )

                    # Status Update Dropdown Form
                    status_form_url = request.url_for(
                        "update_place_status_from_form_endpoint", place_id=place.id
                    )
                    status_options = "".join(
                        [
                            f'<option value="{s.value}" {"selected" if place_status_enum == s else ""}>{s.value.replace("_", " ").title()}</option>'
                            for s in PlaceStatus
                        ]
                    )
                    popup_parts.append(
                        f'<form action="{status_form_url}" method="post" style="display: inline-block; margin-right: 5px;" target="_top"><select name="status" onchange="this.form.submit()" title="Change Status">{status_options}</select><noscript><button type="submit">Update</button></noscript></form>'
                    )

                    # Edit Place Button
                    popup_parts.append(
                        f'<button type="button" onclick="window.parent.showEditPlaceForm(\'{escaped_js_string_for_html_attr}\')" title="Edit Place Details">Edit</button>'
                    )

                    # Review Button (conditional text)
                    if has_review_content or has_image:
                        popup_parts.append(
                            f'<button type="button" onclick="window.parent.showSeeReviewModal(\'{escaped_js_string_for_html_attr}\')" title="See Review / Image">See Review</button>'
                        )
                    else:
                        popup_parts.append(
                            f'<button type="button" onclick="window.parent.showReviewForm(\'{escaped_js_string_for_html_attr}\')" title="Add Review / Image">Add Review</button>'
                        )

                    # Delete Button Form
                    delete_form_url = request.url_for(
                        "delete_place_from_form_endpoint", place_id=place.id
                    )
                    popup_parts.append(
                        f'<form action="{delete_form_url}" method="post" target="_top" style="display: inline-block;" onsubmit="return confirm(\'Are you sure you want to delete this place?\');"><button type="submit" title="Delete Place">Delete</button></form>'
                    )

                    popup_parts.append("</div>")  # End actions div
                    popup_html = "".join(popup_parts)

                    # Create Marker
                    marker_color = status_color_map.get(
                        place_status_enum, default_color
                    )
                    marker_icon = category_icons.get(place_category_enum, default_icon)
                    folium.Marker(
                        location=[place_lat, place_lon],
                        popup=folium.Popup(popup_html, max_width=350),
                        tooltip=f"{place_name} ({html.escape(place_status_enum.value.replace('_', ' ').title())})",
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

            logger.info(
                f"MAIN: Successfully added {marker_count} markers for user {current_user.email}."
            )
            map_html_content = m._repr_html_()  # Get HTML representation of the map
        else:
            logger.info(
                f"MAIN: No places found for user {current_user.email} to display on map."
            )
            # Still render the base map even if no places
            map_html_content = m._repr_html_()

    except Exception as page_load_error:
        logger.error(
            f"MAIN: Critical error generating map page for user {current_user.email}: {page_load_error}",
            exc_info=True,
        )
        # Keep the default error message for map_html_content

    # Prepare context for Jinja2 template
    context = {
        "request": request,
        "map_html": map_html_content,
        "places": places,  # Pass places list to template if needed elsewhere
        "categories": [c.value for c in PlaceCategory],
        "statuses": [s.value for s in PlaceStatus],
        "current_category": category_str or None,
        "current_status": status_str or None,
        "user_email": current_user.email,
    }
    return templates.TemplateResponse("index.html", context)


# --- API Router for Auth ---
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: database.SupabaseClient = Depends(
        database.get_base_supabase_client
    ),  # Use base client for login
):
    """Handles user login, sets HttpOnly cookie with token."""
    logger.info(f"Login attempt for user: {form_data.username}")
    try:
        # Use asyncio.to_thread for the synchronous Supabase call
        auth_response = await asyncio.to_thread(
            db.auth.sign_in_with_password,
            {"email": form_data.username, "password": form_data.password},
        )
        logger.debug(
            f"Supabase sign_in response: User ID {auth_response.user.id if auth_response.user else 'None'}, Session present: {auth_response.session is not None}"
        )
        if (
            not auth_response
            or not auth_response.session
            or not auth_response.session.access_token
        ):
            # Log specific failure reason if possible from Supabase response structure
            logger.warning(
                f"Login failed for {form_data.username}: No session or token in response."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",  # Keep detail generic
            )

        access_token = auth_response.session.access_token
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,  # Crucial for security
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="Lax",  # Recommended for most cases
            secure=settings.APP_ENV != "development",  # Set Secure flag in production
            path="/",  # Cookie accessible for all paths
        )
        logger.info(f"Login successful for {form_data.username}, token set in cookie.")
        # Return the token in the response body as well (standard practice)
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        # Try to parse Supabase/GoTrue errors more specifically
        err_msg = getattr(e, "message", str(e))
        status_code = status.HTTP_401_UNAUTHORIZED
        detail = "Incorrect email or password"  # Default generic message

        logger.error(f"Login error for {form_data.username}: {err_msg}", exc_info=False)

        # Check for common GoTrue error messages
        if "Invalid login credentials" in err_msg:
            pass  # Keep generic detail
        elif "Email not confirmed" in err_msg:
            detail = "Email not confirmed. Please check your inbox."
        elif (
            "User not found" in err_msg
        ):  # Although Supabase might return "Invalid login" for this too
            pass  # Keep generic detail for security (don't reveal email existence)
        else:
            # If it's not a recognized auth error, maybe it's a server issue
            logger.error(
                f"Unexpected login error for {form_data.username}", exc_info=True
            )
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            detail = "An internal error occurred during login."

        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},  # Standard for 401
        )


@auth_router.post("/signup", response_model=Msg, status_code=status.HTTP_201_CREATED)
async def signup_user(
    user_in: UserCreate,
    db: database.SupabaseClient = Depends(database.get_base_supabase_client),
):
    """Handles new user registration."""
    logger.info(f"Signup attempt for email: {user_in.email}")
    # create_supabase_user already handles potential exceptions and logging
    await auth_utils.create_supabase_user(user_data=user_in, db=db)
    # If the above didn't raise an exception, it means signup was initiated.
    # Supabase might require email confirmation depending on project settings.
    return Msg(
        message="Signup successful. Please check your email for a confirmation link if required."
    )


@auth_router.post("/request-password-reset", response_model=Msg)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: database.SupabaseClient = Depends(database.get_base_supabase_client),
):
    """Initiates the password reset flow."""
    logger.info(f"Password reset request for: {reset_data.email}")
    # This function usually just triggers an email and doesn't throw errors
    # for non-existent users to prevent enumeration attacks.
    await auth_utils.initiate_supabase_password_reset(email=reset_data.email, db=db)
    # Always return a generic success message
    return Msg(
        message="If an account exists for this email, a password reset link has been sent."
    )


@auth_router.post("/reset-password", response_model=Msg)
async def reset_password(
    new_password: str = Form(...),
    # This endpoint typically requires the user to be authenticated
    # via the token received after clicking the password reset link.
    # The frontend handles exchanging the code in the URL for a session,
    # then calls this endpoint with the new session cookie active.
    db: database.SupabaseClient = Depends(get_db),  # Use the authenticated client
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """Sets a new password for the authenticated user (post-reset flow)."""
    # Note: This assumes the user is already authenticated via the reset token flow
    # handled by the frontend (redirect -> code exchange -> session set -> call this).
    logger.warning(
        f"Attempting password update for user {current_user.email} via recovery flow."
    )
    try:
        # We use the client already authenticated by Depends(get_db)
        response = await asyncio.to_thread(
            db.auth.update_user, {"password": new_password}
        )
        if response and response.user:
            logger.info(f"Password successfully updated for user: {current_user.email}")
            return Msg(message="Password updated successfully.")
        else:
            # This case might indicate the token used wasn't valid anymore,
            # or some other issue with the update call.
            logger.error(
                f"Password update failed for user {current_user.email}. Supabase response: {response}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password update failed. The reset link may have expired or the request was invalid.",
            )
    except Exception as e:
        err_msg = getattr(e, "message", str(e))
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "Could not update password due to an internal error."

        # Check for specific Supabase/GoTrue errors related to password update
        if "Password requires" in err_msg:
            detail = "Password does not meet requirements."
            status_code = status.HTTP_400_BAD_REQUEST
        elif "same password" in err_msg.lower():
            detail = "New password cannot be the same as the old password."
            status_code = status.HTTP_400_BAD_REQUEST
        elif hasattr(e, "status_code") and e.status_code == 401:  # e.g., token expired
            detail = "Authentication failed or reset link expired."
            status_code = status.HTTP_401_UNAUTHORIZED
        elif (
            hasattr(e, "status_code") and e.status_code == 422
        ):  # e.g., validation error
            detail = "Invalid request data for password update."
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        logger.error(
            f"Error during password update for user {current_user.email}: {err_msg}",
            exc_info=(status_code == 500),  # Log full trace for unexpected errors
        )
        raise HTTPException(status_code=status_code, detail=detail)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    # Use Depends(get_db) to get the authenticated client needed for sign_out
    auth_db: database.SupabaseClient = Depends(get_db),
    # Inject current_user to ensure only authenticated users can logout
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """Logs the current user out by calling Supabase sign_out and clearing the cookie."""
    logger.info(f"Logout request for user: {current_user.email}")
    try:
        # Sign out invalidates the refresh token server-side.
        # Requires the authenticated client instance provided by get_db.
        logger.debug(f"Calling Supabase sign_out for user {current_user.email}")
        # Use the injected authenticated client (auth_db)
        await asyncio.to_thread(auth_db.auth.sign_out)
        logger.info(
            f"Supabase sign_out API call completed successfully for user: {current_user.email}"
        )
    except Exception as e:
        # Log the error but proceed to clear the cookie anyway.
        err_msg = getattr(e, "message", str(e))
        # Check if it's a known auth error (e.g., token already invalid)
        status_code = getattr(e, "status", None) or getattr(e, "status_code", None)
        if status_code == 401:
            logger.warning(
                f"Supabase sign_out failed (401), likely token already invalid for {current_user.email}. Proceeding with cookie clear."
            )
        else:
            logger.error(
                f"Error during Supabase sign_out call for {current_user.email}: {err_msg}",
                exc_info=True,  # Log trace for unexpected errors during signout
            )
        # No need to raise an exception here, just log and clear cookie

    # Always clear the cookie on the client-side regardless of server-side success/failure.
    response.delete_cookie(
        "access_token",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=settings.APP_ENV != "development",
    )
    logger.info(f"Access token cookie cleared for user: {current_user.email}")
    # Return No Content, the client-side JS handles the redirect.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.get("/me", response_model=UserInToken)
async def read_users_me(
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """Returns the basic information of the currently authenticated user."""
    logger.debug(f"'/me' endpoint accessed by user: {current_user.email}")
    return current_user


app.include_router(auth_router)


# --- Geocode Endpoint ---
@app.get(
    "/geocode",
    response_model=models.GeocodeResult,
    summary="Geocode Address",
    tags=["Tools"],
    # This endpoint doesn't strictly require authentication, but rate limiting might be wise.
    # For now, it's public.
)
async def geocode_address_endpoint(address: str = Query(..., min_length=3)):
    """Geocodes a given address string using OpenCage."""
    logger.info(f"Public Geocoding request for: '{address}'")
    # perform_geocode handles errors and raises HTTPException
    result = await perform_geocode(address)
    return result


# --- Form Handling Endpoints ---
# These endpoints handle traditional form submissions (e.g., from popups)
# and typically redirect back to the main page.


@app.post(
    "/places/",
    status_code=status.HTTP_303_SEE_OTHER,  # Use 303 for POST-Redirect-Get pattern
    summary="Create New Place (Form)",
    tags=["Forms"],
    # No response_model needed as we redirect
)
async def create_new_place_endpoint(
    request: Request,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    place_status_input: PlaceStatus = Form(
        ..., alias="status"
    ),  # Renamed to avoid conflict
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
):
    """Handles the submission of the 'Add New Place' form."""
    logger.info(f"FORM Create place received for user {current_user.email}.")
    redirect_url = request.url_for("read_root")  # Redirect back to map page

    try:
        # Validate data using Pydantic model
        place_data = models.PlaceCreate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            category=category,
            status=place_status_input,
            address=address,
            city=city,
            country=country,
            # Note: rating/review_title are not in this form
        )
    except (ValidationError, ValueError) as e:
        logger.error(
            f"FORM Create place validation error for user {current_user.email}: {e}",
            exc_info=False,
        )
        # TODO: Implement flash messages to show error on redirect
        # For now, just redirect back
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    # Call CRUD function to create the place
    created_place = await crud.create_place(
        place=place_data, user_id=current_user.id, db=db
    )

    if created_place is None:
        logger.error(
            f"FORM Failed to create place '{place_data.name}' for user {current_user.email} in DB."
        )
        # TODO: Flash error message
    else:
        logger.info(
            f"FORM Place '{created_place.name}' (ID: {created_place.id}) created for user {current_user.email}."
        )
        # TODO: Flash success message

    # Redirect back to the map page
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/places/{place_id}/update-status",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Update Place Status (Form)",
    tags=["Forms"],
)
async def update_place_status_from_form_endpoint(
    request: Request,
    place_id: int,
    new_status: PlaceStatus = Form(..., alias="status"),  # Read status from form
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """Handles status updates submitted from the map popup dropdown form."""
    logger.info(
        f"FORM Update status for place {place_id} to {new_status.value} by user {current_user.email}"
    )
    # Prepare update payload
    place_update = models.PlaceUpdate(
        status=new_status, updated_at=datetime.now(timezone.utc)
    )

    # Call CRUD function
    updated_place = await crud.update_place(
        place_id=place_id, user_id=current_user.id, place_update=place_update, db=db
    )

    if updated_place is None:
        logger.warning(
            f"FORM Failed to update status for place ID {place_id}, user {current_user.email}."
        )
        # TODO: Flash error
    else:
        logger.info(
            f"FORM Status updated for place ID {place_id} by user {current_user.email}."
        )
        # TODO: Flash success

    # Redirect back to the map page (or potentially the previous filtered view)
    # Getting the previous URL with filters might require passing query params or using Referer header carefully
    return RedirectResponse(
        url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post(
    "/places/{place_id}/edit",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Handle Edit Place Form Submission",
    tags=["Forms"],
)
async def edit_place_from_form_endpoint(
    request: Request,
    place_id: int,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    # Include service client dependency if needed for image deletion during update
    db_service: Optional[database.SupabaseClient] = Depends(
        get_supabase_service_client
    ),
    # Form fields matching the edit form in index.html
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: PlaceCategory = Form(...),
    status_input: PlaceStatus = Form(..., alias="status"),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    rating: Optional[int] = Form(None),  # Rating can be None
    review_title: Optional[str] = Form(None),
    review_text: Optional[str] = Form(None),
    remove_image: Optional[str] = Form(None),  # Checkbox value is 'yes' if checked
):
    """Handles the submission of the main 'Edit Place' form."""
    logger.info(
        f"FORM Edit place submission for ID {place_id} by user {current_user.email}"
    )
    redirect_url = request.url_for("read_root")

    try:
        # Construct the update payload dictionary
        update_payload_dict = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "status": status_input,
            "address": address
            if address is not None
            else None,  # Ensure None if empty string potentially
            "city": city if city is not None else None,
            "country": country if country is not None else None,
            "rating": rating,  # Pass rating directly (can be None)
            "review_title": review_title.strip() if review_title else None,
            "review": review_text.strip() if review_text else None,
            "updated_at": datetime.now(timezone.utc),
        }

        # Handle image removal specifically
        if remove_image == "yes":
            # Explicitly set image_url to None in the payload
            update_payload_dict["image_url"] = None
            logger.debug(f"Edit form signals removal of image for place {place_id}")
        else:
            # If checkbox not checked, don't include image_url in payload
            # to avoid accidentally setting it to None if field wasn't present.
            # crud.update_place handles keeping the existing URL if not provided.
            pass

        # Validate payload using Pydantic model
        # Filter payload before validation to handle optional fields correctly
        final_payload = {
            k: v
            for k, v in update_payload_dict.items()
            if k == "image_url" or v is not None
        }

        if not final_payload:
            logger.warning(
                f"Edit form for place {place_id} resulted in empty update payload."
            )
            # Redirect back without change, maybe flash a message?
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

        place_update_data = models.PlaceUpdate(
            **final_payload
        )  # Validate final payload

        # Call CRUD update function
        updated_place = await crud.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_data,
            db=db,
            db_service=db_service,  # Pass service client for potential image deletion
        )

        if updated_place is None:
            logger.error(
                f"FORM Failed to update place ID {place_id}, user {current_user.email}."
            )
            # TODO: Flash error
        else:
            logger.info(
                f"FORM Place ID {place_id} updated by user {current_user.email}."
            )
            # TODO: Flash success

    except ValidationError as e:
        logger.error(
            f"FORM Edit place validation error ID {place_id}, user {current_user.email}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error
    except Exception as e:
        logger.error(
            f"FORM Unexpected error editing place ID {place_id}, user {current_user.email}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/places/{place_id}/review-image",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Add/Update Review and Image (Form)",
    tags=["Forms"],
)
async def add_review_image_endpoint(
    request: Request,
    place_id: int,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    db_service: Optional[database.SupabaseClient] = Depends(
        get_supabase_service_client
    ),
    # Form fields from the review/image modal form
    review_title: str = Form(""),  # Default to empty string if not provided
    review_text: str = Form(""),  # Default to empty string
    rating: Optional[int] = Form(None),  # Rating is optional
    image_file: Optional[UploadFile] = File(
        None, alias="image"
    ),  # Optional image upload
    remove_image: Optional[str] = Form(None),  # Checkbox value 'yes'
):
    """Handles the submission of the review and image form."""
    logger.info(
        f"FORM Review/Image submission for ID {place_id} by user {current_user.email}."
    )
    redirect_url = request.url_for("read_root")
    image_public_url = None  # Variable to store uploaded image URL
    update_payload = {}  # Dictionary to build the update payload

    # --- Handle Image Upload/Removal First ---
    if remove_image == "yes":
        logger.info(
            f"Review form signals removal of existing image for place {place_id}"
        )
        # Set image_url to None in the DB update later
        update_payload["image_url"] = None  # Explicit intent to remove
    elif image_file and image_file.filename:
        # Only process if a file was actually uploaded
        logger.info(
            f"Processing image upload: {image_file.filename} for place {place_id}"
        )
        try:
            # Call CRUD function to upload image
            image_public_url = await crud.upload_place_image(
                place_id=place_id, user_id=current_user.id, file=image_file, db=db
            )
            if image_public_url:
                update_payload["image_url"] = image_public_url
                logger.info(
                    f"Image uploaded successfully for place {place_id}, URL: {image_public_url}"
                )
            else:
                # Upload function might return None without raising HTTP exception on some failures
                logger.error(
                    f"Image upload function returned None for place {place_id}, user {current_user.email}."
                )
                # TODO: Flash warning/error message
                # Decide if we should proceed with text/rating update or stop
                # For now, let's stop if upload was attempted but failed softly
                return RedirectResponse(
                    url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
                )
        except HTTPException as http_exc:
            # CRUD function raises HTTPException on critical errors (e.g., 404, 500)
            logger.error(
                f"Image upload failed for place {place_id}: {http_exc.status_code} - {http_exc.detail}"
            )
            # TODO: Flash error message based on http_exc.detail
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )  # Stop processing if upload fails hard
        except Exception as e:
            # Catch unexpected errors during upload logic
            logger.error(
                f"Unexpected error during image upload processing for place {place_id}: {e}",
                exc_info=True,
            )
            # TODO: Flash generic error
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

    # --- Prepare and Execute DB Update for Review/Rating/Image URL ---
    try:
        # Add review, rating, and potentially image URL to payload
        update_payload.update(
            {
                "review_title": review_title.strip() if review_title else None,
                "review": review_text.strip() if review_text else None,
                "rating": rating,  # Pass rating directly (can be None)
                # Automatically mark as visited if review/rating/image is added? Optional.
                "status": PlaceStatus.VISITED,  # Enforce visited status on review add/edit
                "updated_at": datetime.now(timezone.utc),
            }
        )

        # Filter out keys with None values, *unless* it's image_url being set to None
        final_update_payload = {
            k: v for k, v in update_payload.items() if k == "image_url" or v is not None
        }

        # Check if there's anything actually to update (excluding automatic updated_at/status)
        # Need special check for image_url = None
        is_image_removal = (
            "image_url" in final_update_payload
            and final_update_payload["image_url"] is None
        )
        has_other_changes = any(
            k in final_update_payload
            for k in ["review_title", "review", "rating", "image_url"]
            if k != "image_url" or final_update_payload.get(k) is not None
        )

        if not is_image_removal and not has_other_changes:
            logger.warning(
                f"No actual review/image data provided or changed for place {place_id}"
            )
            # Maybe flash a message?
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

        # Validate the final payload
        place_update_model = models.PlaceUpdate(**final_update_payload)

        # Call CRUD update function
        updated_place = await crud.update_place(
            place_id=place_id,
            user_id=current_user.id,
            place_update=place_update_model,
            db=db,
            db_service=db_service,  # Pass service client for potential old image deletion
        )

        if updated_place:
            logger.info(f"FORM Review/image details updated for place ID {place_id}.")
            # TODO: Flash success
        else:
            logger.error(
                f"FORM Failed to update review/image details in DB for place ID {place_id}."
            )
            # This is problematic if image was uploaded but DB failed. Orphaned image?
            # TODO: Flash failure
            # Consider deleting uploaded image if DB update fails? Complex rollback.

    except ValidationError as e:
        logger.error(
            f"FORM Review/Image Pydantic validation error ID {place_id}: {e.errors()}",
            exc_info=False,
        )
        # TODO: Flash validation error
    except Exception as e:
        logger.error(
            f"FORM Unexpected error saving review/image details ID {place_id}: {e}",
            exc_info=True,
        )
        # TODO: Flash generic error

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post(
    "/places/{place_id}/delete",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Handle Delete Place Form (Soft Delete)",
    tags=["Forms"],
)
async def delete_place_from_form_endpoint(
    request: Request,
    place_id: int,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    db_service: Optional[database.SupabaseClient] = Depends(
        get_supabase_service_client
    ),
):
    """Handles the submission of the delete confirmation from the map popup."""
    logger.warning(
        f"FORM Soft Delete request for place ID {place_id} by user {current_user.email}"
    )
    redirect_url = request.url_for("read_root")

    # Call CRUD soft delete function
    success = await crud.delete_place(
        place_id=place_id, user_id=current_user.id, db=db, db_service=db_service
    )

    if not success:
        logger.error(
            f"FORM Failed to soft delete place ID {place_id} for user {current_user.email}."
        )
        # TODO: Flash error
    else:
        logger.info(
            f"FORM Place ID {place_id} soft deleted by user {current_user.email}."
        )
        # TODO: Flash success

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- JSON API Endpoints ---
# These endpoints provide a programmatic way to interact with places data.
api_router = APIRouter(prefix="/api/v1", tags=["API - Places"])


@api_router.get("/places/", response_model=List[models.Place])
async def list_places_api(
    category: Optional[PlaceCategory] = Query(None),
    status_filter: Optional[PlaceStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """API endpoint to list places for the authenticated user, with optional filters."""
    logger.info(
        f"API List request for user {current_user.email}, Filters: cat={category}, status={status_filter}, skip={skip}, limit={limit}"
    )
    places_db = await crud.get_places(
        db=db,
        user_id=current_user.id,
        category=category,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
        include_deleted=False,  # API usually excludes deleted items by default
    )
    # Pydantic automatically handles serialization to the Place model
    return places_db


@api_router.get("/places/{place_id}", response_model=models.Place)
async def get_place_api(
    place_id: int,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
):
    """API endpoint to retrieve a specific place by ID for the authenticated user."""
    logger.info(f"API Get place request: ID {place_id} by user {current_user.email}")
    db_place = await crud.get_place_by_id(
        place_id=place_id, user_id=current_user.id, db=db, include_deleted=False
    )
    if db_place is None:
        # Log lookup attempt details
        logger.warning(
            f"API Get place failed: Place ID {place_id} not found or not accessible by user {current_user.email}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or access denied",
        )
    return db_place


@api_router.delete("/places/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place_api(
    place_id: int,
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    db_service: Optional[database.SupabaseClient] = Depends(
        get_supabase_service_client
    ),
):
    """API endpoint to soft delete a specific place by ID for the authenticated user."""
    logger.warning(
        f"API Soft Delete place request: ID {place_id} by user {current_user.email}"
    )
    success = await crud.delete_place(
        place_id=place_id, user_id=current_user.id, db=db, db_service=db_service
    )
    if not success:
        # Check if it didn't exist or was already deleted vs. actual failure
        existing = await crud.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        status_code = status.HTTP_404_NOT_FOUND
        detail = "Place not found or access denied."
        if existing and existing.deleted_at:
            # It was already deleted, maybe treat as success (idempotent)?
            # Or return a different status? For now, treat as not found for deletion.
            logger.info(
                f"API Delete failed because place ID {place_id} was already deleted by user {current_user.email}."
            )
        elif existing:
            # Exists but delete failed for other reason (DB error?)
            logger.error(
                f"API Delete failed unexpectedly for existing place ID {place_id}, user {current_user.email}."
            )
            status_code = status.HTTP_400_BAD_REQUEST
            detail = "Place deletion failed."
        else:
            logger.warning(
                f"API Delete failed: Place ID {place_id} not found for user {current_user.email}."
            )

        raise HTTPException(status_code=status_code, detail=detail)
    # If successful, return 204 No Content implicitly
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api_router.put("/places/{place_id}", response_model=models.Place)
async def update_place_api(
    place_id: int,
    place_update: models.PlaceUpdate,  # Request body is parsed into this model
    db: database.SupabaseClient = Depends(get_db),
    current_user: models.UserInToken = Depends(get_current_active_user),
    db_service: Optional[database.SupabaseClient] = Depends(
        get_supabase_service_client
    ),
):
    """API endpoint to update an existing place by ID for the authenticated user."""
    logger.info(
        f"API Update place request: ID {place_id} by user {current_user.email}."
    )
    # Ensure updated_at is set if not provided in the request
    if place_update.updated_at is None:
        place_update.updated_at = datetime.now(timezone.utc)

    # Call CRUD function
    updated_place = await crud.update_place(
        place_id=place_id,
        user_id=current_user.id,
        place_update=place_update,
        db=db,
        db_service=db_service,
    )
    if updated_place is None:
        # Check if it failed because place doesn't exist vs. other error
        existing = await crud.get_place_by_id(
            place_id=place_id, user_id=current_user.id, db=db, include_deleted=True
        )
        detail = "Place not found or access denied."
        status_code = status.HTTP_404_NOT_FOUND
        if existing:
            detail = "Could not update place."
            status_code = status.HTTP_400_BAD_REQUEST  # Or 500 if internal DB error?
            logger.error(
                f"API Update failed for existing place ID {place_id}, user {current_user.email}."
            )
        else:
            logger.warning(
                f"API Update failed: Place ID {place_id} not found for user {current_user.email}."
            )

        raise HTTPException(status_code=status_code, detail=detail)

    logger.info(
        f"API Place ID {place_id} updated successfully by user {current_user.email}."
    )
    return updated_place


app.include_router(api_router)


# --- Health Check ---
@app.get(
    "/health", status_code=status.HTTP_200_OK, summary="Health Check", tags=["System"]
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# --- HTML Pages ---
@app.get("/login", response_class=HTMLResponse, tags=["Pages"])
async def login_page(
    request: Request,
    # Use optional user check: if logged in, redirect away from login page
    user: models.UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the login page."""
    if user:
        logger.debug(
            f"User {user.email} already logged in, redirecting from /login to /"
        )
        return RedirectResponse(
            url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
        )
    # User not logged in, show the login template
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse, tags=["Pages"])
async def signup_page(
    request: Request,
    # Use optional user check: if logged in, redirect away from signup page
    user: models.UserInToken | None = Depends(get_optional_current_user),
):
    """Serves the signup page."""
    if user:
        logger.debug(
            f"User {user.email} already logged in, redirecting from /signup to /"
        )
        return RedirectResponse(
            url=request.url_for("read_root"), status_code=status.HTTP_303_SEE_OTHER
        )
    # User not logged in, show the signup template
    return templates.TemplateResponse("signup.html", {"request": request})
