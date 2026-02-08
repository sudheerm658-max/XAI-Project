# Grok Insights Backend

> Production-ready asynchronous backend for large-scale conversation analysis via Grok

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-≥0.109-009485.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker-compose up --build
curl http://localhost:8000/health
```

### Local Python

```bash
make install
make db-init
make run
```

Server running at `http://localhost:8000`

## ✨ Features

### Core Capabilities

- **Async Processing Pipeline**: Non-blocking I/O for 5k–10k conversation ingestion
- **Adaptive Batching**: Throughput optimization with automatic backpressure handling
- **Two-Stage Filtering**: Cheap prefilter + expensive Grok analysis (40–60% cost savings)
- **Semantic Caching**: SHA256 hash-based deduplication to avoid re-analysis
- **Circuit Breaker**: Automatic cooldown on repeated failures
- **Rate Limiting**: Per-IP sliding window (configurable limits)

### Production Ready

- **Structured Logging**: JSON output for easy parsing
- **Prometheus Metrics**: Request latency, Grok calls, token/cost tracking
- **Health Checks**: Comprehensive system status monitoring
- **Database Support**: SQLite (dev), PostgreSQL (production)
- **Container Ready**: Multi-stage Dockerfile, docker-compose included
- **Fully Configurable**: Environment-based settings with sensible defaults

### API Endpoints

```
POST   /api/v1/conversations           # Single conversation
POST   /api/v1/conversations/bulk      # Batch (up to 500)
GET    /api/v1/insights?limit=100      # Retrieve insights
GET    /api/v1/insights/trends?days=7  # Aggregated analytics
GET    /health                         # Health check
GET    /metrics                        # Prometheus metrics
```

Complete API documentation: [docs/API.md](docs/API.md)

## 📋 System Architecture

```
┌─────────────────────────────────────┐
│   FastAPI HTTP Server               │
│  (Rate Limiting Middleware)         │
├─────────────────────────────────────┤
│  API Endpoints                      │
│  ├─ POST /conversations (single)    │
│  ├─ POST /conversations/bulk        │
│  └─ GET /insights, /trends          │
├─────────────────────────────────────┤
│  Async Queue (in-memory)            │
│  └─ Backpressure: monitor queue     │
│                   depth             │
├─────────────────────────────────────┤
│  Worker Loop                        │
│  ├─ Adaptive batching               │
│  ├─ Cheap prefilter (heuristic)     │
│  └─ Cache lookup (SHA256)           │
├─────────────────────────────────────┤
│  Grok Analysis (pluggable)          │
│  ├─ Sentiment, topics, summary      │
│  └─ Token/cost estimation           │
├─────────────────────────────────────┤
│  Database (SQLAlchemy + SQLite/PG)  │
│  ├─ Conversations table             │
│  ├─ Insights table                  │
│  └─ Analysis cache table            │
└─────────────────────────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design decisions.

## 🔧 Installation

### Requirements

- Python 3.11+
- pip or conda
- Docker & Docker Compose (optional)

### Setup

1. **Clone repository:**
   ```bash
   git clone <repo-url>
   cd grok-insights-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   # Or with dev tools: pip install -e ".[dev,test]"
   ```

4. **Initialize database:**
   ```bash
   make db-init
   ```

5. **Start server:**
   ```bash
   make run
   ```

## 📖 Usage

### Ingest a Conversation

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "tweet_123",
    "text": "Love your service! Great support."
  }'
```

Response:
```json
{"id": 1, "enqueued": true}
```

### Get Insights

```bash
curl http://localhost:8000/api/v1/insights?limit=5
```

### View Trends

```bash
curl "http://localhost:8000/api/v1/insights/trends?days=7"
```

### Load Test

```bash
python scripts/load_test.py \
  --num-conversations 2000 \
  --concurrency 10
```

See [QUICKSTART.md](QUICKSTART.md) for more examples.

## ⚙️ Configuration

Configuration via environment variables (or `.env` file):

```bash
# Application
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./data/data.db  # or postgresql://...

# Grok Analysis
GROK_MODE=mock  # mock or real
GROK_API_KEY=your-api-key-here
GROK_COST_PER_1K=0.002

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60

# Adaptive Batching
MIN_BATCH_SIZE=1
MAX_BATCH_SIZE=50
START_BATCH_SIZE=5

# Circuit Breaker
ERROR_THRESHOLD=5
CIRCUIT_BREAKER_COOLDOWN_SECONDS=10
```

Copy `.env.example` to `.env` and customize.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#configuration) for complete reference.

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test
pytest tests/unit/test_core.py::test_settings_defaults

# Run by marker
pytest -m unit    # Unit tests only
pytest -m integration
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 30-second setup guide
- **[docs/API.md](docs/API.md)** - Complete API reference
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Design decisions & tradeoffs
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide

## 🐳 Docker Deployment

### Development

```bash
docker-compose up --build
curl http://localhost:8000/health
```

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for scaling & production setups.

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics (Prometheus)

```bash
curl http://localhost:8000/metrics
```

Available metrics:
- `requests_total` - Total HTTP requests
- `request_latency_seconds` - Request latency histogram
- `grok_calls_total` - Grok API call count
- `grok_call_errors_total` - Grok API errors
- `analysis_cache_hits_total` - Cache hit count
- `estimated_tokens_total` - Tokens consumed
- `estimated_cost_usd_total` - Estimated cost
- `processing_queue_depth` - Queue depth gauge

### Status Summary

```bash
curl http://localhost:8000/status/summary
```

## 🔐 Security

### Current (Development)

- No authentication required
- Open CORS
- Health check endpoints public

### Production Recommendations

1. Add API key authentication (middleware)
2. Use HTTPS/TLS (nginx reverse proxy)
3. Restrict CORS origins
4. Use secrets manager for API keys
5. Enable database encryption at rest
6. Regular security scanning (trivy, etc.)

See [docs/DEPLOYMENT.md#security-hardening](docs/DEPLOYMENT.md#security-hardening) for detailed hardening guide.

## 🚀 Scaling

### Single Container (< 100 QPS)

✅ Works out of the box with SQLite

### Multi-Container (100–1k QPS)

- Switch to PostgreSQL
- Add load balancer (nginx)
- Scale to 3–5 containers

### High Scale (> 1k QPS)

- Kubernetes deployment
- PostgreSQL with read replicas
- Distributed queue (Redis + Celery)
- Message broker (RabbitMQ)

See [docs/DEPLOYMENT.md#production-architecture](docs/DEPLOYMENT.md#production-architecture) for details.

## 🛠️ Development Commands

```bash
make help              # Show all commands
make install           # Install dependencies
make install-dev       # Install dev dependencies
make run               # Run dev server (hot reload)
make test              # Run tests
make test-cov          # Run with coverage
make lint              # Lint code
make format            # Format code (black + isort)
make docker-build      # Build Docker image
make docker-run        # Run in Docker
make db-init           # Initialize database
```

## 📁 Project Structure

```
src/grok_insights/          # Main package
├── main.py                 # FastAPI app factory
├── core/                   # Core modules (settings, logging)
├── api/                    # API routers (endpoints)
├── db/                     # Database layer (models, session)
├── schemas/                # Pydantic validation schemas
├── services/               # Business logic services
└── worker/                 # Background processing

tests/                      # Test suite
├── unit/                   # Unit tests
├── integration/            # API integration tests
└── load/                   # Load/performance tests

docker/                     # Docker files
docs/                       # Documentation
scripts/                    # Utility scripts
```

## 🎯 Production Checklist

- [x] Async processing with backpressure
- [x] Rate limiting (429 responses)
- [x] Circuit breaker error recovery
- [x] Comprehensive metrics
- [x] Health check endpoint
- [x] Structured JSON logging
- [x] Database migrations (Alembic)
- [x] Configuration management
- [x] Test suite (unit + integration)
- [x] Docker deployment ready
- [x] Security hardening guide
- [x] Performance tuning guide
- [ ] Real Grok API integration (placeholder)
- [ ] Distributed queue (Redis/Celery)
- [ ] Auto-scaling (Kubernetes)

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am "Add my feature"`
4. Format code: `make format`
5. Run tests: `make test`
6. Push: `git push origin feature/my-feature`
7. Submit PR

## 📝 License

MIT License - see LICENSE file

## 🙋 Support

- **Docs**: See `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/example/grok-insights-backend/issues)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) (coming soon)

## 👨‍💻 Author

Built for X / Grok Insights Assessment - February 2026

---

**Ready to scale?** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production setup.
