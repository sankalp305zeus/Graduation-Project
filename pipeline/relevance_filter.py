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
feedback with no category-discovery signal at all. (normalize_embeddings=True
was ruled out separately — confirmed no change on the real corpus.)

Batches reviews per Groq call (default 20/batch) and PROACTIVELY paces
requests against a rolling 60s window (RateLimiter below) so most batches
succeed on the first attempt instead of needing reactive 429 retries — the
first real run without this hit 429s on 48.3% of the corpus (980/2029
fell back). See docs/GROQ_MIGRATION_AND_FAILPROOFING.md for the RPM/TPM
math this is based on.

FAIL-SAFE DEFAULT: if a batch call fails after retries, or the model's
response is missing/malformed for a given review ID, that review is KEPT
(treated as relevant), never silently discarded. An API failure is not
evidence a review is irrelevant. Unlike the first version, every review's
outcome is now recorded with its SOURCE ('llm' = genuine model verdict,
'fallback' = kept by default) in a classifications ledger
(--classifications-output), not just aggregate counts — this is what
makes --resume-from possible: a review already classified with source
'llm' is never re-sent to Groq.

PROVIDERS: this script defaults to a LOCAL Ollama model (llama3.2:3b),
because relevance filtering is a one-time bulk job (~100+ batched calls
for a 2000-review corpus) that Groq's free-tier daily quota cannot absorb.
Local inference has no rate limits, so pacing is disabled and retries
reduce to basic transient-error handling on that path. --provider groq
still works and keeps the full pacing/backoff machinery. Groq remains the
default everywhere ELSE in the project (mvp-shell/api/recommend.js, the
n8n workflow) — this is not a project-wide provider change.

  ollama: needs `ollama serve` running and `ollama pull llama3.2:3b`.
          A preflight check fails loudly if either is missing, rather than
          letting every batch degrade to keep-all (a "successful" run that
          filters nothing). Output is constrained by a JSON schema, since
          a 3B model drops IDs and malforms JSON far more readily than a
          70B — and each such slip becomes an unfiltered review.
  groq:   needs GROQ_API_KEY. Pinned to llama-3.3-70b-versatile, the same
          model used in recommend.js and the n8n workflow.

Usage:
  # Default (local Ollama):
  python relevance_filter.py --input ../data/processed/cleaned_reviews.jsonl \
                              --output ../data/processed/relevant_reviews.jsonl

  # Hosted Groq instead:
  python relevance_filter.py --provider groq \
                              --input ../data/processed/cleaned_reviews.jsonl \
                              --output ../data/processed/relevant_reviews.jsonl

  # Resume a prior run, reclassifying only what wasn't a genuine verdict:
  python relevance_filter.py --input ../data/processed/cleaned_reviews.jsonl \
                              --output ../data/processed/relevant_reviews.jsonl \
                              --resume-from ../data/processed/relevance_classifications.jsonl

  # One-time bootstrap for a run made with the OLD version of this script
  # (which only wrote the kept subset, with no per-review source tag).
  # Can only recover confirmed genuine discards (reviews absent from the
  # old output — the fallback path never discards, so absence is reliable)
  # — reviews present in the old output are ambiguous (could be genuine-yes
  # OR fallback) and are marked for reclassification, not skipped.
  python relevance_filter.py --bootstrap-legacy-output ../data/processed/relevant_reviews.jsonl \
                              --input ../data/processed/cleaned_reviews.jsonl \
                              --classifications-output ../data/processed/relevance_classifications.jsonl

  python relevance_filter.py --self-check   # verify batching/parsing/retry/
                                             # fallback/pacing/resume logic,
                                             # no API key or real time needed
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL = 'llama-3.3-70b-versatile'  # Groq path
BATCH_SIZE = 20

# Local Ollama path — the default for THIS script, because relevance
# filtering is a one-time bulk job (~100+ batched calls for a 2000-review
# corpus) that Groq's free tier cannot absorb without constant 429
# fighting. Groq stays the default everywhere else in the project
# (mvp-shell/api/recommend.js, the n8n workflow) — this is not a
# project-wide provider change.
OLLAMA_MODEL = 'llama3.2:3b'
OLLAMA_HOST = 'http://localhost:11434'
OLLAMA_TIMEOUT = 300  # seconds per batch; local inference is slower per call than hosted
# Smaller default batch than Groq's: llama3.2:3b is a 3B model and degrades
# noticeably when asked to emit long multi-item JSON, and every dropped ID
# becomes a kept_via_fallback (unfiltered) review. Override with --batch-size.
OLLAMA_BATCH_SIZE = 10

# Escalating backoff for when a 429 slips through the proactive pacer
# anyway (clock drift, another process sharing the same Groq account,
# etc.) — per docs/GROQ_MIGRATION_AND_FAILPROOFING.md ("back off with
# increasing wait (e.g. 10s, then 30s, then 60s)"). Shorter waits for
# non-rate-limit errors — those aren't quota-driven.
RATE_LIMIT_BACKOFFS = [10, 30, 60]
OTHER_ERROR_BACKOFFS = [2, 5]

# Proactive pacing budget — conservative end of Groq's published 6k-12k
# TPM range, same conservative choice already made for the n8n workflow's
# pacing node (workflows/02-theme-extraction.json).
TPM_BUDGET = 6000
RPM_BUDGET = 30
CHARS_PER_TOKEN = 4
RESPONSE_TOKENS_PER_REVIEW = 15  # rough size of one {"id":"...","relevant":false} entry

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

# Ollama accepts a JSON schema (not just format="json") to constrain output —
# verified against the ollama package's own type definition:
#   format: Optional[Union[Literal['', 'json'], JsonSchemaValue]]
# Worth using: llama3.2:3b is far likelier than a 70B to emit malformed JSON
# or silently drop review IDs, and both of those degrade to kept_via_fallback,
# which is exactly the failure that made the first Groq run unusable.
# Schema-constrained decoding attacks that at the source.
OLLAMA_FORMAT_SCHEMA = {
    'type': 'object',
    'properties': {
        'classifications': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'relevant': {'type': 'boolean'},
                },
                'required': ['id', 'relevant'],
            },
        },
    },
    'required': ['classifications'],
}


class RateLimiter:
    """Proactive pacing against a rolling 60s window — waits BEFORE a batch
    if sending it would exceed the RPM or TPM budget, instead of only
    reacting after a 429 already happened. Uses actual post-call token
    usage when available (record()), falling back to the pre-call estimate
    when a call fails and no real usage was returned."""

    def __init__(self, tpm_budget=TPM_BUDGET, rpm_budget=RPM_BUDGET):
        self.tpm_budget = tpm_budget
        self.rpm_budget = rpm_budget
        self.token_window = []    # [(timestamp, tokens), ...]
        self.request_window = []  # [timestamp, ...]

    def _prune(self, now):
        self.token_window = [(t, tok) for t, tok in self.token_window if now - t < 60]
        self.request_window = [t for t in self.request_window if now - t < 60]

    def wait_before_batch(self, estimated_tokens):
        now = time.time()
        self._prune(now)

        wait_seconds = 0.0

        if len(self.request_window) >= self.rpm_budget:
            oldest = self.request_window[0]
            wait_seconds = max(wait_seconds, 60 - (now - oldest))

        tokens_in_window = sum(tok for _, tok in self.token_window)
        projected = tokens_in_window + estimated_tokens
        if projected > self.tpm_budget:
            excess = projected - self.tpm_budget
            wait_seconds = max(wait_seconds, min(60, (excess / self.tpm_budget) * 60))

        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def record(self, tokens):
        now = time.time()
        self.token_window.append((now, tokens))
        self.request_window.append(now)


def estimate_batch_tokens(batch):
    system_tokens = len(SYSTEM_PROMPT) // CHARS_PER_TOKEN
    user_payload = json.dumps([{'id': r['id'], 'text': r['text']} for r in batch])
    input_tokens = system_tokens + len(user_payload) // CHARS_PER_TOKEN
    output_tokens = len(batch) * RESPONSE_TOKENS_PER_REVIEW
    return input_tokens + output_tokens


def build_user_payload(batch):
    return json.dumps([{'id': r['id'], 'text': r['text']} for r in batch])


def parse_classifications(text):
    """Shared by every provider — the response text shape is identical
    regardless of who produced it. Raises json.JSONDecodeError on malformed
    output; the retry layer handles that."""
    parsed = json.loads(text)
    result = {}
    for item in parsed.get('classifications', []):
        if 'id' in item and 'relevant' in item:
            result[item['id']] = bool(item['relevant'])
    return result


class GroqProvider:
    """Hosted Groq. Rate-limited, so it uses proactive pacing + escalating
    429 backoff."""

    name = 'groq'
    paced = True

    def __init__(self, model=MODEL):
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
        self.client = Groq(api_key=api_key, max_retries=0)
        self.model = model

    @property
    def rate_limit_exceptions(self):
        from groq import RateLimitError
        return (RateLimitError,)

    @property
    def transient_exceptions(self):
        from groq import APIConnectionError, InternalServerError
        return (APIConnectionError, InternalServerError)

    def preflight(self):
        return  # nothing cheap to check; a bad key surfaces on the first call

    def call(self, batch):
        """Returns (text, actual_tokens_or_None)."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': build_user_payload(batch)},
            ],
        )
        usage = getattr(response, 'usage', None)
        actual_tokens = getattr(usage, 'total_tokens', None) if usage else None
        return response.choices[0].message.content, actual_tokens


class OllamaProvider:
    """Local Ollama over its REST API. No rate limits, so pacing is disabled
    and retries are basic transient-error handling only (no escalating
    429 backoff — there are no 429s to escalate against).

    Endpoint/payload/response shape verified against the official ollama
    python package's own source (POST /api/chat, response.message.content).
    """

    name = 'ollama'
    paced = False

    def __init__(self, model, host, timeout):
        import requests

        self.requests = requests
        self.model = model
        self.host = host.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        # Ollama is a local service by definition. If the environment has
        # HTTP_PROXY set without localhost in no_proxy, requests would try
        # to tunnel localhost traffic through it and fail confusingly —
        # bypass proxies explicitly rather than depend on env hygiene.
        self.session.trust_env = False

    @property
    def rate_limit_exceptions(self):
        return ()  # local inference has no rate limit

    @property
    def transient_exceptions(self):
        return (self.requests.exceptions.RequestException,)

    def preflight(self):
        """Fail loudly NOW if Ollama isn't running or the model isn't
        pulled. Without this, either failure degrades to keep-all on every
        batch — a 100% fallback rate that looks like a completed run but
        filters nothing."""
        try:
            response = self.session.get(f'{self.host}/api/tags', timeout=10)
            response.raise_for_status()
        except self.requests.exceptions.RequestException as e:
            print(f'[error] cannot reach Ollama at {self.host} ({e}). Is `ollama serve` running?', file=sys.stderr)
            sys.exit(1)

        available = [m.get('name', '') for m in response.json().get('models', [])]
        # `ollama list` reports "llama3.2:3b"; tolerate a bare "llama3.2"
        # being requested against a tagged entry.
        if not any(m == self.model or m.split(':')[0] == self.model.split(':')[0] for m in available):
            print(f'[error] model "{self.model}" not found in Ollama. Available: {available or "(none)"}\n'
                  f'        Pull it first:  ollama pull {self.model}', file=sys.stderr)
            sys.exit(1)
        print(f'Ollama preflight OK: {self.host}, model "{self.model}" available')

    def call(self, batch):
        """Returns (text, None) — token counts are irrelevant with no
        rate limit to pace against."""
        response = self.session.post(
            f'{self.host}/api/chat',
            json={
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': build_user_payload(batch)},
                ],
                'stream': False,
                'format': OLLAMA_FORMAT_SCHEMA,
                'options': {'temperature': 0},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()['message']['content'], None


def classify_batch_with_retry(provider, batch):
    """Returns ({id: bool} or None, tokens_for_pacing). tokens_for_pacing is
    always a number (actual usage on success, the pre-call estimate on
    total failure) so the rate limiter's window stays meaningful either
    way.

    Rate-limit backoff only escalates for providers that actually have
    rate limits (Groq). For a local provider, rate_limit_exceptions is
    empty, so only the short transient-error path can ever fire."""
    estimated_tokens = estimate_batch_tokens(batch)
    rate_limit_attempt = 0
    other_attempt = 0

    rate_limit_errors = tuple(provider.rate_limit_exceptions)
    transient_errors = tuple(provider.transient_exceptions) + (json.JSONDecodeError,)

    while True:
        try:
            text, actual_tokens = provider.call(batch)
            result = parse_classifications(text)
            return result, (actual_tokens if actual_tokens is not None else estimated_tokens)
        except rate_limit_errors:
            if rate_limit_attempt >= len(RATE_LIMIT_BACKOFFS):
                print(f'[error] batch of {len(batch)} exhausted rate-limit retries — '
                      f'falling back to keep-all for this batch', file=sys.stderr)
                return None, estimated_tokens
            wait = RATE_LIMIT_BACKOFFS[rate_limit_attempt]
            print(f'[warn] rate limited — waiting {wait}s (attempt {rate_limit_attempt + 1}/{len(RATE_LIMIT_BACKOFFS)})', file=sys.stderr)
            time.sleep(wait)
            rate_limit_attempt += 1
        except transient_errors as e:
            if other_attempt >= len(OTHER_ERROR_BACKOFFS):
                print(f'[error] batch of {len(batch)} exhausted retries ({e}) — '
                      f'falling back to keep-all for this batch', file=sys.stderr)
                return None, estimated_tokens
            wait = OTHER_ERROR_BACKOFFS[other_attempt]
            print(f'[warn] batch failed ({e}) — retrying in {wait}s', file=sys.stderr)
            time.sleep(wait)
            other_attempt += 1


class NullRateLimiter:
    """No-op pacer for providers without rate limits (local Ollama)."""

    def wait_before_batch(self, estimated_tokens):
        return

    def record(self, tokens):
        return


def filter_reviews(provider, reviews, batch_size=BATCH_SIZE, rate_limiter=None):
    """Returns (kept_reviews, classifications, stats).
    classifications: {id: {'relevant': bool, 'source': 'llm'|'fallback'}} —
    per-review provenance, which is what makes resuming possible."""
    if rate_limiter is None:
        rate_limiter = RateLimiter() if getattr(provider, 'paced', True) else NullRateLimiter()

    kept_reviews = []
    classifications = {}
    stats = {'relevant': 0, 'discarded': 0, 'kept_via_fallback': 0}

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]

        rate_limiter.wait_before_batch(estimate_batch_tokens(batch))
        result, tokens_for_pacing = classify_batch_with_retry(provider, batch)
        rate_limiter.record(tokens_for_pacing)

        for review in batch:
            relevant = result.get(review['id']) if result is not None else None
            if relevant is None:
                # Either the whole batch failed (result is None), or the
                # model omitted this specific ID from an otherwise-parseable
                # response — both are fail-safe: keep, don't guess "no".
                kept_reviews.append(review)
                classifications[review['id']] = {'relevant': True, 'source': 'fallback'}
                stats['kept_via_fallback'] += 1
            elif relevant:
                kept_reviews.append(review)
                classifications[review['id']] = {'relevant': True, 'source': 'llm'}
                stats['relevant'] += 1
            else:
                classifications[review['id']] = {'relevant': False, 'source': 'llm'}
                stats['discarded'] += 1

        print(f'  [progress] {min(i + batch_size, len(reviews))}/{len(reviews)} classified', file=sys.stderr)

    return kept_reviews, classifications, stats


def load_classifications_ledger(path):
    """{id: {'relevant': bool, 'source': str}} from a previous run's
    --classifications-output."""
    previous = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            previous[row['id']] = {'relevant': row['relevant'], 'source': row['source']}
    return previous


def partition_for_resume(reviews, previous):
    """Splits reviews into (carry_over, needs_classification). carry_over
    is {id: {'relevant', 'source'}} for reviews with a prior GENUINE ('llm')
    verdict — never re-sent to Groq. Everything else (missing from the
    ledger, or previously 'fallback') needs (re)classification."""
    carry_over = {}
    needs_classification = []
    for r in reviews:
        prev = previous.get(r['id'])
        if prev and prev['source'] == 'llm':
            carry_over[r['id']] = prev
        else:
            needs_classification.append(r)
    return carry_over, needs_classification


def bootstrap_legacy_ledger(all_reviews, legacy_kept_ids):
    """Migrates a run made with the OLD version of this script (which only
    wrote the kept subset, with no per-review source) into a classifications
    ledger. Only genuine discards are recoverable — the old fallback path
    NEVER discarded, so any review absent from legacy_kept_ids is a
    confirmed genuine 'no'. Reviews present in legacy_kept_ids are
    ambiguous (could be genuine-yes or fallback-kept) and are marked
    'fallback' so they get reclassified rather than silently trusted."""
    ledger = {}
    for r in all_reviews:
        if r['id'] in legacy_kept_ids:
            ledger[r['id']] = {'relevant': True, 'source': 'fallback'}  # ambiguous — will be reclassified
        else:
            ledger[r['id']] = {'relevant': False, 'source': 'llm'}  # confirmed genuine discard
    return ledger


class _StubProvider:
    """Mock provider for the self-check — mirrors the real provider
    interface (call/rate_limit_exceptions/transient_exceptions/paced)."""

    def __init__(self, responses, rate_limit_exc=(), transient_exc=(), paced=True):
        self._responses = responses  # callable(batch) -> (text, tokens), or raises
        self._rate_limit_exc = rate_limit_exc
        self._transient_exc = transient_exc
        self.paced = paced
        self.calls = 0

    @property
    def rate_limit_exceptions(self):
        return self._rate_limit_exc

    @property
    def transient_exceptions(self):
        return self._transient_exc

    def call(self, batch):
        self.calls += 1
        return self._responses(batch, self.calls)


def run_self_check():
    import httpx
    import requests
    from groq import APIConnectionError, RateLimitError
    import unittest.mock as mock

    fake_request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
    groq_rl = (RateLimitError,)
    groq_transient = (APIConnectionError,)

    ok = True

    def expect(name, condition):
        nonlocal ok
        print(f'  [{"PASS" if condition else "FAIL"}] {name}')
        ok = ok and condition

    # --- filter_reviews scenarios (stub provider, mocked time.sleep) ---

    well_formed = _StubProvider(
        lambda batch, n: (json.dumps({
            'classifications': [
                {'id': 'r1', 'relevant': True},
                {'id': 'r2', 'relevant': False},
            ],
        }), 123),
        rate_limit_exc=groq_rl, transient_exc=groq_transient,
    )
    with mock.patch('time.sleep'):
        kept, classifications, stats = filter_reviews(well_formed, [
            {'id': 'r1', 'text': 'I never tried the pharmacy section'},
            {'id': 'r2', 'text': 'App crashed on checkout, 1 star'},
        ])
    expect('well-formed batch: r1 kept, r2 discarded', {r['id'] for r in kept} == {'r1'})
    expect('stats: 1 relevant, 1 discarded, 0 fallback', stats == {'relevant': 1, 'discarded': 1, 'kept_via_fallback': 0})
    expect('classifications ledger tags r1/r2 source=llm',
           classifications['r1']['source'] == 'llm' and classifications['r2']['source'] == 'llm')

    malformed = _StubProvider(lambda batch, n: ('not valid json at all', None),
                              rate_limit_exc=groq_rl, transient_exc=groq_transient)
    with mock.patch('time.sleep'):
        kept2, classifications2, stats2 = filter_reviews(malformed, [
            {'id': 'r3', 'text': 'some review'},
            {'id': 'r4', 'text': 'another review'},
        ])
    expect('malformed JSON: both reviews kept via fallback, none silently lost',
           {r['id'] for r in kept2} == {'r3', 'r4'} and stats2['kept_via_fallback'] == 2)
    expect('classifications ledger tags r3/r4 source=fallback',
           classifications2['r3']['source'] == 'fallback' and classifications2['r4']['source'] == 'fallback')

    partial = _StubProvider(
        lambda batch, n: (json.dumps({'classifications': [{'id': 'r5', 'relevant': False}]}), None),
        rate_limit_exc=groq_rl, transient_exc=groq_transient,
    )
    with mock.patch('time.sleep'):
        kept3, classifications3, stats3 = filter_reviews(partial, [
            {'id': 'r5', 'text': 'generic complaint'},
            {'id': 'r6', 'text': 'omitted by the model'},
        ])
    expect('missing ID in response: r5 genuinely discarded, r6 kept via fallback',
           {r['id'] for r in kept3} == {'r6'} and stats3 == {'relevant': 0, 'discarded': 1, 'kept_via_fallback': 1})

    def flaky(batch, n):
        if n <= 2:
            raise RateLimitError('rate limited', response=httpx.Response(429, request=fake_request), body=None)
        return json.dumps({'classifications': [{'id': 'r7', 'relevant': True}]}), None

    flaky_provider = _StubProvider(flaky, rate_limit_exc=groq_rl, transient_exc=groq_transient)
    with mock.patch('time.sleep'):
        kept4, _c4, stats4 = filter_reviews(flaky_provider, [{'id': 'r7', 'text': 'x'}])
    expect('rate-limited twice then succeeds: retried until success, not a premature fallback',
           flaky_provider.calls == 3 and {r['id'] for r in kept4} == {'r7'} and stats4['kept_via_fallback'] == 0)

    def always_fails(batch, n):
        raise APIConnectionError(message='connection refused', request=fake_request)

    with mock.patch('time.sleep'):
        kept5, _c5, stats5 = filter_reviews(
            _StubProvider(always_fails, rate_limit_exc=groq_rl, transient_exc=groq_transient),
            [{'id': 'r8', 'text': 'x'}])
    expect('persistent failure: exhausts retries, falls back to keep, does not raise',
           {r['id'] for r in kept5} == {'r8'} and stats5['kept_via_fallback'] == 1)

    # --- Ollama provider: payload construction + response parsing ---
    # Verified against a mocked requests session rather than a live Ollama
    # (none available in the build environment) — this proves the request
    # shape and response-field access match the contract read out of the
    # official ollama package's source.

    captured = {}

    class _FakeHTTPResponse:
        status_code = 200

        def raise_for_status(self):
            return

        def json(self):
            return {'message': {'role': 'assistant', 'content': json.dumps({
                'classifications': [{'id': 'r9', 'relevant': True}],
            })}}

    ollama = OllamaProvider(model='llama3.2:3b', host='http://localhost:11434', timeout=300)

    def fake_post(url, json=None, timeout=None):
        captured['url'] = url
        captured['payload'] = json
        captured['timeout'] = timeout
        return _FakeHTTPResponse()

    ollama.session.post = fake_post
    text, tokens = ollama.call([{'id': 'r9', 'text': 'never tried the pet section'}])

    expect('ollama: posts to /api/chat on the configured host',
           captured['url'] == 'http://localhost:11434/api/chat')
    expect('ollama: payload pins the model, disables streaming, sends system+user messages',
           captured['payload']['model'] == 'llama3.2:3b'
           and captured['payload']['stream'] is False
           and [m['role'] for m in captured['payload']['messages']] == ['system', 'user'])
    expect('ollama: constrains output with a JSON schema (not just format="json")',
           captured['payload']['format'] == OLLAMA_FORMAT_SCHEMA)
    expect('ollama: reads response["message"]["content"], returns no token count',
           parse_classifications(text) == {'r9': True} and tokens is None)
    expect('ollama: no rate-limit exceptions declared (nothing to escalate against)',
           tuple(ollama.rate_limit_exceptions) == ())
    expect('ollama: paced=False so filter_reviews uses the no-op limiter',
           ollama.paced is False)

    # A local provider must never take the escalating 10/30/60s rate-limit
    # path — only the short transient one — even when its calls keep failing.
    def conn_error(batch, n):
        raise requests.exceptions.ConnectionError('refused')

    local_failing = _StubProvider(conn_error, rate_limit_exc=(),
                                  transient_exc=(requests.exceptions.RequestException,), paced=False)
    with mock.patch('time.sleep') as local_sleep:
        kept6, _c6, stats6 = filter_reviews(local_failing, [{'id': 'r10', 'text': 'x'}])
    expect('local provider failure: short transient retries only, no 10/30/60s escalation',
           [c[0][0] for c in local_sleep.call_args_list] == OTHER_ERROR_BACKOFFS
           and stats6['kept_via_fallback'] == 1 and {r['id'] for r in kept6} == {'r10'})

    # --- RateLimiter: proactive pacing itself ---

    limiter = RateLimiter(tpm_budget=1000, rpm_budget=30)
    with mock.patch('time.sleep') as sleep_mock:
        limiter.wait_before_batch(500)  # well under budget — no wait
        limiter.record(500)
    expect('RateLimiter: under budget triggers no wait', sleep_mock.call_count == 0)

    limiter2 = RateLimiter(tpm_budget=1000, rpm_budget=30)
    with mock.patch('time.sleep') as sleep_mock2:
        limiter2.record(900)  # simulate a prior call that used most of the budget
        limiter2.wait_before_batch(500)  # 900 + 500 > 1000 -> must wait
    expect('RateLimiter: projected-over-budget triggers a proactive wait', sleep_mock2.call_count == 1 and sleep_mock2.call_args[0][0] > 0)

    limiter3 = RateLimiter(tpm_budget=100000, rpm_budget=2)
    with mock.patch('time.sleep') as sleep_mock3:
        limiter3.record(10)
        limiter3.record(10)  # 2 requests already in window, rpm_budget=2
        limiter3.wait_before_batch(10)  # 3rd request must wait for RPM, even though TPM is fine
    expect('RateLimiter: RPM ceiling alone triggers a wait even when TPM has headroom',
           sleep_mock3.call_count == 1 and sleep_mock3.call_args[0][0] > 0)

    # --- Resume logic ---

    previous = {
        'r1': {'relevant': True, 'source': 'llm'},
        'r2': {'relevant': False, 'source': 'llm'},
        'r3': {'relevant': True, 'source': 'fallback'},
        # r4 not present at all (new review since the last run)
    }
    reviews = [{'id': f'r{i}', 'text': 'x'} for i in range(1, 5)]
    carry_over, needs_classification = partition_for_resume(reviews, previous)
    expect('resume: genuine llm verdicts (r1, r2) carried over, not reclassified',
           set(carry_over.keys()) == {'r1', 'r2'})
    expect('resume: fallback (r3) and unseen (r4) both need (re)classification',
           {r['id'] for r in needs_classification} == {'r3', 'r4'})

    # --- Legacy bootstrap ---

    all_reviews = [{'id': f'r{i}', 'text': 'x'} for i in range(1, 6)]
    legacy_kept_ids = {'r1', 'r3'}  # old output only ever contained kept (relevant OR fallback) IDs
    bootstrapped = bootstrap_legacy_ledger(all_reviews, legacy_kept_ids)
    expect('bootstrap: reviews absent from legacy output are confirmed genuine discards (source=llm)',
           bootstrapped['r2']['source'] == 'llm' and bootstrapped['r2']['relevant'] is False
           and bootstrapped['r4']['source'] == 'llm' and bootstrapped['r5']['source'] == 'llm')
    expect('bootstrap: reviews present in legacy output are ambiguous, marked for reclassification (source=fallback)',
           bootstrapped['r1']['source'] == 'fallback' and bootstrapped['r3']['source'] == 'fallback')

    print('Self-check passed.' if ok else 'Self-check FAILED.')
    sys.exit(0 if ok else 1)


def run_bootstrap(input_path, legacy_output_path, classifications_output_path):
    with open(input_path, encoding='utf-8') as f:
        all_reviews = [json.loads(line) for line in f if line.strip()]
    with open(legacy_output_path, encoding='utf-8') as f:
        legacy_kept_ids = {json.loads(line)['id'] for line in f if line.strip()}

    ledger = bootstrap_legacy_ledger(all_reviews, legacy_kept_ids)

    confirmed_discards = sum(1 for c in ledger.values() if c['source'] == 'llm')
    ambiguous = sum(1 for c in ledger.values() if c['source'] == 'fallback')

    out_path = Path(classifications_output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        for rid, c in ledger.items():
            f.write(json.dumps({'id': rid, 'relevant': c['relevant'], 'source': c['source']}) + '\n')

    print(f'Bootstrapped {len(ledger)} reviews from {legacy_output_path}:')
    print(f'  {confirmed_discards} confirmed genuine discards (will be skipped on --resume-from)')
    print(f'  {ambiguous} ambiguous "kept" reviews — could be genuine-yes or fallback, will be RECLASSIFIED '
          f'(the old script never recorded which)')
    print(f'Wrote {out_path} — pass it to --resume-from on your next run.')


def main():
    parser = argparse.ArgumentParser(description='Filter cleaned reviews to those relevant for category-discovery clustering')
    parser.add_argument('--input', type=str, default='../data/processed/cleaned_reviews.jsonl')
    parser.add_argument('--output', type=str, default='../data/processed/relevant_reviews.jsonl')
    parser.add_argument('--classifications-output', type=str, default='../data/processed/relevance_classifications.jsonl')
    parser.add_argument('--provider', choices=['groq', 'ollama'], default='ollama',
                         help='ollama (default for THIS script — local, no rate limits) or groq. '
                              'Groq remains the default everywhere else in the project '
                              '(recommend.js, the n8n workflow) — this flag is scoped to this script only.')
    parser.add_argument('--groq-model', type=str, default=MODEL)
    parser.add_argument('--ollama-model', type=str, default=OLLAMA_MODEL)
    parser.add_argument('--ollama-host', type=str, default=OLLAMA_HOST)
    parser.add_argument('--ollama-timeout', type=int, default=OLLAMA_TIMEOUT,
                         help='Per-batch read timeout in seconds — local inference on a small model is slower '
                              'per call than a hosted one, so this is generous by default')
    parser.add_argument('--batch-size', type=int, default=None,
                         help=f'Default: {BATCH_SIZE} for groq, {OLLAMA_BATCH_SIZE} for ollama (a 3B model handles '
                              f'shorter multi-item JSON far more reliably than a 70B)')
    parser.add_argument('--resume-from', type=str, default=None,
                         help='A previous --classifications-output — reviews already classified there with '
                              'source=llm are carried over, not re-sent to the model')
    parser.add_argument('--bootstrap-legacy-output', type=str, default=None,
                         help='One-off: migrate a run made with the OLD version of this script (a plain kept-only '
                              'JSONL) into a classifications ledger written to --classifications-output, then exit')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    if args.bootstrap_legacy_output:
        run_bootstrap(args.input, args.bootstrap_legacy_output, args.classifications_output)
        return

    if args.provider == 'ollama':
        provider = OllamaProvider(args.ollama_model, args.ollama_host, args.ollama_timeout)
        default_batch_size = OLLAMA_BATCH_SIZE
        model_label = args.ollama_model
    else:
        provider = GroqProvider(args.groq_model)
        default_batch_size = BATCH_SIZE
        model_label = args.groq_model
    batch_size = args.batch_size if args.batch_size is not None else default_batch_size

    # Fails loudly and exits if Ollama isn't running or the model isn't
    # pulled — without it, either failure would degrade to keep-all on
    # every batch: a "successful" run that filtered nothing.
    provider.preflight()

    with open(args.input, encoding='utf-8') as f:
        reviews = [json.loads(line) for line in f if line.strip()]
    reviews_by_id = {r['id']: r for r in reviews}

    carry_over = {}
    to_classify = reviews
    if args.resume_from:
        previous = load_classifications_ledger(args.resume_from)
        carry_over, to_classify = partition_for_resume(reviews, previous)
        print(f'Resuming from {args.resume_from}: {len(carry_over)} reviews carried over '
              f'(genuine prior verdict), {len(to_classify)} need (re)classification')

    print(f'Classifying {len(to_classify)} reviews via {provider.name} ({model_label}) '
          f'in batches of {batch_size}...')
    _kept_from_new, new_classifications, stats = filter_reviews(provider, to_classify, batch_size)

    all_classifications = dict(carry_over)
    all_classifications.update(new_classifications)
    kept_reviews = [reviews_by_id[rid] for rid, c in all_classifications.items() if c['relevant']]

    classifications_out_path = Path(args.classifications_output)
    classifications_out_path.parent.mkdir(parents=True, exist_ok=True)
    with classifications_out_path.open('w', encoding='utf-8') as f:
        for rid, c in all_classifications.items():
            f.write(json.dumps({'id': rid, 'relevant': c['relevant'], 'source': c['source']}) + '\n')

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        for r in kept_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    total = len(reviews)
    classified_now = len(to_classify)
    discard_rate = (stats['discarded'] / classified_now * 100) if classified_now else 0
    print(f'\nDone. {len(kept_reviews)}/{total} reviews kept overall.')
    if carry_over:
        print(f'  carried over from resume: {len(carry_over)}')
    print(f'  this run — relevant (genuine LLM yes): {stats["relevant"]}')
    print(f'  this run — discarded (genuine LLM no): {stats["discarded"]} ({discard_rate:.1f}% of reclassified)')
    print(f'  this run — kept_via_fallback (API/parse failure or missing ID — NOT a relevance judgment): {stats["kept_via_fallback"]}')
    if classified_now and stats['kept_via_fallback'] > classified_now * 0.1:
        print(f'  [warn] kept_via_fallback is >10% of what was (re)classified this run — check GROQ_API_KEY, '
              f'rate limits, or the model output shape before trusting the filtered set', file=sys.stderr)
    print(f'Wrote {len(kept_reviews)} relevant reviews to {out_path}')
    print(f'Wrote the full classifications ledger to {classifications_out_path} — pass it to --resume-from next time')


if __name__ == '__main__':
    main()
