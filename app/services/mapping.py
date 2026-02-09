from typing import List, Dict, Any
from app.models.places import Place
from app.core.config import logger

def prepare_map_data(places: List[Place]) -> Dict[str, Any]:
    """
    Serializes place data and calculates initial map configuration for native Leaflet.
    
    Args:
        places: A list of Place objects retrieved from the database.
        
    Returns:
        A dictionary containing the serialized places and the map configuration (center, zoom).
    """
    logger.info(f"Preparing map data for {len(places)} places.")

    # Serialize Pydantic models to JSON-compatible dictionaries
    # Pydantic V2 mode='json' automatically handles UUID, Datetime, and Enum serialization
    serialized_places = [place.model_dump(mode="json") for place in places]

    # Default center (Bogotá) and zoom
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
            
            # Adjust zoom based on density
            if len(valid_coords) > 50:
                zoom_start = 10
            elif len(valid_coords) > 10:
                zoom_start = 11
            else:
                zoom_start = 13

    return {
        "places": serialized_places,
        "config": {
            "center": map_center,
            "zoom": zoom_start
        }
    }