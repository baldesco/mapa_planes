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
    name: str = Field(..., min_length=1, max_length=100)
    category: PlaceCategory = Field(default=PlaceCategory.OTHER)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)


# --- Create Model (Input for POST /places/) ---
class PlaceCreate(PlaceBase):
    status: PlaceStatus = Field(default=PlaceStatus.PENDING)
    review_title: Optional[str] = Field(
        None, max_length=150, description="Title for the review (optional on creation)"
    )

    # Ensure lat/lon are required explicitly
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# --- Update Model (Input for PUT /places/{id}) ---
class PlaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[PlaceCategory] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[PlaceStatus] = None
    review_title: Optional[str] = Field(None, max_length=150)
    review: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[HttpUrl | str | None] = None
    deleted_at: Optional[datetime] = None

    @field_validator("review", "review_title", "name", "address", "city", "country")
    @classmethod
    def strip_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v


# --- Database Model (Representation matching DB schema) ---
class PlaceInDB(PlaceBase):
    id: int
    status: PlaceStatus
    review_title: Optional[str] = None
    review: Optional[str] = None
    image_url: Optional[HttpUrl | str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- API Response Model ---
class Place(PlaceInDB):
    pass


# --- List Response Model ---
class PlaceList(BaseModel):
    places: List[Place]


# --- Geocoding Response Model ---
class GeocodeResult(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    display_name: str
