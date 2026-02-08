# Grok API Integration Guide

## Overview

The Grok Insights Backend supports both **mock** and **real** Grok AI analysis modes. This guide explains how to set up and use the real Grok API from xAI.

## Prerequisites

1. **Grok API Access**
   - Create an account at [console.x.ai](https://console.x.ai)
   - Generate an API key from your account dashboard
   - Ensure you have credits/billing set up

2. **Environment Setup**
   - Python 3.11+
   - Virtual environment activated
   - All dependencies installed: `pip install -r requirements.txt` (includes `httpx`)

## Configuration

### 1. Set Your API Key

Add your Grok API key to `.env`:

```bash
# .env
GROK_API_KEY=xai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROK_MODE=real
GROK_MODEL=grok-1
GROK_API_BASE_URL=https://api.x.ai/v1
```

Or set as environment variable:

```bash
# PowerShell
$env:GROK_API_KEY="xai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:GROK_MODE="real"
```

### 2. Optional: Adjust Cost Settings

```bash
# Cost per 1000 tokens (in USD)
GROK_COST_PER_1K=0.002  # Adjust based on current Grok pricing
```

## Modes

### Mock Mode (Development/Testing)

```bash
GROK_MODE=mock
```

- **Behavior:** Heuristic sentiment detection + naive topic extraction
- **Cost:** Free (simulated)
- **Latency:** 0-0.9s (simulated)
- **Use Case:** Testing, development, CI/CD

### Real Mode (Production)

```bash
GROK_MODE=real
```

- **Behavior:** Actually calls xAI Grok API
- **Cost:** Charged per token (~$0.002 per 1k tokens)
- **Latency:** 1-3s per request (depends on network + Grok)
- **Use Case:** Production analysis with real AI

## Testing the Integration

### 1. Start the Server

```bash
python -m uvicorn src.grok_insights.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Test a Single Request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "test_grok_1",
    "text": "I love this product! The customer support team is absolutely amazing. They resolved my issue in minutes. Thank you so much!"
  }'
```

Response (202 Accepted):
```json
{
  "id": 1,
  "conversation_id": 1,
  "status": "enqueued"
}
```

### 3. Check the Result

Once the worker processes it:

```bash
curl http://127.0.0.1:8000/api/v1/insights/1
```

Response with real Grok analysis:
```json
{
  "id": 1,
  "conversation_id": 1,
  "summary": "Customer expresses strong satisfaction with product and support team performance",
  "sentiment": "positive",
  "topics": ["customer_support", "product_satisfaction", "service_quality"],
  "tokens_used": 87,
  "estimated_cost": "$0.00017",
  "processing_time_ms": 2345,
  "grok_model": "grok-1"
}
```

## API Response Format

When using real Grok API, the analysis returns:

```json
{
  "summary": "1-2 sentence summary",
  "sentiment": "positive|negative|neutral",
  "topics": ["topic1", "topic2", "topic3"],
  "meta": {
    "mock": false,
    "latency": 2.345,
    "estimated_tokens": 87,
    "estimated_cost": 0.00017,
    "model": "grok-1"
  }
}
```

## Performance Considerations

### Token Estimation

- Grok tokens ≈ 4 characters per token
- Longer texts = more tokens = higher cost
- Example: 1000 characters ≈ 250 tokens ≈ $0.0005

### Rate Limiting

The backend implements rate limiting:
- **Default:** 60 requests per 60 seconds per IP
- **Can be changed:** Update `RATE_LIMIT_REQUESTS` in settings

Grok API itself has rate limits—check your [account dashboard](https://console.x.ai) for current limits.

### Batching

The worker automatically batches conversations for efficiency:
- **Adaptive batch size:** Starts at 5, grows to 50 based on success rate
- **Backpressure:** Shrinks batch size if queue grows too large
- **Circuit breaker:** Pauses for 10s if 5+ consecutive errors occur

## Monitoring

### View Real-Time Metrics

```bash
curl http://127.0.0.1:8000/metrics | grep grok
```

Key metrics:
- `grok_calls_total` — Total API calls made
- `grok_call_errors` — Failed API calls
- `grok_call_latency_seconds` — Response time histogram
- `estimated_cost_usd` — Total cost so far

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Shows:
- Worker status (running/paused)
- Queue depth (pending conversations)
- Database status

## Troubleshooting

### "GROK_API_KEY not configured"

**Problem:** Error occurs when trying to analyze with `GROK_MODE=real`

**Solution:**
1. Check `.env` file exists and contains `GROK_API_KEY`
2. Reload the server after updating `.env`
3. Verify API key format (should start with `xai-`)

### HTTP 401 / Invalid API Key

**Problem:** 401 Unauthorized from xAI API

**Solution:**
1. Verify API key at [console.x.ai](https://console.x.ai)/api-keys
2. Check key hasn't expired
3. Ensure billing is active

### HTTP 429 / Rate Limited

**Problem:** Too many requests to Grok API

**Solution:**
1. Reduce concurrency: `--concurrency 1` in load test
2. Increase batch flush timeout: `QUEUE_FLUSH_TIMEOUT_SECONDS=2.0`
3. Lower `MAX_BATCH_SIZE` to reduce simultaneous requests

### Timeout Errors

**Problem:** Grok API takes too long to respond

**Solution:**
1. Increase timeout: Check `httpx` timeout setting (default 30s)
2. Try again—Grok API may be experiencing latency
3. Check xAI status page for incidents

### JSON Parsing Errors

**Problem:** "Failed to parse Grok JSON response"

**Solution:**
- The integration includes fallback parsing
- Logs will show the raw response
- This may indicate Grok API changed format—contact support

## Cost Estimation

Running a load test with real Grok API:

```bash
python scripts/load_test.py \
  --base-url http://localhost:8000 \
  --num-conversations 100 \
  --concurrency 5
```

**Estimated cost for 100 conversations:**
- Average text: 500 characters
- Tokens per text: ~125
- Cost per request: $0.00025
- **Total: ~$0.025** (2.5 cents)

## Switching Back to Mock Mode

To avoid costs during testing, switch back to mock:

```bash
GROK_MODE=mock
```

No code changes needed—the worker automatically uses the configured mode.

## Advanced: Custom Analysis Prompts

To customize the analysis prompt, edit `_analyze_real()` in [src/grok_insights/worker/grok_client.py](../../src/grok_insights/worker/grok_client.py):

```python
system_prompt = """Your custom prompt here.
Must return JSON with: summary, sentiment, topics, tokens_used"""
```

## API Endpoints

### Ingest Conversations

```
POST /api/v1/conversations
POST /api/v1/conversations/bulk
```

### Get Results

```
GET /api/v1/insights
GET /api/v1/insights/{id}
GET /api/v1/insights/conversation/{conversation_id}
GET /api/v1/insights/trends
```

See [API.md](./API.md) for full documentation.

## Support

- **xAI Grok Documentation:** https://docs.x.ai
- **Issues:** Check logs with `docker logs` or the `/health` endpoint
- **Monitoring:** Use `/metrics` endpoint for Prometheus integration

---

**Last Updated:** February 8, 2026
