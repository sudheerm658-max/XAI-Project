#!/usr/bin/env python3
"""
Create a small sample (N rows) from a large Kaggle CSV and transform
rows into Grok Insights conversation objects, saving to a JSON file.

Usage:
  python scripts/create_sample_from_csv.py --csv "C:\path\to\twcs.csv" --output ./data/kaggle/conversations_sample.json --rows 100
"""
import argparse
import pandas as pd
import json
from pathlib import Path

def create_sample(csv_path: str, output_path: str, rows: int = 100):
    csv_file = Path(csv_path)
    out_file = Path(output_path)
    if not csv_file.exists():
        raise SystemExit(f"CSV not found: {csv_file}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"Loading first {rows} rows from {csv_file}...")
    try:
        df = pd.read_csv(csv_file, nrows=rows, encoding='utf-8')
    except Exception:
        df = pd.read_csv(csv_file, nrows=rows, encoding='latin1')
    print(f"Loaded {len(df)} rows; transforming...")
    conversations = []
    for idx, row in df.iterrows():
        # choose text field
        text = None
        for col in ('text','tweet_text','content'):
            if col in df.columns and pd.notna(row.get(col)):
                text = str(row[col]).strip()
                break
        if not text or len(text) < 5:
            continue
        external_id = None
        for col in ('tweet_id','id','tweet_id_str'):
            if col in df.columns and pd.notna(row.get(col)):
                external_id = str(row[col])
                break
        if not external_id:
            external_id = f"sample_{idx}"
        thread_id = None
        for col in ('author_id','user_id','author'):
            if col in df.columns and pd.notna(row.get(col)):
                thread_id = f"author_{row[col]}"
                break
        if not thread_id:
            thread_id = f"thread_{idx}"
        conversations.append({
            'external_id': external_id,
            'text': text,
            'thread_id': thread_id,
            'raw': row.to_dict(),
        })
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, indent=2, default=str)
    print(f"Wrote {len(conversations)} conversations to {out_file}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True, help='Path to twcs.csv')
    p.add_argument('--output', default='./data/kaggle/conversations_sample.json')
    p.add_argument('--rows', type=int, default=100)
    args = p.parse_args()
    create_sample(args.csv, args.output, args.rows)
