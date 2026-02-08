FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Production stage
FROM base as production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.grok_insights.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

COPY requirements.txt .
RUN pip install --no-cache-dir -e .[dev,test]

COPY . .

EXPOSE 8000 8001

CMD ["uvicorn", "src.grok_insights.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
