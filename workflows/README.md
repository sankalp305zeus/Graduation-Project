# 02-theme-extraction.json — Import & Test Guide

This is the hub-and-spoke theme extraction workflow: 1 orchestrator + 3 spoke
agents (Theme, JTBD/Segment, Opportunity), built from the corrected NotebookLM
plan. This is the workflow the submission brief calls "demonstrate your
review analysis workflow" — it needs a public, clickable link.

## Import

1. n8n → Workflows → **Import from File** → select `02-theme-extraction.json`
2. Add an **Ollama credential** (`ollamaApi`, Base URL `http://localhost:11434`)
   to **all four** `lmChatOllama` nodes (Theme Agent Model, JTBD Agent Model,
   Opportunity Agent Model, Orchestrator Model) — the JSON deliberately ships
   without credentials, you must attach your own after import. All four are
   pinned to `llama3.1:latest`.
3. Activate the workflow to get its public webhook URL

**Prerequisites:** `ollama serve` running, and `ollama pull llama3.1:latest`.

> ⚠️ **If you run n8n in Docker**, `localhost:11434` resolves to the *container*,
> not your host — the Ollama credential's Base URL must be
> `http://host.docker.internal:11434` (Mac/Windows) or your host's LAN IP
> (Linux). Running n8n natively via `npx n8n` keeps `localhost` correct.

## Provider: local Ollama (was Groq)

Theme extraction makes **4 LLM calls per cluster** — at 50-150 clusters
that's **200-600 calls** for one full run, which exceeds Groq's free-tier
daily cap (the same cap that already blocked a relevance-filtering run).
The 4 model nodes therefore run against a **local Ollama** instance.

- **Model is `llama3.1:latest` (8B), not the 3B used by
  `pipeline/relevance_filter.py`.** That script does binary yes/no
  classification; these agents do theme naming, JTBD inference, and
  opportunity scoring, which need real reasoning.
- **Pacing removed.** The token-aware `Compute Rate Limit Pacing` code node
  and the `Rate Limit Pause` Wait node are both **deleted** — local
  inference has no RPM/TPM ceiling to pace against. `Evidence Validator`
  now loops straight back to `Loop Clusters`.
- **Retries simplified to basic error handling.** The 4 model nodes keep
  `retryOnFail: true` but at `maxTries: 2, waitBetweenTries: 5000` — enough
  to absorb a cold model load or a momentarily busy Ollama, with no
  escalating 429 backoff since there are no 429s locally.
- **Expect this run to be slower in wall-clock time than Groq**, since a
  local 8B model is far slower per call than hosted inference — but it runs
  unattended with no quota to exhaust.
- **`mvp-shell/api/recommend.js` stays on Groq** — one call per
  recommendation is low-volume and unaffected by the daily cap.

### If the agents return unparseable output

`llama3.1:latest` is much smaller than the 70B this workflow was originally
written against, so malformed JSON is more likely. The `Evidence Validator`
already handles it gracefully (emits `validation_error` for that cluster and
keeps going, rather than failing the run). If it happens often, open the 4
model nodes and set **Options → Output Format → JSON**. That wasn't enabled
by default deliberately: it couldn't be tested against a live n8n instance
from the build environment, and if it interfered with the Agent node's own
output handling it would break *every* cluster — a worse failure than
occasional parse errors that are already caught and reported.

## Before running the full corpus — test with 2 fake clusters first

**Loop Clusters output indices — now VERIFIED, do not swap.** Read out of
the `n8n-nodes-base` SplitInBatchesV3 source: `outputNames: ['done','loop']`,
and `execute()` returns `[processedItems, []]` when no items remain vs
`[[], returnItems]` while looping. So **output 0 = done, output 1 = loop**,
and the shipped wiring (0 → Aggregate All Results, 1 → Prepare Cluster Text)
is correct for `typeVersion: 3`. If the workflow finishes instantly, that is
*not* the cause — see the Code node mode note below.

Still genuinely unverified: the **Wait For All Spokes** merge node's exact
output shape, which the **Reshape For Synthesizer** code node has an inline
comment about adjusting if needed.

### Code node execution mode (fixed — cause of a silent instant "success")

Every Code node here returns an **array** of items, which n8n only permits in
**Run Once for All Items** mode — and that is the Code node's default when
`mode` is unset (confirmed in `Code.node.js`; the each-item validator
explicitly rejects array returns with *"please use the 'Run Once for All
Items' mode instead"*).

The nodes originally read their input with `$input.item` / `$(node).item`,
which are the **Run Once for Each Item** APIs and don't exist in all-items
mode. That failed at the *first* Code node after the webhook — presenting as
an execution that ends in milliseconds with only the Webhook node ticked.
All five nodes now use `$input.first()` / `$(node).first()`, which is exact
here because `batchSize` is 1, so the loop's current item is the only item.

Send this test payload to the webhook before trusting it with real data:

```json
{
  "corpus_total": 100,
  "corpus_total_basis": "manual_test_payload",
  "clusters": [
    {
      "cluster_id": "test-1",
      "reviews": [
        {"id": "r1", "text": "I never buy electronics here, too scared about returns if something breaks", "rating": 3},
        {"id": "r2", "text": "Wish there was an easy way to return a broken phone charger", "rating": 2},
        {"id": "r3", "text": "Great app but I only trust it for groceries, not gadgets", "rating": 4}
      ]
    },
    {
      "cluster_id": "test-2",
      "reviews": [
        {"id": "r4", "text": "Didn't know Blinkit sold baby products until my friend told me", "rating": 5},
        {"id": "r5", "text": "More people should know about the baby care section, it's hidden", "rating": 4}
      ]
    }
  ]
}
```

`corpus_total` is included so this test also exercises the prevalence
path — with 100 as the denominator, `test-1` should come back with
`prevalence_pct: 3` (3 of 100) and `test-2` with `2`. Omit those two
top-level fields and the workflow falls back to the 5 reviews in the
payload, reporting `prevalence_basis:
"clustered_reviews_in_payload_fallback"` — which is also worth seeing once,
to confirm the fallback labels itself rather than silently producing a
percentage of the wrong thing.

**What to check in the n8n execution log after this test run:**
- Does the loop actually iterate twice (once per cluster) and then stop?
- Does `Evidence Validator`'s output for `test-1` include all 3 of
  `r1, r2, r3` in `evidence_ids` (not just whatever the LLM sampled)?
- Is `prevalence_pct` 3 for `test-1` and 2 for `test-2`, with
  `prevalence_basis: "manual_test_payload"`?
- Did all four agents return parseable JSON, or is there a
  `validation_error` (see the unparseable-output note above)?
- Does the final response include both clusters?

If the loop doesn't terminate, or `Reshape For Synthesizer` errors out, the
most likely cause is a mismatch between what I assumed for
`splitInBatches`/`merge` output shapes and your n8n version's actual
behavior — open those two nodes in the UI, check their real output data
structure from the test execution, and adjust the code node accordingly.
This is expected due-diligence before trusting the workflow with your full
corpus, not a sign something is fundamentally broken.

## Design notes (why it's built this way)

- **Evidence IDs are deterministic, not LLM-selected.** The LLM only reads
  5-8 sample reviews per cluster to name the theme. The `evidence_ids`
  attached to each theme in the final output come from the full cluster
  membership (known from your upstream HDBSCAN clustering, passed through
  untouched) — this is what lets a theme have 30+ evidence reviews for the
  D.2 eval, even though the LLM only ever reads a handful.
- **Fan-out needs no special node.** `Prepare Cluster Text`'s single output
  connects directly to all three spoke agents — n8n handles one-to-many
  connections natively.
- **Evidence Validator is deterministic code, not another LLM call** —
  per the blueprint's own rule (Part A, Failure 4): never trust an LLM to
  grade itself. It substring-checks cited IDs against real cluster
  membership and flags (doesn't silently discard) any hallucinated IDs.
- **No rate limiting.** Removed along with the Groq→Ollama swap — local
  inference has no quota to pace against. `Evidence Validator` loops
  directly back to `Loop Clusters`.
- **Prevalence is computed deterministically, not by the LLM.** Each theme
  carries `prevalence_pct` — its `evidence_count` as a share of
  `corpus_total` (supplied by `pipeline/cluster.py` in the webhook payload).
  This exists because AI severity rankings mislead on their own: review text
  over-represents angry 1-star writers, so a "severity 5" theme covering
  0.4% of the corpus is a very different product decision from the same
  score at 15%. **Always report the two together.** Like `evidence_ids`,
  this is arithmetic over real cluster membership — not the model's opinion.
- **The prevalence denominator is always labelled.** `prevalence_basis`
  travels with every percentage: `embedded_reviews_analyzed` (the default —
  the post-relevance-filter corpus that was actually clustered),
  `explicit_--corpus-total` (you passed `cluster.py --corpus-total N`, e.g.
  the full pre-filter cleaned count), or
  `clustered_reviews_in_payload_fallback` (no `corpus_total` in the payload
  at all — an older `clusters.json`, or a hand-written test payload). An
  unlabelled percentage is precisely the misleading number prevalence is
  meant to prevent, so the basis is never dropped. If `corpus_total` is
  missing or zero, `prevalence_pct` is `null` rather than a bogus figure.
