"""
Database session and connection management.

Provides SQLAlchemy session factory and dependency injection patterns.
"""

from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool

from src.grok_insights.core.settings import settings
from src.grok_insights.db.base import Base

logger = logging.getLogger(__name__)


# Global session factory (initialized on startup)
_SessionLocal: sessionmaker | None = None


def init_db() -> None:
    """
    Initialize database connection and create tables.
    Called once on application startup.
    """
    global _SessionLocal
    
    logger.info("Initializing database: %s", settings.DATABASE_URL)
    
    # Create engine with appropriate pooling strategy
    if settings.database_is_sqlite:
        # SQLite with StaticPool for development/testing
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DATABASE_ECHO,
        )
    else:
        # Use QueuePool for PostgreSQL/MySQL with proper settings
        engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Test connection before use
            echo=settings.DATABASE_ECHO,
        )
    
    # Log all SQL in development
    if settings.DEBUG and settings.DATABASE_ECHO:
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            logger.debug("EXECUTE: %s", statement)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize session factory
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )
    logger.info("Database initialized successfully")


def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy session instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first")
    return _SessionLocal()


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """
    Context manager for database session.
    Automatically closes session after use.
    
    Usage:
        with get_session_context() as session:
            # Use session
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class SessionManager:
    """
    Thread-safe session manager for dependency injection.
    """
    
    def __init__(self):
        if _SessionLocal is None:
            raise RuntimeError("Database not initialized")
        self.SessionLocal = _SessionLocal
    
    def get_session(self) -> Session:
        """Get a new session."""
        return self.SessionLocal()
    
    def __call__(self) -> Session:
        """Allow instance to be used as callable (for FastAPI dependency)."""
        return self.get_session()


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.
    
    Returns:
        SessionManager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
