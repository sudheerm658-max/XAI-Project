#!/usr/bin/env python3
"""
Sample data ingester for Grok Insights.
Can ingest from CSV or JSON files and submit conversations to the backend.

Usage:
  python scripts/ingest_sample.py --source sample_data.json --api-url http://localhost:8000 --batch-size 100
"""

import asyncio
import aiohttp
import argparse
import json
import csv
from pathlib import Path
from typing import List, Dict, Any


async def ingest_conversations_bulk(session: aiohttp.ClientSession, api_url: str, conversations: List[Dict[str, Any]]) -> int:
    """Ingest a batch of conversations, return count ingested."""
    try:
        async with session.post(
            f"{api_url}/api/v1/conversations/bulk",
            json=conversations,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 202:
                data = await resp.json()
                return data.get('ingested', 0)
    except Exception as e:
        print(f"Ingestion error: {e}")
    return 0


async def load_and_ingest(api_url: str, source_file: str, batch_size: int = 100):
    """Load data from file and ingest into backend."""
    source_path = Path(source_file)
    if not source_path.exists():
        print(f"File not found: {source_file}")
        return
    
    conversations = []
    
    # Load data
    if source_file.endswith('.json'):
        with open(source_file, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                conversations = data
            elif isinstance(data, dict) and 'conversations' in data:
                conversations = data['conversations']
    elif source_file.endswith('.csv'):
        with open(source_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conversations.append({
                    'external_id': row.get('id') or row.get('external_id'),
                    'text': row.get('text') or row.get('content'),
                    'raw': dict(row),
                })
    else:
        print("Unsupported file format. Use .json or .csv")
        return
    
    print(f"Loaded {len(conversations)} conversations from {source_file}")
    
    # Ingest in batches
    total_ingested = 0
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i+batch_size]
            ingested = await ingest_conversations_bulk(session, api_url, batch)
            total_ingested += ingested
            print(f"  Batch {i//batch_size + 1}: ingested {ingested} conversations")
            await asyncio.sleep(0.5)  # gentle rate limiting
    
    print(f"\nTotal ingested: {total_ingested}/{len(conversations)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest sample data')
    parser.add_argument('--source', required=True, help='Source file (JSON or CSV)')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    args = parser.parse_args()
    
    asyncio.run(load_and_ingest(args.api_url, args.source, args.batch_size))
