"""
Row-accounting check: verify every review in the cleaned corpus lands in
exactly one of four buckets, with no unexplained gap and no double-count.

  total cleaned-corpus rows ==
      reviews inserted with a category
    + reviews inserted with category=NULL
    + HDBSCAN noise points (from cluster.py's clusters.json)
    + NO_COHERENT_THEME-skipped cluster reviews

This imports categorize()/build_rows()/load_reviews_by_id() directly from
pipeline/ingest_themes.py rather than reimplementing the categorization
logic — it verifies the REAL ingest behavior, not a parallel guess at it
that could silently drift out of sync.

This does NOT just compare aggregate counts (two independent bugs could
cancel out and still match). It does a real set-based cross-check: every
corpus review ID must appear in exactly one bucket. IDs found in zero
buckets (an unexplained gap) or in more than one bucket (a double-count)
are reported by ID, not hidden behind a matching total.

Usage:
  python row_accounting_check.py \
      --corpus-input ../data/processed/cleaned_reviews.jsonl \
      --clusters-input ../data/processed/clusters.json \
      --themes-input ../data/processed/n8n_themes_response.json \
      --reviews-input ../data/processed/embedded_reviews.jsonl

  python row_accounting_check.py --self-check   # synthetic data, no
                                                 # real corpus needed
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pipeline'))
from ingest_themes import build_rows, load_reviews_by_id  # noqa: E402


def load_corpus_ids(path):
    ids = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ids.add(json.loads(line)['id'])
    return ids


def load_noise_ids(clusters_path, corpus_ids, all_clustered_ids):
    with open(clusters_path, encoding='utf-8') as f:
        clusters_payload = json.load(f)

    if 'noise_review_ids' in clusters_payload:
        return set(clusters_payload['noise_review_ids'])

    # Fallback for a clusters.json written before cluster.py logged noise
    # IDs directly — lower confidence, since this can't distinguish "true
    # HDBSCAN noise" from any other reason a review might be unclustered.
    print('[warn] clusters.json has no noise_review_ids field (predates the '
          'logging change) — falling back to corpus_ids - all_clustered_ids, '
          'which is less precise', file=sys.stderr)
    return corpus_ids - all_clustered_ids


def get_no_coherent_theme_ids(themes):
    ids = set()
    for theme in themes:
        if theme.get('theme_name') == 'NO_COHERENT_THEME' or theme.get('is_valid_cluster') is False:
            ids.update(theme.get('evidence_ids', []))
    return ids


def run_accounting(corpus_ids, noise_ids, categorized_ids, null_categorized_ids, no_coherent_theme_ids):
    """Returns (ok, report_lines). Does the real set-based cross-check —
    not just a count comparison."""
    buckets = {
        'categorized': categorized_ids,
        'null_categorized': null_categorized_ids,
        'hdbscan_noise': noise_ids,
        'no_coherent_theme_skipped': no_coherent_theme_ids,
    }

    lines = []
    ok = True

    for name, ids in buckets.items():
        lines.append(f'  {name}: {len(ids)}')

    union_ids = set().union(*buckets.values())

    missing = corpus_ids - union_ids
    if missing:
        ok = False
        lines.append(f'[FAIL] {len(missing)} corpus review(s) unaccounted for in any bucket: {sorted(missing)}')

    phantom = union_ids - corpus_ids
    if phantom:
        ok = False
        lines.append(f'[FAIL] {len(phantom)} review ID(s) appear in a bucket but not in the corpus (phantom IDs): {sorted(phantom)}')

    # Pairwise overlap check — a review counted in more than one bucket is a
    # double-count bug, not a rounding error to shrug off.
    bucket_names = list(buckets.keys())
    for i in range(len(bucket_names)):
        for j in range(i + 1, len(bucket_names)):
            overlap = buckets[bucket_names[i]] & buckets[bucket_names[j]]
            if overlap:
                ok = False
                lines.append(f'[FAIL] {len(overlap)} review(s) double-counted in both '
                             f'"{bucket_names[i]}" and "{bucket_names[j]}": {sorted(overlap)}')

    if ok:
        lines.append(f'[PASS] all {len(corpus_ids)} corpus reviews accounted for in exactly one bucket, no gaps, no double-counts')

    return ok, lines


def run_self_check():
    print('Scenario 1: well-formed synthetic data — expect a clean pass')
    corpus_ids = {f'r{i}' for i in range(1, 11)}  # r1..r10
    categorized_ids = {'r1', 'r2', 'r3'}
    null_categorized_ids = {'r4', 'r5'}
    no_coherent_theme_ids = {'r6', 'r7'}
    noise_ids = {'r8', 'r9', 'r10'}

    ok1, lines1 = run_accounting(corpus_ids, noise_ids, categorized_ids, null_categorized_ids, no_coherent_theme_ids)
    for line in lines1:
        print(' ', line)
    check1 = ok1 is True
    print(f'  [{"PASS" if check1 else "FAIL"}] scenario 1 correctly reports a clean accounting')

    print('\nScenario 2: deliberately broken — one review (r11) in the corpus but in NO bucket')
    corpus_ids_broken = corpus_ids | {'r11'}  # r11 exists in the corpus but nothing accounts for it
    ok2, lines2 = run_accounting(corpus_ids_broken, noise_ids, categorized_ids, null_categorized_ids, no_coherent_theme_ids)
    for line in lines2:
        print(' ', line)
    check2 = ok2 is False and any('r11' in line for line in lines2)
    print(f'  [{"PASS" if check2 else "FAIL"}] scenario 2 correctly detects and names the gap (r11) rather than passing')

    print('\nScenario 3: deliberately broken — one review (r1) double-counted in two buckets')
    null_categorized_broken = null_categorized_ids | {'r1'}  # r1 also already in categorized_ids
    ok3, lines3 = run_accounting(corpus_ids, noise_ids, categorized_ids, null_categorized_broken, no_coherent_theme_ids)
    for line in lines3:
        print(' ', line)
    check3 = ok3 is False and any('r1' in line and 'double-counted' in line for line in lines3)
    print(f'  [{"PASS" if check3 else "FAIL"}] scenario 3 correctly detects and names the double-count (r1) rather than passing')

    if check1 and check2 and check3:
        print('\nSelf-check passed.')
        sys.exit(0)
    else:
        print('\nSelf-check FAILED.')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Verify every cleaned-corpus review lands in exactly one accounting bucket')
    parser.add_argument('--corpus-input', type=str, default='../data/processed/cleaned_reviews.jsonl')
    parser.add_argument('--clusters-input', type=str, default='../data/processed/clusters.json')
    parser.add_argument('--themes-input', type=str, default='../data/processed/n8n_themes_response.json')
    parser.add_argument('--reviews-input', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    corpus_ids = load_corpus_ids(args.corpus_input)

    with open(args.clusters_input, encoding='utf-8') as f:
        clusters_payload = json.load(f)
    all_clustered_ids = {r['id'] for c in clusters_payload['clusters'] for r in c['reviews']}
    noise_ids = load_noise_ids(args.clusters_input, corpus_ids, all_clustered_ids)

    with open(args.themes_input, encoding='utf-8') as f:
        themes_payload = json.load(f)
    themes = themes_payload.get('themes', [])

    reviews_by_id = load_reviews_by_id(args.reviews_input)
    _theme_rows, review_rows_by_id, _skipped_no_category, _skipped_invalid_cluster, _assignments = build_rows(themes, reviews_by_id)

    categorized_ids = {rid for rid, row in review_rows_by_id.items() if row['category'] is not None}
    null_categorized_ids = {rid for rid, row in review_rows_by_id.items() if row['category'] is None}
    no_coherent_theme_ids = get_no_coherent_theme_ids(themes)

    ok, lines = run_accounting(corpus_ids, noise_ids, categorized_ids, null_categorized_ids, no_coherent_theme_ids)
    print(f'Total cleaned-corpus rows: {len(corpus_ids)}')
    for line in lines:
        print(' ', line)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
