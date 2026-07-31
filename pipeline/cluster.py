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
    print('[error] hdbscan not installed. Run: pip install -r requirements.txt', file=sys.stderr)
    sys.exit(1)

MIN_CLUSTER_SIZE = 10  # raised from 5 alongside the UMAP step — after reduction
                        # HDBSCAN finds finer structure, so a slightly larger
                        # floor keeps themes eval-able (blueprint D.2 wants
                        # >30 evidence reviews per theme; several small clusters
                        # can still roll up into one theme later)

# UMAP dimensionality reduction before HDBSCAN — the BERTopic architecture.
# Rationale: density-based clustering degrades in high dimensions because
# pairwise distances concentrate into a narrow band (verified locally on
# synthetic 384-dim data: spread/mean was 0.214 raw vs 1.628 after UMAP),
# leaving HDBSCAN unable to find density contrast.
# metric='cosine' is correct for normalized sentence embeddings (embed.py
# emits unit vectors); metric='euclidean' is correct AFTER UMAP because the
# reduced space is a euclidean embedding of those cosine neighbourhoods.
UMAP_N_COMPONENTS = 5
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.0
UMAP_METRIC = 'cosine'
UMAP_RANDOM_STATE = 42  # pinned: the PRD requires every number in the deck to
                         # be regenerable, and UMAP is stochastic by default


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


def reduce_dimensions(embeddings, n_components=UMAP_N_COMPONENTS, n_neighbors=UMAP_N_NEIGHBORS,
                      min_dist=UMAP_MIN_DIST, metric=UMAP_METRIC, random_state=UMAP_RANDOM_STATE):
    """384 dims -> n_components dims. See the UMAP_* constants above for why."""
    try:
        import umap
    except ImportError:
        print('[error] umap-learn not installed. Run: pip install -r requirements.txt', file=sys.stderr)
        sys.exit(1)

    n_samples = len(embeddings)
    # UMAP needs n_neighbors < n_samples; clamp rather than crash so small
    # test corpora still run (a 20-review smoke test shouldn't hard-fail).
    effective_neighbors = min(n_neighbors, max(2, n_samples - 1))
    if effective_neighbors != n_neighbors:
        print(f'[warn] only {n_samples} records — clamping UMAP n_neighbors '
              f'{n_neighbors} -> {effective_neighbors}', file=sys.stderr)

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=effective_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
    )
    return reducer.fit_transform(embeddings)


def cluster_records(records, min_cluster_size=MIN_CLUSTER_SIZE, use_umap=True, **umap_kwargs):
    embeddings = np.array([r['embedding'] for r in records])

    if use_umap:
        vectors = reduce_dimensions(embeddings, **umap_kwargs)
    else:
        # Escape hatch for A/B-ing against the pre-UMAP behaviour on real
        # data. Kept because on synthetic corpora with clean topic structure
        # raw HDBSCAN actually outperformed UMAP+HDBSCAN — which regime real
        # review embeddings fall into is an empirical question, so make it
        # one command to check rather than a code edit.
        vectors = embeddings

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean')
    labels = clusterer.fit_predict(vectors)

    clusters = {}
    noise_records = []
    for record, label in zip(records, labels):
        if label == -1:
            noise_records.append(record)
            continue  # HDBSCAN's noise points — not assigned to any cluster,
                      # correctly excluded rather than forced into a group
        clusters.setdefault(str(label), []).append(record)

    return clusters, noise_records


def structure_diagnostic(records, k=10):
    """Is there local topical structure in the embeddings AT ALL?

    Distinguishes "the clustering algorithm is misconfigured" from "this
    corpus has no recoverable topic structure, so no algorithm will help."
    Reports mean cosine similarity to each point's k nearest neighbours vs.
    to random other points. If those two numbers are close, the embeddings
    have no local neighbourhood structure and the fix is upstream (embedding
    model, review length, corpus composition) — not in HDBSCAN's parameters.
    """
    embeddings = np.array([r['embedding'] for r in records], dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / np.clip(norms, 1e-12, None)

    # Sample to keep the full similarity matrix tractable on large corpora.
    n = len(normalized)
    sample_n = min(n, 1500)
    rng = np.random.default_rng(0)
    idx = rng.choice(n, size=sample_n, replace=False) if sample_n < n else np.arange(n)
    sample = normalized[idx]

    sims = sample @ sample.T
    np.fill_diagonal(sims, -np.inf)
    k_eff = min(k, sample_n - 1)
    knn = np.sort(sims, axis=1)[:, -k_eff:]
    mean_knn = float(knn.mean())

    off_diag = sims[np.isfinite(sims)]
    mean_random = float(off_diag.mean())

    return {
        'mean_norm': float(norms.mean()),
        'mean_cos_to_%d_nearest' % k_eff: mean_knn,
        'mean_cos_to_random': mean_random,
        'separation': mean_knn - mean_random,
    }


def to_n8n_payload(clusters, noise_records, corpus_total, corpus_total_basis):
    """Matches the schema documented in workflows/README.md's test payload.

    Extra top-level fields alongside `clusters` — the n8n webhook's
    "Validate & Parse Input" node reads them explicitly now, and older
    payloads without them still work (the workflow falls back).

    `noise_review_ids`: noise reviews logged by actual ID, not just a count,
    for evals/row_accounting_check.py.

    `corpus_total` / `corpus_total_basis`: the denominator the workflow uses
    to compute each theme's prevalence_pct. The BASIS is carried alongside
    the number deliberately — "% of corpus" is meaningless without saying
    which corpus, and an unlabeled percentage is exactly the kind of
    misleading figure prevalence is meant to guard against.
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
        'corpus_total': corpus_total,
        'corpus_total_basis': corpus_total_basis,
    }


def print_report(records, clusters, noise_records, min_cluster_size, use_umap):
    sizes = sorted((len(m) for m in clusters.values()), reverse=True)
    total = len(records)
    noise_pct = len(noise_records) / total * 100 if total else 0

    print(f'\n=== cluster report (min_cluster_size={min_cluster_size}, '
          f'umap={"on" if use_umap else "OFF"}) ===')
    print(f'records          : {total}')
    print(f'clusters         : {len(sizes)}')
    print(f'noise            : {len(noise_records)} ({noise_pct:.1f}%)')
    if sizes:
        clustered = sum(sizes)
        quartiles = np.percentile(sizes, [25, 50, 75])
        print(f'clustered        : {clustered} ({clustered / total * 100:.1f}%)')
        print(f'size min/med/max : {min(sizes)} / {int(quartiles[1])} / {max(sizes)}')
        print(f'size p25/p75     : {int(quartiles[0])} / {int(quartiles[2])}')
        print(f'largest 10       : {sizes[:10]}')
        big = sum(1 for s in sizes if s >= 30)
        print(f'clusters >=30 ev : {big}  (blueprint D.2 wants >30 evidence reviews per theme)')

    # Blueprint targets roughly 50-150 clusters for a corpus this size.
    if sizes:
        if len(sizes) < 10:
            print('[warn] very few clusters — try a LOWER --min-cluster-size, or --no-umap to compare')
        elif len(sizes) > 200:
            print('[warn] very many clusters — try a HIGHER --min-cluster-size')
        if noise_pct > 50:
            print(f'[warn] {noise_pct:.0f}% noise is high — lower --min-cluster-size, or run '
                  f'--report --no-umap to see whether UMAP is helping or hurting on this corpus')


def main():
    parser = argparse.ArgumentParser(description='Cluster embedded reviews with UMAP + HDBSCAN')
    parser.add_argument('--input', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/clusters.json')
    parser.add_argument('--min-cluster-size', type=int, default=MIN_CLUSTER_SIZE)
    parser.add_argument('--corpus-total', type=int, default=None,
                         help='Denominator for each theme\'s prevalence_pct. Defaults to the number of embedded '
                              'records read from --input (i.e. the post-relevance-filter corpus that was actually '
                              'analyzed). Pass the full pre-filter cleaned-corpus count here instead if you want '
                              'prevalence reported against every review scraped — the basis is recorded in the '
                              'payload either way so the percentage is never ambiguous.')
    parser.add_argument('--report', action='store_true',
                         help='Print cluster count, size distribution and noise %% WITHOUT writing any output — '
                              'for tuning --min-cluster-size quickly')
    parser.add_argument('--no-umap', action='store_true',
                         help='Skip the UMAP step and run HDBSCAN on raw embeddings (the pre-fix behaviour). '
                              'Use with --report to A/B whether UMAP actually helps on this corpus')
    parser.add_argument('--umap-components', type=int, default=UMAP_N_COMPONENTS)
    parser.add_argument('--umap-neighbors', type=int, default=UMAP_N_NEIGHBORS)
    parser.add_argument('--umap-min-dist', type=float, default=UMAP_MIN_DIST)
    parser.add_argument('--umap-metric', type=str, default=UMAP_METRIC)
    parser.add_argument('--umap-random-state', type=int, default=UMAP_RANDOM_STATE)
    args = parser.parse_args()

    records = load_embedded_records(args.input)
    if len(records) < args.min_cluster_size:
        print(f'[error] only {len(records)} embedded records found — need at least {args.min_cluster_size} to cluster', file=sys.stderr)
        sys.exit(1)

    use_umap = not args.no_umap
    print(f'Clustering {len(records)} embedded records '
          f'(min_cluster_size={args.min_cluster_size}, umap={"on" if use_umap else "OFF"})...')
    clusters, noise_records = cluster_records(
        records, args.min_cluster_size, use_umap=use_umap,
        n_components=args.umap_components, n_neighbors=args.umap_neighbors,
        min_dist=args.umap_min_dist, metric=args.umap_metric,
        random_state=args.umap_random_state,
    ) if use_umap else cluster_records(records, args.min_cluster_size, use_umap=False)

    if args.report:
        print_report(records, clusters, noise_records, args.min_cluster_size, use_umap)
        diag = structure_diagnostic(records)
        print('\n=== embedding structure diagnostic ===')
        print(f'mean vector norm            : {diag["mean_norm"]:.4f}  (expect ~1.0 — embed.py normalizes)')
        knn_key = [k for k in diag if k.startswith('mean_cos_to_') and 'random' not in k][0]
        print(f'{knn_key:28}: {diag[knn_key]:.4f}')
        print(f'mean_cos_to_random          : {diag["mean_cos_to_random"]:.4f}')
        print(f'separation (knn - random)   : {diag["separation"]:.4f}')
        # Calibration reference points, measured locally on 1180-record
        # synthetic corpora of the same shape as this pipeline's:
        #   ~0.44 = 14 genuine topics present   -> 15 clusters, 4.5% noise
        #   ~0.14 = pure noise, no topics at all -> 72% noise, spurious clusters
        # Treat as indicative, not a hard rule — the floor drifts with corpus
        # size, since k-NN in any high-dim sample beats random slightly.
        sep = diag['separation']
        if sep < 0.15:
            print('[warn] separation is at the no-structure baseline (~0.14 on pure-noise synthetic\n'
                  '       data of this size). The embeddings appear to have little local topic\n'
                  '       structure, so NO clustering parameter will fix this — look upstream:\n'
                  '       embedding model quality on short review text, review length after\n'
                  '       cleaning, or corpus composition.')
        elif sep < 0.30:
            print('[note] weak-to-moderate separation. Some structure exists but it is not sharp;\n'
                  '       expect high noise. Compare --report --no-umap before tuning further.')
        print('\n(--report: nothing written)')
        return

    if args.corpus_total is not None:
        corpus_total = args.corpus_total
        corpus_total_basis = 'explicit_--corpus-total'
    else:
        corpus_total = len(records)
        corpus_total_basis = 'embedded_reviews_analyzed'

    payload = to_n8n_payload(clusters, noise_records, corpus_total, corpus_total_basis)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    sizes = [len(c['reviews']) for c in payload['clusters']]
    print(f'Done. {len(payload["clusters"])} clusters formed, {len(noise_records)} reviews unclustered (noise).')
    if sizes:
        print(f'Cluster sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}')
    print(f'Prevalence denominator: corpus_total={corpus_total} (basis: {corpus_total_basis})')
    print(f'Wrote n8n-ready payload to {out_path}')
    print('This file is POST-able directly to the 02-theme-extraction.json webhook.')


if __name__ == '__main__':
    main()
