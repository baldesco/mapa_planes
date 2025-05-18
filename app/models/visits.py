import uuid
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime


class VisitBase(BaseModel):
    visit_datetime: datetime
    review_title: Optional[str] = Field(None, max_length=150)
    review_text: Optional[str] = Field(None, max_length=1000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    image_url: Optional[HttpUrl | str] = None
    reminder_enabled: bool = False  # This might become deprecated if only using .ics
    reminder_offsets_hours: Optional[List[int]] = Field(
        None, description="e.g., [12, 24, 48]"
    )


class VisitCreate(VisitBase):
    place_id: int


class VisitUpdate(BaseModel):
    visit_datetime: Optional[datetime] = None
    review_title: Optional[str] = Field(None, max_length=150)
    review_text: Optional[str] = Field(None, max_length=1000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    image_url: Optional[HttpUrl | str | None] = Field(
        None, description="URL of image or None to remove"
    )
    reminder_enabled: Optional[bool] = None  # Might be deprecated
    reminder_offsets_hours: Optional[List[int] | None] = Field(
        None, description="List of hours or None to clear"
    )
    updated_at: Optional[datetime] = None


class VisitInDB(VisitBase):
    id: int
    place_id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Visit(VisitInDB):
    pass


class CalendarEventCustomization(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=200)
    duration_value: int = Field(..., gt=0, le=999)  # Example limits
    duration_unit: Literal["minutes", "hours", "days"]
    # Boolean flags for predefined alarms in the ICS file
    remind_1_day_before: bool = False
    remind_2_hours_before: bool = False
    remind_15_mins_before: bool = False
