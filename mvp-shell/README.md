# Discovery Concierge — MVP Shell

Plain Vite + React + Supabase. No proprietary platform, no generated-code lock-in —
every file here is yours to edit directly.

**In-app branding note:** the UI says "QuickCart," not "Blinkit." Deliberate choice —
using the real trademarked name/logo in a live public deployment (this will end up on
Vercel with a public link in your deck) risks IP issues for a portfolio piece. Describe
it as "modeled on Blinkit's quick-commerce flow" in your README/deck instead; the visual
language (yellow/green, dense cards) already signals it clearly without using the name.

## What's built

- Persona switcher (6 personas, seeded across all 11 categories — see `supabase/seed.sql`)
- Home grid showing each persona's usual categories
- Cart with a live free-delivery progress bar (threshold: ₹199)
- **The core mechanic:** when the cart is ₹40–80 short of free delivery, a Discovery Card
  appears recommending a product from a category that persona has never tried, price-matched
  to the deficit. Accept/Dismiss both log to `event_log`.
- Runs immediately with local mock data (`src/data/`) — no Supabase setup required to see it working.

## What's explicitly NOT built (by design, per your instructions)

The recommendation logic in `src/App.jsx` (`pickRecommendation`) is deterministic —
closest-price match from the persona's `never_tried` list. No AI call, no RAG, no
serverless proxy. The "Why am I seeing this?" text in `DiscoveryCard.jsx` is hardcoded
placeholder copy, clearly commented where it needs to become a real citation.

## Setup

```bash
npm install
npm run dev
```

Opens with mock data immediately — no Supabase needed to see the UI working.

### Connecting real Supabase (when ready)

1. Create a Supabase project
2. SQL Editor → run `supabase/schema.sql`, then `supabase/seed.sql`
3. `cp .env.example .env.local`, fill in your Project URL + anon key (Project Settings → API)
4. Restart `npm run dev` — the app auto-detects the env vars and switches from mock data
   to live Supabase reads/writes. If the Supabase call ever fails, it silently falls back
   to mock data rather than crashing.

## Next steps (in order)

1. **Swap in real personas.** Once interviews are done, replace the 6 rows in
   `supabase/seed.sql` (and `src/data/mockPersonas.js` to match) with personas
   authored from real interview subjects. Keep the "simulated data, derived from
   primary research" label somewhere visible in the deck/demo.
2. **Wire the real recommendation engine.** Replace `pickRecommendation()` in
   `App.jsx` with a call to a Vercel serverless function that proxies the Claude
   API (never call the API directly from the browser — the key would be exposed).
   That function should do RAG retrieval against your discovery engine's themes
   table and return a recommendation + real evidence-based reasoning.
3. **Replace the placeholder "why" text** in `DiscoveryCard.jsx` with the real
   citation returned by that API call.
4. **Deploy to Vercel**, connect your production Supabase project, add an
   uptime pinger so the judge's click isn't slow from cold-start.

## File map

```
src/
  App.jsx                 — main logic: cart state, discovery trigger, recommendation picking
  supabaseClient.js        — Supabase reads/writes with automatic mock-data fallback
  components/
    PersonaSwitcher.jsx
    CategoryGrid.jsx
    CartPanel.jsx
    DiscoveryCard.jsx      — has the placeholder "why" text, clearly marked for replacement
  data/
    mockPersonas.js         — mirrors supabase/seed.sql, keep both in sync manually
    mockProducts.js
supabase/
  schema.sql               — run first
  seed.sql                 — run second, re-runnable (truncates before inserting)
```
