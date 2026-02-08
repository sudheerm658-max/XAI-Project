"""
API endpoints for health checks and metrics.
"""

import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.grok_insights.core.settings import settings
from src.grok_insights.schemas import HealthOut, MetricsOut
from src.grok_insights.db.session import get_session
from src.grok_insights.db.models import Conversation, Insight, AnalysisCache
from src.grok_insights.worker.processor import get_queue_stats
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter()

# Track application start time
_START_TIME = time.time()


@router.get("/health", response_model=HealthOut)
async def health_check(session: Session = Depends(get_session)):
    """
    Health check endpoint.
    
    Returns:
    - status: ok, degraded, or unhealthy
    - uptime_seconds: Seconds since server start
    - queue_size: Number of items pending processing
    - worker_running: Whether background worker is active
    - db_ok: Database connectivity status
    """
    status_val = "ok"
    db_ok = True
    message = None
    
    # Check database
    try:
        session.query(Conversation).limit(1).all()
    except Exception as e:
        db_ok = False
        status_val = "degraded"
        message = f"Database error: {str(e)}"
        logger.error("Health check: database failed", exc_info=True)
    
    # Get queue stats
    queue_stats = get_queue_stats()
    queue_size = queue_stats.get("size", 0)
    
    # Worker status (would need access to app state in production)
    worker_running = queue_stats.get("worker_running", True)
    
    # Determine overall status
    if queue_size > 10000:
        status_val = "degraded"
        message = "High queue depth"
    
    uptime = time.time() - _START_TIME
    
    return HealthOut(
        status=status_val,
        uptime_seconds=uptime,
        queue_size=queue_size,
        worker_running=worker_running,
        db_ok=db_ok,
        message=message,
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """
    Prometheus-format metrics endpoint.
    
    Exposes:
    - Request rates and latencies
    - Grok API call metrics
    - Cache effectiveness
    - Estimated cost/token consumption
    - Queue depth
    """
    return generate_latest().decode("utf-8")


@router.get("/status/summary", response_model=MetricsOut)
async def get_summary(session: Session = Depends(get_session)):
    """
    Get a summary of key metrics.
    """
    # Count totals
    total_conversations = session.query(func.count(Conversation.id)).scalar() or 0
    total_insights = session.query(func.count(Insight.id)).scalar() or 0
    cache_hits = session.query(func.count(AnalysisCache.hit_count)).scalar() or 0
    
    # Calculate cache hit rate
    total_analyses = total_insights
    cache_hit_rate = (cache_hits / total_analyses * 100) if total_analyses > 0 else 0
    
    # Estimate cost
    avg_tokens = 100  # Rough estimate
    cost_per_1k = settings.GROK_COST_PER_1K
    estimated_total_cost = (total_insights * avg_tokens / 1000) * cost_per_1k
    
    # Get queue stats
    queue_stats = get_queue_stats()
    queue_depth = queue_stats.get("size", 0)
    
    return MetricsOut(
        total_requests=0,  # Would need request counting
        total_conversations_ingested=total_conversations,
        total_insights_generated=total_insights,
        cache_hit_rate=cache_hit_rate,
        avg_analysis_latency_ms=300,  # Mock value
        estimated_total_cost_usd=estimated_total_cost,
        queue_depth=queue_depth,
    )
