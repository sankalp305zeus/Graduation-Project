# PRD: Blinkit Discovery Concierge — Data Pipeline & AI Engine Activation

**For: Claude Code, as an implementation-planning and build brief.**
**Human collaborator: will answer questions when asked — this doc explicitly
flags every point where you should ask rather than assume.**

---

## 0a. Provider decision — read `docs/GROQ_MIGRATION_AND_FAILPROOFING.md` FIRST

The human collaborator has chosen **Groq (free tier)** as the LLM provider
for cost reasons. This affects Task 0's file inventory (recommend.js and
the n8n workflow currently reference Anthropic) and adds real rate-limit
constraints that change how the bulk theme-extraction job (Phase 1) must
be paced. Read that doc before starting Phase 1 — it has specific token/
rate-limit math for this exact workflow, not generic advice.

## 0. Context (read once, don't re-derive)

This is a 20-day solo graduation project (deadline Aug 4, 3:59 PM IST — check
actual remaining days against today's date before planning your schedule).
Product: a research + AI system analyzing why Blinkit users don't explore
new product categories, validated with real user interviews, culminating in
a deployed AI-native MVP. Full narrative context is in
`docs/blinkit-growth-final-blueprint.md` — read it if you need the "why,"
but this PRD is the "what to build now."

**Direct evaluator feedback from a prior cohort (see
`docs/prior-cohort-feedback.md` if present) flagged this exact risk: too
much building before real review-mining data exists.** That is the reason
this PRD's Phase 1 is entirely about getting REAL data flowing, not adding
new features. Do not expand scope beyond this PRD without asking first.

---

## 1. TASK 0 — Fix the repo structure before running anything

Code was written across several sessions at inconsistent folder depths.
Several scripts use relative paths like `../data/raw` that assume a
specific sibling-folder layout. **Reconcile into this structure first**,
moving files as needed (do not rewrite the scripts' internal logic, just
their location, unless a path constant needs updating to match):

```
blinkit-growth-intelligence/          <- repo root
├── scrapers/                         <- playstore.py, appstore.py, reddit.py,
│                                         requirements.txt, .env.example, README.md
├── pipeline/                         <- clean.py, embed.py, cluster.py
│                                         (currently nested under ai-engine/pipeline/ — move up)
├── data/
│   ├── raw/
│   └── processed/
├── workflows/                        <- 02-theme-extraction.json, README.md
├── supabase/                         <- ALL .sql files, consolidated:
│   ├── 01_schema.sql                    (personas/products/event_log — from mvp-shell/supabase/schema.sql)
│   ├── 02_seed.sql                      (from mvp-shell/supabase/seed.sql)
│   ├── 03_themes_schema.sql             (reviews/themes — from ai-engine/supabase/themes_schema.sql)
│   └── 04_seed_themes.sql               (from ai-engine/supabase/seed_themes.sql)
├── evals/                            <- basket_analysis.py, operational_metrics.py
│                                         (currently under ai-engine/evals/ — move up)
├── docs/                             <- blinkit-growth-final-blueprint.md, ai-architecture.md,
│                                         ai-limitations-and-mitigations.md, metrics-dictionary.md,
│                                         interview-screener-guide.md, blinkit-survey-questionnaire-v2.md
└── mvp-shell/                        <- the actual Vercel-deployed project. Keep as-is EXCEPT:
    ├── api/                              <- move ai-engine/api/{recommend.js,guardrails.js,
    │                                         guardrails.test.js} HERE. Vercel's convention is
    │                                         that /api at the deployed project's root becomes
    │                                         serverless functions — verify this is still current
    │                                         Vercel behavior before assuming it (my info may be
    │                                         stale); check Vercel's docs if anything about
    │                                         function deployment doesn't work as expected.
    ├── src/
    ├── supabase/                         <- can be removed once root-level /supabase/ is the
    │                                         single source of truth; don't leave duplicates
    └── ... (rest unchanged)
```

**After moving files, update path references:**
- `scrapers/README.md` and `pipeline/*.py` both default to `../data/raw` /
  `../data/processed` — once `scrapers/` and `pipeline/` are siblings at
  repo root with `data/` also at repo root, these resolve correctly with
  no code changes needed. Verify by running each script's `--help` and
  checking the default paths make sense from the new location.
- `pipeline/cluster.py` outputs a payload meant to be POSTed to the n8n
  webhook — confirm `workflows/README.md`'s test payload still matches
  `cluster.py`'s actual output shape after the move.

**Acceptance criteria for Task 0**: every script in `scrapers/`, `pipeline/`,
and `evals/` runs successfully with its default (no-argument) path
configuration from its new location, without needing `--input`/`--output`
overrides for a basic test.

---

## 2. What already exists — use it, don't regenerate it

| Area | Files | Status |
|---|---|---|
| Scrapers | `scrapers/{playstore,appstore,reddit}.py` | Built, syntax-checked. **Never run against live data.** |
| Cleaning | `pipeline/clean.py` | Built AND tested (dedupe/PII/language filter verified on synthetic data). |
| Embedding | `pipeline/embed.py` | Built, syntax-checked only. **Never run live** — needs an embeddings API key (see open question in §5). |
| Clustering | `pipeline/cluster.py` | Built AND tested — correctly recovered 3/3 synthetic clusters. Output format matches the n8n webhook's expected input. |
| Theme extraction | `workflows/02-theme-extraction.json` | Built, JSON-validated, 18 nodes (hub + 3 spokes + evidence validator). **Never run in a live n8n instance.** |
| Supabase schema | `supabase/*.sql` | Built. `themes`/`reviews` currently seeded with **placeholder-only** data (`is_placeholder = true`). |
| Recommendation API | `mvp-shell/api/recommend.js` | Built, syntax-checked. **Never called live** — needs Supabase + Anthropic credentials. |
| Guardrails | `mvp-shell/api/guardrails.js` | Built AND tested — 8/8 unit tests passing (`guardrails.test.js`). |
| MVP frontend | `mvp-shell/` (full Vite+React app) | Built, screenshot-verified working with mock data. **Still calls the OLD local placeholder recommendation logic, NOT `/api/recommend`.** |
| Evals | `evals/basket_analysis.py`, `evals/operational_metrics.py` | Built AND tested against hand-calculated examples. **Missing**: `quote_fidelity.py`, `theme_support.py`, `cross_model_agreement.py`, `coverage_diversity.py` — described in `docs/blinkit-growth-final-blueprint.md` Part D but never actually implemented as code. Build these in Phase 3. |

Do not rewrite anything in the "Built AND tested" rows without a specific
reason — they're verified correct.

---

## 3. Phase 1 (URGENT — do this first): get real data flowing

**Goal**: replace every placeholder in `supabase/themes` and
`supabase/reviews` with real, evidence-backed output from actual scraped
Blinkit reviews.

- [ ] **1.1** Run `scrapers/playstore.py` against live Play Store (no auth
      needed). Target: 3,000–5,000 reviews. Commit raw output to
      `data/raw/` immediately — this is the project's disaster insurance.
- [ ] **1.2** Run `scrapers/appstore.py` (no auth, expect ~500 reviews max —
      this is an Apple RSS feed limitation, not a bug).
- [ ] **1.3** Attempt `scrapers/reddit.py` — **ask the human collaborator
      for Reddit API credentials before running this** (needs a free
      registered app at reddit.com/prefs/apps — see `scrapers/.env.example`).
      If credentials aren't available or the scraper underperforms, per
      direct evaluator feedback this is an accepted fallback: Play Store
      alone is sufficient if the workflow and insights are demonstrated well.
      **Do not block Phase 1 on Reddit succeeding.**
- [ ] **1.4** Run `pipeline/clean.py` on the combined raw output.
- [ ] **1.5** Run `pipeline/embed.py` — **STOP and ask the human
      collaborator which embedding provider to use before running this**
      (see open question in §5 — this has a real cost/account tradeoff,
      don't assume OpenAI is acceptable just because the code currently
      targets it).
- [ ] **1.6** Run `pipeline/cluster.py` on the embedded output. Verify
      cluster count and sizes look reasonable (blueprint targets roughly
      50-150 clusters from a corpus this size — if you get 2 clusters or
      2,000, something's wrong upstream, don't proceed silently).
- [ ] **1.7** Import `workflows/02-theme-extraction.json` into a real n8n
      instance (self-hosted or n8n Cloud — **ask the human collaborator
      which they've set up**, per the blueprint's note that the Cloud trial
      expires in ~14 days and may not survive to judging week). Attach a
      real Anthropic API key to all 4 `lmChatAnthropic` nodes.
- [ ] **1.8** Test the workflow with the 2-cluster payload in
      `workflows/README.md` FIRST. Confirm the Split In Batches loop
      actually terminates and the Evidence Validator's `evidence_ids`
      output equals full cluster membership, not just the LLM's sample
      (this was a deliberate design decision — see the workflow's own
      inline comments if the behavior looks wrong).
- [ ] **1.9** Once the test payload works, POST the real `clusters.json`
      from step 1.6 to the webhook. This may need batching/pacing given
      real corpus size — the workflow already has a 2-second rate-limit
      Wait node between LLM calls.
- [ ] **1.10** Write the real theme output into `supabase.themes` and
      `supabase.reviews` with `is_placeholder = false`. **No script exists
      for this step yet — build one** (`pipeline/ingest_themes.py` or
      similar): takes the n8n webhook's JSON response, upserts into
      Supabase. This is new code, not a move/fix.

**Acceptance criteria for Phase 1**: `supabase.themes` contains real rows
with `is_placeholder = false`, each with `evidence_count > 0`, and running
`evals/quote_fidelity.py` (built in Phase 3) against them shows a
verifiable hallucination rate — not an assumed 0%.

---

## 4. Phase 2: wire the real recommendation engine

**Only start this after Phase 1's acceptance criteria are met.**

- [ ] **2.1** Set up a Supabase project if not already done; run all 4 SQL
      files in `supabase/` in order.
- [ ] **2.2** Set up a Vercel project for `mvp-shell/`. Add environment
      variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (server-side
      only, never the anon key here), `ANTHROPIC_API_KEY`.
- [ ] **2.3** **Ask the human collaborator before doing this step**: update
      `mvp-shell/src/App.jsx` to call `POST /api/recommend` instead of the
      local `pickRecommendation()` function. This is a meaningful behavior
      change to the working demo — confirm they want it wired in now versus
      testing `recommend.js` standalone first (this was flagged as an open
      question previously and may not be answered yet).
- [ ] **2.4** Test the full live flow: pick a persona in the UI, add items
      until the discovery card triggers, confirm it calls the real API and
      returns a guardrail-passed, evidence-grounded recommendation — not
      the deterministic fallback (check `guardrail_status` in the response;
      if it's ever anything other than `PASSED` during testing, that's
      worth investigating, not ignoring).
- [ ] **2.5** Resolve the placeholder-theme handling open question (§5) —
      implementation depends on the human's answer.
- [ ] **2.6** Add an uptime pinger (e.g. UptimeRobot, free tier) hitting the
      deployed Vercel URL every ~10 min during Aug 4-15, so cold-start
      latency doesn't slow down a judge's click.

---

## 5. Open questions — ASK, do not assume defaults

These are real decisions with tradeoffs. Stop and ask the human
collaborator before proceeding past the point where each one matters:

1. **Embeddings provider** (blocks step 1.5): LLM calls now use Groq, but
   Groq's embeddings support could not be confirmed as reliably available
   (see `docs/GROQ_MIGRATION_AND_FAILPROOFING.md` Task D). Recommended
   default: rewrite `pipeline/embed.py` to use a local `sentence-transformers`
   model (zero cost, zero rate limits) — but this changes the vector
   dimension in the Supabase schema from 1536 to 384, so **confirm with the
   human collaborator before implementing**, don't silently swap it.
2. **n8n hosting** (blocks step 1.7): self-hosted (e.g. Railway/Render,
   ~$5/mo) vs. n8n Cloud paid tier (~$20-24/mo) vs. free trial (risks
   expiring before judging week, Aug 13-15). Ask which they've already set
   up or want to set up.
3. **Frontend wiring timing** (blocks step 2.3): wire `/api/recommend` into
   the live UI immediately once it's tested, or keep them decoupled longer
   for independent testing first?
4. **Placeholder theme handling** (affects step 2.5): once real themes
   exist for some categories but not others, should `recommend.js` prefer
   real themes and fall back to placeholder ones only for uncovered
   categories, or should placeholder rows just be deleted once ANY real
   coverage exists (accepting some categories temporarily have zero
   RAG-grounded recommendations)?
5. **Reddit credentials** (affects step 1.3): does the human collaborator
   already have a registered Reddit app, or does this need to happen before
   that step can run?

---

## 6. Phase 3: build the missing eval scripts

Referenced in `docs/blinkit-growth-final-blueprint.md` Part D but never
implemented. Each should follow the existing pattern in
`evals/basket_analysis.py` and `evals/operational_metrics.py`: a
`--self-check` mode with a hand-verifiable example, real logic that's
independently testable without needing a live LLM call where possible.

- [ ] **3.1** `evals/quote_fidelity.py` — for every quote the pipeline
      attributes to a review ID, exact/normalized substring match against
      the raw corpus in `data/processed/`. Output: hallucination rate,
      list of failing quotes.
- [ ] **3.2** `evals/theme_support.py` — LLM-as-judge: for each theme,
      retrieve its `evidence_ids`, have a DIFFERENT model than whatever
      generated the theme score each review (yes/partial/no support).
      Output: per-theme support %.
- [ ] **3.3** `evals/cross_model_agreement.py` — classify a random 200-review
      sample into the theme taxonomy with two different models
      independently, compute Cohen's κ.
- [ ] **3.4** `evals/coverage_diversity.py` — % of relevant corpus assigned
      ≥1 theme, broken down by source (guards against over-indexing on one
      subreddit or review source).
- [ ] **3.5** Human spot-check tooling — not a script exactly, but generate
      a stratified random 50-review CSV export with a blank
      "human_classification" column, ready for the human collaborator to
      fill in by hand and compare against the AI's classification.

**Do not build a Complaint-to-Order Ratio calculator** — no complaints
table exists in this schema, and no real complaint data will exist for this
prototype. Computing it would mean fabricating a number, which this
project's own blueprint explicitly treats as worse than not having the
metric (see `docs/ai-limitations-and-mitigations.md`).

---

## 7. Non-negotiable constraints (carried through every phase)

- **Never trust an LLM to grade itself.** Every eval and every guardrail
  check must be deterministic code, not another model call grading the
  first one — the one exception is `theme_support.py`'s LLM-as-judge
  pattern, which is deliberately a DIFFERENT model than whatever generated
  the theme, per blueprint D.2.
- **Every number that reaches the deck must be regenerable by a script in
  this repo.** No number should exist that a person typed in by hand.
- **Guardrail failures degrade gracefully.** A failed check falls back to
  the deterministic placeholder recommendation — never an error, never a
  silent pass-through of unvalidated output.
- **Small-sample outputs are not findings.** Anything computed against the
  6 seed personas or a small demo corpus is a correctness demonstration,
  not a result — flag this explicitly in any output, the way
  `basket_analysis.py` already does.
- **Don't expand scope beyond this PRD.** If something looks like it needs
  a new feature or a new architectural decision not covered here, stop and
  ask rather than deciding unilaterally — this exact failure mode
  (building ahead of validated need) is what the evaluator feedback flagged
  as the #1 recurring problem in the prior cohort.

---

## 8. Explicitly out of scope for Claude Code in this PRD

These remain the human's parallel-track responsibility, not a coding task:
conducting the 5-6 user interviews, distributing/analyzing the survey,
writing the 10-slide deck, recruiting interviewees, GitHub repo identity
setup (name-leak protection), and the final submission checklist. Don't
pick these up even if they seem related — flag if you think one is
blocking your work, don't just do it.
