from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


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
