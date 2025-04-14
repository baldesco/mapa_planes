import uuid
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

# Import the new Tag model
from .tags import Tag


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
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    review_title: Optional[str] = Field(
        None, max_length=150, description="Title for the review"
    )
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    # Tags are not added during initial creation via this model


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
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    review_title: Optional[str] = Field(None, max_length=150)
    review: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[HttpUrl | str | None] = Field(
        None, description="URL of the image or None to remove"
    )
    deleted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Add tags field: Expects a list of tag names from the frontend
    tags: Optional[List[str]] = Field(
        None, description="List of tag names to associate with the place."
    )

    @field_validator("review", "review_title", "name", "address", "city", "country")
    @classmethod
    def strip_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v

    # Optional: Add validator for tags to ensure they are clean strings
    @field_validator(
        "tags", mode="before"
    )  # Use mode='before' if input might not be list
    @classmethod
    def clean_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if not isinstance(v, list):
            # Could add handling for comma-separated string if needed, but list is preferred
            raise ValueError("Tags must be provided as a list of strings.")
        cleaned_tags = [
            tag.strip().lower() for tag in v if isinstance(tag, str) and tag.strip()
        ]
        # Remove duplicates while preserving order (if needed, though set is easier)
        seen = set()
        unique_tags = [x for x in cleaned_tags if not (x in seen or seen.add(x))]
        return unique_tags if unique_tags else None  # Return None if list becomes empty


# --- Database Model (Representation matching DB schema) ---
class PlaceInDB(PlaceBase):
    id: int
    user_id: uuid.UUID
    status: PlaceStatus
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_title: Optional[str] = None
    review: Optional[str] = None
    image_url: Optional[HttpUrl | str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # Add tags list, populated after fetching place
    tags: List[Tag] = []

    class Config:
        from_attributes = True


# --- API Response Model ---
class Place(PlaceInDB):
    pass  # Inherits tags from PlaceInDB


# --- List Response Model ---
class PlaceList(BaseModel):
    places: List[Place]
