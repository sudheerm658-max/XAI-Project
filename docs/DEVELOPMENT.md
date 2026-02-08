# Development Guide

## Project Structure

```
grok-insights-backend/
├── src/                                # Source code
│   └── grok_insights/                 # Main package
│       ├── __init__.py
│       ├── main.py                    # FastAPI app factory
│       ├── core/                      # Core modules
│       │   ├── __init__.py
│       │   ├── settings.py            # Configuration (pydantic-settings)
│       │   └── logging_config.py      # Structured logging
│       ├── api/                       # FastAPI routers
│       │   ├── __init__.py
│       │   ├── conversations.py       # /api/v1/conversations endpoints
│       │   ├── insights.py            # /api/v1/insights endpoints
│       │   └── health.py              # /health, /metrics endpoints
│       ├── db/                        # Database layer
│       │   ├── __init__.py
│       │   ├── base.py               # SQLAlchemy declarative base
│       │   ├── models.py             # ORM models
│       │   └── session.py            # Session management & DI
│       ├── schemas/                   # Pydantic models
│       │   └── __init__.py           # Request/response schemas
│       ├── services/                  # Business logic
│       │   ├── __init__.py
│       │   ├── conversation_service.py
│       │   └── insight_service.py
│       └── worker/                    # Async background processing
│           ├── __init__.py
│           ├── processor.py           # Worker loop & queue
│           └── grok_client.py         # Pluggable Grok client
│
├── tests/                             # Test suite
│   ├── conftest.py                    # Pytest fixtures
│   ├── unit/                          # Unit tests
│   ├── integration/                   # API integration tests
│   └── load/                          # Load/performance tests
│
├── docker/                            # Docker build files
│   ├── Dockerfile                     # Production image
│   └── Dockerfile.dev                 # Development image
│
├── scripts/                           # Utility scripts
│   ├── __init__.py
│   ├── load_test.py                   # Load testing
│   ├── ingest_sample.py               # Test data ingestion
│   └── init_db.py                     # Database initialization
│
├── docs/                              # Documentation
│   ├── api.md                         # API reference
│   ├── architecture.md                # Architecture & design
│   ├── deployment.md                  # Deployment guide
│   ├── development.md                 # This file
│   └── troubleshooting.md             # Troubleshooting guide
│
├── alembic/                           # Database migrations
│   ├── versions/                      # Migration files
│   └── env.py
│
├── pyproject.toml                     # Python project metadata
├── Makefile                           # Development commands
├── docker-compose.yml                 # Dev/test environment
├── docker-compose.prod.yml            # Production environment
├── pytest.ini                         # Pytest configuration
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── .dockerignore                      # Docker ignore rules
└── README.md                          # Project overview
```

## Setup

### Prerequisites
- Python 3.11+
- pip or conda
- Docker (optional, for containerized development)

### Local Development

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows: venv\Scripts\activate
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev,test]"
   # or using: make install-dev
   ```

3. **Initialize database:**
   ```bash
   make db-init
   # or: python -c "from src.grok_insights.db.session import init_db; init_db()"
   ```

4. **Start development server:**
   ```bash
   make run
   # Runs: uvicorn src.grok_insights.main:app --reload
   ```

5. **Server is running at:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## Development Workflow

### Code Quality

**Format code:**
```bash
make format
# Runs: black + isort
```

**Lint code:**
```bash
make lint
# Runs: ruff + mypy
```

**Run tests:**
```bash
make test
# Runs: pytest tests/
```

**Test coverage:**
```bash
make test-cov
# Generates: htmlcov/index.html
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_core.py

# Specific test
pytest tests/unit/test_core.py::test_settings_defaults

# With markers
pytest -m unit
pytest -m integration
pytest -m "not slow"

# With coverage
pytest --cov=src --cov-report=html
```

### Load Testing

```bash
# Quick test (500 conversations)
make load-test

# Custom parameters
python scripts/load_test.py \
  --base-url http://localhost:8000 \
  --num-conversations 5000 \
  --concurrency 20 \
  --batch-size 100
```

### Configuration

Configuration is managed via `pydantic-settings` and environment variables.

**Development configuration (.env):**
```bash
cp .env.example .env
# Edit .env with your settings
```

**Environment variables take precedence over .env file.**

See `src/grok_insights/core/settings.py` for all available options.

### Database Migrations (Alembic)

```bash
# Create a new migration
alembic revision --autogenerate -m "Add user_id to conversations"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current
```

## Architecture Patterns

### Dependency Injection

FastAPI's `Depends()` is used for dependency injection:

```python
from fastapi import Depends
from src.grok_insights.db.session import get_session

@router.get("/items")
async def list_items(session: Session = Depends(get_session)):
    return session.query(Item).all()
```

### Service Layer

Business logic lives in services:

```python
# services/conversation_service.py
class ConversationService:
    def __init__(self, session: Session):
        self.session = session
    
    def create_conversation(self, data: ConversationCreate) -> int:
        # Business logic here
        pass

# Usage in endpoint
@router.post("/conversations")
async def create(data: ConversationCreate, session: Session = Depends(get_session)):
    service = ConversationService(session)
    conv_id = service.create_conversation(data)
    return {"id": conv_id}
```

### Async/Await

All I/O is async:

```python
# Endpoints
@router.post("/ingest")
async def ingest(payload: ConversationCreate):
    # Async database operations
    # Async queue operations
    # Async external API calls

# Worker
async def worker_loop():
    while True:
        # Async processing
        await analyze(text)
```

### Structured Logging

Logging produces JSON output in production:

```python
import logging
from src.grok_insights.core.logging_config import get_logger

logger = get_logger(__name__)

logger.info("User created", extra={"user_id": 123})
# Output: {"timestamp": "...", "level": "INFO", "logger": "...", "message": "User created", "user_id": 123}
```

## Common Tasks

### Add a new API endpoint

1. Create handler in `api/new_route.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/new")

@router.get("")
async def list():
    return {"items": []}
```

2. Include in `main.py`:
```python
from src.grok_insights.api import new_route

app.include_router(new_route.router, prefix="/api/v1", tags=["new"])
```

3. Add tests in `tests/integration/test_new_route.py`:
```python
def test_list(client):
    response = client.get("/api/v1/new")
    assert response.status_code == 200
```

### Add a new database model

1. Create model in `db/models.py`:
```python
class NewModel(Base, TimestampMixin):
    __tablename__ = "new_models"
    id = Column(Integer, primary_key=True)
    name = Column(String(256))
```

2. Create migration:
```bash
alembic revision --autogenerate -m "Add new_models table"
```

3. Apply migration:
```bash
alembic upgrade head
```

### Add a new setting

1. Add to `core/settings.py`:
```python
class Settings(BaseSettings):
    NEW_SETTING: str = "default_value"
```

2. Use in code:
```python
from src.grok_insights.core.settings import settings

value = settings.NEW_SETTING
```

3. Set via environment:
```bash
export NEW_SETTING="custom_value"
```

## Debugging

### Enable SQL logging

```python
# In settings
DATABASE_ECHO: bool = True
```

### Enable debug logging

```bash
export LOG_LEVEL=DEBUG
python run_server.py
```

### Use debugger

```python
import pdb; pdb.set_trace()
```

Or with VS Code:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["src.grok_insights.main:app", "--reload"],
            "console": "integratedTerminal"
        }
    ]
}
```

## Performance Considerations

### Database

- Use connection pooling (configured in settings)
- Index frequently queried columns (done in models)
- Use pagination for large result sets

### Async

- Don't block the event loop with CPU-intensive work
- Use `asyncio.create_task()` for fire-and-forget operations
- Use `asyncio.gather()` for concurrent operations

### Caching

- Semantic caching via SHA256 hashes (in worker)
- Consider adding Redis for distributed caching

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and commit: `git commit -am "Add my feature"`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a pull request

**Code style:**
- Format with `black` and `isort`
- Lint with `ruff`
- Type check with `mypy`
- Test coverage > 80%

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Asyncio](https://docs.python.org/3/library/asyncio.html)

## Support

For issues or questions:
1. Check [troubleshooting.md](troubleshooting.md)
2. Review existing [GitHub issues](https://github.com/example/grok-insights-backend/issues)
3. Create a new issue with details
