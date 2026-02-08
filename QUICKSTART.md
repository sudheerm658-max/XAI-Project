# Grok Insights Backend - Quick Start Guide

## 30-Second Start

### Option 1: Docker (Recommended)
```bash
docker-compose up --build
curl http://localhost:8000/health
```

### Option 2: Local Python
```bash
pip install -r requirements.txt
python -m app.main  # or: uvicorn app.main:app --reload
curl http://localhost:8000/health
```

---

## First Test Run

### 1. Ingest a conversation:
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"external_id":"t1","text":"This is a great feature! Thanks for the support."}'
```

### 2. Check health:
```bash
curl http://localhost:8000/health
```

### 3. View insights (wait a moment):
```bash
curl http://localhost:8000/api/v1/insights?limit=5
```

### 4. Run load test:
```bash
python scripts/load_test.py --num-conversations 500 --concurrency 5
```

### 5. View metrics:
```bash
curl http://localhost:8000/metrics | head -50
```

---

## Environment Variables (Optional)

Create a `.env` file or set environment variables:
```bash
export DATABASE_URL=sqlite:///./data.db
export GROK_MODE=mock
export RATE_LIMIT=120
export MAX_BATCH=50
```

See `README.md` for full list of configuration options.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/conversations` | Ingest single conversation |
| POST | `/api/v1/conversations/bulk` | Ingest up to 500 conversations |
| GET | `/api/v1/insights?limit=100` | Retrieve recent insights |
| GET | `/api/v1/trends?days=7` | Aggregated trends over time window |
| GET | `/health` | Health & status check |
| GET | `/metrics` | Prometheus metrics |

---

## Troubleshooting

**Queue not processing?**
```bash
curl http://localhost:8000/health
# Check worker_running: true
docker-compose logs backend | grep -i error
```

**Rate limited?**
- Default: 60 req/60s per IP
- Change: `export RATE_LIMIT=200`

**Database issue?**
- SQLite in container is at `/app/data/data.db`
- For production: use PostgreSQL (`DATABASE_URL=postgresql://...`)

---

For full docs, see `README.md`.
