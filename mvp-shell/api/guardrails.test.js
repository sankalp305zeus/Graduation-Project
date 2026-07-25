import { runGuardrails } from './guardrails.js'

const validProducts = [
  { id: 'p10', name: 'Nivea Face Wash 100ml', category: 'Personal Care & Beauty', price: 199 },
  { id: 'p01', name: 'Amul Milk 1L', category: 'Groceries & Fresh Produce', price: 66 },
]
const validThemes = [
  { id: 'th_001', category: 'Personal Care & Beauty', evidence_ids: ['rev_001', 'rev_002'] },
]
const baseContext = {
  validProducts,
  validThemes,
  neverTriedCategories: ['Personal Care & Beauty', 'Electronics Accessories'],
}

let passed = 0
let failed = 0
function check(name, condition) {
  if (condition) { console.log(`  PASS  ${name}`); passed++ }
  else { console.log(`  FAIL  ${name}`); failed++ }
}

console.log('Test 1: fully valid recommendation should pass')
const valid = {
  product_id: 'p10',
  reasoning: 'This face wash is popular with users who buy groceries regularly.',
  evidence_ids: ['rev_001'],
}
const r1 = runGuardrails(valid, baseContext)
check('valid recommendation passes', r1.passed === true)

console.log('\nTest 2: hallucinated product_id should fail')
const r2 = runGuardrails({ ...valid, product_id: 'p999_fake' }, baseContext)
check('catches hallucinated product', r2.passed === false && r2.failures.some(f => f.includes('HALLUCINATED_PRODUCT')))

console.log('\nTest 3: recommending an already-tried category should fail')
const r3 = runGuardrails({ ...valid, product_id: 'p01' }, baseContext) // p01 is Groceries, not never_tried
check('catches category violation', r3.passed === false && r3.failures.some(f => f.includes('CATEGORY_VIOLATION')))

console.log('\nTest 4: hallucinated evidence_ids should fail')
const r4 = runGuardrails({ ...valid, evidence_ids: ['rev_999_fake'] }, baseContext)
check('catches hallucinated evidence', r4.passed === false && r4.failures.some(f => f.includes('HALLUCINATED_EVIDENCE')))

console.log('\nTest 5: empty evidence_ids should fail (ungrounded output)')
const r5 = runGuardrails({ ...valid, evidence_ids: [] }, baseContext)
check('catches ungrounded output', r5.passed === false && r5.failures.some(f => f.includes('UNGROUNDED_OUTPUT')))

console.log('\nTest 6: malformed output (missing field) should fail')
const r6 = runGuardrails({ product_id: 'p10' }, baseContext)
check('catches malformed output', r6.passed === false && r6.failures.some(f => f.includes('MALFORMED_OUTPUT')))

console.log('\nTest 7: sensitive health inference should fail')
const r7 = runGuardrails({ ...valid, reasoning: 'Since you seem to be pregnant, try this instead.' }, baseContext)
check('catches sensitive inference', r7.passed === false && r7.failures.some(f => f.includes('SENSITIVE_INFERENCE')))

console.log('\nTest 8: PII in reasoning should fail')
const r8 = runGuardrails({ ...valid, reasoning: 'Call us at 9876543210 for more info.' }, baseContext)
check('catches PII leak', r8.passed === false && r8.failures.some(f => f.includes('PII_LEAK')))

// --- Adversarial cases ---
// These probe data-hygiene edge cases rather than LLM hallucination —
// confirming guardrails.js fails closed (rejects) or documents a known
// scope limit, never crashes, and never lets a bad recommendation through.

console.log('\nTest 9: category string case-mismatch should fail closed, not crash')
// Real catalog casing is 'Pet Supplies' (see mvp-shell/src/data/mockProducts.js);
// this product is seeded with a lowercase category, simulating a data-entry
// inconsistency between products.category and personas.never_tried.
const caseMismatchContext = {
  validProducts: [
    { id: 'p_pet', name: 'Pet Shampoo', category: 'pet supplies', price: 72 },
  ],
  validThemes: [
    { id: 'th_002', category: 'pet supplies', evidence_ids: ['rev_010'] },
  ],
  neverTriedCategories: ['Pet Supplies'], // canonical casing
}
const r9 = runGuardrails(
  { product_id: 'p_pet', reasoning: 'This pet shampoo suits users exploring pet care for the first time.', evidence_ids: ['rev_010'] },
  caseMismatchContext,
)
check(
  'case-mismatched category fails closed (CATEGORY_VIOLATION), no crash — checkCategoryEligible is case-sensitive by design',
  r9.passed === false && r9.failures.some(f => f.includes('CATEGORY_VIOLATION')),
)

console.log('\nTest 10: persona with contradictory always_orders/never_tried data should not crash')
// guardrails.js's context shape never includes always_orders at all (see
// recommend.js's guardrail call — only validProducts/validThemes/
// neverTriedCategories are passed in), so a persona whose always_orders
// upstream ALSO contains this category is invisible to this check by
// construction. This documents that scope limit rather than papering over
// it: guardrails.js can't catch that contradiction, only that it doesn't
// crash on it. Catching self-contradictory persona data belongs at
// seed/entry-time validation, not in this guardrail layer.
const contradictoryPersonaContext = {
  ...baseContext,
  neverTriedCategories: ['Personal Care & Beauty'], // same category this (hypothetical) persona also always_orders
}
const r10 = runGuardrails(valid, contradictoryPersonaContext)
check(
  'does not crash on contradictory persona data (passes its own narrow check; the contradiction itself is out of scope for guardrails.js)',
  r10.passed === true,
)

console.log('\nTest 11: empty candidate product list should fail closed, not crash')
const emptyCandidatesContext = {
  validProducts: [],
  validThemes: baseContext.validThemes,
  neverTriedCategories: baseContext.neverTriedCategories,
}
const r11 = runGuardrails(valid, emptyCandidatesContext)
check(
  'empty candidate list fails closed (HALLUCINATED_PRODUCT) without crashing on product.category lookup',
  r11.passed === false && r11.failures.some(f => f.includes('HALLUCINATED_PRODUCT')),
)

console.log(`\n${passed} passed, ${failed} failed`)
process.exit(failed > 0 ? 1 : 0)
