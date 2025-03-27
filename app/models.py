"""Pydantic models for API data validation and serialization."""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


# --- Enums ---
class PlaceCategory(str, Enum):
    RESTAURANT = "restaurant"
    ENTERTAINMENT = "entertainment"
    PARK = "park"
    SHOPPING = "shopping"
    OTHER = "other"


class PlaceStatus(str, Enum):
    PENDING = "pending"
    PENDING_PRIORITIZED = "pending_prioritized"
    VISITED = "visited"


# --- Base Model ---
class PlaceBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the place"
    )
    category: PlaceCategory = Field(
        default=PlaceCategory.OTHER, description="Category of the place"
    )
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: Optional[str] = Field(None, max_length=255, description="Street address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    country: Optional[str] = Field(None, max_length=100, description="Country")


# --- Create Model (Input for POST /places/) ---
class PlaceCreate(PlaceBase):
    status: PlaceStatus = Field(
        default=PlaceStatus.PENDING, description="Initial status of the place"
    )

    # Ensure lat/lon are provided explicitly during creation via API
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# --- Update Model (Input for PUT /places/{id}) ---
class PlaceUpdate(BaseModel):
    # All fields are optional for updates
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[PlaceCategory] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[PlaceStatus] = None
    review: Optional[str] = Field(
        None, max_length=1000, description="User review (longer length allowed)"
    )  # Increased length
    # image_url is typically updated internally via upload endpoint

    @field_validator("review")
    @classmethod
    def strip_review(cls, v: Optional[str]) -> Optional[str]:
        """Remove leading/trailing whitespace from review."""
        if v is not None:
            return v.strip()
        return v


# --- Database Model (Representation matching DB schema) ---
class PlaceInDB(PlaceBase):
    id: int
    status: PlaceStatus
    review: Optional[str] = None
    image_url: Optional[HttpUrl | str] = (
        None  # Allow string for flexibility, convert on output if needed
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 replaces orm_mode


# --- API Response Model (Data sent back to clients) ---
class Place(PlaceInDB):
    # Inherits all fields from PlaceInDB
    # Add any transformations needed for API output here if necessary
    pass


# --- List Response Model ---
class PlaceList(BaseModel):
    places: List[Place]


# --- Geocoding Response Model ---
class GeocodeResult(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None  # Specific street address part
    city: Optional[str] = None
    country: Optional[str] = None
    display_name: str  # Full address string from geocoder
