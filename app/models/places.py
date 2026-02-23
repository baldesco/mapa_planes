import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from .tags import Tag

if TYPE_CHECKING:
    from .visits import Visit  # For type hinting the list of visits


# --- Enums ---
class PlaceCategory(str, Enum):
    RESTAURANT = "restaurant"
    ENTERTAINMENT = "entertainment"
    PARK = "park"
    SHOPPING = "shopping"
    TRIP = "trip"
    OTHER = "other"


class PlaceStatus(str, Enum):
    PENDING = "pending"
    PENDING_PRIORITIZED = "pending_prioritized"
    PENDING_SCHEDULED = "pending_scheduled"
    VISITED = "visited"


# --- Base Model ---
class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: PlaceCategory = Field(default=PlaceCategory.OTHER)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    timezone_iana: str | None = Field(None, description="e.g., America/Bogota")
    description: str | None = Field(None, max_length=1000)
    # image_url removed from PlaceBase


# --- Create Model (Input for POST /places/) ---
class PlaceCreate(PlaceBase):
    status: PlaceStatus = Field(default=PlaceStatus.PENDING)
    # Tags are not added during initial creation via this model


# --- Update Model (Input for PUT /places/{id}) ---
class PlaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    category: PlaceCategory | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    address: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    timezone_iana: str | None = None
    status: PlaceStatus | None = None
    # image_url removed from PlaceUpdate
    deleted_at: datetime | None = None
    updated_at: datetime | None = None
    description: str | None = Field(None, max_length=1000)
    tags: list[str] | None = Field(
        None, description="List of tag names to associate with the place."
    )

    @field_validator(
        "name", "address", "city", "country", "timezone_iana", "description"
    )
    @classmethod
    def strip_text_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("Tags must be provided as a list of strings.")
        cleaned_tags = [
            tag.strip().lower() for tag in v if isinstance(tag, str) and tag.strip()
        ]
        seen = set()
        unique_tags = [x for x in cleaned_tags if not (x in seen or seen.add(x))]
        return unique_tags if unique_tags else None


# --- Database Model (Representation matching DB schema) ---
class PlaceInDB(PlaceBase):
    id: int
    user_id: uuid.UUID
    status: PlaceStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    tags: list[Tag] = []
    visits: list["Visit"] = []  # Will be populated by CRUD

    class Config:
        from_attributes = True


# --- API Response Model ---
class Place(PlaceInDB):
    # Inherits tags and visits from PlaceInDB
    pass


# --- List Response Model ---
class PlaceList(BaseModel):
    places: list[Place]
