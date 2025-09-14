# routes:

Note: the routes are categorised by the entity they are associated with: 

### Venue Routes: 
- POST /venue : this route is elementary and requires the creation of a venue object. the venue object should hold the city of the venue, the types of seats in the venue. Name of the venue, description of the venue along with an integer venue id, something like venue-00001, if this is not possible use a unique id generator like uuid. 

- GET /venue : this should return a list of venue objects, venue objects can be filtered by city. 

### venue-seat routes

- POST /venue/{venue-id}/seats : this route allows users to add seats to a specific venue. it is necessary to ensure that the specified venue-id exists. each seat object should have a row and seatnum, combined the row and seatnum, along with the venue-id should create a unique item. seat objects should be partitioned by venue as pk.  

- GET /venue/{venue-id}/seats : this route should allow users to get the complete list of seats at an event and their type. 

### User routes: 
- POST /user : this route is used to create a new user with a unique integer userid something like user-00001. The user should have an email address and a phone number. 

- GET /user/{user-id}/bookings : this route should not create an entire history of the users bookings, sorted by time! 

### Event routes: 

- POST /events : this route creates an entirely new event. it requires the following fields: venue-id, name, start-time, duration, artists list, tags list, description, and prices for diffrent types of seats. It is necessary to ensure that an event is only created with a valid not-deleted venue. 

- GET /events : this route should return all events that meet a certain criteria. events can be filtered by location, time and tags. these filters will be passed as query params. 

### event-seat routes. 

- POST /{event-id}/event-seats : this route creates a set of event seat objects that contains all of the seats of the venue associated with the given event. These objects will be partitioned by event-id and will have additional attributes: seat-state, booking-id, holding-id, hold-ttl, and price(extracted using seat type attribute of venue and price attribute of event ). booking id/holding-id is nullable and is only available when seat is in booked/held state respectively. 

- POST /{event-id}/hold : this route updates the event-seat object and sets it state to held, along with returning a holding-id! it accepts user-id and a list of seats. seat only goes into hold state if it is available state, or if the hold-ttl has passed.  it also creates holding objects with specified holding-id, ttl, seat-ids that are being held. The event seat holding operation must be performed in a transactional manner. 

- POST /{holding-id}/confirm : accepts a holding-id, and cofirms seats of that booking-ids if payment-status(string) is successful. It creates a booking object with all of the booking details. date, event, time, seats, state(can be cancelled later)

- POST /{booking-id}/cancel : this request basically cancels the booking and frees the event-seat object from booked state to available state. This allows it to be booked by someone else. 

### analytics routes: 
- GET /{event-id}/bookings : this should return a list of booking stats including: cancelations, holds created, number of successful bookings, number of failed holds, etc. This data can be maintained in the event object itself! 