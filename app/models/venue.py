from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class VenueCreate(BaseModel):
    name: str
    city: str
    description: str
    seat_types: List[str]  # e.g., ["VIP", "Standard", "Economy"]


class Venue(BaseModel):
    venue_id: str
    name: str
    city: str
    description: str
    seat_types: List[str]
    created_at: datetime


class VenueResponse(BaseModel):
    venue_id: str
    name: str
    city: str
    description: str
    seat_types: List[str]
    created_at: str
