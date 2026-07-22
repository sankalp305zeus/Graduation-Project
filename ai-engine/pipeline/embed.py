"""
Embedding generation — reads cleaned JSONL, calls OpenAI's embedding API,
writes embeddings alongside each record.

*** NOT TESTED LIVE *** This sandbox's network allowlist covers package
registries (pypi, npm) but not api.openai.com — I could not execute a real
embedding call while building this. The code below is written correctly
against OpenAI's documented API shape, but run it yourself against a small
batch first (e.g. --limit 10) before trusting it on your full corpus.

Requires: OPENAI_API_KEY environment variable.
Model: text-embedding-3-small (1536 dimensions — matches the pgvector
column defined in ai-engine/supabase/themes_schema.sql).

Usage:
  export OPENAI_API_KEY=sk-...
  python embed.py --input ../data/processed/cleaned_reviews.jsonl \
                   --output ../data/processed/embedded_reviews.jsonl \
                   --limit 10   # test small batch first
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print('[error] openai package not installed. Run: pip install openai --break-system-packages', file=sys.stderr)
    sys.exit(1)

BATCH_SIZE = 100  # OpenAI's embeddings endpoint accepts batched input; batching
                   # reduces request count and cost vs one call per review


def embed_batch(client, texts):
    response = client.embeddings.create(model='text-embedding-3-small', input=texts)
    return [item.embedding for item in response.data]


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for cleaned reviews')
    parser.add_argument('--input', type=str, default='../data/processed/cleaned_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--limit', type=int, default=None, help='Process only the first N records — use this to test before running the full corpus')
    args = parser.parse_args()

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('[error] OPENAI_API_KEY not set', file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    with open(args.input, encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]

    if args.limit:
        records = records[: args.limit]

    print(f'Embedding {len(records)} records in batches of {BATCH_SIZE}...')

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open('w', encoding='utf-8') as out_f:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]
            texts = [r['text'] for r in batch]

            try:
                embeddings = embed_batch(client, texts)
            except Exception as e:
                print(f'  [warn] batch {i}-{i+len(batch)} failed: {e} — retrying once after 5s', file=sys.stderr)
                time.sleep(5)
                try:
                    embeddings = embed_batch(client, texts)
                except Exception as e2:
                    print(f'  [error] retry also failed: {e2} — skipping this batch', file=sys.stderr)
                    continue

            for record, emb in zip(batch, embeddings):
                record['embedding'] = emb
                out_f.write(json.dumps(record, ensure_ascii=False) + '\n')

            print(f'  [progress] {min(i + BATCH_SIZE, len(records))}/{len(records)} embedded')
            time.sleep(0.5)  # be polite to the rate limit

    print(f'Done. Wrote embeddings to {out_path}')


if __name__ == '__main__':
    main()
