# AI Limitations, Failure Modes & Mitigations

Evaluator feedback on the prior cohort explicitly flags this as a common
gap: "most projects ignored hallucination risk, probabilistic outputs,
failure modes, and mitigation strategies." This doc is the direct answer —
and it's honest about what's actually mitigated versus what's a known,
accepted limitation.

---

## Why this matters for THIS system specifically

Two different AI subsystems exist in this project, with different risk
profiles:

1. **The discovery engine** (n8n hub + 3 spoke agents) — analyzes real
   review text to extract themes. Risk: hallucinated quotes, fabricated
   evidence, unsupported theme claims.
2. **The recommendation engine** (`recommend.js`) — generates a live,
   per-persona product recommendation grounded in those themes. Risk:
   recommending non-existent products, recommending already-tried
   categories, fabricating evidence citations, inappropriate inference
   from persona data.

Both are probabilistic — the same input does not guarantee the same output
across runs. Neither is trusted to grade or police itself anywhere in this
system.

---

## Failure modes and what actually catches each one

| Failure mode | Where it could occur | Mitigation | Verified? |
|---|---|---|---|
| Fabricated quote (text that doesn't exist in the source review) | Discovery engine, Theme Agent | `evals/quote_fidelity.py` — exact/normalized substring match against raw corpus; non-matching quotes auto-discarded | Designed, not yet run against real data (no real corpus exists yet) |
| Theme claims not actually supported by its evidence | Discovery engine | `evals/theme_support` — independent judge model scores each evidence review; <75% support or <30 evidence reviews blocks graduation to the deck | Designed, awaits real corpus |
| Hallucinated `product_id` (recommending something not in the real catalog) | Recommendation engine | `guardrails.js: checkProductExists` — deterministic lookup against the real products table | **Unit-tested, 8/8 passing** |
| Recommending a category the persona already orders from | Recommendation engine | `guardrails.js: checkCategoryEligible` — deterministic check against `never_tried` array; also pre-filtered before the LLM call even runs (defense in depth) | **Unit-tested** |
| Hallucinated `evidence_ids` (citing a review that wasn't actually retrieved) | Recommendation engine | `guardrails.js: checkEvidenceGrounded` — cited IDs must be a subset of what was actually retrieved | **Unit-tested** |
| Malformed/unparseable JSON output | Recommendation engine | Schema validation in `guardrails.js`, plus a try/catch parse fallback in `recommend.js` before guardrails even run | **Unit-tested** |
| Sensitive inference (e.g. inferring a health condition from purchase history) | Recommendation engine | `guardrails.js: checkNoSensitiveInference` — pattern-based block on health/condition language in generated reasoning | **Unit-tested** — but see honest caveat below |
| PII leak in generated text | Recommendation engine | `guardrails.js: checkNoPII` — pattern match for phone/email/card-number-shaped strings | **Unit-tested** |
| Cross-model or model-vs-human disagreement on theme classification | Discovery engine | Cohen's κ (cross-model) + blind human spot-check (Part D.3/D.4) — disagreement isn't hidden, it's reported and used as a "limitations" talking point | Designed, awaits real corpus |

**Universal fallback design**: every single guardrail failure in the
recommendation engine falls back to the original deterministic
price-matching logic — never a broken card, never an error state, never a
silent pass-through of unvalidated output.

---

## Honest limitations — what is NOT solved

- **Pattern-based guardrails are a demo-appropriate stand-in, not a
  production HAP/PII classifier.** `checkNoSensitiveInference` and
  `checkNoPII` are regex patterns. They will miss cases a dedicated
  classification model would catch, and can false-positive on benign text
  that happens to match a pattern. A production system needs a real
  classifier here — documented as roadmap, not solved.
- **No live inventory sync.** The hallucination guardrail checks against a
  real *catalog* table, but there's no concept of stock-outs in this
  prototype. A production system needs the recommendation engine to check
  real-time inventory, not just catalog existence.
- **Cold-start is unsolved.** All 6 personas have rich seeded history. A
  brand-new user with zero order history has no `never_tried`/
  `always_orders` signal for the engine to work from — this needs a
  separate strategy (e.g. defaulting to popularity-based recommendations
  until enough history accumulates), not currently built.
- **Small-sample evals are not decision-ready.** Support/Confidence/Lift
  and the operational metrics are mathematically correct (see
  `metrics-dictionary.md`) but statistically meaningless at 6-persona demo
  volume. Presenting them as findings rather than as a working
  demonstration would repeat the exact "fabricated rigor" mistake this
  project has tried to avoid from the start.
- **Guardrail unit tests use synthetic inputs I constructed**, not
  adversarial inputs from a red-team process. They prove each check
  functions correctly against the failure mode it targets — they don't
  prove the guardrails are unbeatable by a determined attempt to break
  them.
- **The recommendation engine has not been tested against a live LLM
  call.** Everything downstream of "Claude responds" (JSON parsing,
  guardrail checks) is verified. Whether Claude's actual real-world outputs
  trigger these guardrails at some meaningful rate is unknown until it's
  run live.

---

## What this section of the deck should say

Per the evaluator feedback's own guidance: don't just list these — explain
what each one means for a product decision. E.g.: "our guardrail
architecture means a bad AI output degrades gracefully to a still-useful
deterministic recommendation, never to a broken or hallucinated one — this
was a deliberate trade-off prioritizing reliability over recommendation
sophistication for a v1."
