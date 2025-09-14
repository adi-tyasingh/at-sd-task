import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def test_venue():
    """Create a test venue for seat testing"""
    venue_data = {
        "name": "Test Arena",
        "city": "Mumbai",
        "description": "A test venue for seat testing",
        "seat_types": ["VIP", "Standard", "Economy"],
    }

    response = client.post("/venue/", json=venue_data)
    assert response.status_code == 200
    return response.json()


def test_create_venue_seats(test_venue):
    """Test creating seats for a venue"""
    venue_id = test_venue["venue_id"]

    seat_data = {
        "seats": [
            {"row": "A", "seat_num": 1, "seat_type": "VIP"},
            {"row": "A", "seat_num": 2, "seat_type": "VIP"},
            {"row": "B", "seat_num": 1, "seat_type": "Standard"},
            {"row": "B", "seat_num": 2, "seat_type": "Standard"},
            {"row": "C", "seat_num": 1, "seat_type": "Economy"},
        ]
    }

    response = client.post(f"/venue/{venue_id}/seats", json=seat_data)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 5
    assert data[0]["venue_id"] == venue_id
    assert data[0]["row"] == "A"
    assert data[0]["seat_num"] == 1
    assert data[0]["seat_type"] == "VIP"
    assert data[0]["seat_pos"] == "A-1"


def test_create_venue_seats_invalid_venue():
    """Test creating seats for non-existent venue"""
    seat_data = {"seats": [{"row": "A", "seat_num": 1, "seat_type": "VIP"}]}

    response = client.post("/venue/venue-nonexistent/seats", json=seat_data)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_venue_seats_invalid_seat_type(test_venue):
    """Test creating seats with invalid seat type"""
    venue_id = test_venue["venue_id"]

    seat_data = {"seats": [{"row": "A", "seat_num": 1, "seat_type": "InvalidType"}]}

    response = client.post(f"/venue/{venue_id}/seats", json=seat_data)

    assert response.status_code == 400
    assert "not valid for this venue" in response.json()["detail"]


def test_create_venue_seats_duplicate_seat(test_venue):
    """Test creating duplicate seats"""
    venue_id = test_venue["venue_id"]

    # Create first seat
    seat_data = {"seats": [{"row": "A", "seat_num": 1, "seat_type": "VIP"}]}

    response = client.post(f"/venue/{venue_id}/seats", json=seat_data)
    assert response.status_code == 200

    # Try to create same seat again
    response = client.post(f"/venue/{venue_id}/seats", json=seat_data)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_venue_seats(test_venue):
    """Test getting all seats for a venue"""
    venue_id = test_venue["venue_id"]

    # First create some seats
    seat_data = {
        "seats": [
            {"row": "A", "seat_num": 1, "seat_type": "VIP"},
            {"row": "A", "seat_num": 2, "seat_type": "VIP"},
            {"row": "B", "seat_num": 1, "seat_type": "Standard"},
        ]
    }

    create_response = client.post(f"/venue/{venue_id}/seats", json=seat_data)
    assert create_response.status_code == 200

    # Now get all seats
    response = client.get(f"/venue/{venue_id}/seats")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert all(seat["venue_id"] == venue_id for seat in data)

    # Check that seats are properly formatted
    seat_positions = [seat["seat_pos"] for seat in data]
    assert "A-1" in seat_positions
    assert "A-2" in seat_positions
    assert "B-1" in seat_positions


def test_get_venue_seats_empty_venue(test_venue):
    """Test getting seats for venue with no seats"""
    venue_id = test_venue["venue_id"]

    response = client.get(f"/venue/{venue_id}/seats")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 0


def test_get_venue_seats_invalid_venue():
    """Test getting seats for non-existent venue"""
    response = client.get("/venue/venue-nonexistent/seats")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
