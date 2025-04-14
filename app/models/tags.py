import uuid

# Import field_validator from pydantic
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


# --- Base Model ---
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def lowercase_and_strip_name(cls, v: str) -> str:
        # Ensure the input is a string before processing
        if not isinstance(v, str):
            raise ValueError("Tag name must be a string")
        return v.strip().lower()


# --- Create Model (Input for creating a tag - usually just name) ---
class TagCreate(TagBase):
    pass


# --- Database Model (Representation matching DB schema) ---
class TagInDB(TagBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2 alias for orm_mode


# --- API Response Model ---
class Tag(TagInDB):
    pass
