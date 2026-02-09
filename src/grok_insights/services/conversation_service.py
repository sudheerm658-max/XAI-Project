"""
Business logic for conversation management.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from src.grok_insights.db.models import Conversation
from src.grok_insights.schemas import ConversationCreate
from src.grok_insights.worker.processor import enqueue_conversation

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation-related operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_conversation(self, data: ConversationCreate) -> int:
        """
        Create and enqueue a single conversation.
        Skips if external_id already exists (idempotent).
        
        Args:
            data: Conversation input data
            
        Returns:
            Created or existing conversation ID
        """
        # Check if conversation with this external_id already exists
        if data.external_id:
            existing = self.session.query(Conversation).filter_by(external_id=data.external_id).first()
            if existing:
                logger.info("Conversation already exists with external_id=%s, returning existing id=%d", data.external_id, existing.id)
                return existing.id
        
        conversation = Conversation(
            external_id=data.external_id,
            thread_id=data.thread_id,
            text=data.text,
            raw=data.raw,
        )
        self.session.add(conversation)
        self.session.flush()
        conv_id = conversation.id
        self.session.commit()
        
        # Enqueue for processing
        enqueue_conversation(conv_id)
        logger.info("Conversation created and enqueued: id=%d", conv_id)
        
        return conv_id
    
    def create_bulk_conversations(self, conversations: List[ConversationCreate]) -> List[int]:
        """
        Create and enqueue multiple conversations.
        Skips duplicates based on external_id (idempotent).
        
        Args:
            conversations: List of conversation input data
            
        Returns:
            List of created or existing conversation IDs
        """
        conv_ids = []
        new_conversations = []
        
        for data in conversations:
            # Check if conversation with this external_id already exists
            if data.external_id:
                existing = self.session.query(Conversation).filter_by(external_id=data.external_id).first()
                if existing:
                    conv_ids.append(existing.id)
                    logger.debug("Conversation already exists with external_id=%s, id=%d", data.external_id, existing.id)
                    continue
            
            # Create new conversation
            conversation = Conversation(
                external_id=data.external_id,
                thread_id=data.thread_id,
                text=data.text,
                raw=data.raw,
            )
            self.session.add(conversation)
            new_conversations.append((conversation, data.external_id))
        
        # Flush to get IDs for new conversations
        if new_conversations:
            self.session.flush()
            for conv, ext_id in new_conversations:
                conv_ids.append(conv.id)
        
        self.session.commit()
        
        # Enqueue all for processing
        for conv_id in conv_ids:
            enqueue_conversation(conv_id)
        
        logger.info("Bulk created %d new conversations (%d total)", len(new_conversations), len(conv_ids))
        return conv_ids
    
    def get_conversation(self, conversation_id: int) -> Conversation | None:
        """Retrieve a conversation by ID."""
        return self.session.query(Conversation).filter_by(id=conversation_id).first()
    
    def get_by_external_id(self, external_id: str) -> Conversation | None:
        """Retrieve a conversation by external ID."""
        return self.session.query(Conversation).filter_by(external_id=external_id).first()
