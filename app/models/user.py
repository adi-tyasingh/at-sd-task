from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


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
