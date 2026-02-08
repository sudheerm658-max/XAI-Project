"""
Background worker for asynchronous conversation analysis.

Implements:
- Adaptive batching with backpressure handling
- Two-stage filtering (cheap prefilter + Grok analysis)
- Semantic caching with SHA256 hashes
- Circuit-breaker error recovery
- Comprehensive observability
"""

import asyncio
import hashlib
import time
import logging
from typing import Dict, Any

from prometheus_client import Counter, Histogram, Gauge

from src.grok_insights.core.settings import settings
from src.grok_insights.db.session import get_session_context
from src.grok_insights.db.models import Conversation, Insight, AnalysisCache, ProcessingLog
from src.grok_insights.worker.grok_client import analyze

logger = logging.getLogger(__name__)

# Global queue for async processing
_processing_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None

# Metrics
grok_calls_total = Counter('grok_calls_total', 'Number of Grok analysis calls')
grok_call_errors = Counter('grok_call_errors_total', 'Number of failed Grok calls')
grok_call_latency = Histogram('grok_call_latency_seconds', 'Grok call latency')
cache_hits = Counter('analysis_cache_hits_total', 'Cache hits')
prefilter_skips = Counter('prefilter_skips_total', 'Conversations skipped by prefilter')
estimated_tokens = Counter('estimated_tokens_total', 'Estimated tokens used')
estimated_cost = Counter('estimated_cost_usd_total', 'Estimated cost in USD')
queue_depth = Gauge('processing_queue_depth', 'Queue depth')


def cheap_prefilter(text: str) -> bool:
    """
    Quick heuristic filter to skip low-value conversations.
    
    Skips:
    - Text < 20 characters
    - URLs and handles
    - Boilerplate thanks messages
    
    Args:
        text: Conversation text
        
    Returns:
        True if text should be analyzed, False if should be skipped
    """
    if not text or len(text.strip()) < settings.MIN_TEXT_LENGTH:
        return False
    
    lt = text.lower()
    
    # Skip pure URLs/handles
    if lt.strip().startswith(('http', 'ftp', '@')):
        return False
    
    # Skip boilerplate
    if any(kw in lt for kw in ('thank', 'thanks', 'welcome')) and len(lt.split()) < 6:
        return False
    
    return True


def get_processing_queue() -> asyncio.Queue:
    """
    Get the global processing queue.
    
    Returns:
        asyncio.Queue instance
    """
    global _processing_queue
    if _processing_queue is None:
        _processing_queue = asyncio.Queue()
    return _processing_queue


def enqueue_conversation(conversation_id: int) -> None:
    """
    Add a conversation to the processing queue.
    
    Args:
        conversation_id: ID of conversation to process
    """
    queue = get_processing_queue()
    try:
        queue.put_nowait(conversation_id)
    except asyncio.QueueFull:
        logger.warning("Processing queue full, dropping conversation %d", conversation_id)


def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics."""
    queue = get_processing_queue()
    return {
        "size": queue.qsize(),
        "worker_running": _worker_task is not None and not _worker_task.done(),
    }


async def worker_loop() -> None:
    """
    Main worker loop for processing conversations.
    
    Implements:
    - Adaptive batching
    - Backpressure handling
    - Circuit breaker
    - Caching
    """
    queue = get_processing_queue()
    
    # Adaptive batching parameters
    min_batch = settings.MIN_BATCH_SIZE
    max_batch = settings.MAX_BATCH_SIZE
    batch_size = settings.START_BATCH_SIZE
    consecutive_errors = 0
    error_threshold = settings.ERROR_THRESHOLD
    cooldown_seconds = settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS
    
    logger.info("Worker loop started (min_batch=%d, max_batch=%d)", min_batch, max_batch)
    
    while True:
        batch = []
        try:
            # Wait for first item with timeout
            item = await asyncio.wait_for(
                queue.get(),
                timeout=settings.QUEUE_FLUSH_TIMEOUT_SECONDS,
            )
            batch.append(item)
            
            # Greedily collect more items up to batch_size
            while len(batch) < batch_size:
                try:
                    item = queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    break
        
        except asyncio.TimeoutError:
            # Nothing available, sleep briefly
            await asyncio.sleep(0.05)
        
        # Check queue depth and adjust batch size (backpressure)
        qsize = queue.qsize()
        queue_depth.set(qsize)
        
        if qsize > settings.BACKPRESSURE_QUEUE_THRESHOLD and batch_size > min_batch:
            batch_size = max(min_batch, batch_size // 2)
            logger.info("Backpressure: reducing batch size to %d (queue=%d)", batch_size, qsize)
        
        if not batch:
            continue
        
        # Process batch
        for conv_id in batch:
            try:
                with get_session_context() as session:
                    # Load conversation
                    conversation = session.query(Conversation).filter_by(id=conv_id).first()
                    if not conversation:
                        logger.warning("Conversation not found: %d", conv_id)
                        continue
                    
                    text = conversation.text or ""
                    
                    # Stage 1: Cheap prefilter
                    if not settings.ENABLE_CHEAP_PREFILTER or cheap_prefilter(text):
                        # Stage 2: Cache lookup
                        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
                        
                        if settings.ENABLE_CACHING:
                            cached = session.query(AnalysisCache).filter_by(text_hash=h).first()
                            if cached:
                                cache_hits.inc()
                                cached.hit_count += 1
                                session.commit()
                                logger.debug("Cache hit for conversation %d", conv_id)
                                continue
                        
                        # Stage 3: Analysis
                        try:
                            start_time = time.time()
                            result = await analyze(text)
                            latency = time.time() - start_time
                            grok_call_latency.observe(latency)
                            grok_calls_total.inc()
                            
                            # Create insight
                            insight = Insight(
                                conversation_id=conv_id,
                                summary=result.get("summary", ""),
                                sentiment=result.get("sentiment", "neutral"),
                                topics=result.get("topics", []),
                                processing_time_ms=int(latency * 1000),
                            )
                            
                            # Handle tokens/cost
                            meta = result.get("meta", {})
                            if isinstance(meta, dict):
                                tokens = int(meta.get("estimated_tokens", 0) or 0)
                                cost = float(meta.get("estimated_cost", 0.0) or 0.0)
                                if tokens:
                                    estimated_tokens.inc(tokens)
                                    insight.tokens_used = tokens
                                if cost:
                                    estimated_cost.inc(cost)
                                    insight.estimated_cost = f"${cost:.6f}"
                            
                            session.add(insight)
                            session.flush()
                            
                            # Cache the result
                            if settings.ENABLE_CACHING:
                                cache_entry = AnalysisCache(
                                    text_hash=h,
                                    insight_id=insight.id,
                                )
                                session.add(cache_entry)
                            
                            session.commit()
                            logger.info("Analyzed conversation %d (latency=%.2fs)", conv_id, latency)
                            
                            # On success, gradually increase batch size
                            consecutive_errors = 0
                            if batch_size < max_batch:
                                batch_size = min(max_batch, int(batch_size * 1.2) + 1)
                        
                        except Exception as e:
                            grok_call_errors.inc()
                            consecutive_errors += 1
                            logger.error("Analysis error for conversation %d: %s", conv_id, str(e))
                            
                            # Shrink batch size to relieve pressure
                            batch_size = max(min_batch, int(batch_size / 2))
                            
                            # Circuit breaker
                            if consecutive_errors >= error_threshold:
                                logger.warning(
                                    "Circuit breaker tripped after %d errors, cooling down %ds",
                                    consecutive_errors, cooldown_seconds,
                                )
                                await asyncio.sleep(cooldown_seconds)
                                consecutive_errors = 0
                    else:
                        # Prefiltered
                        prefilter_skips.inc()
                        logger.debug("Conversation %d skipped by prefilter", conv_id)
            
            except Exception as e:
                logger.exception("Unexpected error processing conversation %d", conv_id)
                continue


def start_worker() -> asyncio.Task:
    """
    Start the background worker task.
    
    Returns:
        asyncio.Task for the worker loop
    """
    global _worker_task
    _worker_task = asyncio.create_task(worker_loop())
    logger.info("Worker task created: %s", _worker_task)
    return _worker_task
