import folium
import html
import json
import uuid
from typing import List, Optional, Tuple
from fastapi import Request

from app.models.places import PlaceInDB, PlaceCategory, PlaceStatus
from app.core.config import logger


def generate_map_html(
    places: List[PlaceInDB],
    request: Request,
    category_filter: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
) -> str:
    """Generates the HTML representation of the Folium map with place markers,
    injecting a click listener for pinning mode."""
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
                # ... (Marker and Popup Generation Logic - ASSUMED CORRECT FROM PREVIOUS) ...
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

                popup_parts = [
                    f"<h4 style='margin-bottom: 8px;'>{place_name}</h4>",
                    "<div style='font-size: 0.9em; max-height: 250px; overflow-y: auto;'>",
                    f"<b>Category:</b> {html.escape(place_category_enum.value.replace('_', ' ').title())}<br>",
                    f"<b>Status:</b> {html.escape(place_status_enum.value.replace('_', ' ').title())}<br>",
                ]
                if rating:
                    stars_html = "".join(
                        [
                            '<i class="fas fa-star" style="color: #FFD700;"></i>'
                            for _ in range(rating)
                        ]
                    ) + "".join(
                        [
                            '<i class="far fa-star" style="color: #ccc;"></i>'
                            for _ in range(5 - rating)
                        ]
                    )
                    popup_parts.append(f"<b>Rating:</b> {stars_html}<br>")
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
                    popup_parts.append(
                        "<hr style='margin: 5px 0; border-top-color: #eee;'>"
                    )
                    if review_title_raw:
                        popup_parts.append(
                            f"<b>Review:</b> {html.escape(review_title_raw)}<br>"
                        )
                    if review_text_raw:
                        snippet = html.escape(review_text_raw[:100]) + (
                            "..." if len(review_text_raw) > 100 else ""
                        )
                        popup_parts.append(f"<i>{snippet}</i><br>")
                    if has_image:
                        img_onclick = f"if(window.parent && window.parent.showImageOverlay){{window.parent.showImageOverlay(event)}}else{{console.error('showImageOverlay not found on parent')}}"
                        popup_parts.append(
                            f'<img src="{html.escape(image_url_str)}" alt="{place_name}" style="max-width: 100px; max-height: 75px; margin-top: 5px; display: block; border-radius: 4px; cursor: pointer;" onclick="{img_onclick}">'
                        )
                popup_parts.append("</div>")
                popup_parts.append(
                    "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px; display: flex; flex-wrap: wrap; gap: 5px;'>"
                )
                status_form_url = request.url_for(
                    "handle_update_place_status_form", place_id=place.id
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
                edit_onclick = f"if(window.parent && window.parent.showEditPlaceForm){{window.parent.showEditPlaceForm('{escaped_js_string_for_html_attr}')}}else{{console.error('showEditPlaceForm not found on parent')}}"
                popup_parts.append(
                    f'<button type="button" onclick="{edit_onclick}" title="Edit Place Details">Edit</button>'
                )
                if has_review_content or has_image:
                    see_review_onclick = f"if(window.parent && window.parent.showSeeReviewModal){{window.parent.showSeeReviewModal('{escaped_js_string_for_html_attr}')}}else{{console.error('showSeeReviewModal not found on parent')}}"
                    popup_parts.append(
                        f'<button type="button" onclick="{see_review_onclick}" title="See Review / Image">See Review</button>'
                    )
                else:
                    add_review_onclick = f"if(window.parent && window.parent.showReviewForm){{window.parent.showReviewForm('{escaped_js_string_for_html_attr}')}}else{{console.error('showReviewForm not found on parent')}}"
                    popup_parts.append(
                        f'<button type="button" onclick="{add_review_onclick}" title="Add Review / Image">Add Review</button>'
                    )
                delete_form_url = request.url_for(
                    "handle_delete_place_form", place_id=place.id
                )
                popup_parts.append(
                    f'<form action="{delete_form_url}" method="post" target="_top" style="display: inline-block;" onsubmit="return confirm(\'Are you sure you want to delete this place?\');"><button type="submit" title="Delete Place">Delete</button></form>'
                )
                popup_parts.append("</div>")
                popup_html = "".join(popup_parts)

                marker_color = status_color_map.get(place_status_enum, default_color)
                marker_icon = category_icons.get(place_category_enum, default_icon)
                folium.Marker(
                    location=[place_lat, place_lon],
                    popup=folium.Popup(popup_html, max_width=350),
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
    # Use Folium's capability to add JS directly to the map object context
    # This should execute after the map instance (map_var_name) is defined
    js_listener_code = f"""
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
    # Add the script to the map's header/script section using branca Element
    from branca.element import Element

    m.get_root().html.add_child(Element(f"<script>{js_listener_code}</script>"))

    # Render the map to HTML
    map_html_content = m._repr_html_()

    return map_html_content
