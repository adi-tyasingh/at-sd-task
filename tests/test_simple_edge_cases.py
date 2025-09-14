import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def test_setup():
    """Create test data for edge case tests"""
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
        ]
    }

    seats_response = client.post(f"/venue/{venue['venue_id']}/seats", json=seat_data)
    assert seats_response.status_code == 200

    # Create user
    user_data = {"email": "test@example.com", "phone": "1234567890"}

    user_response = client.post("/user", json=user_data)
    assert user_response.status_code == 200
    user = user_response.json()

    # Create event (this will create event seats)
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Test Concert",
        "start_time": "2024-12-31T20:00:00Z",
        "duration": 180,
        "artists": ["Artist 1"],
        "tags": ["music"],
        "description": "A test concert event",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    event_response = client.post("/events", json=event_data)
    assert event_response.status_code == 200
    event = event_response.json()

    return {"venue": venue, "user": user, "event": event}


class TestSimpleEdgeCases:
    """Test basic edge cases that don't require confirmation"""

    def test_hold_seats_success(self, test_setup):
        """Test successful seat holding"""
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1", "A-2"]}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200

        holding = hold_response.json()
        assert holding["holding_id"] is not None
        assert holding["seats_held"] == ["A-1", "A-2"]
        assert holding["hold_ttl"] == 180

    def test_hold_nonexistent_seats(self, test_setup):
        """Test holding non-existent seats"""
        hold_data = {
            "user_id": test_setup["user"]["user_id"],
            "seats": ["Z-999"],  # Non-existent seat
        }

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 400
        assert "does not exist" in hold_response.json()["detail"]

    def test_hold_already_held_seats(self, test_setup):
        """Test holding already held seats"""
        # First hold
        hold_data1 = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response1 = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data1
        )
        assert hold_response1.status_code == 200

        # Second hold of same seat
        hold_data2 = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response2 = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data2
        )
        assert hold_response2.status_code == 409
        assert "unavailable" in hold_response2.json()["detail"]

    def test_hold_with_nonexistent_user(self, test_setup):
        """Test holding with non-existent user"""
        hold_data = {"user_id": "nonexistent-user-id", "seats": ["A-1"]}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 404
        assert "not found" in hold_response.json()["detail"]

    def test_hold_with_nonexistent_event(self, test_setup):
        """Test holding with non-existent event"""
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response = client.post("/events/nonexistent-event-id/hold", json=hold_data)
        assert hold_response.status_code == 404
        assert "not found" in hold_response.json()["detail"]

    def test_hold_empty_seat_list(self, test_setup):
        """Test holding with empty seat list"""
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": []}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200

        holding = hold_response.json()
        assert holding["seats_held"] == []
        assert holding["holding_id"] == ""

    def test_hold_duplicate_seats(self, test_setup):
        """Test holding with duplicate seats in request"""
        hold_data = {
            "user_id": test_setup["user"]["user_id"],
            "seats": ["A-1", "A-1", "A-2"],  # A-1 is duplicated
        }

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200

        holding = hold_response.json()
        # Should deduplicate
        assert len(holding["seats_held"]) == 2
        assert "A-1" in holding["seats_held"]
        assert "A-2" in holding["seats_held"]

    def test_get_event_seats(self, test_setup):
        """Test getting event seats"""
        seats_response = client.get(f"/events/{test_setup['event']['event_id']}/seats")
        assert seats_response.status_code == 200

        seats = seats_response.json()
        assert len(seats) == 3  # A-1, A-2, B-1

        # Check seat structure
        for seat in seats:
            assert "seat_pos" in seat
            assert "seat_state" in seat
            assert "price" in seat
            assert seat["seat_state"] == "available"

    def test_get_seats_nonexistent_event(self, test_setup):
        """Test getting seats for non-existent event"""
        seats_response = client.get("/events/nonexistent-event-id/seats")
        assert seats_response.status_code == 404
        assert "not found" in seats_response.json()["detail"]

    def test_confirm_nonexistent_holding(self, test_setup):
        """Test confirming non-existent holding"""
        confirm_data = {"payment_status": "successful"}

        confirm_response = client.post(
            "/nonexistent-holding-id/confirm", json=confirm_data
        )
        assert confirm_response.status_code == 404
        assert "not found" in confirm_response.json()["detail"]

    def test_confirm_invalid_payment_status(self, test_setup):
        """Test confirming with invalid payment status"""
        # First hold some seats
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200
        holding = hold_response.json()

        # Try to confirm with invalid payment status
        confirm_data = {"payment_status": "invalid_status"}

        confirm_response = client.post(
            f"/{holding['holding_id']}/confirm", json=confirm_data
        )
        assert confirm_response.status_code == 400
        assert "must be 'successful' or 'failed'" in confirm_response.json()["detail"]

    def test_confirm_payment_failed(self, test_setup):
        """Test confirming with failed payment"""
        # First hold some seats
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200
        holding = hold_response.json()

        # Try to confirm with failed payment
        confirm_data = {"payment_status": "failed"}

        confirm_response = client.post(
            f"/{holding['holding_id']}/confirm", json=confirm_data
        )
        assert confirm_response.status_code == 400
        assert "Payment failed" in confirm_response.json()["detail"]

    def test_cancel_nonexistent_booking(self, test_setup):
        """Test cancelling non-existent booking"""
        cancel_data = {"booking_id": "nonexistent-booking-id"}

        cancel_response = client.post(
            "/nonexistent-booking-id/cancel", json=cancel_data
        )
        assert cancel_response.status_code == 404
        assert "not found" in cancel_response.json()["detail"]

    def test_hold_expiration_after_time(self, test_setup):
        """Test that holds expire after TTL"""
        # Hold seats
        hold_data = {"user_id": test_setup["user"]["user_id"], "seats": ["A-1"]}

        hold_response = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response.status_code == 200
        holding = hold_response.json()

        # Wait for holding to expire (3 minutes + buffer)
        print("Waiting for holding to expire (3 minutes)...")
        time.sleep(185)  # 3 minutes 5 seconds

        # Try to confirm expired holding
        confirm_data = {"payment_status": "successful"}

        confirm_response = client.post(
            f"/{holding['holding_id']}/confirm", json=confirm_data
        )
        assert confirm_response.status_code == 410
        assert "expired" in confirm_response.json()["detail"]

        # Now the same seats should be available for holding again
        hold_response2 = client.post(
            f"/events/{test_setup['event']['event_id']}/hold", json=hold_data
        )
        assert hold_response2.status_code == 200
