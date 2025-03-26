from pydantic import BaseModel
from typing import Optional, List

class PlaceCreate(BaseModel):
    name: str
    category: str
    latitude: float
    longitude: float

class Place(PlaceCreate):
    id: int
    status: str = "pending"
    reviews: Optional[List["Review"]] = None

class ReviewCreate(BaseModel):
    review_text: Optional[str] = None

class Review(ReviewCreate):
    id: int
    place_id: int
    image_path: Optional[str] = None

# Forward reference to handle the circular dependency
Place.update_forward_refs()