# Scrapers

Run each of these **once, locally**, and commit the output JSONL files to `/data/raw/`.
Per the blueprint (Part C.1): scraping is the flakiest layer of this project — do it early
(Days 1–3), never depend on live scraping again after that.

## Setup

```bash
cd scrapers
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # only needed for reddit.py — fill in your Reddit app credentials
```

## 1. Play Store — `playstore.py`

No auth needed.

```bash
python playstore.py --count 5000 --out ../data/raw/playstore_reviews.jsonl
```

- App: **Blinkit: Groceries & more**, package `com.grofers.customerapp`
  (confirmed live at play.google.com — Blinkit kept the old Grofers package name after rebrand)
- Sorted newest-first. Expect this to be your primary, highest-volume source.
- If it gets blocked mid-run: the script retries once automatically, then keeps whatever
  it already collected and exits cleanly — you'll still have a partial file to commit.

## 2. App Store — `appstore.py`

No auth needed. Uses Apple's public RSS customer-reviews feed.

```bash
python appstore.py --country in --out ../data/raw/appstore_reviews.jsonl
```

- App: **Blinkit: Groceries & more**, App Store ID `960335206`
  (confirmed live at apps.apple.com)
- This feed caps out around ~500 reviews regardless of app popularity — that's an Apple
  limitation, not a bug. Treat this as your secondary source, per the blueprint.

## 3. Reddit — `reddit.py`

**Requires** a free Reddit API app (takes ~2 minutes):
1. Go to https://www.reddit.com/prefs/apps
2. Click "create app" → choose type **script**
3. Copy the client ID (under the app name) and client secret into `.env`

```bash
python reddit.py --limit 50 --out ../data/raw/reddit_threads.jsonl
```

- Searches "blinkit" across r/india, r/delhi, r/bangalore, r/mumbai,
  r/IndianSkincareAddicts, r/onexindia, r/personalfinanceindia
- Pulls both submissions and their top-level comments
- `--limit 50` means up to 50 *submissions* per subreddit (comments come free per submission,
  so actual record count will be higher). Target per blueprint: 300–800 total records.
- If a subreddit search fails (banned/private/rate-limited), the script logs a warning and
  skips it rather than crashing the whole run.

## Output schema (all three scripts)

Every line in every output file is a JSON object with the same shape, so the cleaning
pipeline (`/pipeline/clean.py`) can process all three sources identically:

```json
{
  "id": "ps_abc123",
  "source": "playstore",
  "text": "...",
  "rating": 4,
  "date": "2026-07-10T12:00:00",
  "url": "https://...",
  "lang": null,
  "meta": { "...source-specific fields..." }
}
```

`lang` is left `null` here on purpose — language detection happens once, centrally, in the
cleaning pipeline, not separately in each scraper.

## A note on reliability

Run these scripts and **commit the raw JSONL output to git immediately**. That committed
data is your disaster insurance (blueprint Part A, Failure 1 / Part G). If Play Store or
Reddit changes their API or blocks you next week, it doesn't matter — you already have
the corpus.
