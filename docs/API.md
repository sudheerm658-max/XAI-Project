# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, no authentication required. In production, add API keys via `X-API-Key` header.

## Conversation Endpoints

### POST /conversations

Ingest a single conversation.

**Request:**
```json
{
  "external_id": "tweet_123",
  "thread_id": "conversation_1",
  "text": "This is a great service!",
  "raw": {
    "author": "user@example.com",
    "timestamp": "2026-02-08T10:00:00Z"
  }
}
```

**Response:** `202 Accepted`
```json
{
  "id": 1,
  "enqueued": true
}
```

**Status Codes:**
- `202`: Accepted for processing
- `400`: Invalid request
- `422`: Validation error
- `429`: Rate limited

### POST /conversations/bulk

Ingest up to 500 conversations in a single request.

**Request:**
```json
{
  "conversations": [
    {
      "external_id": "tweet_1",
      "text": "Great service!"
    },
    {
      "external_id": "tweet_2",
      "text": "Love this!"
    }
  ]
}
```

**Response:** `202 Accepted`
```json
{
  "ingested": 2,
  "enqueued": 2
}
```

### GET /conversations

List conversations with pagination.

**Query Parameters:**
- `skip`: Number to skip (default: 0)
- `limit`: Max results (default: 100, max: 1000)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "external_id": "tweet_1",
    "thread_id": null,
    "text": "Great service!",
    "raw": null,
    "created_at": "2026-02-08T10:00:00",
    "updated_at": "2026-02-08T10:00:00"
  }
]
```

### GET /conversations/{id}

Get a specific conversation.

**Response:** `200 OK`
```json
{
  "id": 1,
  "external_id": "tweet_1",
  "text": "Great service!",
  "created_at": "2026-02-08T10:00:00",
  "updated_at": "2026-02-08T10:00:00"
}
```

**Status Codes:**
- `200`: Success
- `404`: Conversation not found

## Insight Endpoints

### GET /insights

Get recent insights.

**Query Parameters:**
- `limit`: Max results (default: 100, max: 1000)
- `sentiment`: Filter by sentiment (positive, negative, neutral)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "conversation_id": 1,
    "summary": "User loves the service",
    "sentiment": "positive",
    "topics": ["service", "support"],
    "tokens_used": 125,
    "estimated_cost": "$0.000250",
    "processing_time_ms": 450,
    "grok_model": "grok-1",
    "created_at": "2026-02-08T10:05:00",
    "updated_at": "2026-02-08T10:05:00"
  }
]
```

### GET /insights/{id}

Get a specific insight.

**Response:** `200 OK`
```json
{
  "id": 1,
  "conversation_id": 1,
  "summary": "User loves the service",
  "sentiment": "positive",
  "topics": ["service", "support"],
  ...
}
```

### GET /insights/conversation/{conversation_id}

Get all insights for a conversation.

**Response:** `200 OK`
```json
[{...}]
```

### GET /insights/trends

Get aggregated trends over time window.

**Query Parameters:**
- `days`: Window size (default: 7, range: 1-365)

**Response:** `200 OK`
```json
{
  "window_days": 7,
  "total_insights": 450,
  "sentiment_counts": {
    "positive": 200,
    "negative": 50,
    "neutral": 200
  },
  "sentiment_distribution": {
    "positive": 44.4,
    "negative": 11.1,
    "neutral": 44.4
  },
  "top_topics": [
    {
      "topic": "support",
      "count": 120,
      "percentage": 26.7
    }
  ]
}
```

## Health & Metrics Endpoints

### GET /health

Health check with system status.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "uptime_seconds": 3600.5,
  "queue_size": 12,
  "worker_running": true,
  "db_ok": true,
  "message": null
}
```

**Status values:**
- `ok`: All systems operational
- `degraded`: Degraded functionality (high queue, DB slow)
- `unhealthy`: System offline

### GET /metrics

Prometheus-format metrics for monitoring.

**Response:** `200 OK` (text/plain)
```
# HELP requests_total Total incoming requests
# TYPE requests_total counter
requests_total 1234

# HELP request_latency_seconds Request latency seconds
# TYPE request_latency_seconds histogram
request_latency_seconds_bucket{le="0.005"} 100
...
```

### GET /status/summary

Summary of key metrics.

**Response:** `200 OK`
```json
{
  "total_requests": 5000,
  "total_conversations_ingested": 2500,
  "total_insights_generated": 2200,
  "cache_hit_rate": 8.5,
  "avg_analysis_latency_ms": 450,
  "estimated_total_cost_usd": 2.50,
  "queue_depth": 12
}
```

## Error Responses

All error responses follow this format:

```json
{
  "error": "ConversationNotFound",
  "detail": "Conversation with id=999 not found",
  "status_code": 404,
  "request_id": "req_12345"
}
```

**Common Status Codes:**
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: Bulk request > 500 items
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limited
- `500 Internal Server Error`: Server error

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1644337200
Retry-After: 42
```

## Examples

### Ingest and process conversation

```bash
# 1. Ingest conversation
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "tweet_1",
    "text": "Love your service! Best customer support ever."
  }'

# Response:
{
  "id": 1,
  "enqueued": true
}

# 2. Wait a moment for processing
sleep 2

# 3. Get insights
curl http://localhost:8000/api/v1/insights?limit=1

# Response:
[{
  "id": 1,
  "conversation_id": 1,
  "sentiment": "positive",
  "summary": "Love your service! Best customer support ever.",
  "topics": ["service", "support"]
}]
```

### Bulk ingest

```bash
curl -X POST http://localhost:8000/api/v1/conversations/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "conversations": [
      {"external_id": "t1", "text": "Great!"},
      {"external_id": "t2", "text": "Love it!"},
      {"external_id": "t3", "text": "Terrible experience"}
    ]
  }'

# Response:
{
  "ingested": 3,
  "enqueued": 3
}
```

### Get trends

```bash
curl "http://localhost:8000/api/v1/insights/trends?days=7"

# Response:
{
  "window_days": 7,
  "total_insights": 1250,
  "sentiment_counts": {
    "positive": 650,
    "negative": 150,
    "neutral": 450
  },
  "sentiment_distribution": {
    "positive": 52.0,
    "negative": 12.0,
    "neutral": 36.0
  },
  "top_topics": [...]
}
```

## Rate Limiting

Default: 60 requests per IP per 60 seconds.

When rate limited, you receive:
```
HTTP 429 Too Many Requests
Retry-After: 42
```

Retry after the specified seconds, or exponential backoff.

## Pagination

For endpoints returning lists:

```bash
# Get first 100 items
curl "http://localhost:8000/api/v1/conversations?skip=0&limit=100"

# Get items 100-199
curl "http://localhost:8000/api/v1/conversations?skip=100&limit=100"

# Max limit is 1000
curl "http://localhost:8000/api/v1/conversations?skip=0&limit=1000"
```

## Interactive API Docs

When DEBUG=true:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
