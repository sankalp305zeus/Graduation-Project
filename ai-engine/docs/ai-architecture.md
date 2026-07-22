# AI Engine Architecture — Discovery Concierge

Ties together: scrapers → cleaning pipeline → n8n theme extraction → Supabase
→ RAG recommendation engine → MVP frontend. This doc exists so anyone
(including future-you) can see what's real, what's placeholder, and why.

## End-to-end flow

```
1. SCRAPERS (Python, run once, local — already built, not yet executed)
   Play Store + App Store + Reddit -> raw JSONL

2. pipeline/clean.py  [TESTED — dedupe/PII/language filter verified on synthetic data]
   raw JSONL -> cleaned JSONL

3. pipeline/embed.py  [NOT TESTED LIVE — no network path to OpenAI from build sandbox]
   cleaned JSONL -> embedded JSONL (calls OpenAI text-embedding-3-small)

4. pipeline/cluster.py  [TESTED — correctly recovered 3/3 synthetic clusters]
   embedded JSONL -> clusters.json, in the exact shape 02-theme-extraction.json expects

5. n8n workflow (02-theme-extraction.json, built earlier)
   clusters.json POSTed to webhook -> hub + 3 spoke agents -> validated themes

6. Supabase `themes` + `reviews` tables (schema built, seeded with PLACEHOLDER data)
   Real n8n output should be inserted here with is_placeholder = false

7. api/recommend.js + api/guardrails.js  [guardrails unit-tested 8/8 —
   recommend.js NOT tested live, no Supabase/Anthropic credentials in sandbox]
   Vercel serverless function: RAG retrieval from themes -> Claude call ->
   deterministic guardrail check -> real recommendation OR safe fallback

8. mvp-shell frontend (built earlier)
   NOT YET WIRED to call /api/recommend — still calls the local
   pickRecommendation() placeholder. See "Open questions" below.

9. evals/basket_analysis.py + evals/operational_metrics.py
   [both self-check verified against hand-calculated examples]
   Compute Support/Confidence/Lift, Attach Rate, CDI, FAI from event_log data
```

## What's real vs. placeholder — no ambiguity

| Component | Status |
|---|---|
| Scraper code | Built, syntax-checked. **Not yet run against live data.** |
| clean.py | Built AND tested — verified dedup/PII/language filtering on synthetic input. |
| embed.py | Built, syntax-checked. **Not tested** — needs your OpenAI credentials. |
| cluster.py | Built AND tested — correctly recovered 3 synthetic clusters, 0 false groupings. |
| n8n workflow (02) | Built, JSON-validated. **Not tested in a live n8n instance.** |
| themes/reviews tables | Schema built. Seeded with **7 placeholder themes, clearly flagged `is_placeholder = true`** — not derived from real review text. |
| guardrails.js | Built AND tested — 8/8 unit tests passing, verified each check catches what it should. |
| recommend.js | Built, syntax-checked. **Not tested live** — needs your Supabase + Anthropic credentials. |
| basket_analysis.py | Built AND tested — Support/Confidence/Lift verified against a hand-calculated example. |
| operational_metrics.py | Built AND tested — all 4 metrics verified against hand-calculated examples. |
| mvp-shell frontend | Built, screenshot-verified. **Still calls the OLD placeholder logic, not recommend.js.** |

## Guardrails — what's implemented, mapped to the research doc's 4 categories

| Category (from the doc) | What's actually implemented | What's deferred |
|---|---|---|
| Hallucination & Accuracy | `checkProductExists` — recommended product_id must exist in the real catalog, checked deterministically | Live OMS/ERP inventory sync (doesn't exist for a prototype — there's no real inventory system) |
| Behavioral Alignment | `checkCategoryEligible` — recommended category must be in the persona's `never_tried` list | Age-restricted/regulated-item filtering (not relevant — this catalog has no such items) |
| Data & Privacy | `checkNoPII` — pattern-based check for phone/email/card numbers in generated reasoning text | Full PII-scrubbing pipeline on training data (exists in clean.py already, upstream of this) |
| Appropriateness / HAP | `checkNoSensitiveInference` — pattern-based check blocking health/condition inferences in reasoning | A real HAP classifier model (per the doc's citation of dedicated toxicity-detection tools) — pattern matching is a reasonable stand-in for a demo, not for production |

Also implemented, not in the doc's 4 categories but necessary: `checkOutputSchema`
(malformed JSON) and `checkEvidenceGrounded` (cited evidence_ids must exist in
the retrieved themes — directly reuses the "never trust the LLM to grade
itself" pattern from the n8n Evidence Validator node).

**Every guardrail failure falls back to the original deterministic
recommendation logic** — the user never sees a broken card, they see a
slightly-less-personalized-but-still-sensible one.

## Evals — what's real code vs. what needs real volume

`basket_analysis.py` (Support/Confidence/Lift) and `operational_metrics.py`
(Attach Rate, CDI, FAI, AOV trend) are correctly implemented — every function
passes a hand-calculated self-check (`python3 <file> --self-check`). But:

**With 6 demo personas, these numbers are not findings.** Support/Confidence/
Lift need real transaction volume to mean anything statistically. Run
`--self-check` to prove the code works; don't run it against demo telemetry
and report the output as a result in your deck.

**Complaint-to-Order Ratio (COR) is intentionally NOT implemented.** It
requires a complaints/returns table that doesn't exist anywhere in this
schema. Building a COR calculator against zero real complaint data would
mean fabricating a number — exactly what this whole project's blueprint
(Part A, Failure 4) already identified as worse than not having the metric.

## Deliberately NOT built — and why

The research document you uploaded describes a full production system:
hybrid collaborative + content-based + contextual filtering, Apriori/
FP-Growth association-rule mining, a continuous learning/retraining loop,
and "guardian agent" autonomous guardrail subsystems. None of this is built,
on purpose:

- **Apriori/FP-Growth**: these need thousands of real transactions to mine
  meaningful rules. With 6 personas there's nothing to mine. `basket_analysis.py`
  gives you the same Support/Confidence/Lift math these algorithms are built
  on — swap in a real rule-mining library once you have real order volume.
- **Hybrid collaborative + content + contextual filtering**: collaborative
  filtering specifically needs many real users' behavior to find patterns
  across people — impossible with 6 synthetic personas by definition.
- **Continuous learning engine**: needs a live production feedback loop that
  doesn't exist for a 13-day prototype.
- **Guardian agent subsystems**: autonomous agents that "cross-reference and
  correct in real time" are themselves probabilistic systems needing their
  own evals — adding one AI system to guard another without evaluating the
  guardian doesn't reduce risk, it just hides it one layer deeper.

These are legitimate future-roadmap content — they belong on your deck's
slide 10 ("from one analysis to a continuous PM discovery platform"), not in
code that needs to work in 13 days.

## Open questions — need your input before going further

Per your instruction not to assume:

1. **embed.py calls OpenAI's API**, which means a second paid API account
   beyond Anthropic. Are you okay with that, or would you rather I rewrite
   it against Voyage AI (Anthropic's recommended embeddings partner) or a
   free local embedding model (lower quality, but zero extra cost/signup)?
2. **recommend.js isn't wired into the mvp-shell yet** — App.jsx still calls
   the old local placeholder function. Want me to make that connection now,
   or do you want to test recommend.js standalone against your own Supabase/
   Anthropic credentials first before it's live in the UI?
3. **Placeholder themes vs. real ones** — once real n8n output exists, do you
   want old placeholder themes deleted, or kept with `is_placeholder = true`
   so recommend.js can be told to prefer real themes but fall back to
   placeholders for categories that don't have real coverage yet?
