from pydantic import BaseModel
from typing import Optional


# --- Geocoding Response Model ---
class GeocodeResult(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    display_name: str


class Msg(BaseModel):
    """Simple message response model."""

    message: str
