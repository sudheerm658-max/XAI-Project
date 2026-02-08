DEMO SCRIPT — Grok Insights Backend (4–5 minute demo)
=====================================================

Purpose: run a concise live demo showing server startup, ingesting sample data, monitoring `/health` and `/metrics`, viewing insights, and explaining architecture and tradeoffs.

Checklist (before recording)
- Ensure `.env` contains `GROK_MODE=mock` to avoid API costs during demo
- Start server locally: `uvicorn src.grok_insights.main:app --reload --host 127.0.0.1 --port 8000`
- Open terminal for `curl` commands and a second terminal for `watch`/metrics

Script (timed)

0:00 — Intro (15s)
- One-line project purpose: "A production-oriented backend to ingest and analyze conversations using Grok."

0:15 — Start server (20s)
```bash
python -m uvicorn src.grok_insights.main:app --reload --host 127.0.0.1 --port 8000
```
- Mention configuration reading from `.env` and `settings.py`.

0:35 — Show API docs briefly (20s)
- Open `http://127.0.0.1:8000/docs` and point to `POST /api/v1/conversations/bulk` and `/metrics`.

0:55 — Ingest sample (60s)
```bash
# Create small sample (already prepared in repo)
python scripts/create_sample_csv_simple.py --csv "path/to/twcs.csv" --output ./data/kaggle/conversations_sample.json --rows 100

# Ingest
python scripts/ingest_sample.py --source ./data/kaggle/conversations_sample.json --api-url http://127.0.0.1:8000 --batch-size 50
```
- Note: worker uses adaptive batching, prefilter, and caching to optimize cost.

1:55 — Monitor health & metrics (40s)
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/metrics | grep grok_calls_total
```
- Explain metrics: `grok_calls_total`, `estimated_cost_usd_total`, `processing_queue_depth`.

2:35 — Show saved insights (40s)
```bash
curl http://127.0.0.1:8000/api/v1/insights?limit=10
```
- Explain fields: `summary`, `sentiment`, `topics`, `estimated_cost`.

3:15 — Explain resilience & cost controls (60s)
- Adaptive batching and backpressure
- Circuit breaker and retries (demo shows `GROK_MODE=mock` but `_analyze_real()` has retries, 429 handling, and jittered backoff)
- Semantic caching (SHA256 of text) reduces re-analysis cost

4:15 — Closing (30s)
- Next steps: run load test, production deployment (Postgres, Redis queue, Kubernetes), monitoring dashboards.

Recording tips
- Use Loom or OBS. Start recording before you run the server so you capture startup logs.
- Keep terminal fonts large and highlight key commands.
