"""
Embedding generation — reads cleaned JSONL, generates embeddings with a
local sentence-transformers model, writes embeddings alongside each record.

Runs entirely offline after the model weights are cached (downloaded once
from the Hugging Face Hub on first use, then reused). Zero cost, zero rate
limits, zero extra API account beyond what this project already needs.

Model: all-MiniLM-L6-v2 (384 dimensions — matches the pgvector column
defined in supabase/03_themes_schema.sql). This is a deliberate tradeoff:
lower semantic quality than a hosted embeddings API, appropriate for a
13-day prototype with a few thousand reviews (see
docs/GROQ_MIGRATION_AND_FAILPROOFING.md Task D for the reasoning).

Requires: pip install -r requirements.txt (sentence-transformers)

Usage:
  python embed.py --input ../data/processed/cleaned_reviews.jsonl \
                   --output ../data/processed/embedded_reviews.jsonl \
                   --limit 10   # test small batch first

  python embed.py --self-check   # verify the model loads and produces
                                  # 384-dim embeddings on synthetic input,
                                  # no real corpus needed
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print(
        '[error] sentence-transformers not installed. Run: pip install -r requirements.txt',
        file=sys.stderr,
    )
    sys.exit(1)

MODEL_NAME = 'all-MiniLM-L6-v2'
EXPECTED_DIM = 384
BATCH_SIZE = 100  # encode() batches internally, but chunking keeps memory
                   # bounded and gives progress output on large corpora


def embed_batch(model, texts):
    # normalize_embeddings=True is required for cluster.py's HDBSCAN step,
    # which uses metric='euclidean'. For unit vectors, euclidean distance
    # and cosine similarity are monotonically related (||a-b||^2 = 2 -
    # 2*cos(a,b)); without normalization, review length dominates distance
    # instead of meaning. This was the root cause of a real 2029-review run
    # producing 2 giant clusters (max 814) instead of the expected 50-150.
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return [emb.tolist() for emb in embeddings]


def run_self_check():
    print(f'Loading {MODEL_NAME} (first run downloads weights from Hugging Face Hub)...')
    model = SentenceTransformer(MODEL_NAME)

    texts = [
        'I never buy electronics here, too scared about returns if something breaks',
        'Great app but I only trust it for groceries, not gadgets',
        'Completely unrelated sentence about the weather today',
    ]
    embeddings = embed_batch(model, texts)

    ok = True
    if len(embeddings) != len(texts):
        print(f'  [FAIL] got {len(embeddings)} embeddings for {len(texts)} inputs')
        ok = False
    for i, emb in enumerate(embeddings):
        if len(emb) != EXPECTED_DIM:
            print(f'  [FAIL] embedding {i} has dimension {len(emb)}, expected {EXPECTED_DIM}')
            ok = False

    if ok:
        print(f'  [PASS] {len(texts)} texts embedded, each {EXPECTED_DIM}-dim')
        print('Self-check passed.')
        sys.exit(0)
    else:
        print('Self-check FAILED.')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for cleaned reviews')
    parser.add_argument('--input', type=str, default='../data/processed/cleaned_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--limit', type=int, default=None, help='Process only the first N records — use this to test before running the full corpus')
    parser.add_argument('--self-check', action='store_true', help='Run against synthetic input and verify embedding shape, no corpus needed')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    print(f'Loading {MODEL_NAME} (first run downloads weights from Hugging Face Hub)...')
    model = SentenceTransformer(MODEL_NAME)

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

            embeddings = embed_batch(model, texts)

            for record, emb in zip(batch, embeddings):
                record['embedding'] = emb
                out_f.write(json.dumps(record, ensure_ascii=False) + '\n')

            print(f'  [progress] {min(i + BATCH_SIZE, len(records))}/{len(records)} embedded')

    print(f'Done. Wrote embeddings to {out_path}')


if __name__ == '__main__':
    main()
