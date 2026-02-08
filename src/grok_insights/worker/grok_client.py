"""
Pluggable Grok client for conversation analysis.

Supports:
- Mock mode (development/testing)
- Real mode (production, requires API key)
"""

import asyncio
import httpx
import os
import time
from typing import Dict, Any
import logging
import json

from src.grok_insights.core.settings import settings

logger = logging.getLogger(__name__)


async def analyze(text: str) -> Dict[str, Any]:
    """
    Analyze text using Grok API.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with:
        - summary: Brief summary
        - sentiment: positive | negative | neutral
        - topics: List of extracted topics
        - meta: Metadata (tokens, latency, cost)
    """
    if settings.GROK_MODE == 'mock':
        return await _analyze_mock(text)
    elif settings.GROK_MODE == 'real':
        return await _analyze_real(text)
    else:
        raise ValueError(f"Unknown GROK_MODE: {settings.GROK_MODE}")


async def _analyze_mock(text: str) -> Dict[str, Any]:
    """
    Mock analysis implementation for development.
    
    Simple heuristic sentiment detection and topic extraction.
    """
    start_time = time.time()
    
    # Simulate network latency
    simulated_latency = min(0.3 + len(text) / 2000, 0.9)
    await asyncio.sleep(simulated_latency)
    
    # Simple sentiment detection
    lt = (text or "").lower()
    sentiment = "neutral"
    if any(w in lt for w in ('love', 'great', 'happy', 'thanks', 'thank you', 'excellent')):
        sentiment = "positive"
    if any(w in lt for w in ('hate', 'bad', 'angry', 'worst', 'terrible', 'awful')):
        sentiment = "negative"
    
    # Basic summary (first 500 chars)
    summary = (text or "")[:500]
    
    # Naive topic extraction: long words
    words = [w.strip('.,!?:;()"\'') for w in lt.split()]
    candidates = [w for w in words if len(w) > 5 and w not in {'thanks', 'great', 'really'}]
    
    seen = set()
    topics = []
    for w in candidates:
        if w not in seen and w.isalpha():
            seen.add(w)
            topics.append(w)
            if len(topics) >= 5:
                break
    
    # Estimate tokens (rough: ~4 chars per token)
    estimated_tokens = max(1, int(len(text) / 4) if text else 1)
    cost_per_1k = settings.GROK_COST_PER_1K
    estimated_cost = (estimated_tokens / 1000.0) * cost_per_1k
    
    latency = time.time() - start_time
    
    return {
        'summary': summary,
        'sentiment': sentiment,
        'topics': topics,
        'meta': {
            'mock': True,
            'latency': latency,
            'estimated_tokens': estimated_tokens,
            'estimated_cost': estimated_cost,
        },
    }


async def _analyze_real(text: str) -> Dict[str, Any]:
    """
    Real Grok API integration via xAI API.
    
    Requires:
    - GROK_API_KEY environment variable (set in settings)
    - Network access to api.x.ai
    
    Uses OpenAI-compatible chat completions API.
    """
    if not settings.GROK_API_KEY:
        logger.error("GROK_API_KEY not configured. Set it in .env or environment variables.")
        raise ValueError(
            "GROK_API_KEY not configured. "
            "Please set GROK_API_KEY environment variable or update .env file."
        )
    
    start_time = time.time()

    # Prepare system prompt
    system_prompt = (
        "Analyze the provided text and return a JSON response with exactly these fields:\n"
        "{\n  \"summary\": \"1-2 sentence summary of the text\",\n"
        "  \"sentiment\": \"positive, negative, or neutral\",\n"
        "  \"topics\": [\"topic1\", \"topic2\", ...],\n"
        "  \"tokens_used\": estimated number of tokens used\n}\n\n"
        "Return ONLY valid JSON, no additional text."
    )

    timeout = settings.GROK_HTTP_TIMEOUT
    max_retries = max(1, settings.GROK_MAX_RETRIES)
    backoff_base = max(0.1, settings.GROK_RETRY_BACKOFF_BASE)
    max_jitter = max(0.0, settings.GROK_RETRY_MAX_JITTER)

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{settings.GROK_API_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.GROK_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text},
                        ],
                        "temperature": 0.0,
                        "max_tokens": 500,
                    },
                )

            # Handle 429 specially (rate limit)
            if resp.status_code == 429:
                retry_after = None
                try:
                    retry_after = int(resp.headers.get("Retry-After", "0"))
                except Exception:
                    retry_after = None
                wait = retry_after if retry_after and retry_after > 0 else (backoff_base * (2 ** (attempt - 1)))
                # jitter
                wait = wait + (max_jitter * (0.5 - os.urandom(1)[0] / 255.0))
                logger.warning("Grok API rate limited (429). Attempt %d/%d - sleeping %.2fs", attempt, max_retries, wait)
                await asyncio.sleep(max(0.0, wait))
                last_exc = httpx.HTTPStatusError("429 Too Many Requests", request=resp.request, response=resp)
                continue

            resp.raise_for_status()
            result = resp.json()

            # Extract the content
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
            else:
                raise ValueError("Unexpected response format from Grok API")

            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse Grok JSON response; using fallback parser")
                analysis = _parse_grok_response_fallback(content)

            tokens_used = result.get("usage", {}).get("completion_tokens", 0) or 0
            if isinstance(analysis, dict) and "tokens_used" in analysis:
                try:
                    tokens_used = int(analysis.get("tokens_used", tokens_used))
                except Exception:
                    pass

            cost_per_1k = settings.GROK_COST_PER_1K
            estimated_cost = (tokens_used / 1000.0) * cost_per_1k

            latency = time.time() - start_time
            logger.info("Grok analysis succeeded (attempt=%d) latency=%.2fs tokens=%d cost=$%.6f", attempt, latency, tokens_used, estimated_cost)

            return {
                "summary": analysis.get("summary", text[:200]) if isinstance(analysis, dict) else text[:200],
                "sentiment": (analysis.get("sentiment", "neutral").lower() if isinstance(analysis, dict) else "neutral"),
                "topics": (analysis.get("topics", []) if isinstance(analysis, dict) else []),
                "meta": {
                    "mock": False,
                    "latency": latency,
                    "estimated_tokens": tokens_used,
                    "estimated_cost": estimated_cost,
                    "model": settings.GROK_MODEL,
                },
            }

        except httpx.HTTPStatusError as e:
            last_exc = e
            logger.error("Grok API HTTP error on attempt %d/%d: %s", attempt, max_retries, str(e))
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_exc = e
            logger.warning("Grok API transport/timeout error on attempt %d/%d: %s", attempt, max_retries, str(e))
        except Exception as e:
            last_exc = e
            logger.exception("Unexpected error calling Grok API on attempt %d/%d", attempt, max_retries)

        # Backoff before next attempt
        if attempt < max_retries:
            backoff = backoff_base * (2 ** (attempt - 1))
            # jitter in range [-max_jitter/2, +max_jitter/2]
            jitter = (os.urandom(2)[0] / 255.0 - 0.5) * max_jitter
            wait = max(0.0, backoff + jitter)
            logger.info("Retrying Grok API in %.2fs (attempt %d/%d)", wait, attempt + 1, max_retries)
            await asyncio.sleep(wait)

    # All retries failed
    logger.error("Grok API analysis failed after %d attempts", max_retries)
    if last_exc:
        raise last_exc
    raise RuntimeError("Grok API analysis failed")


def _parse_grok_response_fallback(content: str) -> Dict[str, Any]:
    """
    Fallback parser if Grok response isn't valid JSON.
    Extracts structured data from plain text response.
    """
    result = {
        "summary": content[:200] if content else "",
        "sentiment": "neutral",
        "topics": [],
    }
    
    # Try to extract sentiment
    content_lower = content.lower()
    if "positive" in content_lower or "good" in content_lower:
        result["sentiment"] = "positive"
    elif "negative" in content_lower or "bad" in content_lower:
        result["sentiment"] = "negative"
    
    return result


async def analyze_batch(texts: list[str]) -> list[Dict[str, Any]]:
    """
    Analyze multiple texts in parallel.
    
    Args:
        texts: List of texts to analyze
        
    Returns:
        List of analysis results
    """
    tasks = [analyze(text) for text in texts]
    return await asyncio.gather(*tasks)
