"""
App Store review scraper for Blinkit, via Apple's public RSS customer-reviews feed.
No auth required. This feed is capped at roughly the ~500 most recent reviews
(10 pages x ~50 reviews, page cap enforced by Apple) — this is a known limitation
of the RSS approach, not a bug in this script (Medium confidence on the exact cap;
Apple doesn't document it precisely and it has shifted before).

App: Blinkit: Groceries & more
App Store ID: 960335206
  (verified live at https://apps.apple.com/us/app/blinkit-groceries-more/id960335206)

Feed URL pattern:
  https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortby=mostrecent/page={page}/json

Output schema (JSONL, one record per line):
  {id, source, text, rating, date, url, lang, meta}

Usage:
  python appstore.py --country in --out ../data/raw/appstore_reviews.jsonl
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

APP_ID = "960335206"
MAX_PAGES = 10  # Apple's RSS feed does not reliably return pages beyond ~10
BASE_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortby=mostrecent/page={page}/json"


def fetch_page(country: str, page: int) -> list[dict]:
    url = BASE_URL.format(country=country, app_id=APP_ID, page=page)
    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    data = resp.json()

    entries = data.get("feed", {}).get("entry", [])
    # The first entry on page 1 is sometimes app metadata, not a review — it lacks 'im:rating'.
    reviews = [e for e in entries if "im:rating" in e]
    return reviews


def normalize(raw: dict, country: str) -> dict:
    """Map an Apple RSS <entry> dict to the unified schema."""
    review_id = raw.get("id", {}).get("label", "")
    return {
        "id": f"as_{review_id}",
        "source": "appstore",
        "text": raw.get("content", {}).get("label", "").strip(),
        "rating": int(raw.get("im:rating", {}).get("label", 0)) if raw.get("im:rating") else None,
        "date": raw.get("updated", {}).get("label"),
        "url": f"https://apps.apple.com/{country}/app/id{APP_ID}?see-all=reviews",
        "lang": None,  # language filter runs in the cleaning pipeline (C.2), not here
        "meta": {
            "title": raw.get("title", {}).get("label"),
            "app_version": raw.get("im:version", {}).get("label"),
            "author": raw.get("author", {}).get("name", {}).get("label"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape Blinkit App Store reviews via RSS")
    parser.add_argument("--country", type=str, default="in", help="App Store country code (default in)")
    parser.add_argument("--out", type=str, default="../data/raw/appstore_reviews.jsonl")
    args = parser.parse_args()

    all_reviews = []
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        print(f"  [progress] fetching page {page}/{MAX_PAGES}...", file=sys.stderr)
        try:
            raw_entries = fetch_page(args.country, page)
        except requests.RequestException as e:
            print(f"  [warn] page {page} failed: {e} — retrying once after 5s", file=sys.stderr)
            time.sleep(5)
            try:
                raw_entries = fetch_page(args.country, page)
            except requests.RequestException as e2:
                print(f"  [error] retry also failed: {e2} — stopping at page {page}", file=sys.stderr)
                break

        if not raw_entries:
            print(f"  [info] page {page} empty — feed exhausted", file=sys.stderr)
            break

        new_count = 0
        for raw in raw_entries:
            record = normalize(raw, args.country)
            if record["id"] in seen_ids:
                continue
            seen_ids.add(record["id"])
            all_reviews.append(record)
            new_count += 1

        if new_count == 0:
            print(f"  [info] page {page} returned only duplicates — feed exhausted", file=sys.stderr)
            break

        time.sleep(1.5)  # be polite

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for record in all_reviews:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {len(all_reviews)} reviews to {out_path}")
    print(
        "[note] App Store RSS caps out around ~500 reviews regardless of app size — "
        "this is expected, not a failure. Treat App Store as your secondary source (per blueprint C.1).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
