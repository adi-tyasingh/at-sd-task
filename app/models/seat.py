from pydantic import BaseModel
from typing import List, Optional


class SeatCreate(BaseModel):
    row: str
    seat_num: int
    seat_type: str


class Seat(BaseModel):
    venue_id: str
    row: str
    seat_num: int
    seat_type: str
    seat_pos: str  # Combined row and seat_num for unique identification


class SeatResponse(BaseModel):
    venue_id: str
    row: str
    seat_num: int
    seat_type: str
    seat_pos: str


class VenueSeatCreate(BaseModel):
    seats: List[SeatCreate]
