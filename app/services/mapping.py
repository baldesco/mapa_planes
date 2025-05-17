import folium
import html
import json
from typing import List, Optional
from fastapi import Request
from branca.element import Element
from datetime import datetime, timezone

from app.models.places import Place, PlaceCategory, PlaceStatus
from app.core.config import logger


def generate_map_html(
    places: List[Place],
    request: Request,
    category_filter: Optional[PlaceCategory] = None,
    status_filter: Optional[PlaceStatus] = None,
) -> str:
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
        PlaceStatus.PENDING_SCHEDULED: "purple",
    }
    default_color = "gray"

    popup_style = """
<style>
    .map-popup-container { font-family: 'Poppins', sans-serif; font-size: 13px; line-height: 1.5; color: #212529; max-width: 280px; }
    .map-popup-container h4 { margin: 0 0 7px 0; padding-bottom: 5px; font-size: 1.15em; font-weight: 600; color: #1B5E20; border-bottom: 1px solid #eee; }
    .popup-content-scrollable { max-height: 150px; overflow-y: auto; margin-bottom: 10px; padding-right: 5px; word-wrap: break-word; }
    .popup-content-scrollable p, .popup-content-scrollable b, .popup-content-scrollable i, .popup-content-scrollable span { font-size: 0.9em; margin-bottom: 3px; }
    .popup-content-scrollable b { font-weight: 500; color: #333; }
    .popup-tags-container { margin-top: 6px; margin-bottom: 4px; }
    .popup-tag { display: inline-block; background-color: #f0f0f0; color: #555; padding: 2px 7px; border-radius: 10px; font-size: 0.75em; margin-right: 3px; margin-bottom: 3px; white-space: nowrap; }
    .popup-visits-info { font-style: italic; color: #555; font-size: 0.85em; margin-top:8px; padding-top: 5px; border-top: 1px dashed #eee; }
    .popup-actions { margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; display: flex; flex-wrap: wrap; gap: 5px; justify-content: flex-start; }
    .popup-actions button, .popup-actions form button {
        padding: 4px 8px; font-size: 0.8em; font-weight: 500; border-radius: 4px; cursor: pointer; border: none;
        color: white; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: background-color 0.2s, transform 0.1s; margin: 0;
    }
    .popup-actions button:hover, .popup-actions form button:hover { transform: translateY(-1px); box-shadow: 0 1px 3px rgba(0,0,0,0.15); }
    .popup-actions button:active, .popup-actions form button:active { transform: translateY(0); box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
    .popup-btn-edit-place { background-color: #ff9800; } .popup-btn-edit-place:hover { background-color: #f57c00; }
    .popup-btn-plan-visit { background-color: #0288d1; } .popup-btn-plan-visit:hover { background-color: #0277bd; }
    .popup-btn-view-visits { background-color: #546e7a; } .popup-btn-view-visits:hover { background-color: #455a64; }
    .popup-btn-delete-place { background-color: #d32f2f; } .popup-btn-delete-place:hover { background-color: #c62828; }
    .popup-actions form { margin: 0; padding: 0; display: inline-flex; }
</style>
"""
    marker_count = 0
    if places:
        for place in places:
            if (
                place.latitude is None
                or place.longitude is None
                or place.status is None
                or place.category is None
            ):
                continue
            try:
                place_name = html.escape(place.name or "Unnamed Place")

                place_data_for_js_actions = {
                    "id": place.id,
                    "name": place.name or "",
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "category": place.category.value,
                    "status": place.status.value,
                    "address": place.address or "",
                    "city": place.city or "",
                    "country": place.country or "",
                    "timezone_iana": place.timezone_iana or "",
                    "tags": [tag.name for tag in place.tags] if place.tags else [],
                }
                js_object_string_for_html_attr = html.escape(
                    json.dumps(place_data_for_js_actions), quote=True
                )

                popup_parts = [
                    "<div class='map-popup-container'>",
                    f"<h4>{place_name}</h4>",
                    "<div class='popup-content-scrollable'>",
                    f"<b>Category:</b> {html.escape(place.category.value.replace('_', ' ').title())}<br>",
                    f"<b>Status:</b> {html.escape(place.status.value.replace('_', ' ').title())}<br>",
                ]
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

                if place.tags:
                    tags_html = "".join(
                        [
                            f'<span class="popup-tag">{html.escape(tag.name)}</span>'
                            for tag in place.tags
                        ]
                    )
                    popup_parts.append(
                        f'<div class="popup-tags-container"><b>Tags:</b> {tags_html}</div>'
                    )

                popup_parts.append("</div>")

                popup_parts.append("<div class='popup-visits-info'>")
                num_future_visits = sum(
                    1
                    for v in place.visits
                    if v.visit_datetime >= datetime.now(timezone.utc)
                )
                if num_future_visits > 0:
                    popup_parts.append(
                        f"{num_future_visits} upcoming visit(s) scheduled."
                    )
                elif place.visits:
                    popup_parts.append(f"{len(place.visits)} past visit(s) recorded.")
                else:
                    popup_parts.append("No visits recorded yet.")
                popup_parts.append("</div>")

                popup_parts.append("<div class='popup-actions'>")
                edit_place_onclick = f"window.parent.showEditPlaceForm('{js_object_string_for_html_attr}');"  # Corrected variable name
                popup_parts.append(
                    f'<button type="button" class="popup-btn-edit-place" onclick="{edit_place_onclick}" title="Edit Place Details">Edit Place</button>'
                )
                plan_visit_onclick = f"window.parent.showPlanVisitForm('{js_object_string_for_html_attr}');"  # Corrected variable name
                popup_parts.append(
                    f'<button type="button" class="popup-btn-plan-visit" onclick="{plan_visit_onclick}" title="Plan a New Visit">Plan Visit</button>'
                )
                view_visits_onclick = f"window.parent.showVisitsListModal('{js_object_string_for_html_attr}');"  # Corrected variable name
                popup_parts.append(
                    f'<button type="button" class="popup-btn-view-visits" onclick="{view_visits_onclick}" title="View All Visits">View Visits</button>'
                )
                delete_form_url = request.url_for(
                    "handle_delete_place_form", place_id=place.id
                )
                popup_parts.append(
                    f'<form action="{delete_form_url}" method="post" target="_top" onsubmit="return confirm(\'Are you sure you want to delete this place and all its visits?\');"><button type="submit" class="popup-btn-delete-place" title="Delete Place">Delete</button></form>'
                )
                popup_parts.append("</div>")
                popup_parts.append("</div>")

                popup_html_content = popup_style + "".join(popup_parts)
                marker_color = status_color_map.get(place.status, default_color)
                marker_icon_name = category_icons.get(place.category, default_icon)

                folium.Marker(
                    location=[place.latitude, place.longitude],
                    popup=folium.Popup(popup_html_content, max_width=300),
                    tooltip=f"{place_name} ({html.escape(place.status.value.replace('_', ' ').title())})",
                    icon=folium.Icon(
                        color=marker_color, icon=marker_icon_name, prefix="fa"
                    ),
                ).add_to(m)
                marker_count += 1
            except Exception as marker_error:
                logger.error(
                    f"MAPGEN: Error processing marker for place ID {getattr(place, 'id', 'Unknown')}: {marker_error}",
                    exc_info=True,
                )
        logger.info(f"MAPGEN: Successfully added {marker_count} markers.")
    else:
        logger.info("MAPGEN: No places found to display on map.")

    map_var_name_js = json.dumps(map_var_name)
    script_content = f"""
        setTimeout(function() {{
            try {{
                if (window.parent && typeof window.parent.attachMapClickListener === 'function') {{
                    window.parent.attachMapClickListener({map_var_name_js});
                }} else {{ console.error('Iframe: Cannot attach map listener: Parent window function not found.'); }}
            }} catch (e) {{ console.error('Iframe: Error calling parent window function for map listener:', e); }}
        }}, 500);
    """
    script_element = Element(f"<script>{script_content}</script>")
    m.get_root().html.add_child(script_element)
    return m._repr_html_()
