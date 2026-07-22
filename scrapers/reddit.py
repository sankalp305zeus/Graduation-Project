"""
Reddit scraper for Blinkit-related posts and comments, via PRAW (official Reddit API wrapper).

Requires a registered Reddit app (free): https://www.reddit.com/prefs/apps
  -> create a "script" type app -> gives you client_id + client_secret
Set credentials in a .env file (see .env.example) — never hardcode them.

Output schema (JSONL, one record per line):
  {id, source, text, rating, date, url, lang, meta}
  (rating is null for Reddit — no star-rating concept; meta.score holds upvotes)

Usage:
  python reddit.py --limit 300 --out ../data/raw/reddit_threads.jsonl
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import praw
from dotenv import load_dotenv

load_dotenv()

SUBREDDITS = [
    "india",
    "delhi",
    "bangalore",
    "mumbai",
    "IndianSkincareAddicts",
    "onexindia",
    "personalfinanceindia",
]
SEARCH_TERM = "blinkit"


def get_reddit_client() -> praw.Reddit:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "blinkit-growth-research/0.1")

    if not client_id or not client_secret:
        print(
            "[error] REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. "
            "Copy .env.example to .env and fill in your app credentials from "
            "https://www.reddit.com/prefs/apps",
            file=sys.stderr,
        )
        sys.exit(1)

    return praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)


def normalize_submission(sub) -> dict:
    text = (sub.title or "") + "\n" + (sub.selftext or "")
    return {
        "id": f"rd_sub_{sub.id}",
        "source": "reddit",
        "text": text.strip(),
        "rating": None,
        "date": time_to_iso(sub.created_utc),
        "url": f"https://reddit.com{sub.permalink}",
        "lang": None,
        "meta": {
            "type": "submission",
            "subreddit": str(sub.subreddit),
            "score": sub.score,
            "num_comments": sub.num_comments,
        },
    }


def normalize_comment(comment, subreddit_name: str) -> dict:
    return {
        "id": f"rd_com_{comment.id}",
        "source": "reddit",
        "text": (comment.body or "").strip(),
        "rating": None,
        "date": time_to_iso(comment.created_utc),
        "url": f"https://reddit.com{comment.permalink}",
        "lang": None,
        "meta": {
            "type": "comment",
            "subreddit": subreddit_name,
            "score": comment.score,
        },
    }


def time_to_iso(epoch: float) -> str:
    import datetime

    return datetime.datetime.utcfromtimestamp(epoch).isoformat() + "Z"


def scrape_reddit(reddit: praw.Reddit, limit_per_subreddit: int) -> list[dict]:
    all_records = []

    for sub_name in SUBREDDITS:
        print(f"  [progress] searching r/{sub_name} for '{SEARCH_TERM}'...", file=sys.stderr)
        try:
            subreddit = reddit.subreddit(sub_name)
            results = subreddit.search(SEARCH_TERM, limit=limit_per_subreddit, sort="relevance")

            for submission in results:
                all_records.append(normalize_submission(submission))

                # Pull top-level comments too — skip AutoModerator, deleted, empty
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    if comment.author is None:
                        continue
                    if str(comment.author).lower() == "automoderator":
                        continue
                    if not comment.body or comment.body in ("[deleted]", "[removed]"):
                        continue
                    all_records.append(normalize_comment(comment, sub_name))

            time.sleep(2)  # rate-limit courtesy between subreddits

        except Exception as e:
            print(f"  [warn] r/{sub_name} failed: {e} — skipping this subreddit, continuing", file=sys.stderr)
            continue

    return all_records


def main():
    parser = argparse.ArgumentParser(description="Scrape Blinkit-related Reddit posts and comments")
    parser.add_argument(
        "--limit", type=int, default=50, help="Max submissions per subreddit search (default 50)"
    )
    parser.add_argument("--out", type=str, default="../data/raw/reddit_threads.jsonl")
    args = parser.parse_args()

    reddit = get_reddit_client()
    records = scrape_reddit(reddit, args.limit)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Done. Wrote {len(records)} records (submissions + comments) to {out_path}")
    if len(records) < 300:
        print(
            f"[note] collected {len(records)} — below the blueprint's 300-800 target. "
            f"Try raising --limit, or accept it: per the blueprint's cut order, "
            f"Reddit is the first source to drop if it underperforms.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
