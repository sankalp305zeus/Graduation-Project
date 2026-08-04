# Deck corrections — verified against the repo, 2026-08-04

Source deck: `Product Case Study Redesign.pdf` (10 slides, fully rasterized —
one image per page, no editable text layer, no source file found). These are
paste-ready corrections; the edits must be made in whatever produced the PDF.

---

## Slide 9 — "Every AI output is checked by deterministic code"

Current subhead:

> Never let the model grade itself. We run 5 guardrail checks with 8/8 passing tests.

**Two numbers are wrong, not one.**

Replace with:

> Never let the model grade itself. We run 6 deterministic guardrail checks,
> with 13 passing tests and 0 failures.

| Claim | Deck says | Actual | How verified |
|---|---|---|---|
| Passing tests | 8/8 | **13 passed, 0 failed** | `node mvp-shell/api/guardrails.test.js` |
| Guardrail checks | 5 | **6** | function count in `mvp-shell/api/guardrails.js` |

The 6 checks, in the order `runGuardrails()` executes them:

1. `checkOutputSchema` — required fields present and correctly typed
2. `checkProductExists` — SKU exists in the real catalog
3. `checkCategoryEligible` — category is in the persona's `never_tried`
4. `checkEvidenceGrounded` — every cited evidence ID resolves; zero citations fails
5. `checkNoSensitiveInference` — pattern-based health/condition inference flag
6. `checkNoPII` — pattern-based phone/email/card detection

The four cards on the slide cover checks 2, 3, 4 and the fallback behaviour.
Checks 1, 5 and 6 are not represented. If the card grid stays at four, the
subhead's "6" is still correct and the cards read as examples — but "Safe
Fallback" is a *consequence*, not a check, so it is not one of the 6.

---

## Slide 7 — intervention comparison table

Currently `Intervention | Reach | Conf. | Verdict`, scored High/Med/Low.
Missing Impact and Effort.

### Scoring conventions (state these on the slide or in the notes)

- All four factors scored **1–5**.
- **Effort: 1 = cheapest.** RICE normally divides by effort in person-months;
  a 1–5 "score" is ambiguous unless the direction is stated.
- **RICE = (Reach x Impact x Confidence) / Effort.**

### The completed table

| Intervention | Reach | Impact | Conf. | Effort | RICE | Verdict |
|---|---|---|---|---|---|---|
| Home Banner | 5 | 2 | 2 | 2 | **10** | Skip |
| Pre-Occasion Push | 3 | 2 | 3 | 4 | **4.5** | Skip |
| Checkout Moment | 4 | 4 | 4 | 1 | **64** | ✓ Winner |

The arithmetic corroborates the verdict the deck already reached — Checkout
Moment wins by ~6x, and it wins on the two factors that are hardest to argue
with (impact and effort), not on a close aggregate.

### One-line justification per cell, with evidence basis

**Reach**
- Home Banner — **5**, *structural*: every session loads the home screen.
- Pre-Occasion Push — **3**, *structural*: gated by notification opt-in, which
  no part of this prototype implements or measures.
- Checkout Moment — **4**, *repo-grounded, and lower than the deck claims*:
  `App.jsx` gates the card to a deficit of `DEFICIT_MIN=40`–`DEFICIT_MAX=80`
  against a `FREE_DELIVERY_THRESHOLD=199`. That is a ₹40-wide window, so the
  card cannot fire on every checkout. The deck's current "High" overstates it.

**Impact**
- Home Banner — **2**, *research-inferred*: slide 6's own root cause is
  category-blindness — users do not consider other categories. A banner asks
  for active attention at a low-intent moment, which is the failure mode being
  described.
- Pre-Occasion Push — **2**, *judgement*: out-of-app, carries no cart context,
  and the occasion must be predicted rather than observed.
- Checkout Moment — **4**, *measured + interview*: the strongest real theme in
  the corpus, "Hidden or unexpected charges" (67 reviews, 5.68% of 1,180
  analyzed, `data/processed/real_themes.json`), has the trigger "attempting to
  complete checkout or make an order" — this exact moment. Slide 7's own quote
  ("The only recommendations I actually see are inside the cart" — Riddhi)
  points the same way. Not a 5: neither source measures *lift*.

**Confidence** (existing column, converted from High/Med/Low)
- Home Banner — **2** (was Low). Pre-Occasion Push — **3** (was Med).
- Checkout Moment — **4** (was High). Deliberately not 5: the supporting
  research is a survey of N=15–19 and 5 interviews — real, but not
  statistically representative.

**Effort** (1 = cheapest)
- Home Banner — **2**, *judgement*: simplest surface, no cart-state dependency.
- Pre-Occasion Push — **4**, *judgement*: needs occasion prediction, push
  infrastructure, opt-in handling and send-time logic. None of it exists here.
- Checkout Moment — **1**, ***measured, not estimated***: it is already built
  and deployed. `DiscoveryCard.jsx`, `guardrails.js` (6 checks, 13/13 tests),
  live at https://graduation-project-delta-ivory.vercel.app/. This is the only
  cell in the table backed by a shipped artifact rather than an estimate.

### What is NOT evidence-backed — say this if asked

Of the 12 scored cells, exactly **one** (Checkout Moment / Effort) is measured,
and **two** (Checkout Moment / Impact and Confidence) rest on real research.
The remaining nine are structural or PM judgement. There is no A/B test, no
acceptance-rate data, and nothing in the repo about banners or push
notifications. If a reviewer asks "where did a 2 come from?", the answer is
prioritisation judgement, not measurement — and the table should be introduced
that way rather than as a computed result.

An honest framing for the slide footer:

> Scored 1–5. Effort inverted (1 = cheapest). Checkout Moment's effort score is
> measured — it is built and deployed. Remaining scores are directional
> prioritisation judgement; no A/B data exists yet.
