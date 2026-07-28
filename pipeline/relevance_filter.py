"""
Relevance pre-filter — classifies cleaned reviews as RELEVANT (discusses
shopping behavior, product categories, discovery, trust/awareness of
categories) or NOT_RELEVANT (generic feedback: app crashes, delivery speed,
customer service, undifferentiated praise/complaints), via a cheap Groq
classification pass.

The blueprint's Part C.2 always specified this step between clean.py and
embed.py, but it was never actually built. Its absence is the likely cause
of a real 2029-review run producing 2 giant clusters (max 814) instead of
the expected 50-150: real Play Store corpora typically run 40-60% generic
feedback with no category-discovery signal at all, which HDBSCAN then
either dumps into one giant catch-all cluster or scatters as noise, rather
than finding 50-150 coherent behavioral themes. (normalize_embeddings=True
was ruled out as the cause — confirmed on the real corpus, no change.)

Batches reviews per Groq call (default 20/batch) — for a 2000+ review
corpus, one-call-per-review would burn through the free tier's ~30 RPM
ceiling long before finishing. See docs/GROQ_MIGRATION_AND_FAILPROOFING.md.

FAIL-SAFE DEFAULT: if a batch call fails after retries, or the model's
response is missing/malformed for a given review ID, that review is KEPT
(treated as relevant), never silently discarded. An API failure is not
evidence a review is irrelevant — this matches the "guardrail failures
degrade gracefully, never a silent drop" pattern used everywhere else in
this project (mvp-shell/api/guardrails.js, the n8n Evidence Validator).
Reviews kept this way are counted separately (kept_via_fallback) from
genuine LLM "relevant" calls, so the real discard rate stays auditable —
run `python relevance_filter.py --self-check` to see this proven against
a mocked client covering malformed JSON, a missing ID, rate-limiting that
eventually succeeds, and persistent failure.

Requires: GROQ_API_KEY. Model pinned to llama-3.3-70b-versatile — same
model already pinned in mvp-shell/api/recommend.js and the n8n workflow,
reused here rather than introducing a second unverified model string.
Re-verify at console.groq.com/docs/models before the live run; this
sandbox's egress policy blocks that site so it could not be checked here.
A smaller/cheaper Groq model may suffice for a yes/no classification —
worth trying if this pass is slow, but verify it's still listed as active
first.

Usage:
  python relevance_filter.py --input ../data/processed/cleaned_reviews.jsonl \
                              --output ../data/processed/relevant_reviews.jsonl

  python relevance_filter.py --self-check   # verify batching/parsing/retry/
                                             # fallback logic against a mocked
                                             # Groq client — no API key needed
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL = 'llama-3.3-70b-versatile'
BATCH_SIZE = 20

# Escalating backoff per docs/GROQ_MIGRATION_AND_FAILPROOFING.md ("back off
# with increasing wait (e.g. 10s, then 30s, then 60s) rather than the
# current 'retry once after fixed delay' pattern"). Shorter waits for
# non-rate-limit errors (network blips, 5xx) — those aren't quota-driven,
# so a long backoff just wastes time.
RATE_LIMIT_BACKOFFS = [10, 30, 60]
OTHER_ERROR_BACKOFFS = [2, 5]

SYSTEM_PROMPT = """You are a classifier for Blinkit (Indian quick-commerce app) user reviews.

For each review, decide whether it is RELEVANT or NOT_RELEVANT:
- RELEVANT: discusses shopping behavior, product categories, discovery of
  new categories, trust or awareness of a category, reasons for buying or
  avoiding a type of product.
- NOT_RELEVANT: generic feedback with no category signal — app crashes,
  delivery speed/lateness, customer service, undifferentiated praise or
  complaints ("great app", "worst app ever").

Respond with ONLY this JSON, no other text, covering EVERY review ID given,
in any order, never omitting one:
{"classifications": [{"id": "...", "relevant": true}, {"id": "...", "relevant": false}]}
"""


def build_client():
    try:
        from groq import Groq
    except ImportError:
        print('[error] groq package not installed. Run: pip install -r requirements.txt', file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print('[error] GROQ_API_KEY not set', file=sys.stderr)
        sys.exit(1)

    # max_retries=0: retry/backoff is handled explicitly by
    # classify_batch_with_retry below, so we control the exact escalation
    # rather than let the SDK's own default retrying interfere with timing.
    return Groq(api_key=api_key, max_retries=0)


def classify_batch(client, model, batch):
    """batch: list of {id, text}. Returns {id: bool}. Raises on any
    request/parse failure — the caller (classify_batch_with_retry) decides
    whether to retry or fall back."""
    user_payload = json.dumps([{'id': r['id'], 'text': r['text']} for r in batch])

    response = client.chat.completions.create(
        model=model,
        max_tokens=2000,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_payload},
        ],
    )
    text = response.choices[0].message.content
    parsed = json.loads(text)  # raises json.JSONDecodeError on malformed output — caller handles it

    result = {}
    for item in parsed.get('classifications', []):
        if 'id' in item and 'relevant' in item:
            result[item['id']] = bool(item['relevant'])
    return result


def classify_batch_with_retry(client, model, batch):
    """Returns {id: bool} on success, or None if all retries are exhausted —
    the caller must then apply the fail-safe default (keep every review in
    this batch)."""
    from groq import APIConnectionError, InternalServerError, RateLimitError

    rate_limit_attempt = 0
    other_attempt = 0

    while True:
        try:
            return classify_batch(client, model, batch)
        except RateLimitError:
            if rate_limit_attempt >= len(RATE_LIMIT_BACKOFFS):
                print(f'[error] batch of {len(batch)} exhausted rate-limit retries — '
                      f'falling back to keep-all for this batch', file=sys.stderr)
                return None
            wait = RATE_LIMIT_BACKOFFS[rate_limit_attempt]
            print(f'[warn] rate limited — waiting {wait}s (attempt {rate_limit_attempt + 1}/{len(RATE_LIMIT_BACKOFFS)})', file=sys.stderr)
            time.sleep(wait)
            rate_limit_attempt += 1
        except (APIConnectionError, InternalServerError, json.JSONDecodeError) as e:
            if other_attempt >= len(OTHER_ERROR_BACKOFFS):
                print(f'[error] batch of {len(batch)} exhausted retries ({e}) — '
                      f'falling back to keep-all for this batch', file=sys.stderr)
                return None
            wait = OTHER_ERROR_BACKOFFS[other_attempt]
            print(f'[warn] batch failed ({e}) — retrying in {wait}s', file=sys.stderr)
            time.sleep(wait)
            other_attempt += 1


def filter_reviews(client, model, reviews, batch_size=BATCH_SIZE):
    """Returns (kept_reviews, stats) where stats breaks down WHY each
    review was kept or discarded, so the discard rate stays auditable."""
    kept_reviews = []
    stats = {'relevant': 0, 'discarded': 0, 'kept_via_fallback': 0}

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        classifications = classify_batch_with_retry(client, model, batch)

        for review in batch:
            if classifications is None:
                # Whole batch failed after retries — fail-safe: keep.
                kept_reviews.append(review)
                stats['kept_via_fallback'] += 1
                continue

            relevant = classifications.get(review['id'])
            if relevant is None:
                # Model omitted this ID from an otherwise-parseable
                # response — fail-safe: keep, don't guess it's irrelevant.
                kept_reviews.append(review)
                stats['kept_via_fallback'] += 1
            elif relevant:
                kept_reviews.append(review)
                stats['relevant'] += 1
            else:
                stats['discarded'] += 1

        print(f'  [progress] {min(i + batch_size, len(reviews))}/{len(reviews)} classified', file=sys.stderr)

    return kept_reviews, stats


class _FakeResponse:
    def __init__(self, content):
        self.choices = [type('C', (), {'message': type('M', (), {'content': content})()})]


def run_self_check():
    import httpx
    from groq import APIConnectionError, RateLimitError

    fake_request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')

    ok = True

    def expect(name, condition):
        nonlocal ok
        print(f'  [{"PASS" if condition else "FAIL"}] {name}')
        ok = ok and condition

    # Scenario 1: well-formed response splits relevant/not correctly.
    class WellFormedClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse(json.dumps({
                        'classifications': [
                            {'id': 'r1', 'relevant': True},
                            {'id': 'r2', 'relevant': False},
                        ],
                    }))

    kept, stats = filter_reviews(WellFormedClient(), MODEL, [
        {'id': 'r1', 'text': 'I never tried the pharmacy section'},
        {'id': 'r2', 'text': 'App crashed on checkout, 1 star'},
    ])
    expect('well-formed batch: r1 kept, r2 discarded', {r['id'] for r in kept} == {'r1'})
    expect('stats: 1 relevant, 1 discarded, 0 fallback', stats == {'relevant': 1, 'discarded': 1, 'kept_via_fallback': 0})

    # Scenario 2: malformed JSON — whole batch must fall back to keep-all,
    # not crash and not silently discard.
    class MalformedClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse('not valid json at all')

    kept2, stats2 = filter_reviews(MalformedClient(), MODEL, [
        {'id': 'r3', 'text': 'some review'},
        {'id': 'r4', 'text': 'another review'},
    ])
    expect('malformed JSON: both reviews kept via fallback, none silently lost',
           {r['id'] for r in kept2} == {'r3', 'r4'} and stats2['kept_via_fallback'] == 2)

    # Scenario 3: response omits one review's ID — that one falls back to
    # keep, the other uses its genuine classification.
    class PartialClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse(json.dumps({
                        'classifications': [{'id': 'r5', 'relevant': False}],
                        # r6 omitted entirely
                    }))

    kept3, stats3 = filter_reviews(PartialClient(), MODEL, [
        {'id': 'r5', 'text': 'generic complaint'},
        {'id': 'r6', 'text': 'omitted by the model'},
    ])
    expect('missing ID in response: r5 genuinely discarded, r6 kept via fallback',
           {r['id'] for r in kept3} == {'r6'} and stats3 == {'relevant': 0, 'discarded': 1, 'kept_via_fallback': 1})

    # Scenario 4: rate-limited twice, then succeeds — proves the retry loop
    # actually retries rather than immediately falling back.
    call_count = {'n': 0}

    class FlakyThenSuccessClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    call_count['n'] += 1
                    if call_count['n'] <= 2:
                        raise RateLimitError('rate limited', response=httpx.Response(429, request=fake_request), body=None)
                    return _FakeResponse(json.dumps({'classifications': [{'id': 'r7', 'relevant': True}]}))

    import unittest.mock as mock
    with mock.patch('time.sleep'):  # don't actually wait 10s+30s in a test
        kept4, stats4 = filter_reviews(FlakyThenSuccessClient(), MODEL, [{'id': 'r7', 'text': 'x'}])
    expect('rate-limited twice then succeeds: retried until success, not a premature fallback',
           call_count['n'] == 3 and {r['id'] for r in kept4} == {'r7'} and stats4['kept_via_fallback'] == 0)

    # Scenario 5: persistent failure exhausts all retries — must still
    # fall back to keep, never raise out of filter_reviews entirely.
    class AlwaysFailsClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise APIConnectionError(message='connection refused', request=fake_request)

    with mock.patch('time.sleep'):
        kept5, stats5 = filter_reviews(AlwaysFailsClient(), MODEL, [{'id': 'r8', 'text': 'x'}])
    expect('persistent failure: exhausts retries, falls back to keep, does not raise',
           {r['id'] for r in kept5} == {'r8'} and stats5['kept_via_fallback'] == 1)

    print('Self-check passed.' if ok else 'Self-check FAILED.')
    sys.exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser(description='Filter cleaned reviews to those relevant for category-discovery clustering')
    parser.add_argument('--input', type=str, default='../data/processed/cleaned_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/relevant_reviews.jsonl')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    parser.add_argument('--self-check', action='store_true', help='Verify batching/retry/fallback logic against a mocked client, no API key needed')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    client = build_client()

    with open(args.input, encoding='utf-8') as f:
        reviews = [json.loads(line) for line in f if line.strip()]

    print(f'Classifying {len(reviews)} reviews in batches of {args.batch_size}...')
    kept_reviews, stats = filter_reviews(client, MODEL, reviews, args.batch_size)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        for r in kept_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    total = len(reviews)
    discard_rate = (stats['discarded'] / total * 100) if total else 0
    print(f'\nDone. {len(kept_reviews)}/{total} reviews kept ({discard_rate:.1f}% discarded).')
    print(f'  relevant (genuine LLM yes): {stats["relevant"]}')
    print(f'  discarded (genuine LLM no): {stats["discarded"]}')
    print(f'  kept_via_fallback (API/parse failure or missing ID — NOT a relevance judgment): {stats["kept_via_fallback"]}')
    if stats['kept_via_fallback'] > total * 0.1:
        print(f'  [warn] kept_via_fallback is >10% of the corpus — check GROQ_API_KEY, rate limits, '
              f'or the model output shape before trusting the filtered set', file=sys.stderr)
    print(f'Wrote {len(kept_reviews)} relevant reviews to {out_path}')


if __name__ == '__main__':
    main()
