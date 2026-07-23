"""
Ingest real theme-extraction output into Supabase.

Takes the n8n webhook's aggregated JSON response (see
workflows/02-theme-extraction.json's "Aggregate All Results" node) and the
embedded reviews JSONL (from embed.py — the source of each review's text,
source, rating, and embedding), and upserts both `themes` and `reviews` rows
with `is_placeholder = false`.

CATEGORIZATION: nothing upstream of this script (cluster.py, the n8n
workflow) ever assigns one of the 11 product categories to a cluster/theme,
but `themes.category` is NOT NULL and recommend.js filters themes by
category. This script closes that gap with a DETERMINISTIC keyword match
against theme_name/theme_description/core_job/opportunity fields — no extra
LLM call, consistent with this project's "never trust an LLM to grade
itself" pattern used everywhere else (guardrails.js, the Evidence Validator
node). Themes with zero keyword hits are skipped and reported, not
guessed — see CATEGORY_KEYWORDS below to extend coverage.

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (NOT the anon key — the
themes/reviews RLS policies only grant public SELECT, no INSERT; anon-key
writes fail silently). Set these in pipeline/.env or export them directly.

Usage:
  python ingest_themes.py --themes-input ../data/processed/n8n_themes_response.json \
                           --reviews-input ../data/processed/embedded_reviews.jsonl

  python ingest_themes.py --self-check   # verify categorization logic only,
                                          # no Supabase credentials needed
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Deterministic keyword -> category map. Matched case-insensitively as
# substrings against the theme's combined text. Extend this list rather
# than adding an LLM call if real themes keep coming back unmatched.
CATEGORY_KEYWORDS = {
    'Groceries & Fresh Produce': [
        'grocery', 'groceries', 'vegetable', 'fruit', 'milk', 'bread',
        'produce', 'fresh produce', 'dairy', 'atta', 'rice', 'dal', 'eggs',
    ],
    'Snacks & Beverages': [
        'snack', 'chips', 'cookie', 'biscuit', 'beverage', 'soda', 'juice',
        'soft drink', 'chocolate', 'namkeen', 'tea', 'coffee',
    ],
    'Household Essentials': [
        'cleaner', 'cleaning', 'detergent', 'dishwash', 'toilet cleaner',
        'tissue', 'household', 'mop', 'broom', 'sanitizer', 'disinfectant',
    ],
    'Personal Care & Beauty': [
        'face wash', 'skincare', 'skin care', 'moisturizer', 'lip balm',
        'makeup', 'beauty', 'shampoo', 'soap', 'perfume', 'deodorant',
        'cosmetic', 'personal care',
    ],
    'Baby Care': [
        'baby', 'diaper', 'infant', 'toddler', 'baby wipes', 'baby lotion',
        'formula milk',
    ],
    'Pet Supplies': [
        'pet food', 'dog food', 'cat food', 'puppy', 'kitten', 'pet shampoo',
        'litter', ' pet ', 'pet supplies',
    ],
    'Electronics Accessories': [
        'charger', 'charging cable', 'earphone', 'electronics', 'usb cable',
        'headphone', 'adapter', 'gadget',
    ],
    'Home & Kitchen': [
        'kitchen', 'cookware', 'utensil', 'home decor', 'furniture',
        'appliance', 'storage container',
    ],
    'Pharmacy & Health': [
        'medicine', 'pharmacy', 'health supplement', 'tablet', 'vitamin',
        'first aid', 'thermometer', 'prescription', 'over-the-counter',
    ],
    'Stationery & Books': [
        'stationery', ' pen ', 'notebook', 'book', 'pencil', 'paper',
        'stapler',
    ],
    'Toys & Gifting': [
        'toy', 'gift', 'gifting', 'board game', 'puzzle', 'kids play',
    ],
}


def categorize(theme):
    """Returns (category, hit_count) for the best keyword match, or (None, 0)."""
    text = ' '.join(
        filter(None, [
            theme.get('theme_name', ''),
            theme.get('theme_description', ''),
            theme.get('core_job', ''),
            theme.get('opportunity_title', ''),
            theme.get('opportunity_detail', ''),
        ])
    ).lower()
    text = f' {text} '  # padding so ' pen ' / ' pet ' style keywords can match at boundaries

    best_category, best_hits = None, 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_category, best_hits = category, hits

    return best_category, best_hits


def run_self_check():
    cases = [
        ({'theme_name': 'Distrust of returns for gadgets', 'theme_description': 'Users worry about returning a broken phone charger'}, 'Electronics Accessories'),
        ({'theme_name': 'Unaware of baby section', 'theme_description': 'Users did not know Blinkit sold diapers and baby wipes'}, 'Baby Care'),
        ({'theme_name': 'Only trusts groceries', 'theme_description': 'Prefers fresh produce and milk over other categories'}, 'Groceries & Fresh Produce'),
        ({'theme_name': 'Skin concerns', 'theme_description': 'Hesitant to try new face wash or moisturizer brands'}, 'Personal Care & Beauty'),
        ({'theme_name': 'Completely unrelated', 'theme_description': 'Nothing here matches any category keyword at all'}, None),
    ]

    ok = True
    for theme, expected in cases:
        category, hits = categorize(theme)
        passed = category == expected
        status = 'PASS' if passed else 'FAIL'
        print(f'  [{status}] "{theme["theme_name"]}" -> {category} (expected {expected})')
        ok = ok and passed

    if ok:
        print('Self-check passed.')
        sys.exit(0)
    else:
        print('Self-check FAILED.')
        sys.exit(1)


def load_reviews_by_id(path):
    reviews = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            reviews[r['id']] = r
    return reviews


def main():
    parser = argparse.ArgumentParser(description='Ingest real n8n theme-extraction output into Supabase')
    parser.add_argument('--themes-input', type=str, default='../data/processed/n8n_themes_response.json')
    parser.add_argument('--reviews-input', type=str, default='../data/processed/embedded_reviews.jsonl')
    parser.add_argument('--self-check', action='store_true', help='Verify categorization logic only, no Supabase credentials needed')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_url or not service_role_key:
        print('[error] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must both be set '
              '(the anon key cannot write — themes/reviews RLS only grants public SELECT)', file=sys.stderr)
        sys.exit(1)

    try:
        from supabase import create_client
    except ImportError:
        print('[error] supabase package not installed. Run: pip install -r requirements.txt', file=sys.stderr)
        sys.exit(1)

    supabase = create_client(supabase_url, service_role_key)

    with open(args.themes_input, encoding='utf-8') as f:
        payload = json.load(f)
    themes = payload.get('themes', [])

    reviews_by_id = load_reviews_by_id(args.reviews_input)

    theme_rows = []
    review_rows_by_id = {}
    skipped_no_category = []
    skipped_invalid_cluster = []

    for theme in themes:
        if theme.get('theme_name') == 'NO_COHERENT_THEME' or theme.get('is_valid_cluster') is False:
            skipped_invalid_cluster.append(theme.get('cluster_id'))
            continue

        category, hits = categorize(theme)
        if not category:
            skipped_no_category.append(theme.get('cluster_id'))
            continue

        evidence_ids = theme.get('evidence_ids', [])  # full deterministic cluster membership, not sample_evidence_ids
        theme_rows.append({
            'id': f'theme_{theme["cluster_id"]}',
            'category': category,
            'theme_name': theme.get('theme_name', ''),
            'description': theme.get('theme_description', ''),
            'evidence_ids': evidence_ids,
            'is_placeholder': False,
        })

        for review_id in evidence_ids:
            source_review = reviews_by_id.get(review_id)
            if not source_review:
                continue  # review referenced by the cluster but missing from embedded corpus — skip, don't fabricate
            review_rows_by_id[review_id] = {
                'id': source_review['id'],
                'source': source_review.get('source', 'unknown'),
                'text': source_review['text'],
                'rating': source_review.get('rating'),
                'category': category,
                'embedding': source_review.get('embedding'),
            }

    if theme_rows:
        supabase.table('themes').upsert(theme_rows).execute()
    if review_rows_by_id:
        supabase.table('reviews').upsert(list(review_rows_by_id.values())).execute()

    print(f'Ingested {len(theme_rows)} themes, {len(review_rows_by_id)} reviews.')
    if skipped_invalid_cluster:
        print(f'Skipped {len(skipped_invalid_cluster)} clusters with no coherent theme: {skipped_invalid_cluster}')
    if skipped_no_category:
        print(f'Skipped {len(skipped_no_category)} clusters — no category keyword match '
              f'(extend CATEGORY_KEYWORDS or categorize manually): {skipped_no_category}', file=sys.stderr)


if __name__ == '__main__':
    main()
