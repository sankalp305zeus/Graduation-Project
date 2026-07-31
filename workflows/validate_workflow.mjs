#!/usr/bin/env node
/**
 * Static validator for the n8n workflow JSON.
 *
 * Exists because two consecutive failed imports were caused by the same
 * class of bug: a Code node whose `mode`, input accessor, and return shape
 * disagreed. n8n only surfaces that at runtime, one node at a time, and an
 * eyeballed review missed it twice — so the rules are encoded here instead.
 *
 * Rules are taken from n8n-nodes-base source, not convention:
 *
 *   Code node (Code.node.js, result-validation.js, JsCodeValidator.js)
 *     - `mode` defaults to 'runOnceForAllItems' when unset.
 *     - runOnceForAllItems : MUST return an array of items.
 *                            May use $input.all() / .first() / .last().
 *     - runOnceForEachItem : MUST return a single object, NOT an array
 *                            ("please use the 'Run Once for All Items' mode
 *                            instead"). $input.first|last|all|itemMatching
 *                            are rejected ("Can't use .X() here").
 *
 *   SplitInBatches v3 (SplitInBatchesV3.node.js)
 *     - outputNames: ['done','loop'] -> output 0 = done, output 1 = loop.
 *       execute() returns [processedItems, []] when finished and
 *       [[], returnItems] while looping.
 *
 * Usage:  node workflows/validate_workflow.mjs [path-to-workflow.json]
 */
import fs from 'fs';

const path = process.argv[2] ?? new URL('./02-theme-extraction.json', import.meta.url).pathname;
const wf = JSON.parse(fs.readFileSync(path, 'utf8'));

let failures = 0;
const fail = (msg) => { console.log(`  FAIL  ${msg}`); failures++; };
const pass = (msg) => console.log(`  PASS  ${msg}`);

// Strip comments so commented-out examples don't trip the accessor checks.
const stripComments = (code) =>
  code.replace(/\/\*[\s\S]*?\*\//g, '').split('\n').filter((l) => !l.trimStart().startsWith('//')).join('\n');

console.log('Code node mode / accessor / return-shape consistency:');
for (const node of wf.nodes.filter((n) => n.type === 'n8n-nodes-base.code')) {
  const mode = node.parameters.mode ?? 'runOnceForAllItems'; // documented default
  const code = stripComments(node.parameters.jsCode ?? '');

  const returnsArray = /return\s*\[/.test(code) || /return\s+[\w.$()]+\.map\s*\(/.test(code);
  const usesEachItemApi = /\$input\.item\b/.test(code) || /\$\([^)]*\)\.item\b/.test(code);
  const usesAllItemsApi = /\$input\.(all|first|last|itemMatching)\s*\(/.test(code);

  if (mode === 'runOnceForAllItems') {
    if (!returnsArray) fail(`${node.name}: all-items mode must return an array`);
    else if (usesEachItemApi) fail(`${node.name}: all-items mode cannot use $input.item / $(node).item`);
    else pass(`${node.name}: all-items + array return + all-items accessors`);
  } else if (mode === 'runOnceForEachItem') {
    if (returnsArray) fail(`${node.name}: each-item mode must return a single object, not an array`);
    else if (usesAllItemsApi) fail(`${node.name}: each-item mode cannot use $input.all/first/last/itemMatching`);
    else pass(`${node.name}: each-item + single-object return + each-item accessors`);
  } else {
    fail(`${node.name}: unknown mode "${mode}"`);
  }
}

console.log('\nSplitInBatches v3 output wiring:');
for (const node of wf.nodes.filter((n) => n.type === 'n8n-nodes-base.splitInBatches')) {
  if (node.typeVersion !== 3) { fail(`${node.name}: expected typeVersion 3, got ${node.typeVersion}`); continue; }
  const outs = wf.connections[node.name]?.main ?? [];
  if (outs.length !== 2) { fail(`${node.name}: expected 2 wired outputs, got ${outs.length}`); continue; }
  const done = (outs[0] ?? []).map((c) => c.node);
  const loop = (outs[1] ?? []).map((c) => c.node);
  // The loop output must feed the per-batch work, and the done output must
  // feed the terminal aggregation — swapping these silently "succeeds".
  if (loop.length === 0) fail(`${node.name}: output 1 (loop) is not wired — the loop body will never run`);
  else pass(`${node.name}: output 1 (loop) -> ${loop.join(', ')}`);
  if (done.length === 0) fail(`${node.name}: output 0 (done) is not wired`);
  else pass(`${node.name}: output 0 (done) -> ${done.join(', ')}`);
}

console.log('\nGraph integrity:');
const names = new Set(wf.nodes.map((n) => n.name));
let dangling = 0;
for (const [src, conns] of Object.entries(wf.connections)) {
  if (!names.has(src)) { fail(`connection source "${src}" is not a node`); dangling++; }
  for (const group of Object.values(conns)) {
    for (const list of group ?? []) {
      for (const c of list ?? []) {
        if (!names.has(c.node)) { fail(`"${src}" -> "${c.node}" (missing node)`); dangling++; }
      }
    }
  }
}
if (dangling === 0) pass(`no dangling connections (${wf.nodes.length} nodes)`);

const ids = wf.nodes.map((n) => n.id);
if (new Set(ids).size !== ids.length) fail('duplicate node ids'); else pass('node ids unique');

console.log(failures === 0 ? '\nWorkflow valid.' : `\n${failures} problem(s) found.`);
process.exit(failures === 0 ? 0 : 1);
