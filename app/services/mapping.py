from typing import List, Dict, Any
from app.models.places import Place
from app.core.config import logger

def prepare_map_data(places: List[Place]) -> Dict[str, Any]:
    """
    Serializes place data and calculates the optimal initial map viewport.
    
    Args:
        places: A list of Place objects with nested tags and visits.
        
    Returns:
        A dictionary containing the serialized places list and 
        map configuration (center and zoom).
    """
    logger.info(f"Mapping Service: Preparing initial state for {len(places)} places.")

    # Pydantic V2 model_dump(mode='json') is highly efficient for serializing 
    # UUIDs, Datetimes, and Enums into frontend-ready formats.
    serialized_places = [place.model_dump(mode="json") for place in places]

    # Default center (Bogotá) if no places exist
    map_center = [4.7110, -74.0721]
    zoom_start = 12

    if places:
        valid_coords = [
            (p.latitude, p.longitude)
            for p in places
            if p.latitude is not None and p.longitude is not None
        ]
        
        if valid_coords:
            # Calculate the geometric center of all markers
            avg_lat = sum(lat for lat, lon in valid_coords) / len(valid_coords)
            avg_lon = sum(lon for lat, lon in valid_coords) / len(valid_coords)
            map_center = [avg_lat, avg_lon]
            
            # Adjust initial zoom based on marker count for a better first impression
            if len(valid_coords) > 50:
                zoom_start = 11
            elif len(valid_coords) > 10:
                zoom_start = 12
            else:
                zoom_start = 14

    return {
        "places": serialized_places,
        "config": {
            "center": map_center,
            "zoom": zoom_start
        }
    }