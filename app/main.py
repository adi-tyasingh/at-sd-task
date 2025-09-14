from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.database import db_client
from app.routers import venue, venue_seat, event, event_seat, user, seat_holding, seat_booking, analytics

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Evently - Event Booking Platform",
    description="A scalable event booking platform for managing venues, events, and seat reservations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(venue.router)
app.include_router(venue_seat.router)
app.include_router(event.router)
app.include_router(event_seat.router)
app.include_router(seat_holding.router)
app.include_router(seat_booking.router)
app.include_router(analytics.router)
app.include_router(user.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Evently",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Evently - Event Booking Platform",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/db-test")
async def test_database():
    """Test DynamoDB connection"""
    return db_client.test_connection()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
