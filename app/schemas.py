"""SQLAlchemy models for the local SQLite database structure."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum as SQLAlchemyEnum,
    Text,
)
from sqlalchemy.sql import func
from .database import Base  # Import Base from database.py
from .models import PlaceCategory, PlaceStatus  # Reuse Pydantic enums for consistency


class PlaceDB(Base):
    """SQLAlchemy model for the 'places' table in the local SQLite database."""

    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)  # Standard SQLite PK
    name = Column(String(100), nullable=False, index=True)
    category = Column(
        SQLAlchemyEnum(PlaceCategory), default=PlaceCategory.OTHER, nullable=False
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(
        SQLAlchemyEnum(PlaceStatus),
        default=PlaceStatus.PENDING,
        nullable=False,
        index=True,
    )
    review = Column(Text, nullable=True)
    image_url = Column(String(1024), nullable=True)  # Store image URL as string

    # Timestamps - Use default=func.now() for creation time
    # onupdate=func.now() attempts to update timestamp on modification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<PlaceDB(id={self.id}, name='{self.name}', status='{self.status.value}')>"
        )


# Define other tables here if your schema grows
