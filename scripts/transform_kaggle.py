#!/usr/bin/env python3
"""
Transform Kaggle Twitter dataset to Grok Insights format.

Converts Kaggle's tweets.csv into conversation objects compatible with
the Grok Insights Backend ingestion API.

Usage:
  python scripts/transform_kaggle.py
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any


def transform_kaggle_data(csv_path: str = './data/kaggle/tweets.csv', 
                         output_path: str = './data/kaggle/conversations.json'):
    """
    Transform Kaggle CSV to Grok Insights format.
    
    Args:
        csv_path: Path to tweets.csv from Kaggle
        output_path: Output path for conversations.json
    """
    
    input_file = Path(csv_path)
    output_file = Path(output_path)
    
    # Check input exists
    if not input_file.exists():
        print(f"Error: {csv_path} not found")
        print("Download from: https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter")
        return
    
    print(f"Loading {csv_path}...")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        print("Trying with different encoding...")
        df = pd.read_csv(csv_path, encoding='latin1')
    
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {df.columns.tolist()}")
    
    conversations = []
    
    # Transform each row
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"  Processing row {idx}/{len(df)}")
        
        # Extract text (handle different column names)
        text = None
        for col in ['text', 'tweet_text', 'content']:
            if col in df.columns and pd.notna(row.get(col)):
                text = str(row[col]).strip()
                break
        
        if not text or len(text) < 5:
            continue  # Skip empty/very short texts
        
        # Extract ID (handle different column names)
        external_id = None
        for col in ['tweet_id', 'id', 'tweet_id_str']:
            if col in df.columns and pd.notna(row.get(col)):
                external_id = str(row[col])
                break
        
        if not external_id:
            external_id = f"tweet_{idx}"
        
        # Extract author/thread info
        thread_id = None
        for col in ['author_id', 'user_id', 'author']:
            if col in df.columns and pd.notna(row.get(col)):
                thread_id = f"author_{row[col]}"
                break
        
        if not thread_id:
            thread_id = f"thread_{idx}"
        
        # Build conversation object
        conversation = {
            "external_id": external_id,
            "text": text,
            "thread_id": thread_id,
            "raw": {
                **row.to_dict(),
            }
        }
        
        conversations.append(conversation)
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    print(f"\nSaving {len(conversations)} conversations to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, indent=2, default=str)
    
    print(f"Success! Created {output_path}")
    print(f"\nDataset summary:")
    print(f"  Total conversations: {len(conversations)}")
    print(f"  Files saved to: {output_file.parent}")
    print(f"\nNext step:")
    print(f"  python scripts/ingest_sample.py --source {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Transform Kaggle CSV to Grok format')
    parser.add_argument('--source', default='./data/kaggle/tweets.csv', 
                       help='Source CSV file from Kaggle')
    parser.add_argument('--output', default='./data/kaggle/conversations.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    transform_kaggle_data(args.source, args.output)
