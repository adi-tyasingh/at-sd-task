from datetime import datetime, date
from typing import List, Dict, Any, Optional
import re
from difflib import SequenceMatcher


def parse_date_filter(date_str: str) -> Optional[datetime]:
    """Parse various date formats and return datetime object"""
    if not date_str:
        return None
    
    # Common date formats to try
    date_formats = [
        "%Y-%m-%d",           # 2024-12-25
        "%d-%m-%Y",           # 25-12-2024
        "%m/%d/%Y",           # 12/25/2024
        "%d/%m/%Y",           # 25/12/2024
        "%Y-%m-%d %H:%M",     # 2024-12-25 19:00
        "%Y-%m-%dT%H:%M:%S",  # 2024-12-25T19:00:00
        "%Y-%m-%dT%H:%M:%SZ", # 2024-12-25T19:00:00Z
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If no format matches, try to parse as ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        return None


def similarity_score(a: str, b: str) -> float:
    """Calculate similarity score between two strings (0-1)"""
    if not a or not b:
        return 0.0
    
    # Convert to lowercase for case-insensitive comparison
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    
    # Exact match
    if a_lower == b_lower:
        return 1.0
    
    # Check if one contains the other
    if a_lower in b_lower or b_lower in a_lower:
        return 0.8
    
    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, a_lower, b_lower).ratio()


def find_similar_items(search_term: str, items: List[str], threshold: float = 0.3) -> List[str]:
    """Find items similar to search term above threshold"""
    if not search_term or not items:
        return []
    
    similar_items = []
    for item in items:
        score = similarity_score(search_term, item)
        if score >= threshold:
            similar_items.append(item)
    
    # Sort by similarity score (highest first)
    similar_items.sort(key=lambda x: similarity_score(search_term, x), reverse=True)
    return similar_items


def filter_events_by_date(events: List[Dict[str, Any]], date_filter: str, filter_type: str = "after") -> List[Dict[str, Any]]:
    """Filter events by date"""
    if not date_filter:
        return events
    
    filter_date = parse_date_filter(date_filter)
    if not filter_date:
        return events
    
    # Make filter_date timezone-aware (UTC)
    if filter_date.tzinfo is None:
        filter_date = filter_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
    
    filtered_events = []
    for event in events:
        try:
            event_time_str = event["start_time"]
            # Handle different timezone formats
            if event_time_str.endswith('Z'):
                event_date = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
            elif '+' in event_time_str or event_time_str.endswith('00:00'):
                event_date = datetime.fromisoformat(event_time_str)
            else:
                # Assume UTC if no timezone info
                event_date = datetime.fromisoformat(event_time_str).replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            if filter_type == "after" and event_date >= filter_date:
                filtered_events.append(event)
            elif filter_type == "before" and event_date <= filter_date:
                filtered_events.append(event)
            elif filter_type == "on" and event_date.date() == filter_date.date():
                filtered_events.append(event)
        except (ValueError, KeyError):
            continue
    
    return filtered_events


def filter_events_by_artists(events: List[Dict[str, Any]], artist_query: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """Filter events by artist similarity"""
    if not artist_query:
        return events
    
    filtered_events = []
    for event in events:
        artists = event.get("artists", [])
        if not artists:
            continue
        
        # Check if any artist matches the query
        similar_artists = find_similar_items(artist_query, artists, threshold)
        if similar_artists:
            filtered_events.append(event)
    
    return filtered_events


def filter_events_by_tags(events: List[Dict[str, Any]], tag_query: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """Filter events by tag similarity"""
    if not tag_query:
        return events
    
    filtered_events = []
    for event in events:
        tags = event.get("tags", [])
        if not tags:
            continue
        
        # Check if any tag matches the query
        similar_tags = find_similar_items(tag_query, tags, threshold)
        if similar_tags:
            filtered_events.append(event)
    
    return filtered_events


def filter_events_by_city(events: List[Dict[str, Any]], city_query: str, venue_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter events by city with venue lookup"""
    if not city_query:
        return events
    
    filtered_events = []
    for event in events:
        venue_id = event.get("venue_id")
        if not venue_id:
            continue
        
        # Get venue from cache or fetch if not cached
        venue = venue_cache.get(venue_id)
        if not venue:
            continue
        
        venue_city = venue.get("city", "").lower()
        if city_query.lower() in venue_city or similarity_score(city_query, venue_city) >= 0.3:
            filtered_events.append(event)
    
    return filtered_events


def filter_events_by_price_range(events: List[Dict[str, Any]], min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """Filter events by price range"""
    if min_price is None and max_price is None:
        return events
    
    filtered_events = []
    for event in events:
        seat_prices = event.get("seat_type_prices", {})
        if not seat_prices:
            continue
        
        # Get the minimum price for this event
        event_min_price = min(seat_prices.values()) if seat_prices else 0
        
        # Check if price is within range
        if min_price is not None and event_min_price < min_price:
            continue
        if max_price is not None and event_min_price > max_price:
            continue
        
        filtered_events.append(event)
    
    return filtered_events


def search_events(events: List[Dict[str, Any]], search_query: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """Search events by name, description, artists, and tags"""
    if not search_query:
        return events
    
    filtered_events = []
    for event in events:
        # Search in name, description, artists, and tags
        searchable_text = [
            event.get("name", ""),
            event.get("description", ""),
            " ".join(event.get("artists", [])),
            " ".join(event.get("tags", []))
        ]
        
        combined_text = " ".join(searchable_text).lower()
        if similarity_score(search_query, combined_text) >= threshold:
            filtered_events.append(event)
    
    return filtered_events


def sort_events(events: List[Dict[str, Any]], sort_by: str = "date", order: str = "asc") -> List[Dict[str, Any]]:
    """Sort events by various criteria"""
    if not events:
        return events
    
    reverse = order.lower() == "desc"
    
    if sort_by == "date":
        events.sort(key=lambda x: x.get("start_time", ""), reverse=reverse)
    elif sort_by == "name":
        events.sort(key=lambda x: x.get("name", "").lower(), reverse=reverse)
    elif sort_by == "price":
        events.sort(key=lambda x: min(x.get("seat_type_prices", {}).values()) if x.get("seat_type_prices") else 0, reverse=reverse)
    
    return events
