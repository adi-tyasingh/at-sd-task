import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def test_event_with_bookings():
    """Create a test event with bookings for analytics tests"""
    # Create venue
    venue_data = {
        "name": "Analytics Stadium",
        "city": "Mumbai",
        "description": "A stadium for analytics testing",
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

    # Create users
    users = []
    for i in range(3):
        user_data = {"email": f"analytics{i}@example.com", "phone": f"123456789{i}"}
        user_response = client.post("/user", json=user_data)
        assert user_response.status_code == 200
        users.append(user_response.json())

    # Create event
    event_data = {
        "venue_id": venue["venue_id"],
        "name": "Analytics Concert",
        "start_time": "2024-12-31T20:00:00Z",
        "duration": 180,
        "artists": ["Analytics Artist"],
        "tags": ["analytics", "testing"],
        "description": "A concert for analytics testing",
        "seat_type_prices": {"VIP": 1000.0, "Standard": 500.0, "Economy": 200.0},
    }

    event_response = client.post("/events", json=event_data)
    assert event_response.status_code == 200
    event = event_response.json()

    # Create some bookings
    bookings = []

    # Booking 1: Hold and confirm A-1 (VIP)
    hold_data1 = {"user_id": users[0]["user_id"], "seats": ["A-1"]}
    hold_response1 = client.post(f"/events/{event['event_id']}/hold", json=hold_data1)
    assert hold_response1.status_code == 200
    holding1 = hold_response1.json()

    confirm_data1 = {"payment_status": "successful"}
    confirm_response1 = client.post(
        f"/{holding1['holding_id']}/confirm", json=confirm_data1
    )
    assert confirm_response1.status_code == 200
    bookings.append(confirm_response1.json())

    # Booking 2: Hold and confirm B-1, B-2 (Standard)
    hold_data2 = {"user_id": users[1]["user_id"], "seats": ["B-1", "B-2"]}
    hold_response2 = client.post(f"/events/{event['event_id']}/hold", json=hold_data2)
    assert hold_response2.status_code == 200
    holding2 = hold_response2.json()

    confirm_data2 = {"payment_status": "successful"}
    confirm_response2 = client.post(
        f"/{holding2['holding_id']}/confirm", json=confirm_data2
    )
    assert confirm_response2.status_code == 200
    bookings.append(confirm_response2.json())

    # Booking 3: Hold C-1 (Economy) but don't confirm (will be held)
    hold_data3 = {"user_id": users[2]["user_id"], "seats": ["C-1"]}
    hold_response3 = client.post(f"/events/{event['event_id']}/hold", json=hold_data3)
    assert hold_response3.status_code == 200
    holding3 = hold_response3.json()

    return {
        "venue": venue,
        "users": users,
        "event": event,
        "bookings": bookings,
        "holdings": [holding1, holding2, holding3],
    }


class TestAnalytics:
    """Test analytics endpoints"""

    def test_get_event_analytics(self, test_event_with_bookings):
        """Test getting comprehensive event analytics"""
        event = test_event_with_bookings["event"]

        response = client.get(f"/events/{event['event_id']}/analytics")
        assert response.status_code == 200

        analytics = response.json()

        # Verify basic event information
        assert analytics["event_id"] == event["event_id"]
        assert analytics["event_name"] == "Analytics Concert"
        assert analytics["venue_id"] == test_event_with_bookings["venue"]["venue_id"]
        assert analytics["venue_name"] == "Analytics Stadium"

        # Verify seat counts
        assert analytics["total_seats"] == 5
        assert analytics["seats_available"] == 0  # A-1, B-1, B-2 booked, C-1 held
        assert analytics["seats_held"] == 1  # C-1
        assert analytics["seats_booked"] == 3  # A-1, B-1, B-2
        assert analytics["seats_sold"] == 3

        # Verify capacity utilization
        expected_utilization = (3 / 5) * 100  # 3 booked out of 5 total
        assert analytics["capacity_utilization"] == expected_utilization

        # Verify booking metrics
        assert analytics["total_bookings"] == 2  # Only confirmed bookings
        assert analytics["successful_bookings"] == 2
        assert analytics["cancelled_bookings"] == 0

        # Verify revenue calculation
        expected_revenue = (
            1000.0 + 500.0 + 500.0
        )  # A-1 (VIP) + B-1 (Standard) + B-2 (Standard)
        assert analytics["revenue_generated"] == expected_revenue

        # Verify average booking value
        expected_avg = expected_revenue / 2  # 2 bookings
        assert analytics["average_booking_value"] == expected_avg

        # Verify event details
        assert analytics["artists"] == ["Analytics Artist"]
        assert analytics["tags"] == ["analytics", "testing"]
        assert analytics["duration"] == 180

    def test_get_event_analytics_nonexistent_event(self, test_event_with_bookings):
        """Test getting analytics for non-existent event"""
        response = client.get("/events/nonexistent-event-id/analytics")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_seat_analytics(self, test_event_with_bookings):
        """Test getting detailed seat analytics"""
        event = test_event_with_bookings["event"]

        response = client.get(f"/events/{event['event_id']}/seats/analytics")
        assert response.status_code == 200

        seat_analytics = response.json()
        assert len(seat_analytics) == 5  # All 5 seats

        # Check seat states
        booked_seats = [s for s in seat_analytics if s["seat_state"] == "booked"]
        held_seats = [s for s in seat_analytics if s["seat_state"] == "held"]
        available_seats = [s for s in seat_analytics if s["seat_state"] == "available"]

        assert len(booked_seats) == 3  # A-1, B-1, B-2
        assert len(held_seats) == 1  # C-1
        assert len(available_seats) == 1  # A-2

        # Verify specific seat details
        a1_seat = next(s for s in seat_analytics if s["seat_pos"] == "A-1")
        assert a1_seat["seat_type"] == "VIP"
        assert a1_seat["price"] == 1000.0
        assert a1_seat["booking_id"] is not None

        c1_seat = next(s for s in seat_analytics if s["seat_pos"] == "C-1")
        assert c1_seat["seat_type"] == "Economy"
        assert c1_seat["price"] == 200.0
        assert c1_seat["holding_id"] is not None

    def test_get_seat_analytics_with_filters(self, test_event_with_bookings):
        """Test getting seat analytics with filters"""
        event = test_event_with_bookings["event"]

        # Filter by seat type
        response = client.get(
            f"/events/{event['event_id']}/seats/analytics?seat_type=VIP"
        )
        assert response.status_code == 200

        vip_seats = response.json()
        assert len(vip_seats) == 2  # A-1, A-2
        for seat in vip_seats:
            assert seat["seat_type"] == "VIP"

        # Filter by seat state
        response = client.get(
            f"/events/{event['event_id']}/seats/analytics?seat_state=booked"
        )
        assert response.status_code == 200

        booked_seats = response.json()
        assert len(booked_seats) == 3  # A-1, B-1, B-2
        for seat in booked_seats:
            assert seat["seat_state"] == "booked"

    def test_get_booking_analytics(self, test_event_with_bookings):
        """Test getting detailed booking analytics"""
        event = test_event_with_bookings["event"]

        response = client.get(f"/events/{event['event_id']}/bookings/analytics")
        assert response.status_code == 200

        booking_analytics = response.json()
        assert len(booking_analytics) == 2  # Only confirmed bookings

        # Verify booking details
        for booking in booking_analytics:
            assert booking["event_id"] == event["event_id"]
            assert booking["state"] == "confirmed"
            assert booking["payment_status"] == "successful"
            assert booking["total_amount"] > 0
            assert booking["seat_count"] > 0

        # Check specific booking amounts
        a1_booking = next(b for b in booking_analytics if "A-1" in b["seats"])
        assert a1_booking["total_amount"] == 1000.0  # VIP price
        assert a1_booking["seat_count"] == 1

        b_booking = next(b for b in booking_analytics if "B-1" in b["seats"])
        assert b_booking["total_amount"] == 1000.0  # 2 Standard seats
        assert b_booking["seat_count"] == 2

    def test_get_booking_analytics_with_filters(self, test_event_with_bookings):
        """Test getting booking analytics with filters"""
        event = test_event_with_bookings["event"]

        # Filter by state
        response = client.get(
            f"/events/{event['event_id']}/bookings/analytics?state=confirmed"
        )
        assert response.status_code == 200

        confirmed_bookings = response.json()
        assert len(confirmed_bookings) == 2
        for booking in confirmed_bookings:
            assert booking["state"] == "confirmed"

    def test_get_revenue_analytics(self, test_event_with_bookings):
        """Test getting revenue analytics"""
        event = test_event_with_bookings["event"]

        response = client.get(f"/events/{event['event_id']}/revenue")
        assert response.status_code == 200

        revenue = response.json()
        assert revenue["event_id"] == event["event_id"]
        assert revenue["total_revenue"] == 2000.0  # 1000 + 500 + 500
        assert revenue["currency"] == "USD"

    def test_get_revenue_analytics_by_seat_type(self, test_event_with_bookings):
        """Test getting revenue analytics broken down by seat type"""
        event = test_event_with_bookings["event"]

        response = client.get(f"/events/{event['event_id']}/revenue?by_seat_type=true")
        assert response.status_code == 200

        revenue = response.json()
        assert revenue["event_id"] == event["event_id"]
        assert revenue["total_revenue"] == 2000.0

        # Check breakdown by seat type
        assert "revenue_by_seat_type" in revenue
        breakdown = revenue["revenue_by_seat_type"]
        assert breakdown["VIP"] == 1000.0  # A-1
        assert breakdown["Standard"] == 1000.0  # B-1 + B-2
        assert breakdown["Economy"] == 0.0  # C-1 is held, not booked

    def test_analytics_with_cancelled_booking(self, test_event_with_bookings):
        """Test analytics with a cancelled booking"""
        event = test_event_with_bookings["event"]
        bookings = test_event_with_bookings["bookings"]

        # Cancel one booking
        cancel_data = {"booking_id": bookings[0]["booking_id"]}
        cancel_response = client.post(
            f"/{bookings[0]['booking_id']}/cancel", json=cancel_data
        )
        assert cancel_response.status_code == 200

        # Get updated analytics
        response = client.get(f"/events/{event['event_id']}/analytics")
        assert response.status_code == 200

        analytics = response.json()

        # Verify updated counts
        assert analytics["seats_available"] == 1  # A-1 is now available
        assert analytics["seats_booked"] == 2  # Only B-1, B-2
        assert analytics["seats_sold"] == 2
        assert analytics["cancelled_bookings"] == 1
        assert analytics["successful_bookings"] == 1  # Only one active booking

        # Verify updated revenue
        expected_revenue = 500.0 + 500.0  # Only B-1 + B-2
        assert analytics["revenue_generated"] == expected_revenue

    def test_analytics_pagination(self, test_event_with_bookings):
        """Test analytics pagination"""
        event = test_event_with_bookings["event"]

        # Test booking analytics pagination
        response = client.get(
            f"/events/{event['event_id']}/bookings/analytics?limit=1&offset=0"
        )
        assert response.status_code == 200

        bookings = response.json()
        assert len(bookings) == 1  # Limited to 1

        # Test with offset
        response = client.get(
            f"/events/{event['event_id']}/bookings/analytics?limit=1&offset=1"
        )
        assert response.status_code == 200

        bookings = response.json()
        assert len(bookings) == 1  # Second booking

    def test_analytics_error_handling(self, test_event_with_bookings):
        """Test analytics error handling"""
        # Test with invalid event ID
        response = client.get("/events/invalid-id/analytics")
        assert response.status_code == 404

        # Test with invalid parameters
        event = test_event_with_bookings["event"]
        response = client.get(
            f"/events/{event['event_id']}/seats/analytics?seat_state=invalid"
        )
        assert response.status_code == 200  # Should return empty list

        response = client.get(
            f"/events/{event['event_id']}/bookings/analytics?state=invalid"
        )
        assert response.status_code == 200  # Should return empty list

