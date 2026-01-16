# API Documentation

## Overview

The Crypto Predict Monitor API provides RESTful endpoints for monitoring crypto prediction markets, managing alerts, and accessing P&L analytics.

## Base URL

- **Development**: `http://localhost:8000`
- **Staging**: `https://staging.your-domain.com`
- **Production**: `https://api.your-domain.com`

## Authentication

### JWT Token Authentication
All protected endpoints require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### Rate Limiting
- **Default**: 100 requests per hour per user
- **P&L Cards**: 5 requests per 5 minutes
- **Health Checks**: No rate limiting

## Core Endpoints

### Health Checks

#### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-13T12:00:00Z",
  "version": "2.0.0",
  "upstream": "dev",
  "services": {
    "database": "healthy",
    "pnl_cards": "healthy",
    "webhook": "healthy"
  }
}
```

#### P&L Service Health
```http
GET /api/pnl-card/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "pnl_cards",
  "initialized": true,
  "timestamp": "2025-01-13T12:00:00Z"
}
```

### Market Monitoring

#### List Markets
```http
GET /markets
```

**Query Parameters:**
- `upstream` (optional): Filter by upstream source (`dev`, `polymarket`, `price`)
- `active_only` (optional): `true` to show only active markets
- `limit` (optional): Number of results (default: 50)

**Response:**
```json
{
  "markets": [
    {
      "id": "0x123...",
      "title": "Will BTC reach $100k by end of 2025?",
      "description": "Bitcoin price prediction market",
      "current_price": 0.75,
      "volume_24h": 1500000,
      "expires_at": "2025-12-31T23:59:59Z",
      "upstream": "polymarket",
      "active": true
    }
  ],
  "total": 1,
  "page": 1
}
```

#### Get Market Details
```http
GET /markets/{market_id}
```

**Response:**
```json
{
  "id": "0x123...",
  "title": "Will BTC reach $100k by end of 2025?",
  "description": "Bitcoin price prediction market",
  "current_price": 0.75,
  "volume_24h": 1500000,
  "total_volume": 5000000,
  "expires_at": "2025-12-31T23:59:59Z",
  "created_at": "2025-01-01T00:00:00Z",
  "upstream": "polymarket",
  "active": true,
  "price_history": [
    {
      "timestamp": "2025-01-13T12:00:00Z",
      "price": 0.75
    }
  ]
}
```

### Alert Management

#### Create Alert Rule
```http
POST /alerts
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "market_id": "0x123...",
  "threshold_price": 0.80,
  "threshold_volume": 1000000,
  "cooldown_minutes": 15,
  "severity": "high",
  "template": "price_alert",
  "enabled": true
}
```

**Response:**
```json
{
  "id": "alert_123",
  "market_id": "0x123...",
  "threshold_price": 0.80,
  "threshold_volume": 1000000,
  "cooldown_minutes": 15,
  "severity": "high",
  "template": "price_alert",
  "enabled": true,
  "created_at": "2025-01-13T12:00:00Z",
  "last_triggered": null
}
```

#### List Alert Rules
```http
GET /alerts
Authorization: Bearer <token>
```

**Query Parameters:**
- `market_id` (optional): Filter by market
- `enabled` (optional): `true` or `false`
- `severity` (optional): `low`, `medium`, `high`

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert_123",
      "market_id": "0x123...",
      "threshold_price": 0.80,
      "threshold_volume": 1000000,
      "cooldown_minutes": 15,
      "severity": "high",
      "template": "price_alert",
      "enabled": true,
      "created_at": "2025-01-13T12:00:00Z",
      "last_triggered": "2025-01-13T11:30:00Z"
    }
  ],
  "total": 1
}
```

#### Update Alert Rule
```http
PUT /alerts/{alert_id}
Authorization: Bearer <token>
```

**Request Body:** Same as Create Alert Rule

#### Delete Alert Rule
```http
DELETE /alerts/{alert_id}
Authorization: Bearer <token>
```

## P&L Card System

### Download P&L Card
```http
GET /api/pnl-card/{user_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `theme` (optional): `dark` or `light` (default: `dark`)
- `period` (optional): `7d`, `30d`, `90d`, `all` (default: `30d`)

**Response:** PNG image file

**Headers:**
```http
Content-Type: image/png
Content-Disposition: attachment; filename="pnl_{user_id}_{date}.png"
```

### Get Shareable P&L Metadata
```http
GET /api/pnl-card/{user_id}/share
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user": "trader123",
  "pnl_percentage": 15.50,
  "pnl_usd": 2500.00,
  "period": "30d",
  "win_rate": 68.0,
  "trades": 45,
  "volume": 125000.00,
  "share_text": "🚀 +15.50% on 45 crypto predictions! 68% win rate. Check it out on Crypto Predict Monitor! #trading #crypto",
  "generated_at": "2025-01-13T12:00:00Z",
  "card_url": "https://api.your-domain.com/api/pnl-card/trader123"
}
```

### P&L Analytics

#### Get P&L Snapshots
```http
GET /api/pnl/snapshots
Authorization: Bearer <token>
```

**Query Parameters:**
- `user_id` (optional): Filter by user
- `period` (optional): `7d`, `30d`, `90d`, `all`
- `limit` (optional): Number of snapshots (default: 100)

**Response:**
```json
{
  "snapshots": [
    {
      "id": "snapshot_123",
      "user_id": "trader123",
      "total_pnl_percentage": 15.50,
      "total_pnl_usd": 2500.00,
      "predictions_count": 45,
      "win_rate": 68.0,
      "total_volume": 125000.00,
      "period": "30d",
      "created_at": "2025-01-13T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1
}
```

#### Get P&L Analytics
```http
GET /api/pnl/analytics
Authorization: Bearer <token>
```

**Query Parameters:**
- `user_id` (optional): Filter by user
- `period` (optional): `7d`, `30d`, `90d`, `all`

**Response:**
```json
{
  "summary": {
    "total_users": 150,
    "avg_pnl_percentage": 8.25,
    "total_volume": 2500000.00,
    "total_predictions": 1250
  },
  "performance": {
    "best_performer": {
      "user_id": "trader456",
      "pnl_percentage": 45.80,
      "win_rate": 85.0
    },
    "worst_performer": {
      "user_id": "trader789",
      "pnl_percentage": -12.30,
      "win_rate": 35.0
    }
  },
  "trends": [
    {
      "date": "2025-01-13",
      "avg_pnl_percentage": 8.25,
      "total_volume": 85000.00
    }
  ]
}
```

#### Import P&L Data
```http
POST /api/pnl/import
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "user_id": "trader123",
  "predictions": [
    {
      "market_id": "0x123...",
      "outcome": "YES",
      "price": 0.75,
      "volume": 1000.00,
      "timestamp": "2025-01-13T12:00:00Z",
      "pnl_usd": 250.00
    }
  ]
}
```

## Database Endpoints

### Database Health
```http
GET /api/health/db
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "healthy",
  "connection": "active",
  "pool_size": 20,
  "active_connections": 5,
  "response_time_ms": 12,
  "timestamp": "2025-01-13T12:00:00Z"
}
```

### Run Migrations
```http
POST /api/db/migrate
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "migrations_run": 3,
  "migrations": [
    {
      "version": "001_initial_schema",
      "status": "completed",
      "timestamp": "2025-01-13T12:00:00Z"
    }
  ]
}
```

## Error Responses

### Standard Error Format
```json
{
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2025-01-13T12:00:00Z",
  "request_id": "req_123456"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication token |
| `FORBIDDEN` | 403 | User lacks permission for this resource |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Validation Errors
```json
{
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {
    "field_errors": [
      {
        "field": "threshold_price",
        "message": "Must be between 0 and 1"
      }
    ]
  }
}
```

## Rate Limiting

### Limits by Endpoint
- **GET /health**: No limit
- **GET /api/pnl-card/\***: 5 requests per 5 minutes
- **POST /alerts**: 10 requests per hour
- **GET /markets**: 100 requests per hour
- **Other endpoints**: 100 requests per hour

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642089600
```

## Webhooks

### Webhook Format
Alerts are sent via Discord webhooks in the following format:

```json
{
  "embeds": [
    {
      "title": "🚀 Price Alert Triggered",
      "description": "Market: Will BTC reach $100k by end of 2025?",
      "color": 16776960,
      "fields": [
        {
          "name": "Current Price",
          "value": "0.80",
          "inline": true
        },
        {
          "name": "Threshold",
          "value": "0.75",
          "inline": true
        },
        {
          "name": "Volume",
          "value": "$1,500,000",
          "inline": true
        }
      ],
      "timestamp": "2025-01-13T12:00:00Z"
    }
  ]
}
```

## SDK Examples

### Python
```python
import requests

# Get markets
response = requests.get(
    "http://localhost:8000/markets",
    headers={"Authorization": f"Bearer {token}"}
)
markets = response.json()

# Create alert
alert_data = {
    "market_id": "0x123...",
    "threshold_price": 0.80,
    "severity": "high"
}
response = requests.post(
    "http://localhost:8000/alerts",
    json=alert_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

### JavaScript
```javascript
// Get P&L card
const response = await fetch(`/api/pnl-card/${userId}`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

if (response.ok) {
  const blob = await response.blob();
  const imageUrl = URL.createObjectURL(blob);
  // Use imageUrl in your app
}
```

## Testing

### Health Check Test
```bash
curl http://localhost:8000/health
```

### Authenticated Request Test
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/pnl-card/health
```

### P&L Card Download Test
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -o pnl_card.png \
     http://localhost:8000/api/pnl-card/user123
```

## Versioning

The API follows semantic versioning:
- **Major version**: Breaking changes
- **Minor version**: New features, backward compatible
- **Patch version**: Bug fixes, backward compatible

Current version: **v2.0.0**

## Changelog

### v2.0.0 (2025-01-13)
- Added P&L card system
- Enhanced authentication with JWT
- Added comprehensive rate limiting
- Improved error handling and validation
- Added performance monitoring endpoints

### v1.0.0 (2025-01-01)
- Initial API release
- Basic market monitoring
- Alert management
- Webhook integration
