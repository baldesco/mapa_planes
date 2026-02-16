from pydantic import BaseModel


# --- Geocoding Response Model ---
class GeocodeResult(BaseModel):
    latitude: float
    longitude: float
    address: str | None = None
    city: str | None = None
    country: str | None = None
    display_name: str


class Msg(BaseModel):
    """Simple message response model."""

    message: str
