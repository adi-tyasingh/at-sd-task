import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def test_venue_with_seats():
    """Create a test venue with seats for event testing"""
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

    return venue


def test_create_event(test_venue_with_seats):
    """Test creating an event with event seats"""
    venue = test_venue_with_seats

    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1", "Artist 2"],
        "tags": ["music", "concert", "live"],
        "description": "A test concert event",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    response = client.post("/events", json=event_data)

    assert response.status_code == 200
    data = response.json()

    assert data["venue_id"] == venue["venue_id"]
    assert data["name"] == event_data["name"]
    assert data["start_time"] == event_data["start_time"]
    assert data["duration"] == event_data["duration"]
    assert data["artists"] == event_data["artists"]
    assert data["tags"] == event_data["tags"]
    assert data["description"] == event_data["description"]
    assert data["seat_type_prices"] == event_data["seat_type_prices"]
    assert "event-" in data["event_id"]


def test_create_event_invalid_venue():
    """Test creating event with non-existent venue"""
    event_data = {
        "venue_id": "venue-nonexistent",
        "name": "Test Concert",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music"],
        "description": "A test concert event",
        "seat_type_prices": {"VIP": 1000.0},
    }

    response = client.post("/events", json=event_data)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_event_missing_seat_type_price(test_venue_with_seats):
    """Test creating event with missing seat type price"""
    venue = test_venue_with_seats

    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music"],
        "description": "A test concert event",
        "seat_type_prices": {
            "VIP": 1000.0
            # Missing Standard and Economy prices
        },
    }

    response = client.post("/events", json=event_data)

    assert response.status_code == 400
    assert "Price not provided for seat type" in response.json()["detail"]


def test_get_events(test_venue_with_seats):
    """Test getting all events"""
    venue = test_venue_with_seats

    # Create an event first
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music", "concert"],
        "description": "A test concert event",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    create_response = client.post("/events", json=event_data)
    assert create_response.status_code == 200

    # Get all events
    response = client.get("/events")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    # Check that our event is in the list
    event_names = [event["name"] for event in data]
    assert "Test Concert" in event_names


def test_get_events_with_filters(test_venue_with_seats):
    """Test getting events with filters"""
    venue = test_venue_with_seats

    # Create an event
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Mumbai Music Festival",
        "start_time": "2024-12-25T19:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music", "festival"],
        "description": "A music festival in Mumbai",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    create_response = client.post("/events", json=event_data)
    assert create_response.status_code == 200

    # Test location filter
    response = client.get("/events?location=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    # Test tags filter
    response = client.get("/events?tags=music")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_event_seats(test_venue_with_seats):
    """Test getting seats for an event"""
    venue = test_venue_with_seats

    # Create an event
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

    create_response = client.post("/events", json=event_data)
    assert create_response.status_code == 200
    event = create_response.json()

    # Get event seats
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
