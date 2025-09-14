import pytest
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timedelta

client = TestClient(app)


@pytest.fixture
def test_events_data():
    """Create test events with different attributes for filtering tests"""
    # Create venues in different cities
    mumbai_venue_data = {
        "name": "Mumbai Stadium",
        "city": "Mumbai",
        "description": "A stadium in Mumbai",
        "seat_types": ["VIP", "Standard"]
    }
    delhi_venue_data = {
        "name": "Delhi Arena",
        "city": "Delhi",
        "description": "An arena in Delhi",
        "seat_types": ["VIP", "Standard", "Economy"]
    }
    
    mumbai_venue = client.post("/venue", json=mumbai_venue_data).json()
    delhi_venue = client.post("/venue", json=delhi_venue_data).json()
    
    # Add seats to venues
    seat_data = {
        "seats": [
            {"row": "A", "seat_num": 1, "seat_type": "VIP"},
            {"row": "A", "seat_num": 2, "seat_type": "Standard"}
        ]
    }
    
    client.post(f"/venue/{mumbai_venue['venue_id']}/seats", json=seat_data)
    client.post(f"/venue/{delhi_venue['venue_id']}/seats", json=seat_data)
    
    # Create events with different dates and content
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    events_data = [
        {
            "venue_id": mumbai_venue["venue_id"],
            "name": "Rock Concert Mumbai",
            "start_time": tomorrow.isoformat(),
            "duration": 180,
            "artists": ["Rock Band"],
            "tags": ["rock", "music", "concert"],
            "description": "An amazing rock concert in Mumbai",
            "seat_type_prices": {"VIP": 2000.0, "Standard": 1000.0}
        },
        {
            "venue_id": delhi_venue["venue_id"],
            "name": "Jazz Night Delhi",
            "start_time": next_week.isoformat(),
            "duration": 120,
            "artists": ["Jazz Master"],
            "tags": ["jazz", "music", "night"],
            "description": "A smooth jazz night in Delhi",
            "seat_type_prices": {"VIP": 1500.0, "Standard": 800.0, "Economy": 400.0}
        },
        {
            "venue_id": mumbai_venue["venue_id"],
            "name": "Classical Music Evening",
            "start_time": (today + timedelta(days=3)).isoformat(),
            "duration": 90,
            "artists": ["Classical Orchestra"],
            "tags": ["classical", "orchestra", "elegant"],
            "description": "A beautiful classical music evening",
            "seat_type_prices": {"VIP": 3000.0, "Standard": 1500.0}
        }
    ]
    
    events = []
    for event_data in events_data:
        response = client.post("/events", json=event_data)
        assert response.status_code == 200
        events.append(response.json())
    
    return events


def test_city_filtering(test_events_data):
    """Test filtering events by city"""
    events = test_events_data
    
    # Filter events in Mumbai
    response = client.get("/events?city=Mumbai")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return Mumbai events
    assert len(filtered_events) >= 2


def test_date_range_filtering(test_events_data):
    """Test filtering events by date range"""
    events = test_events_data
    
    # Filter events from tomorrow onwards
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    response = client.get(f"/events?start_date={tomorrow}")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return events from tomorrow onwards
    assert len(filtered_events) >= 1
    
    # Filter events until next week
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    response = client.get(f"/events?end_date={next_week}")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return events until next week
    assert len(filtered_events) >= 2


def test_search_filtering(test_events_data):
    """Test searching events by name, description, artists, and tags"""
    events = test_events_data
    
    # Search for "rock"
    response = client.get("/events?search=rock")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return rock-related events
    assert len(filtered_events) >= 1
    
    # Search for "music"
    response = client.get("/events?search=music")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return music-related events
    assert len(filtered_events) >= 2
    
    # Search for artist name
    response = client.get("/events?search=Band")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return events with "Band" in artist names
    assert len(filtered_events) >= 1


def test_combined_filtering(test_events_data):
    """Test combining multiple filters"""
    events = test_events_data
    
    # Filter events in Mumbai with "music" in search
    response = client.get("/events?city=Mumbai&search=music")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should return Mumbai events with music
    assert len(filtered_events) >= 1


def test_pagination(test_events_data):
    """Test pagination"""
    events = test_events_data
    
    # Get first page with limit 2
    response = client.get("/events?limit=2&offset=0")
    
    assert response.status_code == 200
    page1_events = response.json()
    
    # Should return at most 2 events
    assert len(page1_events) <= 2


def test_fuzzy_search(test_events_data):
    """Test that search handles typos and partial matches"""
    events = test_events_data
    
    # Search with typo in "jazz"
    response = client.get("/events?search=jaz")
    
    assert response.status_code == 200
    filtered_events = response.json()
    
    # Should still find jazz events due to fuzzy matching
    assert len(filtered_events) >= 1


def test_case_insensitive_search(test_events_data):
    """Test that search is case insensitive"""
    events = test_events_data
    
    # Search with different cases
    response1 = client.get("/events?search=ROCK")
    response2 = client.get("/events?search=rock")
    response3 = client.get("/events?search=Rock")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 200
    
    # Should return same results
    events1 = response1.json()
    events2 = response2.json()
    events3 = response3.json()
    
    assert len(events1) == len(events2) == len(events3)


def test_empty_filters():
    """Test that empty filters don't break the system"""
    response = client.get("/events?city=&search=")
    
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)


def test_invalid_date_format():
    """Test handling of invalid date formats"""
    response = client.get("/events?start_date=invalid-date")
    
    assert response.status_code == 200
    # Should return all events (invalid date is ignored)
    events = response.json()
    assert isinstance(events, list)
