# Evently - Event Booking Platform

A scalable, high-performance event booking platform built with FastAPI and AWS DynamoDB. Evently provides comprehensive seat management, real-time booking capabilities, and detailed analytics for event organizers.

## 🚀 Features

### Core Functionality
- **Venue Management**: Create and manage venues with multiple seat types
- **Event Management**: Create events with dynamic pricing for different seat types
- **Seat Management**: Real-time seat availability tracking with row/seat positioning
- **Seat Holding**: Temporary seat reservations with configurable TTL (default 3 minutes)
- **Booking System**: Secure booking confirmation with payment integration
- **User Management**: User registration and booking history
- **Analytics**: Comprehensive event and booking analytics

### Advanced Features
- **Real-time Filtering**: Filter events by date, price, artists, tags, and location
- **Search Functionality**: Fuzzy search across event names and descriptions
- **Edge Case Handling**: Comprehensive handling of concurrent bookings, expired holds, and payment failures
- **Transaction Safety**: DynamoDB transactions for data consistency
- **Scalable Architecture**: Docker containerization with Nginx reverse proxy

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.11)
- **Database**: AWS DynamoDB
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **Testing**: pytest with async support
- **Code Quality**: Black, isort, pre-commit hooks

### Project Structure
```
atlan/
├── app/
│   ├── models/           # Pydantic data models
│   │   ├── event.py      # Event, booking, and analytics models
│   │   ├── venue.py      # Venue models
│   │   ├── seat.py       # Seat models
│   │   └── user.py       # User models
│   ├── routers/          # API route handlers
│   │   ├── event.py      # Event CRUD operations
│   │   ├── venue.py      # Venue management
│   │   ├── seat_booking.py # Booking confirmation/cancellation
│   │   ├── seat_holding.py # Seat holding operations
│   │   ├── analytics.py  # Analytics endpoints
│   │   └── user.py       # User management
│   ├── database.py       # DynamoDB client wrapper
│   ├── filtering.py      # Event filtering and search
│   ├── utils.py          # Utility functions
│   └── main.py           # FastAPI application
├── tests/                # Comprehensive test suite
├── docker-compose.yml    # Multi-service Docker setup
├── Dockerfile           # Application container
├── nginx.conf           # Nginx configuration
└── requirements.txt     # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- AWS account with DynamoDB access
- AWS credentials (Access Key ID and Secret Access Key)

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd atlan

# Copy environment template
cp docker.env.example .env

# Edit .env with your AWS credentials
nano .env
```

### 2. Configure Environment Variables
```bash
# .env file
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
EVENTS_TABLE_NAME=Evently-Table
DEBUG=False
```

### 3. Run the Application
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 4. Access the Application
- **API Documentation**: http://localhost/docs
- **Application**: http://localhost (port 80)
- **Direct API**: http://localhost:8000
- **Health Check**: http://localhost/health

## 📊 API Endpoints

### Venue Management
- `POST /venue` - Create a new venue
- `GET /venue` - List all venues
- `GET /venue/{venue_id}` - Get venue details
- `POST /venue/{venue_id}/seats` - Add seats to venue

### Event Management
- `POST /events` - Create a new event
- `GET /events` - List events with filtering options
- `GET /events/{event_id}` - Get event details
- `GET /events/{event_id}/seats` - Get event seat availability

### Seat Operations
- `POST /events/{event_id}/hold` - Hold seats temporarily
- `POST /{holding_id}/confirm` - Confirm booking
- `POST /{holding_id}/cancel` - Cancel holding
- `POST /bookings/{booking_id}/cancel` - Cancel confirmed booking

### User Management
- `POST /user` - Create user account
- `GET /user/{user_id}` - Get user details
- `GET /user/{user_id}/bookings` - Get user's booking history

### Analytics
- `GET /events/{event_id}/analytics` - Get comprehensive event analytics
- `GET /analytics/events` - Get analytics for all events

## 🔧 Configuration

### DynamoDB Table Schema
The application uses a single DynamoDB table with the following key structure:
- **Partition Key (pk)**: Entity ID (venue_id, event_id, user_id)
- **Sort Key (sk)**: Entity type prefix (VENUE, EVENT, user-, holding-, booking-)

### Seat States
- `available` - Seat is available for booking
- `held` - Seat is temporarily held (with TTL)
- `booked` - Seat is confirmed and booked

### Hold TTL
- Default hold duration: 180 seconds (3 minutes)
- Configurable via environment variables
- Automatic cleanup of expired holds

## 🧪 Testing

### Run Tests
```bash
# Run all tests
docker-compose exec app pytest

# Run specific test file
docker-compose exec app pytest tests/test_event.py

# Run with coverage
docker-compose exec app pytest --cov=app tests/
```

### Test Coverage
The test suite includes:
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Edge Case Tests**: Concurrent booking scenarios
- **Filtering Tests**: Search and filter functionality
- **Analytics Tests**: Data aggregation and reporting

## 🚀 Deployment

### Production Deployment
```bash
# Build production images
docker-compose -f docker-compose.yml up --build -d

# Scale application instances
docker-compose up --scale app=3 -d

# Monitor logs
docker-compose logs -f
```

### Environment-Specific Configuration
- **Development**: Debug mode enabled, hot reload
- **Production**: Optimized for performance, security headers
- **Staging**: Similar to production with additional logging

## 📈 Performance Features

### Scalability
- **Horizontal Scaling**: Multiple app instances behind Nginx
- **Database Optimization**: Efficient DynamoDB queries with GSI
- **Caching**: Nginx-level caching for static responses
- **Rate Limiting**: 10 requests/second per IP

### Security
- **CORS Configuration**: Configurable cross-origin requests
- **Security Headers**: XSS protection, content type sniffing prevention
- **Input Validation**: Pydantic models for request validation
- **Transaction Safety**: ACID compliance with DynamoDB transactions

## 🔍 Monitoring & Analytics

### Health Checks
- Application health: `/health`
- Database connectivity: `/db-test`
- Nginx status: Built-in health monitoring

### Analytics Capabilities
- **Event Analytics**: Capacity utilization, revenue tracking
- **Booking Analytics**: Success rates, cancellation patterns
- **Seat Analytics**: Individual seat performance
- **User Analytics**: Booking patterns and preferences

## 🛠️ Development

### Code Quality
```bash
# Format code
docker-compose exec app black .

# Sort imports
docker-compose exec app isort .

# Run pre-commit hooks
docker-compose exec app pre-commit run --all-files
```

### Adding New Features
1. Create Pydantic models in `app/models/`
2. Implement business logic in `app/routers/`
3. Add database operations in `app/database.py`
4. Write tests in `tests/`
5. Update API documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check port usage
   lsof -i :80
   lsof -i :8000
   ```

2. **AWS Credentials**
   - Verify `.env` file has correct credentials
   - Ensure DynamoDB permissions are granted
   - Check table name exists

3. **Application Not Starting**
   ```bash
   # Check logs
   docker-compose logs app
   
   # Verify dependencies
   docker-compose exec app pip list
   ```

4. **Database Connection Issues**
   ```bash
   # Test database connection
   curl http://localhost:8000/db-test
   ```

### Support
For additional support, please check the logs and ensure all environment variables are properly configured.

---

**Evently** - Making event booking simple, scalable, and reliable. 🎫

