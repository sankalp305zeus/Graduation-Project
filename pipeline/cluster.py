"""
Clustering — reads embedded reviews, runs HDBSCAN, outputs cluster groups in
EXACTLY the shape 02-theme-extraction.json's webhook expects:
  { "clusters": [ { "cluster_id": "...", "reviews": [ {id, text, rating}, ... ] }, ... ] }

This is pure local computation (sklearn/hdbscan/numpy) — fully testable in
this sandbox with synthetic embeddings, unlike embed.py above. The clustering
ALGORITHM is verified correct here; whether real review embeddings cluster
into meaningful semantic groups can only be judged once real embeddings from
embed.py exist — that's a data question, not a code question.

Usage:
  python cluster.py --input ../data/processed/embedded_reviews.jsonl \
                     --output ../data/processed/clusters.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import hdbscan
except ImportError:
    print('[error] hdbscan not installed. Run: pip install hdbscan --break-system-packages', file=sys.stderr)
    sys.exit(1)

MIN_CLUSTER_SIZE = 5  # per blueprint C.2 — themes need enough evidence to be
                       # eval-able (D.2 wants >30 evidence reviews per theme
                       # eventually; individual HDBSCAN clusters can be smaller,
                       # multiple similar clusters can roll up into one theme
                       # later if needed)


def load_embedded_records(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if 'embedding' not in r:
                continue
            records.append(r)
    return records


def cluster_records(records, min_cluster_size=MIN_CLUSTER_SIZE):
    embeddings = np.array([r['embedding'] for r in records])

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean')
    labels = clusterer.fit_predict(embeddings)

    clusters = {}
    noise_records = []
    for record, label in zip(records, labels):
        if label == -1:
            noise_records.append(record)
            continue  # HDBSCAN's noise points — not assigned to any cluster,
                      # correctly excluded rather than forced into a group
        clusters.setdefault(str(label), []).append(record)

    return clusters, noise_records


def to_n8n_payload(clusters, noise_records):
    """Matches the schema documented in workflows/README.md's test payload.

    `noise_review_ids` is an extra top-level field alongside `clusters` — the
    n8n webhook's "Validate & Parse Input" node only reads `body.clusters`
    and ignores unknown fields, so this doesn't affect the live workflow.
    It exists so noise reviews are durably logged (actual IDs, not just a
    count) for the row-accounting check in evals/row_accounting_check.py —
    previously this was only a number printed to stdout and lost otherwise.
    """
    return {
        'clusters': [
            {
                'cluster_id': f'cluster_{cid}',
                'reviews': [{'id': r['id'], 'text': r['text'], 'rating': r.get('rating')} for r in members],
            }
            for cid, members in clusters.items()
        ],
        'noise_review_ids': [r['id'] for r in noise_records],
    }


def main():
    parser = argparse.ArgumentParser(description='Cluster embedded reviews with HDBSCAN')
    parser.add_argument('--input', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/clusters.json')
    parser.add_argument('--min-cluster-size', type=int, default=MIN_CLUSTER_SIZE)
    args = parser.parse_args()

    records = load_embedded_records(args.input)
    if len(records) < args.min_cluster_size:
        print(f'[error] only {len(records)} embedded records found — need at least {args.min_cluster_size} to cluster', file=sys.stderr)
        sys.exit(1)

    print(f'Clustering {len(records)} embedded records (min_cluster_size={args.min_cluster_size})...')
    clusters, noise_records = cluster_records(records, args.min_cluster_size)

    payload = to_n8n_payload(clusters, noise_records)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    sizes = [len(c['reviews']) for c in payload['clusters']]
    print(f'Done. {len(payload["clusters"])} clusters formed, {len(noise_records)} reviews unclustered (noise).')
    if sizes:
        print(f'Cluster sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}')
    print(f'Wrote n8n-ready payload to {out_path}')
    print('This file is POST-able directly to the 02-theme-extraction.json webhook.')


if __name__ == '__main__':
    main()
