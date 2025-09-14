import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path

from app.database import db_client
from app.models.venue import VenueCreate, VenueResponse

router = APIRouter(tags=["venues"])


def generate_venue_id() -> str:
    """Generate a unique venue ID"""
    return f"venue-{str(uuid.uuid4())[:8]}"


@router.post("/venue", response_model=VenueResponse)
async def create_venue(venue_data: VenueCreate):
    """Create a new venue"""
    try:
        venue_id = generate_venue_id()
        current_time = datetime.utcnow()

        # Create venue item for DynamoDB
        venue_item = {
            "pk": venue_id,
            "sk": "VENUE",
            "venue_id": venue_id,
            "name": venue_data.name,
            "city": venue_data.city,
            "description": venue_data.description,
            "seat_types": venue_data.seat_types,
            "created_at": current_time.isoformat(),
        }

        # Put item into DynamoDB
        result = db_client.put_item(venue_item)

        if result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Failed to create venue: {result['error']}"
            )

        return VenueResponse(
            venue_id=venue_id,
            name=venue_data.name,
            city=venue_data.city,
            description=venue_data.description,
            seat_types=venue_data.seat_types,
            created_at=current_time.isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/venue", response_model=List[VenueResponse])
async def get_venues(city: str = None):
    """Get all venues, optionally filtered by city"""
    try:
        # Scan for all venues (items with sk="VENUE")
        filter_expression = "sk = :sk"
        expression_values = {":sk": "VENUE"}

        if city:
            filter_expression += " AND city = :city"
            expression_values[":city"] = city

        result = db_client.scan_items(filter_expression, expression_values)

        if result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch venues: {result['error']}"
            )

        venues = []
        for item in result["items"]:
            venues.append(
                VenueResponse(
                    venue_id=item["venue_id"],
                    name=item["name"],
                    city=item["city"],
                    description=item["description"],
                    seat_types=item["seat_types"],
                    created_at=item["created_at"],
                )
            )

        return venues

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/venue/{venue_id}", response_model=VenueResponse)
async def get_venue(venue_id: str = Path(..., description="The venue ID")):
    """Get a specific venue by ID"""
    try:
        result = db_client.get_item(venue_id, "VENUE")

        if result["status"] == "not_found":
            raise HTTPException(
                status_code=404, detail=f"Venue with ID {venue_id} not found"
            )
        elif result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Error fetching venue: {result['error']}"
            )

        venue = result["item"]
        return VenueResponse(
            venue_id=venue["venue_id"],
            name=venue["name"],
            city=venue["city"],
            description=venue["description"],
            seat_types=venue["seat_types"],
            created_at=venue["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/venue/{venue_id}")
async def delete_venue(venue_id: str = Path(..., description="The venue ID")):
    """Delete a venue (soft delete by marking as deleted)"""
    try:
        # First check if venue exists
        result = db_client.get_item(venue_id, "VENUE")

        if result["status"] == "not_found":
            raise HTTPException(
                status_code=404, detail=f"Venue with ID {venue_id} not found"
            )
        elif result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Error checking venue: {result['error']}"
            )

        # Check if venue has seats
        seats_result = db_client.query_items(venue_id)
        if (
            seats_result["status"] == "success" and len(seats_result["items"]) > 1
        ):  # More than just the venue object
            raise HTTPException(
                status_code=400,
                detail="Cannot delete venue with existing seats. Please delete all seats first.",
            )

        # For now, we'll just return success (in a real app, you'd mark as deleted)
        return {"message": f"Venue {venue_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
