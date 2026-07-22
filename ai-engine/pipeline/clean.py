"""
Cleaning pipeline — reads raw scraper JSONL, applies dedupe + language filter
+ PII scrub + length filter, writes cleaned JSONL.

This is pure local computation, no network calls — fully testable in any
environment, including sandboxes with no internet access.

Input:  /data/raw/{playstore,appstore,reddit}_reviews.jsonl (schema from the
        scraper scripts: {id, source, text, rating, date, url, lang, meta})
Output: /data/processed/cleaned_reviews.jsonl

Usage:
  python clean.py --input-dir ../data/raw --output ../data/processed/cleaned_reviews.jsonl
"""

import argparse
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

from langdetect import detect, LangDetectException

MIN_LENGTH = 15
ALLOWED_LANGS = {'en'}  # Hinglish gets caught by langdetect inconsistently —
                          # see note in main() about the pragmatic workaround

PII_PATTERNS = [
    (re.compile(r'\b\d{10}\b'), '[PHONE]'),                          # 10-digit phone
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '[EMAIL]'),             # email
    (re.compile(r'\b(?:order|ord)[\s#:-]*\d{6,}\b', re.I), '[ORDER_ID]'),  # order IDs
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[CARD_NUMBER]'),  # card-like numbers
]


def scrub_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def content_hash(text: str) -> str:
    """Normalized hash for exact/near-dup detection — lowercase, whitespace-collapsed."""
    normalized = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def is_likely_english_or_hinglish(text: str) -> bool:
    """
    langdetect is unreliable on short, code-mixed Hinglish text — it often
    misclassifies "yeh app bahut acha hai" as Bengali or Somali because the
    romanized script confuses the n-gram model. Pragmatic workaround: accept
    anything langdetect calls English OR anything containing enough common
    Latin-script English words (a proxy for "readable to an English-speaking
    analyst," which is what actually matters for this project's manual
    eval/spot-check steps in blueprint Part D.4).
    """
    try:
        if detect(text) == 'en':
            return True
    except LangDetectException:
        pass
    # Fallback: count common English function words as a crude Hinglish/English signal
    common_words = {'the', 'is', 'app', 'good', 'not', 'and', 'for', 'i', 'this', 'was', 'but'}
    tokens = set(re.findall(r'\b[a-z]+\b', text.lower()))
    return len(tokens & common_words) >= 2


def clean_records(records):
    seen_hashes = set()
    cleaned = []
    stats = {'total': 0, 'dropped_dup': 0, 'dropped_short': 0, 'dropped_lang': 0, 'kept': 0}

    for r in records:
        stats['total'] += 1
        text = (r.get('text') or '').strip()

        if len(text) < MIN_LENGTH:
            stats['dropped_short'] += 1
            continue

        h = content_hash(text)
        if h in seen_hashes:
            stats['dropped_dup'] += 1
            continue
        seen_hashes.add(h)

        if not is_likely_english_or_hinglish(text):
            stats['dropped_lang'] += 1
            continue

        r['text'] = scrub_pii(text)
        r['lang'] = 'en'  # normalized — see is_likely_english_or_hinglish note above
        cleaned.append(r)
        stats['kept'] += 1

    return cleaned, stats


def main():
    parser = argparse.ArgumentParser(description='Clean raw scraped reviews')
    parser.add_argument('--input-dir', type=str, default='../data/raw')
    parser.add_argument('--output', type=str, default='../data/processed/cleaned_reviews.jsonl')
    args = parser.parse_args()

    input_files = glob.glob(str(Path(args.input_dir) / '*.jsonl'))
    if not input_files:
        print(f'[error] no .jsonl files found in {args.input_dir}', file=sys.stderr)
        sys.exit(1)

    all_records = []
    for f in input_files:
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    all_records.append(json.loads(line))

    print(f'Loaded {len(all_records)} raw records from {len(input_files)} file(s)')

    cleaned, stats = clean_records(all_records)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        for r in cleaned:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f'Done. {stats}')
    print(f'Wrote {len(cleaned)} cleaned records to {out_path}')


if __name__ == '__main__':
    main()
