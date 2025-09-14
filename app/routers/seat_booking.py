from typing import List

from fastapi import APIRouter, HTTPException, Path

from app.database import db_client
from app.models.event import (BookingCancelRequest, BookingResponse,
                              PaymentConfirmRequest)
from app.utils import (create_booking_transaction_items,
                       create_cancellation_transaction_items,
                       create_enhanced_booking_transaction_items,
                       create_enhanced_cancellation_transaction_items,
                       generate_booking_id, get_current_timestamp)

router = APIRouter(tags=["seat-booking"])


@router.post("/{holding_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    holding_id: str = Path(..., description="The holding ID"),
    payment_request: PaymentConfirmRequest = None,
):
    """Confirm a booking by converting held seats to booked seats with comprehensive edge case handling"""
    try:
        # Validate payment status
        if not payment_request or payment_request.payment_status not in [
            "successful",
            "failed",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Payment status must be 'successful' or 'failed'",
            )

        # If payment failed, we don't need to do anything (hold will expire)
        if payment_request.payment_status == "failed":
            raise HTTPException(
                status_code=400, detail="Payment failed. Booking not confirmed."
            )

        # Find the holding record by scanning for holding_id
        # We need to scan because holdings are stored with event_id as pk
        holdings_result = db_client.scan_items(
            filter_expression="holding_id = :holding_id AND begins_with(sk, :holding_prefix)",
            expression_values={
                ":holding_id": holding_id,
                ":holding_prefix": "holding-",
            },
        )

        if holdings_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find holding: {holdings_result['error']}",
            )

        if holdings_result["count"] == 0:
            raise HTTPException(
                status_code=404, detail=f"Holding with ID {holding_id} not found"
            )

        # Handle multiple holdings with same ID (shouldn't happen but safety check)
        if holdings_result["count"] > 1:
            # Log the issue and use the first one
            print(
                f"Warning: Multiple holdings found with ID {holding_id}, using the first one"
            )
            holding_record = holdings_result["items"][0]
        else:
            holding_record = holdings_result["items"][0]

        # Extract data with safe defaults
        event_id = holding_record.get("event_id", "")
        user_id = holding_record.get("user_id", "")
        seats = holding_record.get("seats", [])

        # Validate required fields
        if not event_id:
            raise HTTPException(
                status_code=500, detail="Holding record missing event_id"
            )
        if not user_id:
            raise HTTPException(
                status_code=500, detail="Holding record missing user_id"
            )
        if not seats:
            raise HTTPException(status_code=500, detail="Holding record missing seats")

        # Validate event still exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail="Event no longer exists. Booking cannot be confirmed.",
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error validating event: {event_result['error']}",
            )

        # Validate user still exists
        user_result = db_client.get_item(user_id, "USER")
        if user_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail="User no longer exists. Booking cannot be confirmed.",
            )
        elif user_result["status"] == "error":
            raise HTTPException(
                status_code=500, detail=f"Error validating user: {user_result['error']}"
            )

        # Verify the holding is still valid (not expired)
        created_at = holding_record["created_at"]
        ttl = holding_record["ttl"]

        # Check if hold has expired
        from app.utils import is_hold_expired

        if is_hold_expired(ttl, created_at):
            raise HTTPException(
                status_code=410,
                detail="Holding has expired. Please try holding seats again.",
            )

        # Validate all seats are still held by this holding
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to validate seat states: {seats_result['error']}",
            )

        # Create seat map for validation
        seat_map = {}
        for item in seats_result["items"]:
            if item.get("sk") != "EVENT":  # Skip the event object itself
                seat_map[item.get("seat_pos")] = item

        # Validate each seat is still held by this holding
        invalid_seats = []
        for seat_pos in seats:
            if seat_pos not in seat_map:
                invalid_seats.append(f"{seat_pos} (seat not found)")
                continue

            seat = seat_map[seat_pos]
            seat_state = seat.get("seat_state")
            seat_holding_id = seat.get("holding_id")

            if seat_state != "held":
                invalid_seats.append(f"{seat_pos} (state: {seat_state})")
            elif seat_holding_id != holding_id:
                invalid_seats.append(f"{seat_pos} (held by different holding)")

        if invalid_seats:
            raise HTTPException(
                status_code=409,
                detail=f"Seats are no longer available for confirmation: {invalid_seats}",
            )

        # Generate booking ID
        booking_id = generate_booking_id()

        # Create enhanced transaction items for confirming booking
        transact_items = create_enhanced_booking_transaction_items(
            event_id,
            booking_id,
            holding_id,
            user_id,
            seats,
            payment_request.payment_status,
        )

        # Execute transaction
        transaction_result = db_client.transact_write(transact_items)

        if transaction_result["status"] == "error":
            # Check specific error types for better error messages
            error_str = str(transaction_result["error"])
            if "ConditionalCheckFailed" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="One or more seats are no longer held by this holding. Please try holding seats again.",
                )
            elif "TransactionCanceled" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Transaction was cancelled due to concurrent modifications. Please try again.",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to confirm booking: {transaction_result['error']}",
                )

        # Update event analytics (non-blocking)
        try:
            # Increment successful bookings
            db_client.update_item_conditional(
                event_id,
                "EVENT",
                "ADD successful_bookings :inc",
                "attribute_exists(pk)",
                {":inc": 1},
            )
            # Increment seats sold
            db_client.update_item_conditional(
                event_id,
                "EVENT",
                "ADD seats_sold :inc",
                "attribute_exists(pk)",
                {":inc": len(seats)},
            )
        except Exception:
            # Analytics update failure shouldn't break the booking
            pass

        return BookingResponse(
            booking_id=booking_id,
            event_id=event_id,
            user_id=user_id,
            seats=seats,
            booking_date=get_current_timestamp(),
            state="confirmed",
            payment_status=payment_request.payment_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{booking_id}/cancel", response_model=dict)
async def cancel_booking(
    booking_id: str = Path(..., description="The booking ID"),
    cancel_request: BookingCancelRequest = None,
):
    """Cancel a booking and free the seats with comprehensive validation"""
    try:
        # Find the booking record by scanning for booking_id
        bookings_result = db_client.scan_items(
            filter_expression="booking_id = :booking_id",
            expression_values={":booking_id": booking_id},
        )

        if bookings_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find booking: {bookings_result['error']}",
            )

        if bookings_result["count"] == 0:
            raise HTTPException(
                status_code=404, detail=f"Booking with ID {booking_id} not found"
            )

        # Handle multiple bookings with same ID (shouldn't happen but safety check)
        if bookings_result["count"] > 1:
            # Log the issue and use the first one
            print(
                f"Warning: Multiple bookings found with ID {booking_id}, using the first one"
            )
            booking_record = bookings_result["items"][0]
        else:
            booking_record = bookings_result["items"][0]

        # Extract data with safe defaults
        event_id = booking_record.get("event_id", "")
        user_id = booking_record.get("user_id", "")
        seats = booking_record.get("seats", [])

        # Validate required fields
        if not event_id:
            raise HTTPException(
                status_code=500, detail="Booking record missing event_id"
            )
        if not user_id:
            raise HTTPException(
                status_code=500, detail="Booking record missing user_id"
            )
        if not seats:
            raise HTTPException(status_code=500, detail="Booking record missing seats")

        # Validate event still exists
        event_result = db_client.get_item(event_id, "EVENT")
        if event_result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail="Event no longer exists. Booking cannot be cancelled.",
            )
        elif event_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Error validating event: {event_result['error']}",
            )

        # Check if booking is already cancelled
        if booking_record["state"] == "cancelled":
            raise HTTPException(status_code=400, detail="Booking is already cancelled")

        # Validate all seats are still booked by this booking
        seats_result = db_client.query_items(event_id)
        if seats_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to validate seat states: {seats_result['error']}",
            )

        # Create seat map for validation
        seat_map = {}
        for item in seats_result["items"]:
            if item.get("sk") != "EVENT":  # Skip the event object itself
                seat_map[item.get("seat_pos")] = item

        # Validate each seat is still booked by this booking
        invalid_seats = []
        for seat_pos in seats:
            if seat_pos not in seat_map:
                invalid_seats.append(f"{seat_pos} (seat not found)")
                continue

            seat = seat_map[seat_pos]
            seat_state = seat.get("seat_state")
            seat_booking_id = seat.get("booking_id")

            if seat_state != "booked":
                invalid_seats.append(f"{seat_pos} (state: {seat_state})")
            elif seat_booking_id != booking_id:
                invalid_seats.append(f"{seat_pos} (booked by different booking)")

        if invalid_seats:
            raise HTTPException(
                status_code=409,
                detail=f"Seats are no longer available for cancellation: {invalid_seats}",
            )

        # Create enhanced transaction items for cancelling booking
        transact_items = create_enhanced_cancellation_transaction_items(
            event_id, booking_id, seats, booking_record["sk"]
        )

        # Execute transaction
        transaction_result = db_client.transact_write(transact_items)

        if transaction_result["status"] == "error":
            # Check specific error types for better error messages
            error_str = str(transaction_result["error"])
            if "ConditionalCheckFailed" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="One or more seats are no longer booked by this booking. Booking may have already been cancelled.",
                )
            elif "TransactionCanceled" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Transaction was cancelled due to concurrent modifications. Please try again.",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to cancel booking: {transaction_result['error']}",
                )

        # Update event analytics (non-blocking)
        try:
            # Increment cancellations
            db_client.update_item_conditional(
                event_id,
                "EVENT",
                "ADD cancellations :inc",
                "attribute_exists(pk)",
                {":inc": 1},
            )
            # Decrement seats sold
            db_client.update_item_conditional(
                event_id,
                "EVENT",
                "ADD seats_sold :inc",
                "attribute_exists(pk)",
                {":inc": -len(seats)},
            )
        except Exception:
            # Analytics update failure shouldn't break the cancellation
            pass

        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "event_id": event_id,
            "user_id": user_id,
            "seats_freed": seats,
            "cancelled_at": get_current_timestamp(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
