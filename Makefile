.PHONY: help install install-dev test test-cov lint format clean run docker-build docker-run docker-stop

help:
	@echo "Grok Insights Backend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install dependencies"
	@echo "  make install-dev       Install dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run               Run server (with hot reload)"
	@echo "  make run-prod          Run production server"
	@echo "  make load-test         Run load test"
	@echo ""
	@echo "Quality:"
	@echo "  make test              Run tests"
	@echo "  make test-cov          Run tests with coverage"
	@echo "  make lint              Lint code"
	@echo "  make format            Format code (black + isort)"
	@echo "  make type-check        Type check with mypy"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build      Build Docker image"
	@echo "  make docker-run        Run in Docker"
	@echo "  make docker-stop       Stop Docker container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             Remove build artifacts"
	@echo "  make db-init           Initialize database"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

run:
	uvicorn src.grok_insights.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	uvicorn src.grok_insights.main:app --host 0.0.0.0 --port 8000 --workers 4

load-test:
	python scripts/load_test.py --num-conversations 1000 --concurrency 10

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name "htmlcov" -delete
	find . -type d -name ".mypy_cache" -delete
	rm -rf build/ dist/ *.egg-info/

docker-build:
	docker-compose build

docker-run:
	docker-compose up -d
	@echo "Server running at http://localhost:8000"

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

db-init:
	python -c "from src.grok_insights.db.session import init_db; init_db(); print('Database initialized')"

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

migrate-upgrade:
	alembic upgrade head

migrate-downgrade:
	alembic downgrade -1

.DEFAULT_GOAL := help
