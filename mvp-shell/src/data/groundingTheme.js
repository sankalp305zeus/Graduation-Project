// Real output from the n8n theme-extraction workflow, copied verbatim from
// data/processed/real_themes.json (run of 2026-07-31, 15 clusters, llama3.1
// via local Ollama). Every number below is arithmetic over real cluster
// membership, not an LLM's estimate, and passed the Evidence Validator with
// llm_hallucinated_ids empty.
//
// WHY THIS THEME AND NOT A PER-CATEGORY ONE: none of the 15 extracted themes
// map to a product category. Running pipeline/ingest_themes.py's deterministic
// categorize() over all 15 assigns a category to only 4, all of them
// "Groceries & Fresh Produce" at hit_count=1 (incidental keyword brushes like
// "milk"). The corpus is about delivery, charges and service quality — it
// simply contains no evidence about category discovery. So the card cites the
// theme that genuinely grounds the checkout-gap mechanic, and labels the
// category-fit half as prototype logic. Do not swap this for a fabricated
// per-category citation.
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
