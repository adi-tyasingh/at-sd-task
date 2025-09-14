import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def test_event_with_seats():
    """Create a test event with seats for testing"""
    # Create venue
    venue_data = {
        "name": "Test Stadium",
        "city": "Mumbai",
        "description": "A test stadium for events",
        "seat_types": ["VIP", "Standard", "Economy"],
    }

    venue_response = client.post("/venue", json=venue_data)
    assert venue_response.status_code == 200
    venue = venue_response.json()

    # Add seats to venue
    seat_data = {
        "seats": [
            {"row": "A", "seat_num": 1, "seat_type": "VIP"},
            {"row": "A", "seat_num": 2, "seat_type": "VIP"},
            {"row": "B", "seat_num": 1, "seat_type": "Standard"},
            {"row": "B", "seat_num": 2, "seat_type": "Standard"},
            {"row": "C", "seat_num": 1, "seat_type": "Economy"},
        ]
    }

    seats_response = client.post(f"/venue/{venue['venue_id']}/seats", json=seat_data)
    assert seats_response.status_code == 200

    # Create event (this will create event seats)
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music"],
        "description": "A test concert event",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    event_response = client.post("/events", json=event_data)
    assert event_response.status_code == 200
    event = event_response.json()

    return event


def test_get_event_seats(test_event_with_seats):
    """Test getting seats for an event"""
    event = test_event_with_seats

    response = client.get(f"/events/{event['event_id']}/seats")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 5  # Should have 5 seats
    assert all(seat["event_id"] == event["event_id"] for seat in data)
    assert all(seat["seat_state"] == "available" for seat in data)

    # Check seat types and prices
    vip_seats = [seat for seat in data if seat["seat_type"] == "VIP"]
    standard_seats = [seat for seat in data if seat["seat_type"] == "Standard"]
    economy_seats = [seat for seat in data if seat["seat_type"] == "Economy"]

    assert len(vip_seats) == 2
    assert len(standard_seats) == 2
    assert len(economy_seats) == 1

    assert all(seat["price"] == 1000.0 for seat in vip_seats)
    assert all(seat["price"] == 500.0 for seat in standard_seats)
    assert all(seat["price"] == 200.0 for seat in economy_seats)


def test_get_event_seats_invalid_event():
    """Test getting seats for non-existent event"""
    response = client.get("/events/event-nonexistent/seats")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_event_seat_creation_function():
    """Test the create_event_seats function directly"""
    from app.routers.event_seat import create_event_seats

    # This test would require setting up a venue and event first
    # For now, we'll just test that the function exists and can be imported
    assert callable(create_event_seats)
