# LeakGuard API Documentation

## Overview
LeakGuard is a comprehensive API-driven cybersecurity monitoring system that helps organizations track credential leaks across dark web, data breaches, Telegram channels, and other sources.

## Base URL
```
http://localhost:8000/api/
```

## Authentication
The API uses token-based authentication. Include your token in the Authorization header:
```
Authorization: Token your_token_here
```

## API Endpoints

### 1. User Management

#### Get/Update User Profile
```http
GET /api/profile/
PATCH /api/profile/
```

**Response:**
```json
{
    "id": 1,
    "user": {
        "id": 1,
        "username": "user123",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "date_joined": "2024-01-01T00:00:00Z"
    },
    "email_notifications": true,
    "sms_notifications": false,
    "webhook_url": "",
    "default_severity_threshold": "medium",
    "auto_resolve_false_positives": false,
    "api_key": "abc123...",
    "api_rate_limit": 1000,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### 2. Data Sources

#### List/Create Data Sources
```http
GET /api/sources/
POST /api/sources/
```

**Create Data Source:**
```json
{
    "name": "Telegram Channel XYZ",
    "source_type": "telegram",
    "url": "https://t.me/channel",
    "is_active": true,
    "check_interval": 3600,
    "configuration": {
        "channel_id": "@channel",
        "api_key": "bot_token"
    }
}
```

#### Get/Update/Delete Data Source
```http
GET /api/sources/{id}/
PATCH /api/sources/{id}/
DELETE /api/sources/{id}/
```

### 3. Monitored Credentials

#### List/Create Monitored Credentials
```http
GET /api/credentials/
POST /api/credentials/
```

**Create Credential:**
```json
{
    "credential_type": "email",
    "value": "user@example.com",
    "is_active": true,
    "tags": ["work", "critical"],
    "notes": "Primary work email"
}
```

**Credential Types:**
- `email` - Email addresses
- `username` - Usernames
- `domain` - Domain names
- `phone` - Phone numbers
- `api_key` - API keys
- `password` - Passwords

#### Bulk Create Credentials
```http
POST /api/credentials/bulk/
```

**Request:**
```json
{
    "credentials": [
        {
            "credential_type": "email",
            "value": "user1@example.com",
            "is_active": true,
            "tags": ["work"]
        },
        {
            "credential_type": "username",
            "value": "user123",
            "is_active": true,
            "tags": ["social"]
        }
    ]
}
```

#### Get/Update/Delete Credential
```http
GET /api/credentials/{id}/
PATCH /api/credentials/{id}/
DELETE /api/credentials/{id}/
```

### 4. Credential Leaks

#### List/Create Leaks
```http
GET /api/leaks/
POST /api/leaks/
```

**Query Parameters:**
- `credential_type` - Filter by credential type
- `severity` - Filter by severity (critical, high, medium, low, info)
- `status` - Filter by status (new, investigating, confirmed, false_positive, resolved)
- `source` - Filter by source ID
- `is_verified` - Filter by verification status
- `search` - Search in leaked_value and leak_content
- `ordering` - Order by field (e.g., `-discovered_at`)

**Create Leak:**
```json
{
    "monitored_credential": 1,
    "source": 1,
    "credential_type": "email",
    "leaked_value": "user@example.com",
    "leak_content": "Full leak content here...",
    "leak_url": "https://pastebin.com/abc123",
    "severity": "high",
    "status": "new",
    "confidence_score": 0.95,
    "leak_date": "2024-01-01T00:00:00Z",
    "tags": ["pastebin", "verified"],
    "metadata": {
        "file_size": "1.2MB",
        "leak_count": 1000
    },
    "is_verified": true
}
```

#### Search Leaks
```http
GET /api/leaks/search/?q=search_term&severity=high&source_type=telegram
```

#### Bulk Update Leaks
```http
PATCH /api/leaks/bulk-update/
```

**Request:**
```json
{
    "leak_ids": [1, 2, 3],
    "status": "confirmed",
    "severity": "critical"
}
```

#### Get/Update/Delete Leak
```http
GET /api/leaks/{id}/
PATCH /api/leaks/{id}/
DELETE /api/leaks/{id}/
```

### 5. Alerts

#### List/Create Alerts
```http
GET /api/alerts/
POST /api/alerts/
```

**Query Parameters:**
- `alert_type` - Filter by alert type
- `priority` - Filter by priority
- `is_read` - Filter by read status
- `is_resolved` - Filter by resolved status

**Create Alert:**
```json
{
    "alert_type": "leak_detected",
    "title": "Critical Leak Detected",
    "message": "Your email was found in a data breach",
    "credential_leak": 1,
    "source": 1,
    "priority": "critical"
}
```

#### Mark Alerts as Read
```http
POST /api/alerts/mark-read/
```

**Request:**
```json
{
    "alert_ids": [1, 2, 3]  // Optional: mark all if empty
}
```

#### Get/Update/Delete Alert
```http
GET /api/alerts/{id}/
PATCH /api/alerts/{id}/
DELETE /api/alerts/{id}/
```

### 6. Monitoring Sessions

#### List/Create Monitoring Sessions
```http
GET /api/sessions/
POST /api/sessions/
```

**Create Session:**
```json
{
    "source": 1,
    "configuration": {
        "scan_interval": 300,
        "keywords": ["password", "login"],
        "exclude_patterns": ["test", "demo"]
    }
}
```

#### Get/Update/Delete Session
```http
GET /api/sessions/{id}/
PATCH /api/sessions/{id}/
DELETE /api/sessions/{id}/
```

### 7. Monitoring Control

#### Start Monitoring
```http
POST /api/monitoring/start/
```

**Request:**
```json
{
    "source_id": 1,
    "configuration": {
        "scan_interval": 300,
        "keywords": ["password", "login"]
    }
}
```

#### Stop Monitoring
```http
POST /api/monitoring/stop/
```

**Request:**
```json
{
    "session_id": 1
}
```

### 8. Dashboard & Analytics

#### Dashboard Statistics
```http
GET /api/dashboard/stats/
```

**Response:**
```json
{
    "total_monitored_credentials": 25,
    "active_sources": 8,
    "total_leaks": 156,
    "critical_leaks": 12,
    "high_leaks": 34,
    "medium_leaks": 67,
    "low_leaks": 43,
    "unread_alerts": 5,
    "recent_leaks": [...],
    "recent_alerts": [...]
}
```

#### Leak Analytics
```http
GET /api/analytics/leaks/
```

**Response:**
```json
{
    "leaks_by_severity": {
        "critical": 12,
        "high": 34,
        "medium": 67,
        "low": 43
    },
    "leaks_by_source": {
        "Telegram Channel": 45,
        "Pastebin": 32,
        "Dark Web": 28
    },
    "leaks_over_time": {
        "2024-01-01": 5,
        "2024-01-02": 8,
        "2024-01-03": 3
    },
    "top_leaked_credentials": [
        {
            "leaked_value": "user@example.com",
            "credential_type": "email",
            "count": 15
        }
    ]
}
```

#### Source Analytics
```http
GET /api/analytics/sources/
```

**Response:**
```json
[
    {
        "source_name": "Telegram Channel",
        "source_type": "telegram",
        "total_leaks": 45,
        "last_checked": "2024-01-01T12:00:00Z",
        "is_active": true,
        "success_rate": 95.5
    }
]
```

## Error Responses

### 400 Bad Request
```json
{
    "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
    "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
    "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
    "detail": "A server error occurred."
}
```

## Rate Limiting
- Default rate limit: 1000 requests per hour per user
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## Pagination
All list endpoints support pagination:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

**Response:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/leaks/?page=2",
    "previous": null,
    "results": [...]
}
```

## Filtering & Search
Most list endpoints support:
- **Filtering**: Use query parameters to filter by specific fields
- **Search**: Use `search` parameter for text search
- **Ordering**: Use `ordering` parameter (prefix with `-` for descending)

**Example:**
```
GET /api/leaks/?severity=critical&search=password&ordering=-discovered_at
```

## Webhooks
Configure webhook URL in user profile to receive real-time notifications:
```json
{
    "webhook_url": "https://your-app.com/webhook"
}
```

**Webhook Payload:**
```json
{
    "event_type": "leak_detected",
    "timestamp": "2024-01-01T12:00:00Z",
    "data": {
        "leak_id": 123,
        "severity": "critical",
        "credential_type": "email",
        "leaked_value": "user@example.com"
    }
}
```

## SDK Examples

### Python
```python
import requests

# Set up client
base_url = "http://localhost:8000/api"
headers = {"Authorization": "Token your_token_here"}

# Get dashboard stats
response = requests.get(f"{base_url}/dashboard/stats/", headers=headers)
stats = response.json()

# Create monitored credential
credential_data = {
    "credential_type": "email",
    "value": "user@example.com",
    "is_active": True
}
response = requests.post(f"{base_url}/credentials/", json=credential_data, headers=headers)

# Search for leaks
response = requests.get(f"{base_url}/leaks/search/?q=password&severity=high", headers=headers)
leaks = response.json()
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: {
        'Authorization': 'Token your_token_here'
    }
});

// Get dashboard stats
const stats = await api.get('/dashboard/stats/');

// Create monitored credential
const credential = await api.post('/credentials/', {
    credential_type: 'email',
    value: 'user@example.com',
    is_active: true
});

// Search for leaks
const leaks = await api.get('/leaks/search/', {
    params: { q: 'password', severity: 'high' }
});
```

## Testing
Use the browsable API at `http://localhost:8000/api/` for interactive testing, or tools like Postman, curl, or your preferred API client.

## Support
For API support and questions, please contact the development team or refer to the project documentation.
