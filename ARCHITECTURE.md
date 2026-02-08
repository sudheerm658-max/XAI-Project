# Architecture & Trade-offs

## System Design Overview

### Async Event-Driven Architecture
```
HTTP Request → FastAPI Middleware (Rate Limit) → Endpoint Handler
                                                      ↓
                                               SessionLocal (SQLite)
                                                      ↓
                                              Async Queue (in-memory)
                                                      ↓
                                           Worker Loop (asyncio)
                                                      ↓
                                   Cheap Prefilter → Skip low-value
                                   Cache Lookup → Avoid re-analysis
                                   Grok Analysis (pluggable client)
                                                      ↓
                                           Write Insight + Cache
                                           Emit Prometheus Metrics
```

### Key Design Trade-offs

#### 1. SQLite vs PostgreSQL
- **Choice:** SQLite (prototype)
- **Rationale:** Simple deployment, no external service
- **Trade-off:** Max ~100 QPS; single-writer bottleneck
- **Upgrade path:** Set `DATABASE_URL=postgresql://...` and redeploy

#### 2. In-Memory Queue vs Persistent Queue (Redis/RabbitMQ)
- **Choice:** `asyncio.Queue` (in-memory)
- **Rationale:** No external dependencies; good for prototype
- **Trade-off:** Data loss on restart; no multi-worker scaling
- **Upgrade path:** Use Redis with `aioredis` + Celery for horizontal scaling

#### 3. Cheap Prefilter vs ML-based Filtering
- **Choice:** Heuristic prefilter (check text length, URLs, keywords)
- **Rationale:** O(1) cost; ~40–60% reduction in API calls
- **Trade-off:** Some useful conversations may be skipped; simple rule-based
- **Upgrade path:** Train sentiment/relevance classifier

#### 4. SHA256 Caching vs Semantic Embedding Cache
- **Choice:** Exact text hash (SHA256)
- **Rationale:** Deterministic, zero false positives
- **Trade-off:** Misses similar conversations (must be exact match)
- **Upgrade path:** Add embedding-based similarity (cosine distance on embeddings)

#### 5. Rate Limiting Strategy
- **Choice:** Per-IP sliding window (middleware)
- **Rationale:** Simple, fair, protects against single-client spam
- **Trade-off:** No API key/token-based tiers
- **Upgrade path:** Add API keys with per-key rate limits and usage quotas

#### 6. Metrics Collection
- **Choice:** Prometheus client library (in-process counters/histograms)
- **Rationale:** Lightweight, no external service, standard format
- **Trade-off:** Metrics lost on restart; limited cardinality (need to be careful with labels)
- **Upgrade path:** Add Prometheus scrape endpoint + long-term storage

---

## Performance Characteristics

### Throughput
- **Single-threaded worker:** ~10–50 analyses/sec (depends on Grok latency)
- **With adaptive batching:** ~30–100 conversations/sec (reduced per-conversation overhead)
- **Bottleneck:** Grok API latency (mock: 0.3–0.9s; real: varies by model)

### Latency
- **Ingestion (POST):** <10ms (direct DB write, async queue add)
- **Insight retrieval (GET):** <50ms (simple SQL query)
- **Analysis latency:** 0.3–0.9s (mock Grok)

### Memory
- **Base:** ~50MB (FastAPI + SQLAlchemy + Prometheus)
- **Per queued conversation:** ~1KB (metadata + text)
- **Recommendation:** Keep queue < 10k items; scale workers if needed

### Cost (Estimated)
- **Mock mode:** $0.002 per 1000 tokens (configure via `GROK_COST_PER_1K`)
- **Example:** 10k conversations @ 100 tokens avg = 1M tokens = $2
- **Savings via filtering:** ~40–60% reduction if 50% of conversations are filtered

---

## Resilience & Failure Modes

### Circuit Breaker
- **Trigger:** 5 consecutive errors in analysis
- **Action:** Pause for 10s (configurable `COOLDOWN_SECONDS`)
- **Benefit:** Prevents cascading failures; allows Grok API time to recover
- **Monitor:** Check logs for "circuit breaker tripped"

### Backpressure Handling
- **Mechanism:** Queue-depth gauge triggers batch-size reduction
- **Threshold:** If queue > 1000 items, halve batch size
- **Effect:** Reduces memory pressure; slower but steady throughput
- **Monitor:** `/health` endpoint shows `queue_size`

### Rate Limiting
- **Enforced at:** Middleware level (all endpoints)
- **Response:** 429 with `Retry-After` header
- **Benefit:** Prevents overload from single client or misconfigured bulk ingestion

### Graceful Shutdown
- `shutdown` event cancels worker task
- In-flight work is lost (future: implement worker persistence)
- Queue depth is preserved (async Queue only, not DB)

---

## Security Considerations

### Current Prototype (NOT production-ready):
- **No authentication** (open endpoints)
- **No request validation** beyond Pydantic schemas
- **SQLite on disk** (no encryption at rest)
- **No HTTPS** (relies on reverse proxy in deployment)
- **Rate limiting** is per-IP (can be spoofed behind proxy)

### Recommendations for Production:
1. Add API key authentication + request signing (asymmetric)
2. Use HTTPS behind nginx/load balancer
3. Migrate to PostgreSQL + encrypted storage
4. Implement CORS + CSRF protection
5. Add request logging + audit trail
6. Use secrets manager (AWS Secrets Manager, HashiCorp Vault) for Grok API keys

---

## Observable Metrics

```
# Requests
requests_total{job="grok-insights"}

# Request latency (histogram with buckets)
request_latency_seconds{job="..."}
  - p50, p95, p99 derived from buckets

# Grok analysis
grok_calls_total
grok_call_errors_total
grok_call_latency_seconds

# Cache effectiveness
analysis_cache_hits_total
prefilter_skips_total

# Cost tracking
estimated_tokens_total
estimated_cost_usd_total  # in $USD

# Queue health
processing_queue_depth  # gauge, target 0–1000

# Health
GET /health → {"status":"ok"|"degraded", "queue_size":X, "worker_running":bool}
```

---

## Deployment Checklist

- [x] Single-container Docker image (Python 3.11 slim)
- [x] docker-compose.yml with health check
- [x] Environment-based configuration
- [x] Graceful shutdown hooks
- [x] Prometheus metrics export
- [x] Health check endpoint
- [x] Load testing script
- [x] Documentation (README, QUICKSTART, ARCHITECTURE)
- [ ] TLS/HTTPS (reverse proxy needed)
- [ ] Database migration strategy (SQLite → PostgreSQL)
- [ ] Multi-region deployment (future)
- [ ] Cost monitoring & alerting (future)

---

## Upgrade Path: From Prototype to Production

1. **Database:** SQLite → PostgreSQL
   ```bash
   export DATABASE_URL=postgresql://user:pass@host/db
   docker-compose up  # redeploy
   ```

2. **Queue:** In-memory → Redis + Celery
   ```bash
   # Add to docker-compose.yml: redis service
   # Update app/worker.py to use aioredis
   # Deploy multiple worker containers
   ```

3. **Real Grok API:** Update `app/grok_client.py`
   ```python
   async def analyze(text: str) -> dict:
       async with httpx.AsyncClient() as client:
           response = await client.post("https://api.grok.ai/...", json={"text": text})
           return response.json()
   ```

4. **Monitoring:** Add Prometheus + Grafana
   ```bash
   # docker-compose: add prometheus + grafana services
   # Scrape /metrics from backend
   ```

5. **API Keys + RBAC:** Add authentication layer
   ```python
   @app.post("/api/v1/conversations")
   async def ingest_conversation(payload: ConversationIn, api_key: str = Header(...)):
       # Verify API key, rate limit by key, audit log
   ```

---

## References

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy:** https://sqlalchemy.org/
- **Prometheus Python Client:** https://github.com/prometheus/client_python
- **Docker Compose:** https://docs.docker.com/compose/
