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
        
        Args:
            data: Conversation input data
            
        Returns:
            Created conversation ID
        """
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
        
        Args:
            conversations: List of conversation input data
            
        Returns:
            List of created conversation IDs
        """
        conv_ids = []
        for data in conversations:
            conversation = Conversation(
                external_id=data.external_id,
                thread_id=data.thread_id,
                text=data.text,
                raw=data.raw,
            )
            self.session.add(conversation)
            self.session.flush()
            conv_ids.append(conversation.id)
        
        self.session.commit()
        
        # Enqueue all for processing
        for conv_id in conv_ids:
            enqueue_conversation(conv_id)
        
        logger.info("Bulk created %d conversations", len(conv_ids))
        return conv_ids
    
    def get_conversation(self, conversation_id: int) -> Conversation | None:
        """Retrieve a conversation by ID."""
        return self.session.query(Conversation).filter_by(id=conversation_id).first()
    
    def get_by_external_id(self, external_id: str) -> Conversation | None:
        """Retrieve a conversation by external ID."""
        return self.session.query(Conversation).filter_by(external_id=external_id).first()
