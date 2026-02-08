"""
API endpoints for insights and analytics.
"""

from typing import List
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status

from src.grok_insights.db.session import get_session
from src.grok_insights.db.models import Insight
from src.grok_insights.schemas import InsightOut, TrendsOut, SentimentCount, TopicCount
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights")


@router.get("", response_model=List[InsightOut])
async def get_insights(
    limit: int = 100,
    sentiment: str | None = None,
    session: Session = Depends(get_session),
):
    """
    Retrieve recent insights with optional filtering.
    
    - **limit**: Maximum number of insights (default 100, max 1000)
    - **sentiment**: Filter by sentiment (positive, negative, neutral)
    """
    limit = min(limit, 1000)
    query = session.query(Insight).order_by(Insight.created_at.desc())
    
    if sentiment:
        if sentiment not in ["positive", "negative", "neutral"]:
            raise HTTPException(status_code=400, detail="Invalid sentiment value")
        query = query.filter_by(sentiment=sentiment)
    
    insights = query.limit(limit).all()
    return insights


@router.get("/conversation/{conversation_id}", response_model=List[InsightOut])
async def get_insights_for_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
):
    """
    Get all insights for a specific conversation.
    """
    insights = session.query(Insight).filter_by(conversation_id=conversation_id).all()
    if not insights:
        raise HTTPException(status_code=404, detail="No insights found for this conversation")
    return insights


@router.get("/trends", response_model=TrendsOut)
async def get_trends(
    days: int = 7,
    session: Session = Depends(get_session),
):
    """
    Get aggregated trends over a time window.
    
    - **days**: Time window in days (default 7)
    
    Returns sentiment distribution and top topics.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    insights = session.query(Insight).filter(Insight.created_at >= cutoff).all()
    
    total = len(insights)
    if total == 0:
        return TrendsOut(
            window_days=days,
            total_insights=0,
            sentiment_counts=SentimentCount(),
            top_topics=[],
            sentiment_distribution={},
        )
    
    # Count sentiments
    sentiment_counts = defaultdict(int)
    topic_counts = defaultdict(int)
    
    for insight in insights:
        sentiment_counts[insight.sentiment or "neutral"] += 1
        if insight.topics:
            for topic in insight.topics:
                topic_counts[topic] += 1
    
    # Calculate percentages
    sentiment_dist = {
        k: (v / total * 100) for k, v in sentiment_counts.items()
    }
    
    # Top topics
    top_topics = [
        TopicCount(topic=t, count=c, percentage=(c / total * 100))
        for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    return TrendsOut(
        window_days=days,
        total_insights=total,
        sentiment_counts=SentimentCount(
            positive=sentiment_counts.get("positive", 0),
            negative=sentiment_counts.get("negative", 0),
            neutral=sentiment_counts.get("neutral", 0),
        ),
        top_topics=top_topics,
        sentiment_distribution=sentiment_dist,
    )


@router.get("/{insight_id}", response_model=InsightOut)
async def get_insight(
    insight_id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve a specific insight by ID.
    """
    insight = session.query(Insight).filter_by(id=insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight
