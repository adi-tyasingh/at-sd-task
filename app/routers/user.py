from fastapi import APIRouter, HTTPException, Path
from app.models.user import UserCreate, UserResponse, UserBookingResponse
from app.database import db_client
from datetime import datetime
from typing import List
import uuid

router = APIRouter(tags=["users"])


def generate_user_id() -> str:
    """Generate a unique user ID"""
    return f"user-{str(uuid.uuid4())[:8]}"


@router.post("/user", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """Create a new user"""
    try:
        user_id = generate_user_id()
        current_time = datetime.utcnow()
        
        # Create user item for DynamoDB
        user_item = {
            "pk": user_id,
            "sk": "USER",
            "user_id": user_id,
            "email": user_data.email,
            "phone": user_data.phone,
            "created_at": current_time.isoformat()
        }
        
        # Put user into DynamoDB
        result = db_client.put_item(user_item)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create user: {result['error']}"
            )
        
        return UserResponse(
            user_id=user_id,
            email=user_data.email,
            phone=user_data.phone,
            created_at=current_time.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: str = Path(..., description="The user ID")):
    """Get a specific user by ID"""
    try:
        result = db_client.get_item(user_id, "USER")
        
        if result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        elif result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching user: {result['error']}"
            )
        
        user = result["item"]
        return UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            phone=user["phone"],
            created_at=user["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/user/{user_id}/bookings", response_model=List[UserBookingResponse])
async def get_user_bookings(user_id: str = Path(..., description="The user ID")):
    """Get all bookings for a specific user, sorted by time"""
    try:
        # First verify user exists
        user_result = db_client.get_item(user_id, "USER")
        if user_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        elif user_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error checking user: {user_result['error']}"
            )
        
        # Query all bookings for this user using GSI
        # Note: This assumes we have a GSI with user_id as partition key
        # For now, we'll scan for bookings with user_id
        filter_expression = "sk = :sk AND user_id = :user_id"
        expression_values = {
            ":sk": "BOOKING",
            ":user_id": user_id
        }
        
        result = db_client.scan_items(filter_expression, expression_values)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch user bookings: {result['error']}"
            )
        
        bookings = []
        for item in result["items"]:
            bookings.append(UserBookingResponse(
                booking_id=item["booking_id"],
                event_id=item["event_id"],
                seats=item["seats"],
                booking_date=item["booking_date"],
                state=item["state"]
            ))
        
        # Sort by booking date (most recent first)
        bookings.sort(key=lambda x: x.booking_date, reverse=True)
        
        return bookings
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
