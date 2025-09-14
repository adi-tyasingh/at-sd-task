# Evently - Detailed Specifications

## Database Schema Design

### DynamoDB Table Structure
All entities are stored in a single DynamoDB table using partition key (pk) and sort key (sk) for organization.

#### Entity Schemas:

**Venues:**
- pk: `venue-{id}` (e.g., `venue-00001`)
- sk: `"VENUE"`
- Attributes: name, city, description, venue_id

**Seats (Venue-level):**
- pk: `venue-{id}` (e.g., `venue-00001`)
- sk: `{seat-pos}` (e.g., `A-1`, `B-15`)
- Attributes: row, seat_num, seat_type, venue_id

**Events:**
- pk: `event-{id}` (e.g., `event-00001`)
- sk: `"EVENT"`
- Attributes: venue_id, name, start_time, duration, artists, tags, description, seat_type_prices

**Event-Seats:**
- pk: `event-{id}` (e.g., `event-00001`)
- sk: `{seat-pos}` (e.g., `A-1`, `B-15`)
- Attributes: seat_state, booking_id, holding_id, hold_ttl, price, row, seat_num, seat_type

**Bookings:**
- pk: `event-{id}` (e.g., `event-00001`)
- sk: `{booking-time}` (timestamp for ordering)
- Attributes: booking_id, user_id, seats, booking_date, event_id, state
- **GSI for User View:** 
  - GSI pk: `user-{id}`
  - GSI sk: `{booking-time}`

## Seat Management Flow

### Event-Seat Creation
When creating event-seats:
1. Copy all venue seats for the specified event
2. Add event-specific pricing based on seat type
3. Initialize all seats in `available` state
4. Set booking_id and holding_id to null

### Seat State Transitions

**Available → Held:**
- Condition: All requested seats are available
- Action: Set state to `held`, assign holding_id, set hold_ttl
- Response: Return holding_id

**Available → Held (Partial Failure):**
- Condition: Some requested seats are not available
- Action: No state change
- Response: Return error with unavailable seats

**Held → Held (TTL Not Expired):**
- Condition: Seat is held and TTL is valid
- Action: No state change
- Response: Return "seat is held" error

**Held → Held (TTL Expired):**
- Condition: Seat is held but TTL has expired
- Action: Create new holding_id, update hold_ttl
- Response: Return new holding_id

**Held → Booked:**
- Condition: Valid holding_id provided in confirm request
- Action: Set state to `booked`, set booking_id, clear holding_id
- Response: Return booking confirmation

**Booked → Available:**
- Condition: Valid booking_id provided in cancel request
- Action: Set state to `available`, clear booking_id
- Response: Return cancellation confirmation

## Holding Mechanism

### Configuration
- **Default TTL:** 180 seconds (3 minutes)
- **Cleanup:** No automatic cleanup mechanism required
- **Concurrency:** Transactional operations for seat holding

### Hold Process
1. Check if all requested seats are available or have expired holds
2. If successful, atomically update all seats to held state
3. Generate holding_id and set TTL
4. Create holding record with seat details

## ID Generation Strategy

### Counter-Based IDs
All entities use readable counter-based IDs:
- **Users:** `user-00001`, `user-00002`, etc.
- **Venues:** `venue-00001`, `venue-00002`, etc.
- **Events:** `event-00001`, `event-00002`, etc.
- **Bookings:** `booking-00001`, `booking-00002`, etc.
- **Holdings:** `holding-00001`, `holding-00002`, etc.

## Analytics Tracking

### Event-Level Analytics
Track the following metrics in the event object:
- **Total Bookings:** Number of confirmed bookings
- **Total Cancellations:** Number of cancelled bookings
- **Hold Attempts:** Number of hold requests (successful + failed)
- **Seats Sold:** Total number of individual seats booked
- **Capacity Utilization:** Percentage of total seats sold

### Analytics Updates
- Increment counters in real-time during booking operations
- Calculate capacity utilization on-demand
- Store analytics data as attributes in the event object

## Error Handling Strategy

### Error Response Format
Return descriptive HTTP error responses with clear messages:

```json
{
  "error": "Detailed error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {
    "additional_context": "if needed"
  }
}
```

### Common Error Scenarios
- **404:** Entity not found (venue, event, user, booking)
- **400:** Invalid request data or business logic violations
- **409:** Conflict errors (seats already held/booked)
- **422:** Validation errors for input data

## Testing Strategy

### Mock Testing Approach
- Use mocked DynamoDB calls for unit tests
- Create test fixtures for different scenarios
- Test each API endpoint with positive and negative cases
- Verify state transitions and error conditions

### Test Categories
1. **Unit Tests:** Individual function testing
2. **Integration Tests:** End-to-end API testing
3. **State Transition Tests:** Seat state change validation
4. **Concurrency Tests:** Simultaneous booking scenarios

## Environment Configuration

### Required Environment Variables
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# DynamoDB Configuration
DYNAMODB_TABLE_NAME=evently-table

# Application Configuration
APP_NAME=Evently
DEBUG=True
SEAT_HOLD_TTL=180
```

## Additional Implementation Notes

### Transactional Operations
- Use DynamoDB transactions for multi-seat holding operations
- Ensure atomicity for seat state changes
- Handle transaction conflicts gracefully

### Performance Considerations
- Use batch operations where possible
- Implement efficient querying with proper key design
- Consider read/write capacity units for production scaling

### Data Consistency
- Eventual consistency is acceptable for analytics
- Strong consistency required for seat state operations
- Use conditional writes to prevent race conditions
