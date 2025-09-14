from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EventCreate(BaseModel):
    venue_id: str
    name: str
    start_time: str  # ISO format datetime string
    duration: int  # Duration in minutes
    artists: List[str]
    tags: List[str]
    description: str
    seat_type_prices: Dict[str, float]  # seat_type -> price mapping


class Event(BaseModel):
    event_id: str
    venue_id: str
    name: str
    start_time: str
    duration: int
    artists: List[str]
    tags: List[str]
    description: str
    seat_type_prices: Dict[str, float]
    created_at: str


class EventResponse(BaseModel):
    event_id: str
    venue_id: str
    name: str
    start_time: str
    duration: int
    artists: List[str]
    tags: List[str]
    description: str
    seat_type_prices: Dict[str, float]
    created_at: str


class EventSeat(BaseModel):
    event_id: str
    seat_pos: str
    row: str
    seat_num: int
    seat_type: str
    seat_state: str  # available, held, booked
    booking_id: str = None
    holding_id: str = None
    hold_ttl: int = None
    price: float


class EventSeatResponse(BaseModel):
    event_id: str
    seat_pos: str
    row: str
    seat_num: int
    seat_type: str
    seat_state: str
    booking_id: Optional[str] = None
    holding_id: Optional[str] = None
    hold_ttl: Optional[int] = None
    price: float


class SeatHoldRequest(BaseModel):
    user_id: str
    seats: List[str]  # List of seat positions to hold


class SeatHoldResponse(BaseModel):
    holding_id: str
    seats_held: List[str]
    hold_ttl: int
    expires_at: str


class Holding(BaseModel):
    holding_id: str
    event_id: str
    user_id: str
    seats: List[str]
    created_at: str
    expires_at: str
    ttl: int


class Booking(BaseModel):
    booking_id: str
    event_id: str
    user_id: str
    seats: List[str]
    booking_date: str
    state: str  # confirmed, cancelled
    payment_status: str


class BookingResponse(BaseModel):
    booking_id: str
    event_id: str
    user_id: str
    seats: List[str]
    booking_date: str
    state: str
    payment_status: str


class PaymentConfirmRequest(BaseModel):
    payment_status: str  # "successful" or "failed"


class BookingCancelRequest(BaseModel):
    booking_id: str


class EventAnalytics(BaseModel):
    event_id: str
    event_name: str
    venue_id: str
    venue_name: str
    total_seats: int
    seats_available: int
    seats_held: int
    seats_booked: int
    seats_sold: int
    capacity_utilization: float  # Percentage
    total_bookings: int
    successful_bookings: int
    cancelled_bookings: int
    hold_attempts: int
    failed_holds: int
    revenue_generated: float
    average_booking_value: float
    last_booking_time: str = None
    created_at: str
    start_time: str
    duration: int
    artists: List[str]
    tags: List[str]


class SeatAnalytics(BaseModel):
    seat_pos: str
    row: str
    seat_num: int
    seat_type: str
    seat_state: str
    price: float
    booking_id: Optional[str] = None
    holding_id: Optional[str] = None
    last_updated: Optional[str] = None


class BookingAnalytics(BaseModel):
    booking_id: str
    user_id: str
    seats: List[str]
    booking_date: str
    state: str
    payment_status: str
    total_amount: float
    seat_count: int


class ComprehensiveEventAnalytics(BaseModel):
    # Event Information
    event_id: str
    event_name: str
    venue_id: str
    venue_name: str
    created_at: str
    start_time: str
    duration: int
    artists: List[str]
    tags: List[str]
    description: str

    # Seat Overview
    total_seats: int
    seats_available: int
    seats_held: int
    seats_booked: int
    seats_sold: int
    capacity_utilization: float

    # Booking Overview
    total_bookings: int
    successful_bookings: int
    cancelled_bookings: int
    hold_attempts: int
    failed_holds: int

    # Revenue Overview
    revenue_generated: float
    average_booking_value: float
    currency: str = "USD"
    revenue_by_seat_type: dict

    # Timing
    last_booking_time: str = None

    # Detailed Data
    booking_analytics: List[BookingAnalytics]

    # Performance Metrics
    booking_success_rate: float
    hold_success_rate: float
    cancellation_rate: float
