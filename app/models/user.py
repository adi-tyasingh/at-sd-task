from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    phone: str


class User(BaseModel):
    user_id: str
    email: str
    phone: str
    created_at: datetime


class UserResponse(BaseModel):
    user_id: str
    email: str
    phone: str
    created_at: str


class UserBooking(BaseModel):
    booking_id: str
    event_id: str
    seats: list
    booking_date: str
    state: str


class UserBookingResponse(BaseModel):
    booking_id: str
    event_id: str
    seats: list
    booking_date: str
    state: str
