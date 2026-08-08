# Blinkit Discovery Concierge

An end-to-end prototype for surfacing never-tried product categories to
quick-commerce users at the moment they're closest to a free-delivery
threshold — grounded in a real review corpus, not synthetic data.

**Live prototype:** https://graduation-project-delta-ivory.vercel.app/
**Workflow results:** https://graduation-project-delta-ivory.vercel.app/results

## Using the prototype

Pick a persona, then add 1–2 of their usual items to the cart. A
"New category opportunity" card and a horizontal rail of related
products appear automatically once the cart is close enough to the
₹199 free-delivery threshold (currently between ₹40 and ₹80 short of
it — see `DEFICIT_MIN` / `DEFICIT_MAX` in `mvp-shell/src/App.jsx`).
The threshold bar marks this zone directly, so it's visible even
before or after you're in it. Tap **"Why this?"** on either the card
or a rail item to see the real corpus evidence and an explicit note
on how the pick was chosen.

The recommendation logic is deterministic (price-fit against the
checkout gap, filtered to categories the persona has never ordered) —
not an LLM call. That's disclosed on the card itself, not just here.

## What's real vs. mock in this build

- **Real:** the 5,500 scraped reviews (`data/raw/`), the theme-extraction
  output (`data/processed/real_themes.json` — 15 themes, 1,180 reviews
  analyzed, 0.0% hallucination rate per the deterministic Evidence
  Validator), and the guardrail suite (`mvp-shell/api/guardrails.js` — 6
  checks, 13/13 tests passing).
- **Mock:** the prototype's personas and cart products are not wired to
  Supabase (env vars were never provisioned for this deployment), so it
  runs on local fixture data. This is disclosed in-app via the "Demo
  mode" badge — restyled from a warning banner, not removed. The
  recommendation engine (`mvp-shell/api/recommend.js`) is built and
  guardrail-tested but not yet connected to the frontend, which still
  uses the deterministic placeholder logic described above.

## Repo structure

| Path | Contents |
|---|---|
| `scrapers/` | Play Store / App Store / Reddit review scrapers |
| `pipeline/` | Clean → relevance-filter → embed → cluster → ingest |
| `workflows/` | n8n hub-and-spoke theme-extraction workflow + offline validators |
| `data/raw/` | Committed scraped output (not reproducible by re-scraping) |
| `data/processed/` | Pipeline output — gitignored, regenerable from `data/raw/` |
| `supabase/` | Schema and seed SQL |
| `mvp-shell/` | Vite/React frontend + Vercel serverless API routes |
| `results-page/` | Standalone results page (source of `mvp-shell/public/results/`) |
| `evals/` | Metrics and self-check scripts |
| `docs/` | Architecture, limitations, PRD, deck corrections |

## Running it locally

```bash
cd mvp-shell
npm install
npm run dev
```

Runs against local fixture data with no setup. To connect Supabase,
copy `mvp-shell/.env.example` to `.env.local` and fill in a project URL
and anon key — `supabaseClient.js` falls back to fixtures automatically
if those are absent or still the placeholder value.

## Verifying the claims above

```bash
node mvp-shell/api/guardrails.test.js       # 13 passed, 0 failed
node workflows/validate_workflow.mjs        # static workflow structure checks
node workflows/test_code_nodes.mjs          # workflow Code node behavior checks
python pipeline/ingest_themes.py --self-check   # category-matching logic only
```

## Known limitations

- Personas/products are demo fixtures, not live Supabase data (see above).
- The frontend's recommendation is deterministic placeholder logic, not
  the RAG-grounded `recommend.js` engine — that gap is intentional and
  disclosed, not hidden.
- Survey and interview sample sizes (N=15–19, 5 interviews) are real but
  not statistically representative; treat findings as directional.
- Full guardrail/architecture detail lives in `docs/`, not duplicated here.
