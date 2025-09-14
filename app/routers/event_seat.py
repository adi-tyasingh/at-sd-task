from decimal import Decimal
from typing import List

from fastapi import APIRouter, HTTPException, Path

from app.database import db_client
from app.models.event import EventSeatResponse

router = APIRouter(tags=["event-seats"])


@router.get("/events/{event_id}/seats", response_model=List[EventSeatResponse])
async def get_event_seats(event_id: str = Path(..., description="The event ID")):
    """Get all seats for a specific event"""
    try:
        # First verify event exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404, detail=f"Event with ID {event_id} not found"
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Error checking event: {event_result['error']}"
            )

        # Query all event seats
        result = db_client.query_items(event_id)

        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch event seats: {result['error']}",
            )

        seats = []
        for item in result["items"]:
            # Skip the event object itself (sk="EVENT")
            if item.get("sk") == "EVENT":
                continue

            # Convert Decimal price back to float for response
            price_value = item.get("price", 0.0)
            price = (
                float(price_value) if isinstance(price_value, Decimal) else price_value
            )

            seats.append(
                EventSeatResponse(
                    event_id=item.get("event_id", ""),
                    seat_pos=item.get("seat_pos", ""),
                    row=item.get("row", ""),
                    seat_num=item.get("seat_num", 0),
                    seat_type=item.get("seat_type", ""),
                    seat_state=item.get("seat_state", "available"),
                    booking_id=item.get("booking_id"),
                    holding_id=item.get("holding_id"),
                    hold_ttl=item.get("hold_ttl"),
                    price=price,
                )
            )

        return seats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def create_event_seats(event_id: str, venue_id: str, seat_type_prices: dict) -> int:
    """Create event seats for all venue seats. Returns number of seats created."""
    try:
        # Get all seats for the venue
        seats_result = db_client.query_items(venue_id)
        if seats_result["status"] == "error":
            raise Exception(f"Failed to fetch venue seats: {seats_result['error']}")

        event_seats_created = 0

        # Create event seats for all venue seats
        for item in seats_result["items"]:
            # Skip the venue object itself (sk="VENUE")
            if item.get("sk") == "VENUE":
                continue

            seat_type = item.get("seat_type")
            if seat_type not in seat_type_prices:
                continue  # Skip seats with invalid seat types

            # Create event seat item
            event_seat_item = {
                "pk": event_id,
                "sk": item.get("seat_pos"),  # Use seat position as sort key
                "event_id": event_id,
                "seat_pos": item.get("seat_pos"),
                "row": item.get("row"),
                "seat_num": item.get("seat_num"),
                "seat_type": seat_type,
                "seat_state": "available",
                "booking_id": None,
                "holding_id": None,
                "hold_ttl": None,
                "price": Decimal(str(seat_type_prices[seat_type])),
            }

            # Put event seat into DynamoDB
            seat_result = db_client.put_item(event_seat_item)
            if seat_result["status"] == "error":
                # If seat creation fails, log the error and continue
                print(
                    f"Warning: Failed to create event seat {item.get('seat_pos')}: {seat_result['error']}"
                )
                continue

            event_seats_created += 1

        return event_seats_created

    except Exception as e:
        raise Exception(f"Failed to create event seats: {str(e)}")
