#!/usr/bin/env python3
"""
Simple load test for Grok Insights backend.
Simulates concurrent ingestion and monitors queue depth + metrics.

Usage:
  python scripts/load_test.py --base-url http://localhost:8000 --num-conversations 1000 --concurrency 10
"""

import asyncio
import aiohttp
import time
import argparse
import json
from typing import List, Dict, Any


async def ingest_bulk(session: aiohttp.ClientSession, base_url: str, conversations: List[Dict[str, Any]]) -> bool:
    """Ingest a batch of conversations."""
    try:
        async with session.post(
            f"{base_url}/api/v1/conversations/bulk",
            json=conversations,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 202:
                return True
            else:
                print(f"Error: {resp.status}")
                return False
    except Exception as e:
        print(f"Request failed: {e}")
        return False


async def get_metrics(session: aiohttp.ClientSession, base_url: str) -> str:
    """Fetch Prometheus metrics."""
    try:
        async with session.get(f"{base_url}/metrics", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as e:
        print(f"Metrics fetch failed: {e}")
    return ""


async def get_health(session: aiohttp.ClientSession, base_url: str) -> dict:
    """Fetch health status."""
    try:
        async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Health check failed: {e}")
    return {}


async def run_load_test(base_url: str, num_conversations: int, concurrency: int, batch_size: int = 50):
    """Run the load test."""
    connector = aiohttp.TCPConnector(limit_per_host=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"Starting load test: {num_conversations} conversations, concurrency={concurrency}")
        
        # generate sample conversations
        def gen_conversation(i: int) -> Dict[str, Any]:
            return {
                "external_id": f"tweet_{i}",
                "text": f"This is test conversation {i}. " * 5 + "Thanks for the support! Love your service.",
                "raw": {"id": f"id_{i}", "timestamp": time.time()},
            }
        
        # split into batches and send concurrently
        batches = []
        for start in range(0, num_conversations, batch_size):
            end = min(start + batch_size, num_conversations)
            batch = [gen_conversation(i) for i in range(start, end)]
            batches.append(batch)
        
        start_time = time.time()
        tasks = [ingest_bulk(session, base_url, batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        ingestion_time = time.time() - start_time
        
        success = sum(results)
        print(f"\nIngestion complete: {success}/{len(batches)} batches successful in {ingestion_time:.2f}s")
        
        # wait for processing and check metrics
        print("\nWaiting for processing to complete...")
        for i in range(6):  # poll for up to 30 seconds
            health = await get_health(session, base_url)
            qsize = health.get('queue_size', 0)
            print(f"  Queue depth: {qsize}")
            if qsize == 0:
                print("  Queue empty!")
                break
            await asyncio.sleep(5)
        
        # fetch final metrics
        print("\n=== Final Metrics ===")
        metrics_text = await get_metrics(session, base_url)
        if metrics_text:
            # Extract key metrics
            for line in metrics_text.split('\n'):
                if 'grok_calls_total' in line and not line.startswith('#'):
                    print(f"  Grok calls: {line.split()[-1]}")
                elif 'analysis_cache_hits_total' in line and not line.startswith('#'):
                    print(f"  Cache hits: {line.split()[-1]}")
                elif 'estimated_tokens_total' in line and not line.startswith('#'):
                    print(f"  Est. tokens: {line.split()[-1]}")
                elif 'estimated_cost_usd_total' in line and not line.startswith('#'):
                    print(f"  Est. cost USD: ${line.split()[-1]}")
        
        health = await get_health(session, base_url)
        print(f"\nFinal health: {health}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load test Grok Insights')
    parser.add_argument('--base-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--num-conversations', type=int, default=500, help='Number of conversations to ingest')
    parser.add_argument('--concurrency', type=int, default=5, help='Number of concurrent requests')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size per request')
    args = parser.parse_args()
    
    asyncio.run(run_load_test(args.base_url, args.num_conversations, args.concurrency, args.batch_size))
