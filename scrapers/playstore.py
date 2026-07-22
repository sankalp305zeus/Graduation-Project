"""
Play Store review scraper for Blinkit.

Library: google-play-scraper (pip install google-play-scraper)
App: Blinkit: Groceries & more
Package ID: com.grofers.customerapp
  (verified live at https://play.google.com/store/apps/details?id=com.grofers.customerapp
   — Blinkit was formerly Grofers, package name was never renamed)

Output schema (JSONL, one record per line):
  {id, source, text, rating, date, url, lang, meta}

Usage:
  python playstore.py --count 5000 --out ../data/raw/playstore_reviews.jsonl
"""

import argparse
import json
import sys
import time
from pathlib import Path

from google_play_scraper import Sort, reviews

APP_ID = "com.grofers.customerapp"


def scrape_playstore(count: int, lang: str = "en", country: str = "in") -> list[dict]:
    """
    Pulls up to `count` reviews, newest first, paginating internally.
    google-play-scraper's reviews() function handles pagination via continuation_token.
    """
    all_reviews = []
    continuation_token = None
    batch_size = 200  # library max per call is typically 199-200

    while len(all_reviews) < count:
        try:
            result, continuation_token = reviews(
                APP_ID,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=min(batch_size, count - len(all_reviews)),
                continuation_token=continuation_token,
            )
        except Exception as e:
            print(f"  [warn] batch failed: {e} — retrying once after 5s", file=sys.stderr)
            time.sleep(5)
            try:
                result, continuation_token = reviews(
                    APP_ID,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=min(batch_size, count - len(all_reviews)),
                    continuation_token=continuation_token,
                )
            except Exception as e2:
                print(f"  [error] retry also failed: {e2} — stopping, keeping what we have", file=sys.stderr)
                break

        if not result:
            print("  [info] no more reviews returned — corpus exhausted before target count", file=sys.stderr)
            break

        all_reviews.extend(result)
        print(f"  [progress] {len(all_reviews)}/{count} collected", file=sys.stderr)

        if continuation_token is None:
            break

        time.sleep(1.5)  # be polite, avoid rate-limit/block

    return all_reviews[:count]


def normalize(raw: dict, idx: int) -> dict:
    """Map google-play-scraper's raw review dict to the unified schema."""
    return {
        "id": f"ps_{raw.get('reviewId', idx)}",
        "source": "playstore",
        "text": (raw.get("content") or "").strip(),
        "rating": raw.get("score"),
        "date": raw.get("at").isoformat() if raw.get("at") else None,
        "url": f"https://play.google.com/store/apps/details?id={APP_ID}&reviewId={raw.get('reviewId', '')}",
        "lang": None,  # language filter runs in the cleaning pipeline (C.2), not here
        "meta": {
            "thumbs_up": raw.get("thumbsUpCount"),
            "app_version": raw.get("reviewCreatedVersion"),
            "reply_content": raw.get("replyContent"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape Blinkit Play Store reviews")
    parser.add_argument("--count", type=int, default=5000, help="Target number of reviews (default 5000)")
    parser.add_argument("--lang", type=str, default="en", help="Review language filter (default en)")
    parser.add_argument("--country", type=str, default="in", help="Store country (default in)")
    parser.add_argument("--out", type=str, default="../data/raw/playstore_reviews.jsonl")
    args = parser.parse_args()

    print(f"Scraping up to {args.count} reviews for {APP_ID} (lang={args.lang}, country={args.country})...")
    raw_reviews = scrape_playstore(args.count, lang=args.lang, country=args.country)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(raw_reviews):
            record = normalize(r, i)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {len(raw_reviews)} reviews to {out_path}")
    if len(raw_reviews) < args.count:
        print(
            f"[note] collected fewer than requested ({len(raw_reviews)} < {args.count}). "
            f"This is common — Play Store review pagination exhausts before large counts. "
            f"Not a bug; re-run later or accept the smaller corpus.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
