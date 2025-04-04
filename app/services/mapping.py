import folium
import html
import json
import uuid
from typing import List, Optional
from fastapi import Request

from app.models.places import PlaceInDB, PlaceCategory, PlaceStatus
from app.core.config import logger


def generate_map_html(
    places: List[PlaceInDB],
    request: Request,  # Needed for generating form action URLs
    category_filter: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
) -> str:
    """Generates the HTML representation of the Folium map with place markers."""
    logger.info(
        f"Generating map HTML for {len(places)} places. Filters: cat={category_filter}, status={status_filter}"
    )

    map_center = [4.7110, -74.0721]  # Default center (Bogotá)
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
            # Adjust zoom based on number of points
            if len(valid_coords) > 50:
                zoom_start = 10
            elif len(valid_coords) > 10:
                zoom_start = 11

    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
    map_var_name = m.get_name()  # Get the JS variable name Folium uses

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
                place_lat, place_lon = place.latitude, place.longitude
                place_name = html.escape(place.name or "Unnamed Place")
                place_category_enum = place.category
                place_status_enum = place.status
                review_title_raw = place.review_title
                review_text_raw = place.review
                image_url_str = str(place.image_url or "")
                rating = place.rating

                # Prepare data for JS functions called from popup buttons
                place_data_for_js = {
                    "id": place.id,
                    "name": place.name,
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
                # Escape the JSON string for safe embedding in HTML attribute
                js_object_string = json.dumps(place_data_for_js)
                escaped_js_string_for_html_attr = html.escape(
                    js_object_string, quote=True
                )

                # Build Popup HTML
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
                    )
                    stars_html += "".join(
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
                        # Use window.parent to call function in the main page context from the iframe
                        popup_parts.append(
                            f'<img src="{html.escape(image_url_str)}" alt="{place_name}" style="max-width: 100px; max-height: 75px; margin-top: 5px; display: block; border-radius: 4px; cursor: pointer;" onclick="window.parent.showImageOverlay(event)">'
                        )

                popup_parts.append("</div>")  # End of scrollable content div
                popup_parts.append(
                    "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px; display: flex; flex-wrap: wrap; gap: 5px;'>"
                )  # Action buttons div

                # Status Update Form
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

                # Edit Button (calls JS function)
                popup_parts.append(
                    f'<button type="button" onclick="window.parent.showEditPlaceForm(\'{escaped_js_string_for_html_attr}\')" title="Edit Place Details">Edit</button>'
                )

                # Review/Image Button (calls JS function)
                if has_review_content or has_image:
                    popup_parts.append(
                        f'<button type="button" onclick="window.parent.showSeeReviewModal(\'{escaped_js_string_for_html_attr}\')" title="See Review / Image">See Review</button>'
                    )
                else:
                    popup_parts.append(
                        f'<button type="button" onclick="window.parent.showReviewForm(\'{escaped_js_string_for_html_attr}\')" title="Add Review / Image">Add Review</button>'
                    )

                # Delete Form
                delete_form_url = request.url_for(
                    "handle_delete_place_form", place_id=place.id
                )
                popup_parts.append(
                    f'<form action="{delete_form_url}" method="post" target="_top" style="display: inline-block;" onsubmit="return confirm(\'Are you sure you want to delete this place?\');"><button type="submit" title="Delete Place">Delete</button></form>'
                )

                popup_parts.append("</div>")  # End of action buttons div
                popup_html = "".join(popup_parts)

                # Create Marker
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

    # Inject script to expose map instance globally for JS interaction
    map_html_content = m._repr_html_()
    injection_script = f"""
    <script>
        (function() {{
            function checkMapVar() {{
                if (typeof {map_var_name} !== 'undefined' && {map_var_name} !== null) {{
                    console.log('Folium map instance ({map_var_name}) found, assigning to window.leafletMapInstance.');
                    window.leafletMapInstance = {map_var_name};
                }} else {{
                    setTimeout(checkMapVar, 100); // Check again shortly
                }}
            }}
            checkMapVar();
        }})();
    </script>
    """
    map_html_content += injection_script

    return map_html_content
