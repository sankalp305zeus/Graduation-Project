# Metrics Dictionary

Every metric used anywhere in this project, defined completely. Per direct
evaluator feedback: a metric name alone is not enough — each one needs a
definition, numerator, denominator, formula, rationale, and how it changes
a product decision. This doc exists so no metric in the deck is presented
without all six.

---

## North Star

### % of MAU purchasing ≥1 new category per month
- **Definition**: share of Monthly Active Customers who complete at least one order in a Top-Level Category they had not previously ordered from, within a 30-day window.
- **Numerator**: count of unique MAUs with ≥1 net-new-category order in the period.
- **Denominator**: total MAUs in the same period.
- **Formula**: `numerator / denominator × 100`
- **Rationale**: this is the exact metric named in the original brief — the business goal this entire project exists to move.
- **Decision influence**: this is the metric everything else is a proxy or leading indicator for. If it doesn't move, the MVP mechanism didn't work regardless of how good any other number looks.

---

## Discovery Engine Evals (blueprint Part D)

### Hallucinated-quote rate
- **Definition**: % of quotes the pipeline attributes to a review ID that don't actually appear (exact/normalized substring match) in that review's raw text.
- **Numerator**: count of quotes failing the substring match.
- **Denominator**: total quotes checked.
- **Formula**: `numerator / denominator × 100`
- **Rationale**: a fabricated quote is the single most damaging failure mode for a research-insights product — it's not a matter of degree, it's a trust-destroying error.
- **Decision influence**: target is 0%. Any non-zero rate means quotes get auto-discarded before reaching the deck, not manually reviewed and kept.

### Theme support rate
- **Definition**: % of a theme's evidence reviews that an independent judge model rates as "yes, this supports the theme claim."
- **Numerator**: reviews rated "yes" (or weighted partial-credit for "partial").
- **Denominator**: total evidence reviews sampled for that theme.
- **Formula**: `numerator / denominator × 100`
- **Rationale**: clustering can group reviews that are embedding-similar but not actually about the same underlying issue; this catches that gap.
- **Decision influence**: themes below 75% support (blueprint's stated threshold) or under 30 evidence reviews do not graduate to the deck.

### Cross-model agreement (Cohen's κ)
- **Definition**: statistical agreement between two different models independently classifying the same review sample into the theme taxonomy, corrected for chance agreement.
- **Numerator/Denominator**: not a simple ratio — computed via the standard Cohen's kappa formula: `(observed agreement − expected agreement) / (1 − expected agreement)`.
- **Rationale**: if two different models can't agree on classification, the taxonomy itself may be ambiguous, not just one model being wrong.
- **Decision influence**: κ > 0.6 is reported as "acceptable consistency" — but the actual number gets reported regardless, since an honest 0.55 beats a fabricated 0.95.

### Human-AI agreement
- **Definition**: % agreement between a human's blind classification of a stratified 50-review sample and the AI pipeline's classification of the same reviews.
- **Numerator**: reviews where human and AI classification match.
- **Denominator**: 50 (the sample size).
- **Formula**: `numerator / denominator × 100`
- **Rationale**: the human is the ground-truth check the model-vs-model comparison above can't provide.
- **Decision influence**: disagreement examples become explicit "limitations" content in the deck, not hidden.

---

## AI Engine / Recommendation Metrics

### Guardrail failure rate
- **Definition**: % of AI-generated recommendations that failed at least one deterministic guardrail check (hallucinated product, category violation, hallucinated evidence, malformed output, sensitive inference, or PII leak) and fell back to deterministic logic.
- **Numerator**: recommendations with `guardrail_status != 'PASSED'`.
- **Denominator**: total recommendation requests.
- **Formula**: `numerator / denominator × 100`
- **Rationale**: directly measures how often the generative layer needs its safety net — a proxy for how much the system can be trusted un-audited.
- **Decision influence**: a persistently high rate means the prompt or retrieval quality needs work, not that the guardrails are "too strict."

### Category Diversification Index (CDI)
- **Definition**: 1 minus the Herfindahl-Hirschman Index of a user's purchases across categories — higher means more diversified.
- **Numerator/Denominator**: not a simple ratio — `CDI = 1 − Σ(category_share²)`, where `category_share` = items from that category / total items purchased.
- **Rationale**: a single number capturing purchase concentration; directly tied to the cited churn research (single-category buyers show 1.3x higher churn risk).
- **Decision influence**: this is the metric the MVP's entire mechanism is trying to move upward. Verified correct via hand-calculated self-check (`operational_metrics.py --self-check`).

### Attach Rate
- **Definition**: average number of items per completed basket.
- **Numerator**: total items across all orders.
- **Denominator**: total number of orders.
- **Formula**: `numerator / denominator`
- **Rationale**: the most direct signal that the discovery card is adding items rather than just being seen and ignored.
- **Decision influence**: a flat attach rate despite high card-impression volume means the recommendation itself isn't compelling, even if guardrails are passing.

### Feature Adoption Index (FAI) — recommendation acceptance rate
- **Definition**: % of shown discovery-card recommendations that end in "accepted" rather than "dismissed."
- **Numerator**: accepted events.
- **Denominator**: accepted + dismissed events (total shown).
- **Formula**: `numerator / denominator × 100`
- **Rationale**: validates whether the checkout-moment placement itself is well-timed, independent of what's being recommended.
- **Decision influence**: low FAI with good guardrail-pass rate suggests a UX/timing problem, not a recommendation-quality problem — different fix.

### AOV Trend
- **Definition**: linear regression slope of order value over a sequence of orders.
- **Numerator/Denominator**: not a ratio — least-squares slope of `value` regressed on order sequence.
- **Rationale**: a declining slope is a documented precursor to platform disengagement.
- **Decision influence**: negative trend triggers investigation even if CDI and FAI both look healthy — those can improve while overall spend still declines.

### Support / Confidence / Lift (market basket analysis)
- **Definitions**:
  - Support(A,B) = P(both A and B in the same basket)
  - Confidence(A→B) = P(B in basket | A in basket)
  - Lift(A→B) = Confidence(A→B) / Support(B) — >1 means real association, not chance
- **Formulas**: see `evals/basket_analysis.py`, each verified against a hand-calculated example.
- **Rationale**: standard association-rule-mining metrics; the mathematical foundation the research doc's Apriori/FP-Growth roadmap item would eventually run at scale.
- **Decision influence**: NOT decision-ready at current demo volume (6 personas) — see the explicit warning in the code. Only meaningful once real order volume exists.

---

## Explicitly not defined here: Complaint-to-Order Ratio (COR)

No complaints/returns table exists in this prototype's schema. Defining a
formula with no real data behind it would mean presenting a fabricated
number as if it were measured — the exact anti-pattern this whole project
has tried to avoid since the original blueprint's Part A. Add this once a
real complaints table exists post-launch.
