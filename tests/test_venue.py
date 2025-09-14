import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_venue():
    """Test venue creation endpoint"""
    venue_data = {
        "name": "Test Arena",
        "city": "Mumbai",
        "description": "A beautiful test venue",
        "seat_types": ["VIP", "Standard", "Economy"],
    }

    response = client.post("/venue/", json=venue_data)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == venue_data["name"]
    assert data["city"] == venue_data["city"]
    assert data["description"] == venue_data["description"]
    assert data["seat_types"] == venue_data["seat_types"]
    assert "venue-" in data["venue_id"]
    assert "created_at" in data


def test_get_venues():
    """Test get venues endpoint"""
    response = client.get("/venue/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_get_venues_by_city():
    """Test get venues filtered by city"""
    response = client.get("/venue/?city=Mumbai")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    # All returned venues should be from Mumbai
    for venue in data:
        assert venue["city"].lower() == "mumbai"
