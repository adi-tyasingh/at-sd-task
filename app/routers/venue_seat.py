from fastapi import APIRouter, HTTPException, Path
from app.models.seat import SeatCreate, SeatResponse, VenueSeatCreate
from app.database import db_client
from typing import List

router = APIRouter(tags=["venue-seats"])


def create_seat_pos(row: str, seat_num: int) -> str:
    """Create seat position string from row and seat number"""
    return f"{row}-{seat_num}"


@router.post("/venue/{venue_id}/seats", response_model=List[SeatResponse])
async def create_venue_seats(
    venue_id: str = Path(..., description="The venue ID"),
    seat_data: VenueSeatCreate = None
):
    """Add seats to a specific venue"""
    try:
        # First, verify that the venue exists
        venue_result = db_client.get_item(venue_id, "VENUE")
        if venue_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Venue with ID {venue_id} not found"
            )
        elif venue_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error checking venue: {venue_result['error']}"
            )
        
        venue = venue_result["item"]
        venue_seat_types = venue.get("seat_types", [])
        
        created_seats = []
        
        # Process each seat
        for seat in seat_data.seats:
            # Validate seat type exists in venue
            if seat.seat_type not in venue_seat_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Seat type '{seat.seat_type}' not valid for this venue. Available types: {venue_seat_types}"
                )
            
            seat_pos = create_seat_pos(seat.row, seat.seat_num)
            
            # Check if seat already exists
            existing_seat = db_client.get_item(venue_id, seat_pos)
            if existing_seat["status"] == "success":
                raise HTTPException(
                    status_code=409,
                    detail=f"Seat {seat_pos} already exists for venue {venue_id}"
                )
            
            # Create seat item for DynamoDB
            seat_item = {
                "pk": venue_id,
                "sk": seat_pos,
                "venue_id": venue_id,
                "row": seat.row,
                "seat_num": seat.seat_num,
                "seat_type": seat.seat_type,
                "seat_pos": seat_pos
            }
            
            # Put seat into DynamoDB
            result = db_client.put_item(seat_item)
            
            if result["status"] == "error":
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create seat {seat_pos}: {result['error']}"
                )
            
            created_seats.append(SeatResponse(
                venue_id=venue_id,
                row=seat.row,
                seat_num=seat.seat_num,
                seat_type=seat.seat_type,
                seat_pos=seat_pos
            ))
        
        return created_seats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/venue/{venue_id}/seats", response_model=List[SeatResponse])
async def get_venue_seats(
    venue_id: str = Path(..., description="The venue ID")
):
    """Get all seats for a specific venue"""
    try:
        # First, verify that the venue exists
        venue_result = db_client.get_item(venue_id, "VENUE")
        if venue_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Venue with ID {venue_id} not found"
            )
        elif venue_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error checking venue: {venue_result['error']}"
            )
        
        # Query all seats for this venue
        result = db_client.query_items(venue_id)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch seats: {result['error']}"
            )
        
        seats = []
        for item in result["items"]:
            # Skip the venue object itself (sk="VENUE")
            if item.get("sk") == "VENUE":
                continue
                
            seats.append(SeatResponse(
                venue_id=item["venue_id"],
                row=item["row"],
                seat_num=item["seat_num"],
                seat_type=item["seat_type"],
                seat_pos=item["seat_pos"]
            ))
        
        return seats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
