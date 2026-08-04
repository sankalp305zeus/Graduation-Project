# Loom shot list — "Review Analysis Workflow" submission link

The brief asks for a link that *demonstrates* the review analysis workflow. n8n
runs locally against local Ollama, so a hosted canvas link would be public but
not executable by the evaluator. A recording of a real execution shows more:
the canvas, a live run, and the deterministic Evidence Validator's actual output.

**Target length: 3–4 minutes.** Longer and the evaluator skips.

## Before you hit record

```bash
ollama serve
```

```bash
ollama pull llama3.1:latest
```

```bash
npx n8n
```

Then, in n8n: import `workflows/02-theme-extraction.json`, attach an `ollamaApi`
credential (Base URL `http://localhost:11434`) to **all four** `lmChatOllama`
nodes, and open the workflow canvas.

Sanity-check offline first — both should exit 0:

```bash
node workflows/validate_workflow.mjs
```

```bash
node workflows/test_code_nodes.mjs
```

Close every unrelated tab and window. Nothing on screen but n8n and a terminal.

## The shots, in order

**1. Canvas overview — 40s.** Full workflow zoomed to fit. Say out loud what the
topology is: webhook → validate/parse → loop over clusters → fan out to three
spoke agents (Theme, JTBD/Segment, Opportunity) → merge → synthesize → Evidence
Validator → back to the loop. Name the pattern: hub-and-spoke, one orchestrator,
three specialists.

**2. Point at the Evidence Validator node — 30s. This is the money shot.** Say
plainly: this node is deterministic JavaScript, not another LLM call. It
substring-checks every review ID the model cited against real cluster membership
and *flags* hallucinated IDs rather than silently dropping them. State the rule
it exists to enforce: never trust an LLM to grade itself.

**3. Trigger a live run — 60s.** Click **Execute Workflow**, then in the terminal:

```bash
python send_to_n8n.py test-payload.json
```

Let the canvas animate. Don't cut away — the evaluator wants to see it actually
run. If llama3.1 is slow on the first call (cold model load), say so rather than
editing it out; the retry config exists precisely for that.

**4. Open Evidence Validator's Output tab — 45s.** Show the real JSON for a
cluster. Read out the three fields that matter and why:
- `evidence_count` — full cluster membership, not what the LLM sampled
- `prevalence_pct` + `prevalence_basis` — the percentage never travels without
  its denominator, because a severity-5 theme at 0.4% is a different product
  decision from the same score at 15%
- `llm_hallucinated_ids` — empty here, and it would be *populated*, not hidden,
  if the model had invented an ID

**5. Real corpus result — 30s.** Cut to `data/processed/real_themes.json`. State
the actual numbers: **15 themes from 1,180 analyzed reviews, 0.0% hallucination
rate**, top theme `Hidden or unexpected charges` at 67 reviews / 5.68%
prevalence. Say the corpus is 5,500 real scraped Play Store + App Store reviews
before relevance filtering.

## Do not say

- Don't call the sample sizes representative — the survey is N=15–19 and there
  were 5 interviews. Real, but not statistically representative.
- Don't imply the Vercel prototype is wired to the RAG engine. It isn't, and
  that gap is disclosed deliberately.
- Don't quote a guardrail test count from memory. It is **13** as of now
  (`node mvp-shell/api/guardrails.test.js`).

## After recording

Set the Loom to "anyone with the link can view" — verify in an incognito window
before submitting. A permission-gated link reads as no link at all.
