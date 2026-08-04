// Real output from the n8n theme-extraction workflow, copied verbatim from
// data/processed/real_themes.json (run of 2026-07-31, 15 clusters, llama3.1
// via local Ollama). Every number below is arithmetic over real cluster
// membership, not an LLM's estimate, and passed the Evidence Validator with
// llm_hallucinated_ids empty.
//
// WHY A CORPUS-LEVEL THEME AND NOT A PER-CATEGORY ONE: no real per-category
// theme exists. Running pipeline/ingest_themes.py's deterministic categorize()
// over all 15 extracted themes assigns a category to only 4, all of them
// "Groceries & Fresh Produce" at hit_count=1 (incidental keyword brushes like
// "milk"). The corpus is about delivery, charges and service quality — it
// contains no evidence about category discovery.
//
// So DiscoveryCard's why-panel shows two clearly separated halves: the
// per-category theme from mockThemes.js, which is seeded and carries an
// explicit "Placeholder theme" flag, and this one, which is measured. Keep
// that separation — the panel's honesty depends on a reader being able to
// tell at a glance which half was observed. Do not promote a placeholder
// theme into this file, and do not drop the flag from the other half.
export const GROUNDING_THEME = {
  theme_name: 'Hidden or unexpected charges',
  core_job: 'complete a purchase without unexpected additional costs',
  trigger: 'attempting to complete checkout or make an order',
  user_segment: 'price-sensitive repeat buyer',
  evidence_count: 67,
  prevalence_pct: 5.68,
  prevalence_basis: 'embedded_reviews_analyzed',
  corpus_total: 1180,
}

export const CORPUS = {
  themes_extracted: 15,
  hallucination_rate_pct: '0.0',
  reviews_analyzed: 1180,
  reviews_scraped: 5500,
}
