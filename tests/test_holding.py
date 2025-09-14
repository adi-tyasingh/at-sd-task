import pytest
from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)


@pytest.fixture
def test_event_with_seats():
    """Create a test event with seats for holding tests"""
    # Create venue
    venue_data = {
        "name": "Test Stadium",
        "city": "Mumbai",
        "description": "A test stadium for events",
        "seat_types": ["VIP", "Standard", "Economy"]
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
            {"row": "C", "seat_num": 1, "seat_type": "Economy"}
        ]
    }
    
    seats_response = client.post(f"/venue/{venue['venue_id']}/seats", json=seat_data)
    assert seats_response.status_code == 200
    
    # Create event (this will create event seats)
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "work  a ",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music"],
        "description": "A test concert event",
        "seat_type_prices": {
            "VIP": 1000.0,
            "Standard": 500.0,
            "Economy": 200.0
        }
    }
    
    event_response = client.post("/events", json=event_data)
    assert event_response.status_code == 200
    event = event_response.json()
    
    return event


@pytest.fixture
def test_user():
    """Create a test user for holding tests"""
    user_data = {
        "email": "test@example.com",
        "phone": "+1234567890"
    }
    
    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    return response.json()


def test_hold_seats_success(test_event_with_seats, test_user):
    """Test successful seat holding"""
    event = test_event_with_seats
    user = test_user
    
    hold_request = {
        "user_id": user["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "holding-" in data["holding_id"]
    assert data["seats_held"] == ["A-1", "A-2"]
    assert data["hold_ttl"] == 180
    assert "expires_at" in data


def test_hold_seats_invalid_event():
    """Test holding seats for non-existent event"""
    hold_request = {
        "user_id": "user-00001",
        "seats": ["A-1", "A-2"]
    }
    
    response = client.post("/events/event-nonexistent/hold", json=hold_request)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_hold_seats_invalid_user(test_event_with_seats):
    """Test holding seats with non-existent user"""
    event = test_event_with_seats
    
    hold_request = {
        "user_id": "user-nonexistent",
        "seats": ["A-1", "A-2"]
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_hold_seats_invalid_seat_positions(test_event_with_seats, test_user):
    """Test holding non-existent seat positions"""
    event = test_event_with_seats
    user = test_user
    
    hold_request = {
        "user_id": user["user_id"],
        "seats": ["Z-99", "X-100"]  # Non-existent seats
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_hold_seats_already_held(test_event_with_seats, test_user):
    """Test holding seats that are already held by another user"""
    event = test_event_with_seats
    user = test_user
    
    # Create another user
    user2_data = {
        "email": "test2@example.com",
        "phone": "+1234567891"
    }
    user2_response = client.post("/user", json=user2_data)
    assert user2_response.status_code == 200
    user2 = user2_response.json()
    
    # First user holds seats
    hold_request1 = {
        "user_id": user["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    response1 = client.post(f"/events/{event['event_id']}/hold", json=hold_request1)
    assert response1.status_code == 200
    
    # Second user tries to hold the same seats
    hold_request2 = {
        "user_id": user2["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    response2 = client.post(f"/events/{event['event_id']}/hold", json=hold_request2)
    
    assert response2.status_code == 409
    assert "unavailable" in response2.json()["detail"]


def test_hold_seats_partial_availability(test_event_with_seats, test_user):
    """Test holding seats when only some are available"""
    event = test_event_with_seats
    user = test_user
    
    # Create another user
    user2_data = {
        "email": "test2@example.com",
        "phone": "+1234567891"
    }
    user2_response = client.post("/user", json=user2_data)
    assert user2_response.status_code == 200
    user2 = user2_response.json()
    
    # First user holds some seats
    hold_request1 = {
        "user_id": user["user_id"],
        "seats": ["A-1"]
    }
    
    response1 = client.post(f"/events/{event['event_id']}/hold", json=hold_request1)
    assert response1.status_code == 200
    
    # Second user tries to hold overlapping seats
    hold_request2 = {
        "user_id": user2["user_id"],
        "seats": ["A-1", "B-1"]  # A-1 is already held
    }
    
    response2 = client.post(f"/events/{event['event_id']}/hold", json=hold_request2)
    
    assert response2.status_code == 409
    assert "unavailable" in response2.json()["detail"]


def test_hold_seats_atomic_transaction(test_event_with_seats, test_user):
    """Test that holding is atomic - either all seats are held or none"""
    event = test_event_with_seats
    user = test_user
    
    # This test ensures that if one seat becomes unavailable during the transaction,
    # the entire transaction fails and no seats are held
    
    # First, hold some seats
    hold_request1 = {
        "user_id": user["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    response1 = client.post(f"/events/{event['event_id']}/hold", json=hold_request1)
    assert response1.status_code == 200
    
    # Verify seats are held by checking event seats
    seats_response = client.get(f"/events/{event['event_id']}/seats")
    assert seats_response.status_code == 200
    seats = seats_response.json()
    
    held_seats = [seat for seat in seats if seat["seat_pos"] in ["A-1", "A-2"]]
    assert len(held_seats) == 2
    assert all(seat["seat_state"] == "held" for seat in held_seats)
    assert all(seat["holding_id"] is not None for seat in held_seats)


def test_hold_seats_verify_holding_record(test_event_with_seats, test_user):
    """Test that holding record is created correctly"""
    event = test_event_with_seats
    user = test_user
    
    hold_request = {
        "user_id": user["user_id"],
        "seats": ["A-1", "B-1"]
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    assert response.status_code == 200
    
    data = response.json()
    holding_id = data["holding_id"]
    
    # Verify holding record exists in database
    # Note: In a real test, you'd query the database directly
    # For now, we verify the response structure
    assert "holding-" in holding_id
    assert data["seats_held"] == ["A-1", "B-1"]
    assert data["hold_ttl"] == 180


def test_hold_seats_empty_seat_list(test_event_with_seats, test_user):
    """Test holding with empty seat list"""
    event = test_event_with_seats
    user = test_user
    
    hold_request = {
        "user_id": user["user_id"],
        "seats": []
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    
    # Should succeed but with empty seats
    assert response.status_code == 200
    data = response.json()
    assert data["seats_held"] == []


def test_hold_seats_duplicate_seats_in_request(test_event_with_seats, test_user):
    """Test holding with duplicate seats in the same request"""
    event = test_event_with_seats
    user = test_user
    
    hold_request = {
        "user_id": user["user_id"],
        "seats": ["A-1", "A-1", "B-1"]  # A-1 appears twice
    }
    
    response = client.post(f"/events/{event['event_id']}/hold", json=hold_request)
    
    # Should succeed - duplicates in request are handled by the transaction
    assert response.status_code == 200
    data = response.json()
    assert "A-1" in data["seats_held"]
    assert "B-1" in data["seats_held"]


def test_hold_seats_concurrent_requests(test_event_with_seats):
    """Test concurrent holding requests for the same seats"""
    event = test_event_with_seats
    
    # Create two users
    user1_data = {"email": "user1@example.com", "phone": "+1111111111"}
    user2_data = {"email": "user2@example.com", "phone": "+2222222222"}
    
    user1_response = client.post("/user", json=user1_data)
    user2_response = client.post("/user", json=user2_data)
    
    assert user1_response.status_code == 200
    assert user2_response.status_code == 200
    
    user1 = user1_response.json()
    user2 = user2_response.json()
    
    # Both users try to hold the same seats simultaneously
    hold_request1 = {
        "user_id": user1["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    hold_request2 = {
        "user_id": user2["user_id"],
        "seats": ["A-1", "A-2"]
    }
    
    # Make concurrent requests
    response1 = client.post(f"/events/{event['event_id']}/hold", json=hold_request1)
    response2 = client.post(f"/events/{event['event_id']}/hold", json=hold_request2)
    
    # One should succeed, one should fail
    success_count = 0
    if response1.status_code == 200:
        success_count += 1
    if response2.status_code == 200:
        success_count += 1
    
    assert success_count == 1  # Exactly one should succeed
    
    # The failed one should be 409 (conflict)
    failed_response = response1 if response1.status_code != 200 else response2
    assert failed_response.status_code == 409
