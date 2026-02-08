#!/usr/bin/env python3
"""
Lightweight CSV sampler (no pandas) to create a small conversations JSON
from a large CSV file. Safer for large files on Windows.

Usage:
  python scripts/create_sample_csv_simple.py --csv "C:\path\to\twcs.csv" --output ./data/kaggle/conversations_sample.json --rows 100
"""
import csv
import json
from pathlib import Path
import argparse

def create_sample(csv_path: str, output_path: str, rows: int = 100):
    csv_file = Path(csv_path)
    out_file = Path(output_path)
    if not csv_file.exists():
        raise SystemExit(f"CSV not found: {csv_file}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"Reading up to {rows} rows from {csv_file}")
    conversations = []
    with open(csv_file, 'r', encoding='utf-8', errors='replace') as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= rows:
                break
            # Find text
            text = None
            for col in ('text','tweet_text','content','response_text'):
                if col in row and row[col]:
                    text = row[col].strip()
                    break
            if not text or len(text) < 5:
                continue
            external_id = None
            for col in ('tweet_id','id','tweet_id_str'):
                if col in row and row[col]:
                    external_id = row[col].strip()
                    break
            if not external_id:
                external_id = f"sample_{i}"
            thread_id = None
            for col in ('author_id','user_id','author'):
                if col in row and row[col]:
                    thread_id = f"author_{row[col].strip()}"
                    break
            if not thread_id:
                thread_id = f"thread_{i}"
            conversations.append({
                'external_id': external_id,
                'text': text,
                'thread_id': thread_id,
                'raw': row,
            })
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, indent=2)
    print(f"Wrote {len(conversations)} conversations to {out_file}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--output', default='./data/kaggle/conversations_sample.json')
    p.add_argument('--rows', type=int, default=100)
    args = p.parse_args()
    create_sample(args.csv, args.output, args.rows)
