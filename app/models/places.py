import uuid
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

    class Config:
        from_attributes = True


# --- API Response Model ---
class Place(PlaceInDB):
    pass


# --- List Response Model ---
class PlaceList(BaseModel):
    places: List[Place]
