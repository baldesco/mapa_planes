"""SQLAlchemy models for the local SQLite database structure."""

import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum as SQLAlchemyEnum,
    Text,
    ForeignKey,
    Boolean,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import (
    UUID,
)  # Use UUID for Postgres compatibility if needed
from sqlalchemy.sql import func
from .database import Base  # Import Base from database.py
from .models import PlaceCategory, PlaceStatus  # Reuse Pydantic enums for consistency


# Although Supabase handles the auth.users table, if you ever wanted
# to mirror user info locally (e.g., for complex joins not feasible with Supabase API),
# you might define a local User model. For now, we only link via user_id.
# class UserDB(Base):
#     __tablename__ = "users" # Example, not strictly needed now
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email = Column(String, unique=True, index=True, nullable=False)
#     # hashed_password = Column(String, nullable=False) # Don't store locally if using Supabase Auth
#     is_active = Column(Boolean, default=True)


class PlaceDB(Base):
    """SQLAlchemy model for the 'places' table in the local SQLite database."""

    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)  # Standard SQLite PK
    # Link to user - for local SQLite, UUID might be stored as string or bytes
    # Using String for simplicity here if not using Postgres locally.
    # If using Postgres locally, use UUID(as_uuid=True).
    user_id = Column(
        String, index=True, nullable=False
    )  # Changed type for local SQLite, ensure it's NOT NULL
    # If using local UserDB table:
    # user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=False, index=True)
    category = Column(
        SQLAlchemyEnum(
            PlaceCategory, name="placecategory"
        ),  # Added name for potential compatibility
        default=PlaceCategory.OTHER,
        nullable=False,
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(
        SQLAlchemyEnum(PlaceStatus, name="placestatus"),  # Added name
        default=PlaceStatus.PENDING,
        nullable=False,
        index=True,
    )
    rating = Column(Integer, nullable=True)  # Added rating field
    review_title = Column(String(150), nullable=True)
    review = Column(Text, nullable=True)
    image_url = Column(String(1024), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # Use server_default for created_at
    )
    # Soft Delete column
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Add check constraint for rating if database supports it (SQLite does)
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_check"),
        # Add other constraints or indexes here if needed
    )

    def __repr__(self):
        deleted_marker = "[DELETED] " if self.deleted_at else ""
        return f"<PlaceDB(id={self.id}, user='{self.user_id}', name='{self.name}', status='{self.status.value}') {deleted_marker}>"


# Define other tables here if your schema grows
