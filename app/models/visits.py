import uuid
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class VisitBase(BaseModel):
    visit_datetime: datetime
    review_title: Optional[str] = Field(None, max_length=150)
    review_text: Optional[str] = Field(None, max_length=1000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    image_url: Optional[HttpUrl | str] = (
        None  # Allow HttpUrl for validation, str for flexibility
    )
    reminder_enabled: bool = False
    reminder_offsets_hours: Optional[List[int]] = Field(
        None, description="e.g., [12, 24, 48]"
    )


class VisitCreate(VisitBase):
    place_id: int  # Required when creating a visit through place endpoint


class VisitUpdate(BaseModel):
    visit_datetime: Optional[datetime] = None
    review_title: Optional[str] = Field(None, max_length=150)
    review_text: Optional[str] = Field(None, max_length=1000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    image_url: Optional[HttpUrl | str | None] = Field(
        None, description="URL of image or None to remove"
    )
    reminder_enabled: Optional[bool] = None
    reminder_offsets_hours: Optional[List[int] | None] = Field(
        None, description="List of hours or None to clear"
    )
    updated_at: Optional[datetime] = None  # Will be set by CRUD


class VisitInDB(VisitBase):
    id: int
    place_id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Visit(VisitInDB):
    """API Response model for a Visit."""

    pass
