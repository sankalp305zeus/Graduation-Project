import fs from 'fs';
import { fileURLToPath } from 'url';
// fileURLToPath, not URL.pathname — see validate_workflow.mjs (Windows "C:\C:\..." bug).
const wf = JSON.parse(fs.readFileSync(fileURLToPath(new URL('./02-theme-extraction.json', import.meta.url)),'utf8'));
const code = (name) => wf.nodes.find(n => n.name === name).parameters.jsCode;

// Run an n8n Code node body with mocked $input / $ globals.
function runNode(name, { item, all, refs = {} }) {
  const fn = new Function('$input', '$', code(name));
  const $input = { item, first: () => item, all: () => (all ?? [item]) };
  const $ = (nodeName) => ({ item: { json: refs[nodeName] }, first: () => ({ json: refs[nodeName] }) });
  return fn($input, $);
}

let pass = 0, fail = 0;
const check = (n, c) => { c ? (console.log(`  PASS  ${n}`), pass++) : (console.log(`  FAIL  ${n}`), fail++); };

// --- 1. Validate & Parse Input: corpus_total present ---
const body = {
  clusters: [
    { cluster_id: 'c0', reviews: [{id:'r1',text:'a',rating:3},{id:'r2',text:'b',rating:2}] },
    { cluster_id: 'c1', reviews: [{id:'r3',text:'c',rating:5}] },
  ],
  corpus_total: 1000,
  corpus_total_basis: 'embedded_reviews_analyzed',
};
let out = runNode('Validate & Parse Input', { item: { json: { body } } });
check('validate: one item per cluster', out.length === 2);
check('validate: corpus_total attached to every item',
  out.every(o => o.json.corpus_total === 1000 && o.json.corpus_total_basis === 'embedded_reviews_analyzed'));

// --- 1b. corpus_total absent -> labelled fallback, not silent ---
const bodyNoTotal = { clusters: body.clusters };
out = runNode('Validate & Parse Input', { item: { json: { body: bodyNoTotal } } });
check('validate: missing corpus_total falls back to payload sum (3) and LABELS the basis',
  out[0].json.corpus_total === 3 && out[0].json.corpus_total_basis === 'clustered_reviews_in_payload_fallback');

// --- 2. Prepare Cluster Text passes corpus_total through ---
const clusterItem = { json: { cluster_id:'c0', reviews:[{id:'r1',text:'a',rating:3},{id:'r2',text:'b',rating:2}],
                              corpus_total: 1000, corpus_total_basis: 'embedded_reviews_analyzed' } };
const prepared = runNode('Prepare Cluster Text', { item: clusterItem })[0].json;
check('prepare: carries corpus_total through the loop', prepared.corpus_total === 1000);
check('prepare: full membership preserved (not just sample)',
  JSON.stringify(prepared.all_cluster_member_ids) === JSON.stringify(['r1','r2']));

// --- 3. Evidence Validator: prevalence math ---
const synth = { output: { theme_name:'T', opportunity_scores:{severity:5}, sample_evidence_ids:['r1'] } };
let ev = runNode('Evidence Validator', {
  item: { json: synth },
  refs: { 'Prepare Cluster Text': { ...prepared, all_cluster_member_ids: Array.from({length:37},(_,i)=>`r${i}`) } },
})[0].json;
check('validator: prevalence_pct = 37/1000 = 3.70%', ev.prevalence_pct === 3.7);
check('validator: evidence_count is full membership (37)', ev.evidence_count === 37);
check('validator: basis + denominator reported alongside the %',
  ev.prevalence_basis === 'embedded_reviews_analyzed' && ev.corpus_total === 1000);
check('validator: LLM severity score preserved next to prevalence',
  ev.opportunity_scores.severity === 5);

// --- 3b. divide-by-zero / missing denominator must yield null, not Infinity/NaN ---
ev = runNode('Evidence Validator', {
  item: { json: synth },
  refs: { 'Prepare Cluster Text': { ...prepared, corpus_total: 0, all_cluster_member_ids: ['r1'] } },
})[0].json;
check('validator: corpus_total=0 -> prevalence_pct null (no Infinity/NaN leak)', ev.prevalence_pct === null);

ev = runNode('Evidence Validator', {
  item: { json: synth },
  refs: { 'Prepare Cluster Text': { ...prepared, corpus_total: undefined, all_cluster_member_ids: ['r1'] } },
})[0].json;
check('validator: missing corpus_total -> prevalence_pct null', ev.prevalence_pct === null);

// --- 3c. malformed synthesizer output still handled (regression) ---
ev = runNode('Evidence Validator', {
  item: { json: { output: 'not json{{' } },
  refs: { 'Prepare Cluster Text': prepared },
})[0].json;
check('validator: malformed LLM output still returns validation_error, does not throw',
  typeof ev.validation_error === 'string');

// --- 4. Aggregate echoes the denominator once at top level ---
const agg = runNode('Aggregate All Results', {
  all: [
    { json: { validation_passed: true, corpus_total: 1000, prevalence_basis: 'embedded_reviews_analyzed', prevalence_pct: 3.7 } },
    { json: { validation_passed: false, corpus_total: 1000, prevalence_basis: 'embedded_reviews_analyzed', prevalence_pct: 1.2 } },
  ],
})[0].json;
check('aggregate: surfaces corpus_total + basis at top level', agg.corpus_total === 1000 && agg.prevalence_basis === 'embedded_reviews_analyzed');
check('aggregate: hallucination rate still computed', agg.hallucination_rate_pct === '50.0');


// --- Reshape For Synthesizer: append-mode shape (3 items, input order) ---
const spokes = [
  { json: { output: { theme_name: 'Distrust of electronics returns', sample_evidence_ids: ['r1'] } } },
  { json: { output: { core_job: 'buy reliable essentials', user_segment: 'grocery-only' } } },
  { json: { output: { opportunity_title: 'One-tap returns', frequency_score: 3 } } },
];
let rs = runNode('Reshape For Synthesizer', { item: spokes[0], all: spokes })[0].json;
check('reshape: maps input order -> theme/jtbd/opportunity (no key collision)',
  rs.theme_output.theme_name === 'Distrust of electronics returns' &&
  rs.jtbd_output.core_job === 'buy reliable essentials' &&
  rs.opportunity_output.opportunity_title === 'One-tap returns');
check('reshape: records spokes_received for auditability', rs.spokes_received === 3);

// A missing spoke must degrade to null, not throw and halt the whole corpus run.
rs = runNode('Reshape For Synthesizer', { item: spokes[0], all: spokes.slice(0, 2) })[0].json;
check('reshape: missing 3rd spoke -> null + visible count, does not throw',
  rs.opportunity_output === null && rs.spokes_received === 2);

// Unwrapped agent output (no .output envelope) still passes through.
rs = runNode('Reshape For Synthesizer', { item: spokes[0], all: [{ json: { theme_name: 'raw' } }] })[0].json;
check('reshape: tolerates un-enveloped agent json', rs.theme_output.theme_name === 'raw');

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
