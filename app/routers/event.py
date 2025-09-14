from fastapi import APIRouter, HTTPException, Query
from app.models.event import EventCreate, EventResponse
from app.database import db_client
from app.routers.event_seat import create_event_seats
from app.filtering import (
    filter_events_by_date, filter_events_by_artists, filter_events_by_tags,
    filter_events_by_city, filter_events_by_price_range, search_events, sort_events
)
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
import uuid

router = APIRouter(tags=["events"])


def generate_event_id() -> str:
    """Generate a unique event ID"""
    return f"event-{str(uuid.uuid4())[:8]}"


@router.post("/events", response_model=EventResponse)
async def create_event(event_data: EventCreate):
    """Create a new event and all associated event seats"""
    try:
        # First, verify that the venue exists
        venue_result = db_client.get_item(event_data.venue_id, "VENUE")
        if venue_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Venue with ID {event_data.venue_id} not found"
            )
        elif venue_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error checking venue: {venue_result['error']}"
            )
        
        venue = venue_result["item"]
        venue_seat_types = venue.get("seat_types", [])
        
        # Validate that all seat type prices are provided for venue seat types
        for seat_type in venue_seat_types:
            if seat_type not in event_data.seat_type_prices:
                raise HTTPException(
                    status_code=400,
                    detail=f"Price not provided for seat type '{seat_type}'. Required seat types: {venue_seat_types}"
                )
        
        # Generate event ID and current time
        event_id = generate_event_id()
        current_time = datetime.utcnow()
        
        # Convert prices to Decimal for DynamoDB
        seat_type_prices_decimal = {
            seat_type: Decimal(str(price)) 
            for seat_type, price in event_data.seat_type_prices.items()
        }
        
        # Create event item for DynamoDB
        event_item = {
            "pk": event_id,
            "sk": "EVENT",
            "event_id": event_id,
            "venue_id": event_data.venue_id,
            "name": event_data.name,
            "start_time": event_data.start_time,
            "duration": event_data.duration,
            "artists": event_data.artists,
            "tags": event_data.tags,
            "description": event_data.description,
            "seat_type_prices": seat_type_prices_decimal,
            "created_at": current_time.isoformat(),
            # Analytics fields
            "total_bookings": 0,
            "total_cancellations": 0,
            "hold_attempts": 0,
            "seats_sold": 0
        }
        
        # Put event into DynamoDB
        event_result = db_client.put_item(event_item)
        if event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create event: {event_result['error']}"
            )
        
        # Create event seats using the separate module
        try:
            event_seats_created = create_event_seats(event_id, event_data.venue_id, event_data.seat_type_prices)
            
            if event_seats_created == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No valid seats found in venue. Please ensure venue has seats with valid seat types."
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create event seats: {str(e)}"
            )
        
        return EventResponse(
            event_id=event_id,
            venue_id=event_data.venue_id,
            name=event_data.name,
            start_time=event_data.start_time,
            duration=event_data.duration,
            artists=event_data.artists,
            tags=event_data.tags,
            description=event_data.description,
            seat_type_prices=event_data.seat_type_prices,
            created_at=current_time.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events", response_model=List[EventResponse])
async def get_events(
    # Essential filters
    city: Optional[str] = Query(None, description="Filter by city"),
    start_date: Optional[str] = Query(None, description="Filter events from this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter events until this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in event name, description, artists, and tags"),
    
    # Pagination
    limit: Optional[int] = Query(50, description="Maximum number of events to return"),
    offset: Optional[int] = Query(0, description="Number of events to skip")
):
    """Get all events with advanced filtering and search capabilities"""
    try:
        # Get all events from database
        result = db_client.scan_items("sk = :sk", {":sk": "EVENT"})
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch events: {result['error']}"
            )
        
        # Convert to EventResponse objects
        events = []
        venue_cache = {}  # Cache for venue lookups
        
        for item in result["items"]:
            # Convert Decimal prices back to float for response
            seat_type_prices = {
                seat_type: float(price) if isinstance(price, Decimal) else price
                for seat_type, price in item["seat_type_prices"].items()
            }
            
            event = EventResponse(
                event_id=item["event_id"],
                venue_id=item["venue_id"],
                name=item["name"],
                start_time=item["start_time"],
                duration=item["duration"],
                artists=item["artists"],
                tags=item["tags"],
                description=item["description"],
                seat_type_prices=seat_type_prices,
                created_at=item["created_at"]
            )
            
            # Convert to dict for filtering
            event_dict = event.model_dump()
            events.append(event_dict)
            
            # Cache venue for city filtering
            if city and item["venue_id"] not in venue_cache:
                venue_result = db_client.get_item(item["venue_id"], "VENUE")
                if venue_result["status"] == "success":
                    venue_cache[item["venue_id"]] = venue_result["item"]
        
        # Apply filters
        filtered_events = events
        
        # Date range filtering
        if start_date:
            filtered_events = filter_events_by_date(filtered_events, start_date, "after")
        if end_date:
            filtered_events = filter_events_by_date(filtered_events, end_date, "before")
        
        # City filtering
        if city:
            filtered_events = filter_events_by_city(filtered_events, city, venue_cache)
        
        # Search filtering (name, description, tags)
        if search:
            filtered_events = search_events(filtered_events, search)
        
        # Sort by date (newest first)
        filtered_events = sort_events(filtered_events, "date", "desc")
        
        # Apply pagination
        start_idx = offset or 0
        end_idx = start_idx + (limit or 50)
        paginated_events = filtered_events[start_idx:end_idx]
        
        # Convert back to EventResponse objects
        result_events = []
        for event_dict in paginated_events:
            result_events.append(EventResponse(**event_dict))
        
        return result_events
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


