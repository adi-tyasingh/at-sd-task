# Evently Docker Setup

This document explains how to run the Evently application using Docker and Docker Compose.

## Prerequisites

- Docker
- Docker Compose
- AWS credentials for DynamoDB access

## Quick Start

1. **Set up environment variables:**
   ```bash
   cp docker.env.example .env
   # Edit .env with your actual AWS credentials and table name
   ```

2. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - Application: http://localhost (port 80)
   - Direct API: http://localhost:8000
   - API Documentation: http://localhost/docs

## Services

### Application Service (`app`)
- **Port:** 8000 (internal), 8000 (external)
- **Image:** Built from local Dockerfile
- **Health Check:** `/health` endpoint
- **Environment:** Uses variables from `.env` file

### Nginx Proxy (`nginx`)
- **Ports:** 80 (HTTP), 443 (HTTPS)
- **Features:**
  - Reverse proxy to FastAPI app
  - Rate limiting (10 requests/second)
  - Gzip compression
  - Security headers
  - Health check bypass

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_REGION` | AWS region | us-east-1 |
| `EVENTS_TABLE_NAME` | DynamoDB table name | Evently-Table |
| `DEBUG` | Debug mode | False |

## Commands

### Development
```bash
# Build and start services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production
```bash
# Build for production
docker-compose -f docker-compose.yml up --build -d

# Scale application (if needed)
docker-compose up --scale app=3 -d
```

## Health Checks

- **Application:** `curl http://localhost:8000/health`
- **Through Nginx:** `curl http://localhost/health`

## API Endpoints

All API endpoints are available through the Nginx proxy:

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation
- `POST /venue` - Create venue
- `GET /venue` - List venues
- `POST /events` - Create event
- `GET /events` - List events
- `POST /user` - Create user
- `GET /user/{user_id}` - Get user
- `GET /user/{user_id}/bookings` - Get user bookings

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Check what's using the port
   lsof -i :80
   lsof -i :8000
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

2. **AWS credentials not working:**
   - Verify your `.env` file has correct AWS credentials
   - Ensure your AWS user has DynamoDB permissions
   - Check that the table name exists

3. **Application not starting:**
   ```bash
   # Check application logs
   docker-compose logs app
   
   # Check if all dependencies are installed
   docker-compose exec app pip list
   ```

4. **Nginx not proxying correctly:**
   ```bash
   # Check nginx logs
   docker-compose logs nginx
   
   # Test direct connection to app
   curl http://localhost:8000/health
   ```

### Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs app
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f app
```

## Security Notes

- The Nginx configuration includes basic security headers
- Rate limiting is enabled to prevent abuse
- Consider adding SSL/TLS certificates for production
- Ensure AWS credentials are properly secured
