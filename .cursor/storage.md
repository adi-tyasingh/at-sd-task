# Storage

- since evently is a simple Demo application it will use a simple dynamoDB storage system! A singular DynamoDb table has been created and AWS access key and secret will be provided in the .env file, along with the table name. 

- Since all objects are stored in a single DynamoDB table we will make use of partition key and sorting key to keep objects seperated! Since bookings, seat sales and analytics will be calculated seat wise we will store these with a partition key (pk) of eventID

- Fields like seats and more will be related to venue so they will be partitioned by venue. 
- Fields like event-seats(seat map with price data) will be related to events so they will be partitioned by event! 

Booking IDs need to be partitioned twice, once on the basis of event and also on the basis of user-id, this is to allow users to view their booking history. Use GSI to implement this! 