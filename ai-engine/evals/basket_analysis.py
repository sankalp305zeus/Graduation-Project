"""
Shopping Basket Analysis metrics — Support, Confidence, Lift — computed from
real event_log data (persona_id, product_id, action, timestamp).

IMPORTANT CALIBRATION NOTE, read before trusting any output of this script:
these are textbook-correct implementations, verified against a hand-checked
synthetic example below. But Support/Confidence/Lift are only meaningful at
volume — with 6 demo personas and a handful of accept/dismiss events, any
numbers this produces are NOT findings, they're a demonstration that the
math is implemented correctly. Do not put output from a small demo run in
your deck as if it reflects real user behavior.

A "basket" here = one persona's cart contents at the moment a recommendation
was shown, including whatever they'd already added ("base items") plus
whether they accepted the recommended item.

Usage:
  python basket_analysis.py --event-log events.jsonl
"""

import argparse
import json
from collections import defaultdict


def support(item_a, item_b, baskets):
    """P(A and B both in the same basket)."""
    if not baskets:
        return 0.0
    count = sum(1 for b in baskets if item_a in b and item_b in b)
    return count / len(baskets)


def confidence(item_a, item_b, baskets):
    """P(B in basket | A in basket)."""
    baskets_with_a = [b for b in baskets if item_a in b]
    if not baskets_with_a:
        return 0.0
    count = sum(1 for b in baskets_with_a if item_b in b)
    return count / len(baskets_with_a)


def lift(item_a, item_b, baskets):
    """confidence(A->B) / P(B) — >1 means positive association, not random co-occurrence."""
    if not baskets:
        return 0.0
    conf = confidence(item_a, item_b, baskets)
    support_b = sum(1 for b in baskets if item_b in b) / len(baskets)
    if support_b == 0:
        return 0.0
    return conf / support_b


def build_baskets_from_event_log(events):
    """
    Groups events by persona+session into baskets. In this prototype's
    schema, treat each persona's full event history as one basket — a
    production version would key by session_id instead of persona_id once
    that field exists, since one persona has many separate cart sessions
    over time.
    """
    baskets_dict = defaultdict(set)
    for e in events:
        baskets_dict[e['persona_id']].add(e['product_id'])
    return list(baskets_dict.values())


def all_pairwise_metrics(baskets, min_support=0.0):
    """Computes support/confidence/lift for every pair of items that co-occur at least once."""
    items = sorted({item for basket in baskets for item in basket})
    results = []
    for a in items:
        for b in items:
            if a == b:
                continue
            s = support(a, b, baskets)
            if s < min_support:
                continue
            c = confidence(a, b, baskets)
            l = lift(a, b, baskets)
            results.append({'item_a': a, 'item_b': b, 'support': round(s, 4), 'confidence': round(c, 4), 'lift': round(l, 4)})
    results.sort(key=lambda r: r['lift'], reverse=True)
    return results


def _self_check():
    """
    Hand-verifiable example: 4 baskets, {A,B} co-occur in 2 of 4.
    support(A,B) = 2/4 = 0.5
    confidence(A->B): A appears in 3 baskets, B is in 2 of those -> 2/3 = 0.667
    support(B) = 2/4 = 0.5 -> lift = 0.667 / 0.5 = 1.333
    """
    baskets = [{'A', 'B'}, {'A', 'C'}, {'A', 'B'}, {'C'}]
    s = support('A', 'B', baskets)
    c = confidence('A', 'B', baskets)
    l = lift('A', 'B', baskets)
    assert abs(s - 0.5) < 1e-9, f'support failed: {s}'
    assert abs(c - 0.6667) < 1e-3, f'confidence failed: {c}'
    assert abs(l - 1.3333) < 1e-3, f'lift failed: {l}'
    print('Self-check passed: support=0.5, confidence=0.667, lift=1.333 (all correct)')


def main():
    parser = argparse.ArgumentParser(description='Compute Support/Confidence/Lift from event_log data')
    parser.add_argument('--event-log', type=str, help='Path to event_log JSONL export')
    parser.add_argument('--min-support', type=float, default=0.0)
    parser.add_argument('--self-check', action='store_true', help='Run the hand-verified example instead of real data')
    args = parser.parse_args()

    if args.self_check or not args.event_log:
        _self_check()
        return

    with open(args.event_log, encoding='utf-8') as f:
        events = [json.loads(line) for line in f if line.strip()]

    # Only "accepted" actions count as an item genuinely entering the basket
    accepted_events = [e for e in events if e.get('action') == 'accepted']
    baskets = build_baskets_from_event_log(accepted_events)

    print(f'{len(baskets)} baskets built from {len(accepted_events)} accepted events')
    if len(baskets) < 30:
        print('[WARNING] fewer than 30 baskets — these numbers are not statistically meaningful yet, treat as a code demo only')

    results = all_pairwise_metrics(baskets, min_support=args.min_support)
    for r in results[:10]:
        print(r)


if __name__ == '__main__':
    main()
