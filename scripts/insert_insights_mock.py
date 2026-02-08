#!/usr/bin/env python3
"""
Insert insights for sample conversations using the mock analyzer directly.
This bypasses the background worker and is useful for quick verification.
"""
import asyncio
import json
from src.grok_insights.db.session import init_db, get_session_context
from src.grok_insights.db.models import Insight, AnalysisCache, Conversation
from src.grok_insights.worker.grok_client import _analyze_mock


def analyze_and_insert(sample_json: str = 'data/kaggle/conversations_sample.json'):
    init_db()
    with open(sample_json, 'r', encoding='utf-8') as f:
        convs = json.load(f)
    print('Loaded', len(convs))
    inserted = 0
    for item in convs:
        # find conversation id in DB by external_id
        with get_session_context() as session:
            conv = None
            if item.get('external_id'):
                conv = session.query(Conversation).filter_by(external_id=item['external_id']).first()
            if not conv:
                # fallback: try to match by text
                conv = session.query(Conversation).filter_by(text=item['text']).first()
            if not conv:
                print('Conversation not found in DB for', item.get('external_id'))
                continue
            # Run mock analysis
            res = asyncio.run(_analyze_mock(item['text']))
            # Create insight
            insight = Insight(
                conversation_id=conv.id,
                summary=res.get('summary',''),
                sentiment=res.get('sentiment','neutral'),
                topics=res.get('topics',[]),
                processing_time_ms=int(res.get('meta',{}).get('latency',0)*1000),
            )
            meta = res.get('meta',{})
            tokens = int(meta.get('estimated_tokens',0) or 0)
            cost = float(meta.get('estimated_cost',0.0) or 0.0)
            if tokens:
                insight.tokens_used = tokens
            if cost:
                insight.estimated_cost = f"${cost:.6f}"
            session.add(insight)
            session.flush()
            # cache
            cache = AnalysisCache(text_hash=__import__('hashlib').sha256(item['text'].encode('utf-8')).hexdigest(), insight_id=insight.id)
            session.add(cache)
            inserted += 1
    print('Inserted', inserted, 'insights')

if __name__ == '__main__':
    analyze_and_insert()
