"""
SQLAlchemy ORM models for conversation analysis.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Index, func, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.grok_insights.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """
    Stores conversation data with full thread context.
    
    Supports incremental updates via thread_id tracking.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(256), index=True, nullable=True, unique=True)
    thread_id = Column(String(256), index=True, nullable=True)  # For conversation grouping
    text = Column(Text, nullable=False)
    raw = Column(JSON, nullable=True)  # Full JSON from source
    
    # Relationships
    insights = relationship("Insight", back_populates="conversation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_conversation_ext_id", "external_id"),
        Index("idx_conversation_thread_id", "thread_id"),
        Index("idx_conversation_created_at", "created_at"),
    )


class Insight(Base, TimestampMixin):
    """
    Analysis results from Grok.
    
    Contains sentiment, topics, summary, and metadata.
    """
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True, nullable=False)
    
    # Analysis results
    summary = Column(Text, nullable=True)
    sentiment = Column(String(32), nullable=False, default="neutral")  # positive, negative, neutral
    topics = Column(JSON, nullable=True)  # List of extracted topics
    
    # Cost tracking
    tokens_used = Column(Integer, nullable=True, default=0)
    estimated_cost = Column(String(32), nullable=True)  # "$0.02" format
    
    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    grok_model = Column(String(64), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="insights")
    
    __table_args__ = (
        Index("idx_insight_conversation_id", "conversation_id"),
        Index("idx_insight_sentiment", "sentiment"),
        Index("idx_insight_created_at", "created_at"),
    )


class AnalysisCache(Base, TimestampMixin):
    """
    Cache to avoid re-analyzing duplicate conversations.
    
    Maps text hash → Insight for semantic deduplication.
    """
    __tablename__ = "analysis_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    text_hash = Column(String(256), unique=True, index=True, nullable=False)
    insight_id = Column(Integer, ForeignKey("insights.id"), nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)  # Track cache effectiveness
    
    __table_args__ = (
        Index("idx_text_hash", "text_hash"),
    )


class ProcessingLog(Base, TimestampMixin):
    """
    Audit log for all processing events.
    
    Useful for debugging, cost tracking, and compliance.
    """
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    event_type = Column(String(64), nullable=False)  # ingestion, analysis_start, analysis_complete, error, cache_hit
    status = Column(String(32), nullable=False)  # success, error, skipped
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Additional context
    
    __table_args__ = (
        Index("idx_log_event_type", "event_type"),
        Index("idx_log_status", "status"),
        Index("idx_log_created_at", "created_at"),
    )
