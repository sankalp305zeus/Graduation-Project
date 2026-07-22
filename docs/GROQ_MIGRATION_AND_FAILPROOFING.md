# Groq Migration & Fail-Proofing Addendum

Read alongside `CLAUDE_CODE_PRD.md` — this doesn't replace it, it adds the
specifics needed because the project is switching from Anthropic-for-everything
to Groq (free tier) for LLM calls.

## Why this needs care, not just a find-and-replace

Groq's free tier is rate-limited **at the organization level**: roughly
30 requests/minute and somewhere in the 6,000–12,000 tokens/minute range
(varies by model — verify exact current numbers at
console.groq.com/docs/rate-limits, they change and different sources
disagree on the exact figure). Multiple API keys do NOT raise this limit.

**The math that matters for this project**: `02-theme-extraction.json`
makes 4 LLM calls per cluster (Theme + JTBD + Opportunity spokes running in
parallel, then the Orchestrator Synthesizer). At an estimated 700-1,100
tokens per call (system prompt + review sample + output), that's roughly
2,800-4,400 tokens per cluster. Against a 6,000-12,000 TPM ceiling, this
workflow can process at most a handful of clusters per minute before
hitting a 429 — and with 30 RPM ÷ 4 calls/cluster, you're capped around
7-8 clusters/minute on request count alone even before the token ceiling
bites. **With an expected 50-150 clusters, plan for the full theme-extraction
run to take meaningfully longer than the current 2-second Wait node assumes,
and to hit 429s that need real retry logic, not just the existing "retry
once" pattern.**

---

## Task A: Swap LLM provider in the n8n workflow

- [ ] Change all 4 `@n8n/n8n-nodes-langchain.lmChatAnthropic` nodes in
      `02-theme-extraction.json` to `@n8n/n8n-nodes-langchain.lmChatGroq`
      (confirmed to exist as a native n8n node — no community package needed).
- [ ] Pick a specific Groq-hosted model and PIN it explicitly (e.g.
      `llama-3.3-70b-versatile`) rather than trusting a default — Groq
      deprecates models over time, and an unpinned/default selection can
      silently change underneath you mid-project.
- [ ] Replace the fixed 2-second `Wait` node with rate-limit-AWARE pacing:
      track cumulative tokens sent per rolling 60-second window, and pause
      long enough to stay under budget — not a flat delay. A simple
      approach: after every cluster's 4 calls, wait long enough that you
      never exceed ~6,000 TPM even under the more conservative published
      limit (e.g. if 4 calls average 4,000 tokens per cluster, you can
      safely do roughly 1 cluster every 40-45 seconds against a 6K TPM
      ceiling — this is a starting estimate, not a guarantee; watch actual
      token usage in the first real run and adjust).
- [ ] Add real 429 handling: on a 429 response, back off with increasing
      wait (e.g. 10s, then 30s, then 60s) rather than the current
      "retry once after fixed delay" pattern — a fixed short retry will
      likely just hit the same limit again immediately.
- [ ] **Known-uncertain area, ask if it matters**: I could not confirm
      whether Groq's Batch API (async, processes within 24h-7d, cited at
      50% off) is available on the free tier or requires the paid Developer
      tier. If it IS free-tier-available, it may be a better fit than
      live synchronous calls for the one-time bulk corpus processing —
      worth a 5-minute check at console.groq.com before building the
      live-call pacing logic above, since batch mode would sidestep the
      RPM/TPM problem entirely for this one-time job.

## Task B: Swap LLM provider in recommend.js

- [ ] Replace `@anthropic-ai/sdk` with `groq-sdk` (Groq's API is
      OpenAI-compatible at `https://api.groq.com/openai/v1`, so the
      OpenAI SDK pointed at that base URL also works if `groq-sdk`
      has any gaps).
- [ ] Pin a specific model, same reasoning as Task A.
- [ ] Add basic retry-with-backoff on 429 for the live user-facing call too
      — lower urgency than the bulk job since this is one call per
      recommendation, not thousands, but a demo-time judge click
      shouldn't fail silently.
- [ ] **Real risk worth flagging to the human**: since rate limits are
      ORG-level, running the big n8n bulk processing job (Task A) and
      testing/demoing the live recommendation endpoint (this task) on the
      SAME Groq account competes for the same quota. If both need to run
      close together in time, consider a second free Groq account
      (different email = different org = separate quota) for the live
      demo path, OR make sure the bulk corpus job is fully finished well
      before judging week rather than run concurrently with live testing.

## Task C: Cross-model eval — Groq actually makes this easier

`docs/blinkit-growth-final-blueprint.md` Part D.2/D.3 need a genuinely
different model to judge/cross-check the primary model's output. Groq
hosts several distinct models for free (Llama 3.3 70B, Llama 4 Maverick,
Mixtral, Gemma, GPT-OSS-120B, Qwen3 — verify current list at
console.groq.com/docs/models since availability shifts). Use two different
Groq-hosted models for `cross_model_agreement.py`, OR — better separation
of failure modes — use Claude (already have API access) as the judge model
against Groq as the generator, since two models from different providers
are less likely to share correlated blind spots than two models from the
same provider.

## Task D: Embeddings — do NOT default to Groq for this

I could not confirm Groq has a stable, documented embeddings offering (SDK
methods exist in their client libraries, but no confirmed model name or
availability). Given embedding generation is a one-time bulk batch job
(not a live low-latency need — Groq's whole value proposition is fast
*inference*, which doesn't matter for a background embedding job), the
lower-risk choice is a **local, free, zero-rate-limit model**:

- [ ] Rewrite `pipeline/embed.py` to use a local `sentence-transformers`
      model (e.g. `all-MiniLM-L6-v2`) instead of calling any external API.
      Zero cost, zero rate limits, zero extra account/signup, runs
      entirely offline.
- [ ] **This changes the embedding dimension** from 1536 (OpenAI's
      text-embedding-3-small, what the current schema assumes) to 384
      (MiniLM's actual output dimension). Update
      `supabase/03_themes_schema.sql`'s `vector(1536)` column to
      `vector(384)` to match — this MUST change together with the model,
      or every embedding insert will fail on a dimension mismatch.
- [ ] Ask the human collaborator to confirm this tradeoff before building
      it: a local model is lower-risk operationally but lower-quality
      semantically than a dedicated embeddings API — for a 20-day
      prototype with ~5,000 reviews, this is very likely the right
      tradeoff, but it's their call, not an assumption to bake in silently.

---

## General fail-proofing checklist (applies regardless of provider choice)

- [ ] Every external API call (Groq, Supabase, Reddit) needs a retry with
      backoff, not a bare try/once pattern — network calls fail
      transiently even outside of rate limits.
- [ ] `recommend.js`'s existing guardrail-failure fallback to deterministic
      logic already covers "the AI call succeeded but produced something
      unsafe" — confirm it ALSO covers "the AI call failed entirely"
      (timeout, 429 exhausted retries, network error) with the same
      graceful fallback, not an unhandled exception reaching the user.
- [ ] Pin exact model version strings everywhere (n8n workflow, recommend.js)
      — never rely on a provider's "default model" selection, since that
      can change without your code changing.
- [ ] Log guardrail failures and API failures somewhere inspectable (even
      just structured console output Vercel captures) so a judge-time
      failure is debuggable after the fact, not just a mystery blank card.
