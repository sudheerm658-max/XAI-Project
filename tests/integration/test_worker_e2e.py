import asyncio
import os
import time
import pytest

from src.grok_insights.core.settings import settings
from src.grok_insights.db.session import init_db, get_session_context
from src.grok_insights.db.models import Conversation, Insight
from src.grok_insights.worker.processor import get_processing_queue, enqueue_conversation, worker_loop


@pytest.mark.asyncio
async def test_worker_processes_enqueued_conversation(tmp_path):
    # Use an in-memory sqlite DB for isolation
    settings.DATABASE_URL = "sqlite:///:memory:"
    settings.GROK_MODE = "mock"
    init_db()

    # Insert a conversation directly
    with get_session_context() as session:
        conv = Conversation(external_id="e2e_test_1", text="I love this product, great support!", raw={})
        session.add(conv)
        session.flush()
        conv_id = conv.id

    # Ensure queue is empty then enqueue
    q = get_processing_queue()
    # Start worker loop
    task = asyncio.create_task(worker_loop())

    try:
        enqueue_conversation(conv_id)

        # Wait up to 10s for insight to appear
        deadline = time.time() + 10
        found = False
        while time.time() < deadline:
            with get_session_context() as session:
                insight = session.query(Insight).filter_by(conversation_id=conv_id).first()
                if insight:
                    found = True
                    break
            await asyncio.sleep(0.2)

        assert found, "Worker did not produce an insight for enqueued conversation"
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
