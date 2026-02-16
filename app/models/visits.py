import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class VisitBase(BaseModel):
    visit_datetime: datetime
    review_title: str | None = Field(None, max_length=150)
    review_text: str | None = Field(None, max_length=1000)
    rating: int | None = Field(None, ge=1, le=5)
    image_url: HttpUrl | str | None = None
    reminder_enabled: bool = False  # This might become deprecated if only using .ics
    reminder_offsets_hours: list[int] | None = Field(
        None, description="e.g., [12, 24, 48]"
    )


class VisitCreate(VisitBase):
    place_id: int


class VisitUpdate(BaseModel):
    visit_datetime: datetime | None = None
    review_title: str | None = Field(None, max_length=150)
    review_text: str | None = Field(None, max_length=1000)
    rating: int | None = Field(None, ge=1, le=5)
    image_url: HttpUrl | str | None | None = Field(
        None, description="URL of image or None to remove"
    )
    reminder_enabled: bool | None = None  # Might be deprecated
    reminder_offsets_hours: list[int] | None | None = Field(
        None, description="List of hours or None to clear"
    )
    updated_at: datetime | None = None


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
