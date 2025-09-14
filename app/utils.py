import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.database import db_client


def generate_holding_id() -> str:
    """Generate a unique holding ID"""
    return f"holding-{str(uuid.uuid4())}"


def generate_booking_id() -> str:
    """Generate a unique booking ID"""
    return f"booking-{str(uuid.uuid4())}"


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat()


def get_hold_expiry_time(ttl_seconds: int = 180) -> str:
    """Get hold expiry time (default 180 seconds)"""
    expiry_time = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    return expiry_time.isoformat()


def is_hold_expired(hold_ttl, created_at: str) -> bool:
    """Check if a hold has expired"""
    try:
        # Convert hold_ttl to int if it's a Decimal
        if hasattr(hold_ttl, 'int_value'):
            hold_ttl = hold_ttl.int_value()
        else:
            hold_ttl = int(hold_ttl)
            
        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        expiry_time = created_time + timedelta(seconds=hold_ttl)
        return datetime.utcnow() > expiry_time
    except (ValueError, TypeError, AttributeError):
        return True  # If we can't parse the time, consider it expired


def create_hold_transaction_items(event_id: str, holding_id: str, user_id: str, 
                                 seats: list, ttl: int = 180) -> list:
    """Create transaction items for holding seats"""
    current_time = get_current_timestamp()
    expiry_time = get_hold_expiry_time(ttl)
    
    transact_items = []
    
    # Create holding record
    holding_item = {
        "Put": {
            "TableName": db_client.table_name,
            "Item": {
                "pk": {"S": event_id},
                "sk": {"S": holding_id},
                "holding_id": {"S": holding_id},
                "event_id": {"S": event_id},
                "user_id": {"S": user_id},
                "seats": {"SS": list(seats)},
                "created_at": {"S": current_time},
                "expires_at": {"S": expiry_time},
                "ttl": {"N": str(ttl)}
            }
        }
    }
    transact_items.append(holding_item)
    
    # Update each seat to held state
    for seat_pos in seats:
        seat_item = {
            "Update": {
                "TableName": db_client.table_name,
                "Key": {
                    "pk": {"S": event_id},
                    "sk": {"S": seat_pos}
                },
                "UpdateExpression": "SET seat_state = :state, holding_id = :holding_id, hold_ttl = :ttl",
                "ConditionExpression": "seat_state = :available_state",
                "ExpressionAttributeValues": {
                    ":state": {"S": "held"},
                    ":holding_id": {"S": holding_id},
                    ":ttl": {"N": str(ttl)},
                    ":available_state": {"S": "available"}
                }
            }
        }
        transact_items.append(seat_item)
    
    return transact_items


def create_booking_transaction_items(event_id: str, booking_id: str, holding_id: str, 
                                   user_id: str, seats: list, payment_status: str) -> list:
    """Create transaction items for confirming a booking"""
    current_time = get_current_timestamp()
    
    transact_items = []
    
    # Create booking record
    booking_item = {
        "Put": {
            "TableName": db_client.table_name,
            "Item": {
                "pk": {"S": event_id},
                "sk": {"S": current_time},  # Use timestamp as sort key for ordering
                "booking_id": {"S": booking_id},
                "event_id": {"S": event_id},
                "user_id": {"S": user_id},
                "seats": {"SS": list(seats)},
                "booking_date": {"S": current_time},
                "state": {"S": "confirmed"},
                "payment_status": {"S": payment_status}
            }
        }
    }
    transact_items.append(booking_item)
    
    # Update each seat to booked state
    for seat_pos in seats:
        seat_item = {
            "Update": {
                "TableName": db_client.table_name,
                "Key": {
                    "pk": {"S": event_id},
                    "sk": {"S": seat_pos}
                },
                "UpdateExpression": "SET seat_state = :state, booking_id = :booking_id, holding_id = :null, hold_ttl = :null",
                "ConditionExpression": "seat_state = :held_state AND holding_id = :holding_id",
                "ExpressionAttributeValues": {
                    ":state": {"S": "booked"},
                    ":booking_id": {"S": booking_id},
                    ":null": {"NULL": True},
                    ":held_state": {"S": "held"},
                    ":holding_id": {"S": holding_id}
                }
            }
        }
        transact_items.append(seat_item)
    
    return transact_items


def create_enhanced_booking_transaction_items(event_id: str, booking_id: str, holding_id: str, 
                                            user_id: str, seats: list, payment_status: str) -> list:
    """Create enhanced transaction items for confirming a booking with additional safety checks"""
    current_time = get_current_timestamp()
    
    transact_items = []
    
    # Create booking record with conditional check to prevent duplicate bookings
    booking_item = {
        "Put": {
            "TableName": db_client.table_name,
            "Item": {
                "pk": {"S": event_id},
                "sk": {"S": current_time},  # Use timestamp as sort key for ordering
                "booking_id": {"S": booking_id},
                "event_id": {"S": event_id},
                "user_id": {"S": user_id},
                "seats": {"SS": list(seats)},
                "booking_date": {"S": current_time},
                "state": {"S": "confirmed"},
                "payment_status": {"S": payment_status}
            },
            "ConditionExpression": "attribute_not_exists(booking_id)"  # Prevent duplicate booking IDs
        }
    }
    transact_items.append(booking_item)
    
    # Update each seat to booked state with enhanced conditions
    for seat_pos in seats:
        seat_item = {
            "Update": {
                "TableName": db_client.table_name,
                "Key": {
                    "pk": {"S": event_id},
                    "sk": {"S": seat_pos}
                },
                "UpdateExpression": "SET seat_state = :state, booking_id = :booking_id, holding_id = :null, hold_ttl = :null, updated_at = :updated_at",
                "ConditionExpression": "seat_state = :held_state AND holding_id = :holding_id AND attribute_exists(pk)",
                "ExpressionAttributeValues": {
                    ":state": {"S": "booked"},
                    ":booking_id": {"S": booking_id},
                    ":null": {"NULL": True},
                    ":held_state": {"S": "held"},
                    ":holding_id": {"S": holding_id},
                    ":updated_at": {"S": current_time}
                }
            }
        }
        transact_items.append(seat_item)
    
    # Delete the holding record to prevent reuse
    holding_delete_item = {
        "Delete": {
            "TableName": db_client.table_name,
            "Key": {
                "pk": {"S": event_id},
                "sk": {"S": holding_id}
            },
            "ConditionExpression": "holding_id = :holding_id",
            "ExpressionAttributeValues": {
                ":holding_id": {"S": holding_id}
            }
        }
    }
    transact_items.append(holding_delete_item)
    
    return transact_items


def create_cancellation_transaction_items(event_id: str, booking_id: str, seats: list) -> list:
    """Create transaction items for cancelling a booking"""
    transact_items = []
    
    # Update each seat back to available state
    for seat_pos in seats:
        seat_item = {
            "Update": {
                "TableName": db_client.table_name,
                "Key": {
                    "pk": {"S": event_id},
                    "sk": {"S": seat_pos}
                },
                "UpdateExpression": "SET seat_state = :state, booking_id = :null, holding_id = :null, hold_ttl = :null",
                "ConditionExpression": "seat_state = :booked_state AND booking_id = :booking_id",
                "ExpressionAttributeValues": {
                    ":state": {"S": "available"},
                    ":null": {"NULL": True},
                    ":booked_state": {"S": "booked"},
                    ":booking_id": {"S": booking_id}
                }
            }
        }
        transact_items.append(seat_item)
    
    return transact_items


def create_enhanced_cancellation_transaction_items(event_id: str, booking_id: str, seats: list, booking_sk: str) -> list:
    """Create enhanced transaction items for cancelling a booking with additional safety checks"""
    current_time = get_current_timestamp()
    transact_items = []
    
    # Update each seat back to available state with enhanced conditions
    for seat_pos in seats:
        seat_item = {
            "Update": {
                "TableName": db_client.table_name,
                "Key": {
                    "pk": {"S": event_id},
                    "sk": {"S": seat_pos}
                },
                "UpdateExpression": "SET seat_state = :state, booking_id = :null, holding_id = :null, hold_ttl = :null, updated_at = :updated_at",
                "ConditionExpression": "seat_state = :booked_state AND booking_id = :booking_id AND attribute_exists(pk)",
                "ExpressionAttributeValues": {
                    ":state": {"S": "available"},
                    ":null": {"NULL": True},
                    ":booked_state": {"S": "booked"},
                    ":booking_id": {"S": booking_id},
                    ":updated_at": {"S": current_time}
                }
            }
        }
        transact_items.append(seat_item)
    
    # Update booking state to cancelled
    booking_update_item = {
        "Update": {
            "TableName": db_client.table_name,
            "Key": {
                "pk": {"S": event_id},
                "sk": {"S": booking_sk}
            },
            "UpdateExpression": "SET #state = :state, cancelled_at = :cancelled_at",
            "ConditionExpression": "booking_id = :booking_id AND #state = :confirmed_state",
            "ExpressionAttributeNames": {
                "#state": "state"
            },
            "ExpressionAttributeValues": {
                ":state": {"S": "cancelled"},
                ":booking_id": {"S": booking_id},
                ":confirmed_state": {"S": "confirmed"},
                ":cancelled_at": {"S": current_time}
            }
        }
    }
    transact_items.append(booking_update_item)
    
    return transact_items
