"""Pydantic models for API data validation and serialization."""

import uuid
from pydantic import BaseModel, Field, HttpUrl, field_validator, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime


# --- Enums ---
class PlaceCategory(str, Enum):
    RESTAURANT = "restaurant"
    ENTERTAINMENT = "entertainment"
    PARK = "park"
    SHOPPING = "shopping"
    TRIP = "trip"  # Added category
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
    # Rating and review title are optional on creation, more likely added later
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    review_title: Optional[str] = Field(
        None, max_length=150, description="Title for the review"
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
    rating: Optional[int] = Field(
        None, ge=1, le=5, description="Rating from 1 to 5"
    )  # Added rating
    review_title: Optional[str] = Field(None, max_length=150)
    review: Optional[str] = Field(None, max_length=1000)
    # Allow setting image_url explicitly to None to remove it
    image_url: Optional[HttpUrl | str | None] = Field(
        None, description="URL of the image or None to remove"
    )
    deleted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None  # Keep track of updates internally

    @field_validator("review", "review_title", "name", "address", "city", "country")
    @classmethod
    def strip_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    # Ensure rating is valid if provided
    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


# --- Database Model (Representation matching DB schema) ---
class PlaceInDB(PlaceBase):
    id: int
    user_id: uuid.UUID  # Link to the user who owns this place
    status: PlaceStatus
    rating: Optional[int] = Field(None, ge=1, le=5)  # Added rating, allowing null
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


# --- Authentication Models ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: uuid.UUID
    is_active: bool = True  # Assuming Supabase users are active by default

    class Config:
        from_attributes = True  # For mapping from DB objects potentially


# Minimal representation of the user stored in the token
class UserInToken(BaseModel):
    id: uuid.UUID
    email: EmailStr


# Supabase returns more info, but this is essential for our JWT
class SupabaseUser(BaseModel):
    id: uuid.UUID
    aud: str
    role: str
    email: EmailStr
    # Supabase includes many other fields like confirmed_at, created_at etc.
    # We only map what we strictly need for our app's logic post-login.


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    # This will hold the payload decoded from our JWT
    # Using 'sub' (subject) standard claim for user identifier (email or id)
    sub: str | None = None  # Could be email or UUID string
    id: uuid.UUID | None = None  # Extracted user ID
    email: EmailStr | None = None  # Extracted user email


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str  # The token received via email (or temp password, depending on flow)
    new_password: str = Field(..., min_length=8)


class Msg(BaseModel):
    """Simple message response model."""

    message: str
