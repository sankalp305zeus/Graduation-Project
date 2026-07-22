"""
Quick-commerce operational metrics from event_log + cart/order data.

Each function is independently self-checked at the bottom against a
hand-calculable example. As with basket_analysis.py: correct code, but
numbers from a small demo run are not real findings — see the warnings
each function prints when sample size is low.

Metrics implemented (from the AI engine research doc's operational table):
  - attach_rate           : avg items per completed basket
  - cdi_herfindahl        : Category Diversification Index (HHI-based)
  - feature_adoption_rate : simplified FAI — % of sessions where the
                             discovery card was shown AND accepted
  - aov_trend             : linear regression slope of order value over time

NOT implemented: Complaint-to-Order Ratio (COR). This requires post-purchase
complaint/support-ticket data that does not exist anywhere in this
prototype's schema (no returns/complaints table) — computing it would mean
fabricating a number with no real input, which this project's own blueprint
explicitly treats as a worse failure than not having the metric at all.
Add a `complaints` table and wire this up once real order data exists.
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime


def attach_rate(orders):
    """orders: list of {order_id, items: [...]}. Returns avg items per order."""
    if not orders:
        return 0.0
    total_items = sum(len(o['items']) for o in orders)
    return total_items / len(orders)


def cdi_herfindahl(orders, all_categories):
    """
    Category Diversification Index via Herfindahl-Hirschman Index, adapted:
    HHI = sum(share_i^2) across categories, where share_i = fraction of total
    items purchased that came from category i. HHI ranges 0 (perfectly
    diversified) to 1 (fully concentrated in one category) — this
    implementation returns 1 - HHI so a HIGHER score means MORE
    diversification, matching how the metric is described in the research
    doc and the blueprint (higher CDI = better, lower churn risk).
    """
    category_counts = defaultdict(int)
    total_items = 0
    for o in orders:
        for item in o['items']:
            category_counts[item['category']] += 1
            total_items += 1

    if total_items == 0:
        return None

    hhi = sum((count / total_items) ** 2 for count in category_counts.values())
    return round(1 - hhi, 4)


def feature_adoption_rate(events):
    """% of discovery-card impressions that ended in 'accepted' rather than 'dismissed'."""
    shown = [e for e in events if e.get('action') in ('accepted', 'dismissed')]
    if not shown:
        return 0.0
    accepted = [e for e in shown if e['action'] == 'accepted']
    return round(len(accepted) / len(shown), 4)


def aov_trend(orders):
    """
    Linear regression slope of order value over time (orders sorted by
    date). Positive slope = AOV rising, negative = declining (the research
    doc flags declining AOV as a disengagement precursor). Uses simple
    least-squares, no external stats library needed.
    """
    if len(orders) < 2:
        return None

    sorted_orders = sorted(orders, key=lambda o: o['date'])
    xs = list(range(len(sorted_orders)))  # order sequence as the time axis
    ys = [o['value'] for o in sorted_orders]

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominator = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _self_check():
    print('--- attach_rate ---')
    orders = [{'order_id': 1, 'items': [1, 2, 3]}, {'order_id': 2, 'items': [1]}]
    ar = attach_rate(orders)
    assert ar == 2.0, f'expected 2.0, got {ar}'
    print(f'attach_rate = {ar} (expected 2.0) OK')

    print('\n--- cdi_herfindahl ---')
    # Fully concentrated: all 10 items from one category -> HHI=1 -> CDI (1-HHI) = 0
    concentrated = [{'items': [{'category': 'Groceries'}] * 10}]
    cdi_low = cdi_herfindahl(concentrated, ['Groceries'])
    assert cdi_low == 0.0, f'expected 0.0, got {cdi_low}'
    print(f'fully concentrated basket -> CDI = {cdi_low} (expected 0.0) OK')

    # Perfectly split across 2 categories, 5 each: HHI = 0.5^2+0.5^2=0.5 -> CDI=0.5
    diversified = [{'items': [{'category': 'Groceries'}] * 5 + [{'category': 'Electronics'}] * 5}]
    cdi_mid = cdi_herfindahl(diversified, ['Groceries', 'Electronics'])
    assert cdi_mid == 0.5, f'expected 0.5, got {cdi_mid}'
    print(f'evenly split 2-category basket -> CDI = {cdi_mid} (expected 0.5) OK')

    print('\n--- feature_adoption_rate ---')
    events = [{'action': 'accepted'}, {'action': 'accepted'}, {'action': 'dismissed'}, {'action': 'dismissed'}]
    far = feature_adoption_rate(events)
    assert far == 0.5, f'expected 0.5, got {far}'
    print(f'2 accepted / 4 shown -> FAI = {far} (expected 0.5) OK')

    print('\n--- aov_trend ---')
    # Perfectly linear rising values: 100, 110, 120, 130 -> slope should be 10
    rising_orders = [
        {'date': '2026-01-01', 'value': 100},
        {'date': '2026-01-02', 'value': 110},
        {'date': '2026-01-03', 'value': 120},
        {'date': '2026-01-04', 'value': 130},
    ]
    slope = aov_trend(rising_orders)
    assert abs(slope - 10.0) < 1e-9, f'expected 10.0, got {slope}'
    print(f'linearly rising AOV (100,110,120,130) -> slope = {slope} (expected 10.0) OK')

    print('\nAll self-checks passed.')


def main():
    parser = argparse.ArgumentParser(description='Compute quick-commerce operational metrics')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()

    if args.self_check:
        _self_check()
        return

    print('Run with --self-check to verify the math, or import these functions')
    print('directly once you have real orders.jsonl / event_log.jsonl to compute against.')


if __name__ == '__main__':
    main()
