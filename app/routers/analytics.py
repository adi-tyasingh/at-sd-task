from fastapi import APIRouter, HTTPException, Path, Query
from app.models.event import EventAnalytics, SeatAnalytics, BookingAnalytics, ComprehensiveEventAnalytics
from app.database import db_client
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

router = APIRouter(tags=["analytics"])


@router.get("/events/{event_id}/analytics", response_model=EventAnalytics)
async def get_event_analytics(
    event_id: str = Path(..., description="The event ID"),
    include_seat_details: bool = Query(False, description="Include detailed seat information"),
    include_booking_details: bool = Query(False, description="Include detailed booking information")
):
    """Get comprehensive analytics for an event"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching event: {event_result['error']}"
            )
        
        event_data = event_result["item"]
        
        # Get venue information
        venue_result = db_client.get_item(event_data["venue_id"], "VENUE")
        if venue_result["status"] == "not_found":
            venue_name = "Unknown Venue"
        else:
            venue_name = venue_result["item"].get("name", "Unknown Venue")
        
        # Get all seats for the event
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching seats: {seats_result['error']}"
            )
        
        # Process seat data
        seats = []
        seat_states = {"available": 0, "held": 0, "booked": 0}
        total_revenue = 0.0
        seat_prices = {}
        
        for item in seats_result["items"]:
            if item.get("sk") == "EVENT":
                continue  # Skip the event object itself
            
            seat_state = item.get("seat_state", "available")
            seat_states[seat_state] = seat_states.get(seat_state, 0) + 1
            
            # Calculate revenue for booked seats
            if seat_state == "booked":
                price = float(item.get("price", 0))
                total_revenue += price
                seat_prices[item.get("seat_pos")] = price
            
            seats.append(item)
        
        # Get all bookings for the event
        bookings_result = db_client.scan_items(
            filter_expression="event_id = :event_id AND begins_with(sk, :booking_prefix)",
            expression_values={
                ":event_id": event_id,
                ":booking_prefix": "202"  # Bookings have timestamp as sk starting with year
            }
        )
        
        bookings = []
        if bookings_result["status"] == "success":
            bookings = bookings_result["items"]
        
        # Calculate booking metrics
        total_bookings = len(bookings)
        successful_bookings = len([b for b in bookings if b.get("state") == "confirmed"])
        cancelled_bookings = len([b for b in bookings if b.get("state") == "cancelled"])
        
        # Get hold attempts from event analytics (if available)
        hold_attempts = event_data.get("hold_attempts", 0)
        failed_holds = max(0, hold_attempts - successful_bookings)
        
        # Calculate capacity utilization
        total_seats = len(seats)
        seats_sold = seat_states["booked"]
        capacity_utilization = (seats_sold / total_seats * 100) if total_seats > 0 else 0.0
        
        # Calculate average booking value
        average_booking_value = total_revenue / successful_bookings if successful_bookings > 0 else 0.0
        
        # Get last booking time
        last_booking_time = None
        if bookings:
            # Sort by booking_date and get the most recent
            sorted_bookings = sorted(bookings, key=lambda x: x.get("booking_date", ""), reverse=True)
            last_booking_time = sorted_bookings[0].get("booking_date")
        
        # Build analytics response
        analytics = EventAnalytics(
            event_id=event_id,
            event_name=event_data.get("name", ""),
            venue_id=event_data.get("venue_id", ""),
            venue_name=venue_name,
            total_seats=total_seats,
            seats_available=seat_states["available"],
            seats_held=seat_states["held"],
            seats_booked=seat_states["booked"],
            seats_sold=seats_sold,
            capacity_utilization=round(capacity_utilization, 2),
            total_bookings=total_bookings,
            successful_bookings=successful_bookings,
            cancelled_bookings=cancelled_bookings,
            hold_attempts=hold_attempts,
            failed_holds=failed_holds,
            revenue_generated=round(total_revenue, 2),
            average_booking_value=round(average_booking_value, 2),
            last_booking_time=last_booking_time,
            created_at=event_data.get("created_at", ""),
            start_time=event_data.get("start_time", ""),
            duration=event_data.get("duration", 0),
            artists=event_data.get("artists", []),
            tags=event_data.get("tags", [])
        )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events/{event_id}/seats/analytics", response_model=List[SeatAnalytics])
async def get_seat_analytics(
    event_id: str = Path(..., description="The event ID"),
    seat_type: Optional[str] = Query(None, description="Filter by seat type"),
    seat_state: Optional[str] = Query(None, description="Filter by seat state")
):
    """Get detailed analytics for all seats in an event"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching event: {event_result['error']}"
            )
        
        # Get all seats for the event
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching seats: {seats_result['error']}"
            )
        
        # Process seat data
        seat_analytics = []
        for item in seats_result["items"]:
            if item.get("sk") == "EVENT":
                continue  # Skip the event object itself
            
            # Apply filters
            if seat_type and item.get("seat_type") != seat_type:
                continue
            if seat_state and item.get("seat_state") != seat_state:
                continue
            
            # Convert Decimal price to float
            price = float(item.get("price", 0)) if isinstance(item.get("price"), Decimal) else item.get("price", 0)
            
            seat_analytics.append(SeatAnalytics(
                seat_pos=item.get("seat_pos", ""),
                row=item.get("row", ""),
                seat_num=int(item.get("seat_num", 0)) if isinstance(item.get("seat_num"), Decimal) else item.get("seat_num", 0),
                seat_type=item.get("seat_type", ""),
                seat_state=item.get("seat_state", "available"),
                price=price,
                booking_id=item.get("booking_id"),
                holding_id=item.get("holding_id"),
                last_updated=item.get("updated_at")
            ))
        
        return seat_analytics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events/{event_id}/bookings/analytics", response_model=List[BookingAnalytics])
async def get_booking_analytics(
    event_id: str = Path(..., description="The event ID"),
    state: Optional[str] = Query(None, description="Filter by booking state"),
    limit: int = Query(100, description="Maximum number of bookings to return"),
    offset: int = Query(0, description="Number of bookings to skip")
):
    """Get detailed analytics for all bookings in an event"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
                raise HTTPException(
                status_code=500,
                detail=f"Error fetching event: {event_result['error']}"
            )
        
        # Get all bookings for the event
        bookings_result = db_client.scan_items(
            filter_expression="event_id = :event_id AND begins_with(sk, :booking_prefix)",
            expression_values={
                ":event_id": event_id,
                ":booking_prefix": "202"  # Bookings have timestamp as sk starting with year
            }
        )
        
        if bookings_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching bookings: {bookings_result['error']}"
            )
        
        bookings = bookings_result["items"]
        
        # Apply state filter
        if state:
            bookings = [b for b in bookings if b.get("state") == state]
        
        # Sort by booking date (most recent first)
        bookings.sort(key=lambda x: x.get("booking_date", ""), reverse=True)
        
        # Apply pagination
        bookings = bookings[offset:offset + limit]
        
        # Get seat prices for revenue calculation
        seats_result = db_client.query_items(event_id)
        seat_prices = {}
        if seats_result["status"] == "success":
            for item in seats_result["items"]:
                if item.get("sk") != "EVENT":
                    price = float(item.get("price", 0)) if isinstance(item.get("price"), Decimal) else item.get("price", 0)
                    seat_prices[item.get("seat_pos")] = price
        
        # Process booking data
        booking_analytics = []
        for booking in bookings:
            seats = booking.get("seats", [])
            total_amount = sum(seat_prices.get(seat, 0) for seat in seats)
            
            booking_analytics.append(BookingAnalytics(
                booking_id=booking.get("booking_id", ""),
                user_id=booking.get("user_id", ""),
                seats=seats,
                booking_date=booking.get("booking_date", ""),
                state=booking.get("state", ""),
                payment_status=booking.get("payment_status", ""),
                total_amount=round(total_amount, 2),
                seat_count=len(seats)
            ))
        
        return booking_analytics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events/{event_id}/revenue")
async def get_revenue_analytics(
    event_id: str = Path(..., description="The event ID"),
    by_seat_type: bool = Query(False, description="Break down revenue by seat type")
):
    """Get revenue analytics for an event"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching event: {event_result['error']}"
            )
        
        # Get all seats for the event
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching seats: {seats_result['error']}"
            )
        
        # Calculate revenue by seat type
        revenue_by_type = {}
        total_revenue = 0.0
        
        for item in seats_result["items"]:
            if item.get("sk") == "EVENT":
                continue  # Skip the event object itself
            
            if item.get("seat_state") == "booked":
                seat_type = item.get("seat_type", "unknown")
                price = float(item.get("price", 0)) if isinstance(item.get("price"), Decimal) else item.get("price", 0)
                
                if seat_type not in revenue_by_type:
                    revenue_by_type[seat_type] = 0.0
                
                revenue_by_type[seat_type] += price
                total_revenue += price
        
        # Build response
        response = {
            "event_id": event_id,
            "total_revenue": round(total_revenue, 2),
            "currency": "USD"  # Assuming USD, could be made configurable
        }
        
        if by_seat_type:
            response["revenue_by_seat_type"] = {
                seat_type: round(revenue, 2) 
                for seat_type, revenue in revenue_by_type.items()
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/events/{event_id}/comprehensive", response_model=ComprehensiveEventAnalytics)
async def get_comprehensive_event_analytics(
    event_id: str = Path(..., description="The event ID"),
    include_booking_details: bool = Query(True, description="Include detailed booking information"),
    booking_limit: int = Query(100, description="Maximum number of bookings to include"),
    booking_offset: int = Query(0, description="Number of bookings to skip")
):
    """Get comprehensive analytics for an event in a single response"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching event: {event_result['error']}"
            )
        
        event_data = event_result["item"]
        
        # Get venue information
        venue_result = db_client.get_item(event_data["venue_id"], "VENUE")
        if venue_result["status"] == "not_found":
            venue_name = "Unknown Venue"
        else:
            venue_name = venue_result["item"].get("name", "Unknown Venue")
        
        # Get all seats for the event
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching seats: {seats_result['error']}"
            )
        
        # Process seat data
        seats = []
        seat_states = {"available": 0, "held": 0, "booked": 0}
        total_revenue = 0.0
        revenue_by_seat_type = {}
        
        for item in seats_result["items"]:
            if item.get("sk") == "EVENT":
                continue  # Skip the event object itself
            
            seat_state = item.get("seat_state", "available")
            seat_states[seat_state] = seat_states.get(seat_state, 0) + 1
            
            # Convert Decimal price to float
            price = float(item.get("price", 0)) if isinstance(item.get("price"), Decimal) else item.get("price", 0)
            seat_type = item.get("seat_type", "unknown")
            
            # Calculate revenue for booked seats
            if seat_state == "booked":
                total_revenue += price
                if seat_type not in revenue_by_seat_type:
                    revenue_by_seat_type[seat_type] = 0.0
                revenue_by_seat_type[seat_type] += price
            
            seats.append(item)
        
        # Get all bookings for the event
        bookings_result = db_client.scan_items(
            filter_expression="event_id = :event_id AND begins_with(sk, :booking_prefix)",
            expression_values={
                ":event_id": event_id,
                ":booking_prefix": "202"  # Bookings have timestamp as sk starting with year
            }
        )
        
        bookings = []
        if bookings_result["status"] == "success":
            bookings = bookings_result["items"]
        
        # Calculate booking metrics
        total_bookings = len(bookings)
        successful_bookings = len([b for b in bookings if b.get("state") == "confirmed"])
        cancelled_bookings = len([b for b in bookings if b.get("state") == "cancelled"])
        
        # Get hold attempts from event analytics (if available)
        hold_attempts = event_data.get("hold_attempts", 0)
        failed_holds = max(0, hold_attempts - successful_bookings)
        
        # Calculate capacity utilization
        total_seats = len(seats)
        seats_sold = seat_states["booked"]
        capacity_utilization = (seats_sold / total_seats * 100) if total_seats > 0 else 0.0
        
        # Calculate average booking value
        average_booking_value = total_revenue / successful_bookings if successful_bookings > 0 else 0.0
        
        # Get last booking time
        last_booking_time = None
        if bookings:
            # Sort by booking_date and get the most recent
            sorted_bookings = sorted(bookings, key=lambda x: x.get("booking_date", ""), reverse=True)
            last_booking_time = sorted_bookings[0].get("booking_date")
        
        # Build booking analytics if requested
        booking_analytics = []
        if include_booking_details:
            # Sort by booking date (most recent first)
            sorted_bookings = sorted(bookings, key=lambda x: x.get("booking_date", ""), reverse=True)
            
            # Apply pagination
            paginated_bookings = sorted_bookings[booking_offset:booking_offset + booking_limit]
            
            for booking in paginated_bookings:
                booking_seats = booking.get("seats", [])
                booking_total = sum(revenue_by_seat_type.get(seat.split('-')[0] + '-' + seat.split('-')[1] if '-' in seat else seat, 0) for seat in booking_seats)
                
                booking_analytics.append(BookingAnalytics(
                    booking_id=booking.get("booking_id", ""),
                    user_id=booking.get("user_id", ""),
                    seats=booking_seats,
                    booking_date=booking.get("booking_date", ""),
                    state=booking.get("state", ""),
                    payment_status=booking.get("payment_status", ""),
                    total_amount=round(booking_total, 2),
                    seat_count=len(booking_seats)
                ))
        
        # Calculate performance metrics
        booking_success_rate = (successful_bookings / total_bookings * 100) if total_bookings > 0 else 0.0
        hold_success_rate = (successful_bookings / hold_attempts * 100) if hold_attempts > 0 else 0.0
        cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0.0
        
        # Build comprehensive analytics response
        comprehensive_analytics = ComprehensiveEventAnalytics(
            # Event Information
            event_id=event_id,
            event_name=event_data.get("name", ""),
            venue_id=event_data.get("venue_id", ""),
            venue_name=venue_name,
            created_at=event_data.get("created_at", ""),
            start_time=event_data.get("start_time", ""),
            duration=event_data.get("duration", 0),
            artists=event_data.get("artists", []),
            tags=event_data.get("tags", []),
            description=event_data.get("description", ""),
            
            # Seat Overview
            total_seats=total_seats,
            seats_available=seat_states["available"],
            seats_held=seat_states["held"],
            seats_booked=seat_states["booked"],
            seats_sold=seats_sold,
            capacity_utilization=round(capacity_utilization, 2),
            
            # Booking Overview
            total_bookings=total_bookings,
            successful_bookings=successful_bookings,
            cancelled_bookings=cancelled_bookings,
            hold_attempts=hold_attempts,
            failed_holds=failed_holds,
            
            # Revenue Overview
            revenue_generated=round(total_revenue, 2),
            average_booking_value=round(average_booking_value, 2),
            currency="USD",
            revenue_by_seat_type={seat_type: round(revenue, 2) for seat_type, revenue in revenue_by_seat_type.items()},
            
            # Timing
            last_booking_time=last_booking_time,
            
            # Detailed Data
            booking_analytics=booking_analytics,
            
            # Performance Metrics
            booking_success_rate=round(booking_success_rate, 2),
            hold_success_rate=round(hold_success_rate, 2),
            cancellation_rate=round(cancellation_rate, 2)
        )
        
        return comprehensive_analytics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
