import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user():
    """Test user creation"""
    user_data = {"email": "test@example.com", "phone": "+1234567890"}

    response = client.post("/user", json=user_data)

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == user_data["email"]
    assert data["phone"] == user_data["phone"]
    assert "user-" in data["user_id"]
    assert "created_at" in data


def test_get_user():
    """Test getting a user by ID"""
    # First create a user
    user_data = {"email": "test@example.com", "phone": "+1234567890"}

    create_response = client.post("/user", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()

    # Now get the user
    response = client.get(f"/user/{user['user_id']}")

    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == user["user_id"]
    assert data["email"] == user["email"]
    assert data["phone"] == user["phone"]


def test_get_user_not_found():
    """Test getting a non-existent user"""
    response = client.get("/user/user-nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_user_bookings_empty():
    """Test getting bookings for a user with no bookings"""
    # First create a user
    user_data = {"email": "test@example.com", "phone": "+1234567890"}

    create_response = client.post("/user", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()

    # Get user bookings (should be empty)
    response = client.get(f"/user/{user['user_id']}/bookings")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 0


def test_get_user_bookings_user_not_found():
    """Test getting bookings for non-existent user"""
    response = client.get("/user/user-nonexistent/bookings")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_multiple_users():
    """Test creating multiple users"""
    users_data = [
        {"email": "user1@example.com", "phone": "+1111111111"},
        {"email": "user2@example.com", "phone": "+2222222222"},
        {"email": "user3@example.com", "phone": "+3333333333"},
    ]

    created_users = []
    for user_data in users_data:
        response = client.post("/user", json=user_data)
        assert response.status_code == 200
        created_users.append(response.json())

    # Verify all users have unique IDs
    user_ids = [user["user_id"] for user in created_users]
    assert len(set(user_ids)) == len(user_ids)  # All unique

    # Verify all users can be retrieved
    for user in created_users:
        response = client.get(f"/user/{user['user_id']}")
        assert response.status_code == 200
        assert response.json()["email"] == user["email"]
