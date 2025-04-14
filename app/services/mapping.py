import folium
import html
import json
import uuid
from typing import List, Optional, Tuple
from fastapi import Request
from branca.element import Element  # Import Element directly

from app.models.places import PlaceInDB, PlaceCategory, PlaceStatus
from app.core.config import logger


def generate_map_html(
    places: List[PlaceInDB],
    request: Request,
    category_filter: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
) -> str:
    """Generates the HTML representation of the Folium map with place markers,
    injecting a click listener for pinning mode and custom popup styles."""
    logger.info(
        f"Generating map HTML for {len(places)} places. Filters: cat={category_filter}, status={status_filter}"
    )

    map_center = [4.7110, -74.0721]
    zoom_start = 12
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
            if len(valid_coords) > 50:
                zoom_start = 10
            elif len(valid_coords) > 10:
                zoom_start = 11

    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
    map_var_name = m.get_name()

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

    # --- START: Injected CSS for Popups ---
    popup_style = """
<style>
    .map-popup-container {
        font-family: 'Poppins', sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #212529; /* var(--text-color) */
    }
    .map-popup-container h4 {
        margin: 0 0 8px 0;
        padding-bottom: 6px;
        font-size: 1.2em;
        font-weight: 600;
        color: #1B5E20; /* var(--primary-color-dark) */
        border-bottom: 1px solid #eee;
    }
    .popup-content-scrollable {
        max-height: 150px; /* Reduced height for scroll */
        overflow-y: auto;
        margin-bottom: 12px;
        padding-right: 8px; /* Space for scrollbar */
        word-wrap: break-word;
    }
    .popup-content-scrollable p,
    .popup-content-scrollable b,
    .popup-content-scrollable i,
    .popup-content-scrollable span {
        font-size: 0.95em;
        margin-bottom: 4px;
    }
    .popup-content-scrollable b {
        font-weight: 500;
        color: #444;
    }
    .popup-content-scrollable .rating-stars-display {
        font-size: 1em;
        margin-bottom: 6px;
    }
    .popup-content-scrollable .rating-stars-display .fas { color: #FFD700; }
    .popup-content-scrollable .rating-stars-display .far { color: #ccc; }
    .popup-content-scrollable img {
        max-width: 95%;
        height: auto;
        margin-top: 8px;
        border-radius: 4px;
        display: block;
        border: 1px solid #eee;
        cursor: pointer;
    }
    .popup-actions {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #eee;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        justify-content: flex-start; /* Align buttons left */
    }
    .popup-actions button {
        padding: 5px 10px;
        font-size: 0.85em;
        font-weight: 500;
        border-radius: 5px;
        cursor: pointer;
        border: none;
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: background-color 0.2s, transform 0.1s;
    }
    .popup-actions button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
    }
    .popup-actions button:active {
        transform: translateY(0);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .popup-btn-edit { background-color: #ff9800; /* var(--warning-color) */ }
    .popup-btn-edit:hover { background-color: #f57c00; /* var(--warning-color-hover) */ }
    .popup-btn-add-review { background-color: #0288d1; /* var(--info-color) */ }
    .popup-btn-add-review:hover { background-color: #0277bd; /* var(--info-color-hover) */ }
    .popup-btn-see-review { background-color: #607d8b; /* var(--see-review-bg) */ }
    .popup-btn-see-review:hover { background-color: #455a64; /* var(--see-review-hover-bg) */ }
    .popup-btn-delete { background-color: #d32f2f; /* var(--error-color) */ }
    .popup-btn-delete:hover { background-color: #b71c1c; /* var(--danger-color-hover) */ }
    .popup-actions form { /* Ensure form doesn't add extra space */
        margin: 0;
        padding: 0;
        display: inline-block; /* Keep button inline */
    }
</style>
"""
    # --- END: Injected CSS for Popups ---

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
                    f"MAPGEN: Skipping place ID {place.id} ('{place.name}') due to missing data."
                )
                continue
            try:
                place_lat, place_lon = place.latitude, place.longitude
                place_name = html.escape(place.name or "Unnamed Place")
                place_category_enum = place.category
                place_status_enum = place.status
                review_title_raw = place.review_title
                review_text_raw = place.review
                image_url_str = str(place.image_url or "")
                rating = place.rating

                place_data_for_js = {
                    "id": place.id,
                    "name": place.name or "",
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "category": place_category_enum.value
                    if place_category_enum
                    else PlaceCategory.OTHER.value,
                    "status": place_status_enum.value
                    if place_status_enum
                    else PlaceStatus.PENDING.value,
                    "address": place.address or "",
                    "city": place.city or "",
                    "country": place.country or "",
                    "review_title": review_title_raw or "",
                    "review": review_text_raw or "",
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
                js_object_string = json.dumps(place_data_for_js)
                escaped_js_string_for_html_attr = html.escape(
                    js_object_string, quote=True
                )

                # --- START: Popup HTML Generation ---
                popup_parts = [
                    "<div class='map-popup-container'>",
                    f"<h4>{place_name}</h4>",
                    # Scrollable content area
                    "<div class='popup-content-scrollable'>",
                    f"<b>Category:</b> {html.escape(place_category_enum.value.replace('_', ' ').title())}<br>",
                    f"<b>Status:</b> {html.escape(place_status_enum.value.replace('_', ' ').title())}<br>",
                ]
                if rating:
                    stars_html = "".join(
                        ['<i class="fas fa-star"></i>' for _ in range(rating)]
                    ) + "".join(
                        ['<i class="far fa-star"></i>' for _ in range(5 - rating)]
                    )
                    popup_parts.append(
                        f'<span class="rating-stars-display"><b>Rating:</b> {stars_html}</span><br>'
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

                has_review_content = bool(review_text_raw or review_title_raw or rating)
                has_image = bool(image_url_str and image_url_str.startswith("http"))

                if has_review_content or has_image:
                    if review_title_raw:
                        popup_parts.append(
                            f"<b>Review:</b> {html.escape(review_title_raw)}<br>"
                        )
                    if review_text_raw:
                        popup_parts.append(f"<i>{html.escape(review_text_raw)}</i><br>")
                    if has_image:
                        img_onclick = f"if(window.parent && window.parent.showImageOverlay){{window.parent.showImageOverlay(event)}}else{{console.error('showImageOverlay not found on parent')}}"
                        popup_parts.append(
                            f'<img src="{html.escape(image_url_str)}" alt="{place_name}" onclick="{img_onclick}">'
                        )

                popup_parts.append("</div>")  # End scrollable div

                # Action buttons area
                popup_parts.append("<div class='popup-actions'>")

                # Edit Button
                edit_onclick = f"if(window.parent && window.parent.showEditPlaceForm){{window.parent.showEditPlaceForm('{escaped_js_string_for_html_attr}')}}else{{console.error('showEditPlaceForm not found on parent')}}"
                popup_parts.append(
                    f'<button type="button" class="popup-btn-edit" onclick="{edit_onclick}" title="Edit Place Details">Edit</button>'
                )

                # Add/See Review Button
                if has_review_content or has_image:
                    see_review_onclick = f"if(window.parent && window.parent.showSeeReviewModal){{window.parent.showSeeReviewModal('{escaped_js_string_for_html_attr}')}}else{{console.error('showSeeReviewModal not found on parent')}}"
                    popup_parts.append(
                        f'<button type="button" class="popup-btn-see-review" onclick="{see_review_onclick}" title="See Review / Image">See Review</button>'
                    )
                else:
                    add_review_onclick = f"if(window.parent && window.parent.showReviewForm){{window.parent.showReviewForm('{escaped_js_string_for_html_attr}')}}else{{console.error('showReviewForm not found on parent')}}"
                    popup_parts.append(
                        f'<button type="button" class="popup-btn-add-review" onclick="{add_review_onclick}" title="Add Review / Image">Add Review</button>'
                    )

                # Delete Button (inside a form for POST)
                delete_form_url = request.url_for(
                    "handle_delete_place_form", place_id=place.id
                )
                popup_parts.append(
                    f'<form action="{delete_form_url}" method="post" target="_top" onsubmit="return confirm(\'Are you sure you want to delete this place?\');">'
                    f'<button type="submit" class="popup-btn-delete" title="Delete Place">Delete</button>'
                    f"</form>"
                )

                popup_parts.append("</div>")  # End actions div
                popup_parts.append("</div>")  # End container div
                # --- END: Popup HTML Generation ---

                # Combine style and HTML
                popup_html_content = popup_style + "".join(popup_parts)

                marker_color = status_color_map.get(place_status_enum, default_color)
                marker_icon = category_icons.get(place_category_enum, default_icon)
                folium.Marker(
                    location=[place_lat, place_lon],
                    popup=folium.Popup(
                        popup_html_content, max_width=280
                    ),  # Keep reduced max_width
                    tooltip=f"{place_name} ({html.escape(place_status_enum.value.replace('_', ' ').title())})",
                    icon=folium.Icon(color=marker_color, icon=marker_icon, prefix="fa"),
                ).add_to(m)
                marker_count += 1
            except Exception as marker_error:
                logger.error(
                    f"MAPGEN: Error processing marker for place ID {place.id}: {marker_error}",
                    exc_info=True,
                )
        logger.info(f"MAPGEN: Successfully added {marker_count} markers.")
    else:
        logger.info("MAPGEN: No places found to display on map.")

    # --- Inject Script More Reliably ---
    # 1. Format the JS code with the Python variable first
    formatted_js_code = f"""
        function {map_var_name}_map_click_listener(e) {{
            // Check parent window for pinning state
            if (window.parent && typeof window.parent.isPinningActive === 'function' && window.parent.isPinningActive()) {{
                console.log('IFrame Script (Map Event): Map clicked while parent pinning active. Lat:', e.latlng.lat, 'Lng:', e.latlng.lng);
                // Call function on parent window to handle the click
                if (typeof window.parent.handleMapPinClick === 'function') {{
                    window.parent.handleMapPinClick(e.latlng.lat, e.latlng.lng);
                }} else {{
                    console.error("IFrame Script (Map Event): window.parent.handleMapPinClick is not defined!");
                }}
            }} else {{
                // console.log("IFrame Script (Map Event): Map clicked, but parent not in pinning mode.");
            }}
        }}

        // Add the listener directly to the map instance using its variable name
        // Ensure this runs after the map variable is defined
        try {{
            if (typeof {map_var_name} !== 'undefined') {{
                 console.log("Attaching click listener to {map_var_name}");
                {map_var_name}.on('click', {map_var_name}_map_click_listener);
            }} else {{
                 console.error("Could not attach click listener: map variable {map_var_name} not found immediately.");
                 // Fallback: try again after a short delay - less ideal
                 setTimeout(function() {{
                     if (typeof {map_var_name} !== 'undefined') {{
                         console.log("Attaching click listener to {map_var_name} after delay.");
                         {map_var_name}.on('click', {map_var_name}_map_click_listener);
                     }} else {{
                          console.error("Could not attach click listener even after delay: map variable {map_var_name} not found.");
                     }}
                 }}, 500);
            }}
        }} catch (err) {{
             console.error("Error attaching map click listener:", err);
        }}
    """

    # 2. Wrap the formatted JS code in Jinja2 raw tags to prevent backend interpretation
    # Note: We add the <script> tags *outside* the raw block.
    raw_js_injection = f"<script>{{% raw %}}{formatted_js_code}{{% endraw %}}</script>"

    # 3. Add the raw block wrapped in <script> tags to the map element
    m.get_root().html.add_child(Element(raw_js_injection))

    # Render the map to HTML
    map_html_content = m._repr_html_()

    return map_html_content
