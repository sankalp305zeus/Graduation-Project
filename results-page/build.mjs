/**
 * Builds the extraction results page from REAL workflow output.
 *
 * Inputs (both real, neither mocked):
 *   ../data/processed/real_themes.json      - the aggregated n8n response
 *   ../data/processed/cleaned_reviews.jsonl - review text, joined by id
 *
 * real_themes.json carries evidence IDs but NO review text, so the snippets
 * have to be joined in. Snippets come from `sample_evidence_ids` — the 2
 * reviews the spoke agents actually read — rather than an arbitrary slice of
 * `evidence_ids`, so a snippet never implies the model saw a review it didn't.
 *
 * Output:
 *   data.json    - the payload, for serving over http
 *   index.html   - same payload inlined between the DATA markers, so the page
 *                  also works opened straight off disk (fetch() is blocked on
 *                  file:// by CORS, which would otherwise leave it empty)
 *
 * Usage:
 *   node results-page/build.mjs
 *   node results-page/build.mjs --themes path/to/other-run.json
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const arg = (flag, fallback) => {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

const themesPath = path.resolve(here, arg('--themes', '../data/processed/real_themes.json'));
const reviewsPath = path.resolve(here, arg('--reviews', '../data/processed/cleaned_reviews.jsonl'));

const run = JSON.parse(fs.readFileSync(themesPath, 'utf8'));

// id -> review. Streaming line-by-line rather than JSON.parse on the whole
// file; cleaned_reviews.jsonl is ~1MB now but grows with every scrape.
const reviews = new Map();
for (const line of fs.readFileSync(reviewsPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  try {
    const r = JSON.parse(line);
    if (r.id) reviews.set(r.id, r);
  } catch {
    // A malformed line should cost us one snippet, not the whole build.
  }
}

const MAX_SNIPPET = 240;
function snippetFor(id) {
  const r = reviews.get(id);
  if (!r) return null; // unresolved id -> omitted, never invented
  const text = String(r.text ?? '').trim();
  if (!text) return null;
  return {
    id,
    text: text.length > MAX_SNIPPET ? `${text.slice(0, MAX_SNIPPET).trimEnd()}…` : text,
    truncated: text.length > MAX_SNIPPET,
    rating: r.rating ?? null,
    source: r.source ?? null,
  };
}

const themes = run.themes.map((t) => {
  const ids = Array.isArray(t.evidence_ids) ? t.evidence_ids : [];
  const sampleIds = (Array.isArray(t.sample_evidence_ids) && t.sample_evidence_ids.length
    ? t.sample_evidence_ids
    : ids
  ).slice(0, 2);

  return {
    cluster_id: t.cluster_id ?? null,
    theme_name: t.theme_name ?? '(unnamed cluster)',
    theme_description: t.theme_description ?? '',
    user_segment: t.user_segment ?? null,
    core_job: t.core_job ?? null,
    opportunity_title: t.opportunity_title ?? null,
    evidence_count: typeof t.evidence_count === 'number' ? t.evidence_count : ids.length,
    prevalence_pct: t.prevalence_pct ?? null,
    prevalence_basis: t.prevalence_basis ?? null,
    validation_passed: t.validation_passed === true,
    hallucinated_ids: Array.isArray(t.llm_hallucinated_ids) ? t.llm_hallucinated_ids : [],
    evidence_ids: ids,
    snippets: sampleIds.map(snippetFor).filter(Boolean),
  };
});

// Footer numbers are derived here, never typed in by hand.
const payload = {
  generated_at: run.generated_at ?? null,
  corpus_total: run.corpus_total ?? null,
  prevalence_basis: run.prevalence_basis ?? null,
  total_clusters_processed: run.total_clusters_processed ?? themes.length,
  validator: {
    themes_total: themes.length,
    themes_passed: themes.filter((t) => t.validation_passed).length,
    hallucinated_ids_total: themes.reduce((n, t) => n + t.hallucinated_ids.length, 0),
    hallucination_rate_pct: run.hallucination_rate_pct ?? null,
  },
  themes,
};

fs.writeFileSync(path.join(here, 'data.json'), `${JSON.stringify(payload, null, 2)}\n`);

// Inline the same payload into index.html so the page works off disk too.
const htmlPath = path.join(here, 'index.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const START = '/* DATA:START */';
const END = '/* DATA:END */';
const a = html.indexOf(START);
const b = html.indexOf(END);
if (a === -1 || b === -1 || b < a) {
  console.error('index.html is missing the DATA:START / DATA:END markers — not injecting.');
  process.exit(1);
}
const injected =
  html.slice(0, a + START.length) +
  `\n${JSON.stringify(payload)}\n` +
  html.slice(b);
fs.writeFileSync(htmlPath, injected);

// Publish a copy into the Vercel app's static dir. Vite copies publicDir
// verbatim into dist/, so this lands at /results on the deployed site.
// Generated here rather than copied by hand so the published page can't
// silently drift from results-page/ after a re-run.
const publishDir = path.resolve(here, '../mvp-shell/public/results');
fs.mkdirSync(publishDir, { recursive: true });
fs.writeFileSync(path.join(publishDir, 'index.html'), injected);
fs.writeFileSync(path.join(publishDir, 'data.json'), `${JSON.stringify(payload, null, 2)}\n`);

const unresolved = themes.reduce(
  (n, t) => n + Math.max(0, Math.min(2, t.evidence_ids.length) - t.snippets.length),
  0
);
console.log(`themes:            ${payload.themes.length}`);
console.log(`validated:         ${payload.validator.themes_passed}/${payload.validator.themes_total}`);
console.log(`hallucinated ids:  ${payload.validator.hallucinated_ids_total}`);
console.log(`snippets resolved: ${themes.reduce((n, t) => n + t.snippets.length, 0)}`);
if (unresolved > 0) console.log(`snippets unresolved (id not in corpus): ${unresolved}`);
console.log('wrote data.json + inlined payload into index.html');
console.log(`published to:      ${path.relative(path.resolve(here, '..'), publishDir)} (serves at /results)`);
