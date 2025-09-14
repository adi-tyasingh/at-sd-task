from fastapi import APIRouter, HTTPException, Path
from app.models.event import SeatHoldRequest, SeatHoldResponse
from app.database import db_client
from app.utils import (
    generate_holding_id, get_current_timestamp, get_hold_expiry_time, 
    is_hold_expired, create_hold_transaction_items
)
from typing import List

router = APIRouter(tags=["seat-holding"])


@router.post("/events/{event_id}/hold", response_model=SeatHoldResponse)
async def hold_event_seats(
    event_id: str = Path(..., description="The event ID"),
    hold_request: SeatHoldRequest = None
):
    """Hold seats for an event with atomic transaction"""
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
                detail=f"Error checking event: {event_result['error']}"
            )
        
        # Verify user exists
        user_result = db_client.get_item(hold_request.user_id, "USER")
        if user_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {hold_request.user_id} not found"
            )
        elif user_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error checking user: {user_result['error']}"
            )
        
        # Get all event seats to check availability
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch event seats: {seats_result['error']}"
            )
        
        # Create a map of seat positions to seat data
        seat_map = {}
        for item in seats_result["items"]:
            if item.get("sk") != "EVENT":  # Skip the event object itself
                seat_map[item.get("seat_pos")] = item
        
        # Validate requested seats exist and check availability
        unavailable_seats = []
        expired_holds = []
        
        for seat_pos in hold_request.seats:
            if seat_pos not in seat_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Seat {seat_pos} does not exist for this event"
                )
            
            seat = seat_map[seat_pos]
            seat_state = seat.get("seat_state")
            holding_id = seat.get("holding_id")
            hold_ttl = seat.get("hold_ttl")
            created_at = seat.get("created_at")
            
            if seat_state == "available":
                continue  # Seat is available
            elif seat_state == "booked":
                unavailable_seats.append(seat_pos)
            elif seat_state == "held":
                # Check if hold has expired
                if holding_id and hold_ttl and created_at:
                    if is_hold_expired(hold_ttl, created_at):
                        expired_holds.append(seat_pos)
                    else:
                        unavailable_seats.append(seat_pos)
                else:
                    # Invalid hold data, consider it expired
                    expired_holds.append(seat_pos)
        
        # If any seats are unavailable (not expired), return error
        if unavailable_seats:
            raise HTTPException(
                status_code=409,
                detail=f"Seats are not available: {unavailable_seats}"
            )
        
        # Handle empty seat list
        if not hold_request.seats:
            return SeatHoldResponse(
                holding_id="",
                seats_held=[],
                hold_ttl=180,
                expires_at=get_hold_expiry_time(180)
            )
        
        # Remove duplicate seats from request while preserving order
        unique_seats = []
        seen = set()
        for seat in hold_request.seats:
            if seat not in seen:
                unique_seats.append(seat)
                seen.add(seat)
        
        # Generate holding ID and create transaction
        holding_id = generate_holding_id()
        ttl = 180  # 3 minutes
        
        # Create transaction items for holding seats
        transact_items = create_hold_transaction_items(
            event_id, holding_id, hold_request.user_id, unique_seats, ttl
        )
        
        # Execute transaction
        transaction_result = db_client.transact_write(transact_items)
        
        if transaction_result["status"] == "error":
            # Check if it's a conditional check failure (seat became unavailable)
            if "ConditionalCheckFailed" in str(transaction_result["error"]):
                raise HTTPException(
                    status_code=409,
                    detail="One or more seats became unavailable during the hold process. Please try again."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to hold seats: {transaction_result['error']}"
                )
        
        # Update event analytics
        try:
            update_analytics_result = db_client.update_item_conditional(
                event_id, "EVENT",
                "ADD hold_attempts :inc",
                "attribute_exists(pk)",
                {":inc": 1}
            )
        except Exception:
            # Analytics update failure shouldn't break the hold
            pass
        
        return SeatHoldResponse(
            holding_id=holding_id,
            seats_held=unique_seats,
            hold_ttl=ttl,
            expires_at=get_hold_expiry_time(ttl)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
