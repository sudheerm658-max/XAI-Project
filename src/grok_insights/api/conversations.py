"""
API endpoints for conversation management.
"""

from typing import List
import logging

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks

from src.grok_insights.db.session import get_session
from src.grok_insights.db.models import Conversation
from src.grok_insights.schemas import ConversationCreate, ConversationOut, ConversationInBulk
from src.grok_insights.services.conversation_service import ConversationService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations")


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def ingest_conversation(
    payload: ConversationCreate,
    session: Session = Depends(get_session),
):
    """
    Ingest a single conversation.
    
    - **external_id**: Optional source identifier
    - **thread_id**: Optional conversation thread grouping
    - **text**: Conversation content (required)
    - **raw**: Full raw data from source (optional)
    
    Returns 202 Accepted with conversation ID and queue status.
    """
    service = ConversationService(session)
    conv_id = service.create_conversation(payload)
    logger.info("Conversation ingested: id=%d, ext_id=%s", conv_id, payload.external_id)
    return {"id": conv_id, "enqueued": True}


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def ingest_bulk(
    payload: ConversationInBulk,
    session: Session = Depends(get_session),
):
    """
    Ingest multiple conversations in a single request.
    
    - **max items**: 500 conversations per request
    - Returns 202 Accepted with ingestion summary
    """
    if len(payload.conversations) > 500:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Maximum 500 conversations per bulk request",
        )
    
    service = ConversationService(session)
    conv_ids = service.create_bulk_conversations(payload.conversations)
    logger.info("Bulk ingested %d conversations", len(conv_ids))
    
    return {
        "ingested": len(conv_ids),
        "enqueued": len(conv_ids),
    }


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
):
    """
    Retrieve a conversation by ID.
    """
    conversation = session.query(Conversation).filter_by(id=conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("", response_model=List[ConversationOut])
async def list_conversations(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """
    List conversations with pagination.
    
    - **skip**: Number of items to skip (default 0)
    - **limit**: Maximum items to return (default 100, max 1000)
    """
    limit = min(limit, 1000)
    query = session.query(Conversation).order_by(Conversation.created_at.desc())
    conversations = query.offset(skip).limit(limit).all()
    return conversations
