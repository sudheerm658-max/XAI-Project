#!/usr/bin/env python3
r"""
Twitter CSV to Grok Insights ingester.
Transforms Twitter CSV (twcs.csv) to the backend's conversation format.

Usage:
  python scripts/ingest_twitter.py --source C:\Users\sudhe\Downloads\twitter-dataset\twcs\twcs.csv --api-url http://localhost:8000 --batch-size 50
"""

import asyncio
import aiohttp
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Any


async def ingest_conversations_bulk(session: aiohttp.ClientSession, api_url: str, conversations: List[Dict[str, Any]]) -> int:
    """Ingest a batch of conversations, return count ingested."""
    try:
        # API expects {"conversations": [...]}
        payload = {"conversations": conversations}
        async with session.post(
            f"{api_url}/api/v1/conversations/bulk",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            text = await resp.text()
            if resp.status in (202, 200):
                data = await resp.json()
                return data.get('ingested', len(conversations))
            else:
                print(f"  ERROR {resp.status}: {text}")
                # For debugging: print first conversation in batch
                if conversations:
                    print(f"  Sample conversation in batch: {conversations[0]}")
    except Exception as e:
        print(f"  Ingestion error: {e}")
        import traceback
        traceback.print_exc()
    return 0


async def ingest_twitter_csv(api_url: str, csv_file: str, batch_size: int = 50, limit: int = None):
    """Load Twitter CSV and ingest into backend."""
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"File not found: {csv_file}")
        return
    
    conversations = []
    
    # Parse Twitter CSV
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            
            # Skip empty or very short texts
            text = row.get('text', '').strip()
            if len(text) < 5:
                continue
            
            conversations.append({
                'external_id': f"tweet_{row.get('tweet_id', i)}",
                'text': text,
                'raw': dict(row),  # Store all original fields in raw
            })
    
    print(f"Loaded {len(conversations)} conversations from Twitter CSV")
    
    # Ingest in batches
    total_ingested = 0
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i+batch_size]
            ingested = await ingest_conversations_bulk(session, api_url, batch)
            total_ingested += ingested
            print(f"  Batch {i//batch_size + 1}: ingested {ingested}/{len(batch)} conversations")
            await asyncio.sleep(0.5)  # gentle rate limiting
    
    print(f"\n✓ Total ingested: {total_ingested}/{len(conversations)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest Twitter CSV into Grok Insights')
    parser.add_argument('--source', required=True, help='Path to Twitter CSV file')
    parser.add_argument('--api-url', default='http://localhost:8000', help='Backend API URL')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for ingestion')
    parser.add_argument('--limit', type=int, default=None, help='Max conversations to ingest (for testing)')
    
    args = parser.parse_args()
    asyncio.run(ingest_twitter_csv(args.api_url, args.source, args.batch_size, args.limit))
