# Kaggle Dataset Integration Guide

## Overview

This guide shows how to download the **Twitter Customer Support** dataset from Kaggle and ingest it into your Grok Insights Backend for real-world analysis.

**Dataset:** [Customer Support on Twitter (thoughtvector)](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)  
- ~3,000 customer support conversations
- Fields: tweet_id, author_id, inbound/outbound status, text, created_at

## Prerequisites

1. **Kaggle Account**
   - Sign up at [kaggle.com](https://kaggle.com) (free)
   - Verify email

2. **Kaggle API Credentials**
   - Go to [Account Settings → API](https://www.kaggle.com/settings/account)
   - Click "Create New API Token"
   - Downloads `kaggle.json`
   - Save to: `~/.kaggle/kaggle.json` (or `C:\Users\{username}\.kaggle\kaggle.json` on Windows)

3. **Dependencies**
   ```bash
   pip install kaggle pandas
   ```

## Step 1: Set Up Kaggle API

### Windows PowerShell

```powershell
# Create .kaggle directory
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.kaggle" | Out-Null

# Place your kaggle.json file there
Copy-Item -Path ".\kaggle.json" -Destination "$env:USERPROFILE\.kaggle\kaggle.json"

# Verify
Get-Content "$env:USERPROFILE\.kaggle\kaggle.json"
```

### macOS/Linux

```bash
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

## Step 2: Download the Dataset

### Option A: Using Kaggle CLI (Recommended)

```bash
# Download the dataset
kaggle datasets download -d thoughtvector/customer-support-on-twitter

# Unzip
Expand-Archive -Path customer-support-on-twitter.zip -DestinationPath ./data/kaggle

# List files
Get-ChildItem ./data/kaggle
```

**Expected output:**
```
sentiment_analysis.csv
sqlite.db
tweets.csv
```

### Option B: Manual Download

1. Visit https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter
2. Click "Download" (top right)
3. Extract to `./data/kaggle/`

## Step 3: Inspect the Data

### Check CSV Structure

```powershell
# Read first few rows
python -c "
import pandas as pd
df = pd.read_csv('./data/kaggle/tweets.csv', nrows=5)
print(df.columns.tolist())
print(df.head())
"
```

**Expected columns:**
```
['tweet_id', 'author_id', 'inbound', 'created_at', 'text', 'response_tweet_id', 'response_text']
```

### Sample Row:
```
tweet_id: 123456789
text: "Love your customer service! They helped me resolve my issue so quickly."
inbound: True
created_at: 2020-05-15 10:30:45
```

## Step 4: Transform Data (Optional)

The ingestion script expects this format:

```json
{
  "external_id": "unique_id",
  "text": "conversation text",
  "thread_id": "grouping_id",
  "raw": { "original fields..." }
}
```

### Create Transform Script

```bash
# Create transformation script
cat > scripts/transform_kaggle.py << 'EOF'
#!/usr/bin/env python3
"""
Transform Kaggle Twitter data to Grok Insights format.
Combines inbound/outbound tweets into conversation threads.
"""

import pandas as pd
import json
from pathlib import Path

def transform_kaggle_data(csv_path: str, output_path: str):
    """Transform Kaggle CSV to Grok format."""
    
    df = pd.read_csv(csv_path)
    conversations = []
    
    # Group by thread (inbound + response)
    for idx, row in df.iterrows():
        conversation = {
            "external_id": str(row['tweet_id']),
            "text": str(row['text']),
            "thread_id": f"thread_{row.get('author_id', idx)}",
            "raw": row.to_dict()
        }
        conversations.append(conversation)
    
    # Save as JSON
    with open(output_path, 'w') as f:
        json.dump(conversations, f, indent=2, default=str)
    
    print(f"Transformed {len(conversations)} conversations to {output_path}")

if __name__ == '__main__':
    transform_kaggle_data(
        './data/kaggle/tweets.csv',
        './data/kaggle/conversations.json'
    )
EOF

# Run transformation
python scripts/transform_kaggle.py
```

## Step 5: Ingest into Backend

### Start Server (if not running)

```powershell
# In a new terminal
python -m uvicorn src.grok_insights.main:app --reload --host 127.0.0.1 --port 8000
```

### Ingest Data

```bash
# Small batch first (test)
python scripts/ingest_sample.py \
  --source ./data/kaggle/conversations.json \
  --api-url http://127.0.0.1:8000 \
  --batch-size 50

# Or use CSV directly
python scripts/ingest_sample.py \
  --source ./data/kaggle/tweets.csv \
  --api-url http://127.0.0.1:8000 \
  --batch-size 100
```

### What to Expect

```
Loaded 3000 conversations from ./data/kaggle/tweets.csv
  Batch 1: ingested 100 conversations
  Batch 2: ingested 100 conversations
  ...
  Batch 30: ingested 100 conversations

Total ingested: 3000/3000
```

## Step 6: Monitor Processing

### Check Queue Status

```powershell
# Every 2 seconds
while($true) {
  $health = curl -s http://127.0.0.1:8000/health | ConvertFrom-Json
  Write-Host "Queue: $($health.queue_size) | Worker: $($health.worker_running)"
  Start-Sleep -Seconds 2
}
```

### View Results

```bash
# Get final insights
curl http://127.0.0.1:8000/api/v1/insights?limit=100

# Trends over time
curl http://127.0.0.1:8000/api/v1/insights/trends?days=30

# Cost summary
curl http://127.0.0.1:8000/status/summary
```

## Step 7: Analyze Results

### Get Sentiment Distribution

```powershell
python -c "
import requests

resp = requests.get('http://127.0.0.1:8000/api/v1/insights/trends')
data = resp.json()

print(f\"Positive: {data['sentiment_distribution']['positive']}\")
print(f\"Negative: {data['sentiment_distribution']['negative']}\")
print(f\"Neutral: {data['sentiment_distribution']['neutral']}\")

print(f\"\nTop Topics:\")
for topic, count in data['top_topics'][:5]:
    print(f\"  {topic}: {count}\")
"
```

### Export Results to CSV

```python
import requests
import pandas as pd

# Fetch all insights
resp = requests.get('http://127.0.0.1:8000/api/v1/insights?limit=10000')
insights = resp.json()['items']

# Convert to DataFrame
df = pd.DataFrame(insights)

# Save
df.to_csv('./outputs/grok_analysis_results.csv', index=False)
print(f"Exported {len(df)} insights to CSV")
```

## Full Workflow Example

```bash
# 1. Download dataset
kaggle datasets download -d thoughtvector/customer-support-on-twitter
Expand-Archive -Path customer-support-on-twitter.zip -DestinationPath ./data/kaggle

# 2. Transform data (optional)
python scripts/transform_kaggle.py

# 3. Start server
python -m uvicorn src.grok_insights.main:app --reload &

# 4. Ingest data
python scripts/ingest_sample.py \
  --source ./data/kaggle/tweets.csv \
  --api-url http://127.0.0.1:8000 \
  --batch-size 100

# 5. Monitor until queue is empty
While ($(curl -s http://127.0.0.1:8000/health | ConvertFrom-Json).queue_size -gt 0) {
  Write-Host "Processing..."
  Start-Sleep -Seconds 5
}

# 6. Get results
curl http://127.0.0.1:8000/api/v1/insights/trends
```

## Troubleshooting

### "Kaggle API not found"

```powershell
# Install kaggle package
pip install kaggle

# Verify
kaggle --version
```

### "Invalid API key"

```powershell
# Check kaggle.json exists
Test-Path "$env:USERPROFILE\.kaggle\kaggle.json"

# Check contents
Get-Content "$env:USERPROFILE\.kaggle\kaggle.json"
# Should have: {"username":"...", "key":"..."}
```

### Dataset Already Exists Error

```bash
# Skip if already downloaded
rm ./data/kaggle/*.zip
```

### CSV Parse Errors

```python
# Read with error handling
df = pd.read_csv('./data/kaggle/tweets.csv', 
                  on_bad_lines='skip',
                  encoding='utf-8')
```

### Ingestion Timeout

Reduce batch size:
```bash
python scripts/ingest_sample.py \
  --source ./data/kaggle/tweets.csv \
  --batch-size 25  # Lower batch size
```

## Performance Expectations

| Metric | Value |
|--------|-------|
| Download size | ~50 MB |
| Unzipped size | ~300 MB |
| Conversations | ~3,000 |
| Ingestion time | ~2-5 minutes |
| Processing time (real Grok) | ~1-2 hours |
| Estimated cost | $2-5 USD |
| Storage after DB | ~50 MB |

## Next Steps

1. **Verify ingestion:** Check `/health` endpoint
2. **Monitor costs:** View `/status/summary` for estimated spend
3. **Export results:** Save insights to CSV for analysis
4. **Create visualizations:** Build dashboards from `/metrics`
5. **Integrate frontend:** Connect to web UI for browsing

## File Structure After Setup

```
./data/kaggle/
├── tweets.csv               # Downloaded from Kaggle
├── sentiment_analysis.csv   # Optional additional file
├── conversations.json       # After transformation (optional)
└── archive/                 # Downloaded .zip (can delete)

./data/
├── data.db                  # SQLite with processed data
└── kaggle/                  # Kaggle dataset files
```

## References

- **Kaggle API Docs:** https://github.com/Kaggle/kaggle-api
- **Dataset:** https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter
- **Pandas Docs:** https://pandas.pydata.org/docs/
- **curl examples:** Run `curl --help` for options

---

**Last Updated:** February 8, 2026
