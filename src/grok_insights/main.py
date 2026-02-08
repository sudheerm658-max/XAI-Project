"""
Grok Insights Backend - Main Application Factory

Production-ready FastAPI application with modular structure,
async processing, rate limiting, and comprehensive observability.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.grok_insights.core.settings import settings
from src.grok_insights.core.logging_config import setup_logging
from src.grok_insights.db.session import init_db, get_session_manager
from src.grok_insights.api import conversations, insights, health
from src.grok_insights.worker.processor import start_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application lifecycle: startup and shutdown.
    """
    logger.info("Starting Grok Insights Backend v%s", settings.VERSION)
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start background worker
    worker_task = start_worker()
    app.state.worker_task = worker_task
    logger.info("Background worker started")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")
    if hasattr(app.state, 'worker_task'):
        app.state.worker_task.cancel()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    setup_logging(settings.LOG_LEVEL)
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-ready backend for conversation analysis via Grok",
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Include routers
    app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
    app.include_router(insights.router, prefix="/api/v1", tags=["insights"])
    app.include_router(health.router, tags=["health"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Welcome endpoint with links to available resources."""
        return JSONResponse({
            "message": "Welcome to Grok Insights Backend",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "status": "/status/summary",
            "endpoints": {
                "conversations": "/api/v1/conversations",
                "insights": "/api/v1/insights",
                "trends": "/api/v1/insights/trends"
            }
        })
    
    logger.info("FastAPI application created with %d routes", len(app.routes))
    return app


# Global app instance for server startup
app = create_app()
