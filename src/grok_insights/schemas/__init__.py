"""
Pydantic request/response schemas for API validation and documentation.
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# ===== Conversation Schemas =====

class ConversationBase(BaseModel):
    """Base conversation payload."""
    external_id: Optional[str] = Field(None, max_length=256, description="External ID from source system")
    thread_id: Optional[str] = Field(None, max_length=256, description="Thread/conversation group ID")
    text: str = Field(..., min_length=1, max_length=10000, description="Conversation text/content")
    raw: Optional[Dict[str, Any]] = Field(None, description="Full raw data from source")


class ConversationCreate(ConversationBase):
    """Schema for creating a single conversation."""
    pass


class ConversationInBulk(BaseModel):
    """Schema for bulk conversation ingestion."""
    conversations: List[ConversationCreate] = Field(..., max_items=500)


class ConversationOut(ConversationBase):
    """Schema for conversation response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Insight Schemas =====

class InsightBase(BaseModel):
    """Base insight data."""
    summary: Optional[str] = Field(None, max_length=1000)
    sentiment: str = Field("neutral", pattern="^(positive|negative|neutral)$")
    topics: Optional[List[str]] = Field(default_factory=list, max_items=10)
    tokens_used: Optional[int] = None
    estimated_cost: Optional[str] = None
    processing_time_ms: Optional[int] = None


class InsightOut(InsightBase):
    """Schema for insight response."""
    id: int
    conversation_id: int
    grok_model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Aggregated Analytics Schemas =====

class SentimentCount(BaseModel):
    """Sentiment distribution."""
    positive: int = 0
    negative: int = 0
    neutral: int = 0


class TopicCount(BaseModel):
    """Top topics with occurrence count."""
    topic: str
    count: int
    percentage: float


class TrendsOut(BaseModel):
    """Time-windowed trend aggregation."""
    window_days: int
    total_insights: int
    sentiment_counts: SentimentCount
    top_topics: List[TopicCount]
    sentiment_distribution: Dict[str, float]  # percentages


# ===== Health & Status Schemas =====

class HealthOut(BaseModel):
    """Health check response."""
    status: str = Field(..., pattern="^(ok|degraded|unhealthy)$")
    uptime_seconds: float
    queue_size: int
    worker_running: bool
    db_ok: bool
    message: Optional[str] = None


class MetricsOut(BaseModel):
    """Summary of key metrics."""
    total_requests: int
    total_conversations_ingested: int
    total_insights_generated: int
    cache_hit_rate: float
    avg_analysis_latency_ms: float
    estimated_total_cost_usd: float
    queue_depth: int


# ===== Error Schemas =====

class ErrorOut(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    status_code: int
    request_id: Optional[str] = None
