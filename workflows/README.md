# 02-theme-extraction.json — Import & Test Guide

This is the hub-and-spoke theme extraction workflow: 1 orchestrator + 3 spoke
agents (Theme, JTBD/Segment, Opportunity), built from the corrected NotebookLM
plan. This is the workflow the submission brief calls "demonstrate your
review analysis workflow" — it needs a public, clickable link.

## Import

1. n8n → Workflows → **Import from File** → select `02-theme-extraction.json`
2. Add your Anthropic credential to **all four** `lmChatAnthropic` nodes
   (Theme Agent Model, JTBD Agent Model, Opportunity Agent Model, Orchestrator
   Model) — the JSON deliberately ships without credentials, you must attach
   your own after import
3. Activate the workflow to get its public webhook URL

## Before running the full corpus — test with 2 fake clusters first

The **Loop Clusters** node (`n8n-nodes-base.splitInBatches`) has a note
attached flagging that its exact output-index behavior (which output is
"done" vs "loop") should be verified against your n8n version's UI — I
built it against standard convention (output 0 = done, output 1 = loop)
but couldn't test it live. Same caution applies to the **Wait For All
Spokes** merge node's exact output shape, which the **Reshape For
Synthesizer** code node has an inline comment about adjusting if needed.

Send this test payload to the webhook before trusting it with real data:

```json
{
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

**What to check in the n8n execution log after this test run:**
- Does the loop actually iterate twice (once per cluster) and then stop?
- Does `Evidence Validator`'s output for `test-1` include all 3 of
  `r1, r2, r3` in `evidence_ids` (not just whatever the LLM sampled)?
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
- **Rate limiting:** a 2-second `Wait` node sits between the Evidence
  Validator and the loop-back to Split In Batches, pacing LLM calls per
  the blueprint's rate-limit guidance.
