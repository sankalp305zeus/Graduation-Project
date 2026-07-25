/**
 * POST /api/recommend
 * Body: { personaId: string, cartItems: [{id, category, price}], deficit: number }
 *
 * Replaces the deterministic pickRecommendation() in the mvp-shell's App.jsx.
 * This is the real thing: retrieval-grounded (RAG) generation + deterministic
 * guardrails, with a fallback to the original placeholder logic if anything
 * fails a guardrail. The frontend does not need to change its contract —
 * this returns the same shape (product + reasoning + evidence) either way.
 *
 * NOT TESTED LIVE from this build environment — huggingface.co and
 * api.groq.com are both blocked by this sandbox's egress policy (403 at the
 * proxy), so neither the embeddings model nor a real Groq call could be
 * exercised here. Test this yourself against real credentials before
 * trusting it in a demo. The guardrails.js module IS unit-tested (see
 * guardrails.test.js, 8/8 passing) since that logic needs no external
 * network call.
 */
import { createClient } from '@supabase/supabase-js'
import Groq from 'groq-sdk'
import { runGuardrails } from './guardrails.js'

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // service role, NOT the anon key — this runs server-side only
)
// maxRetries: the SDK auto-retries 429/5xx with exponential backoff (default
// 2); bumped slightly since a demo-time judge click on this single live call
// shouldn't fail silently — see docs/GROQ_MIGRATION_AND_FAILPROOFING.md Task B.
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY, maxRetries: 3 })

// Pinned per docs/GROQ_MIGRATION_AND_FAILPROOFING.md ("pin exact model
// version strings ... never rely on a provider's default"). Groq deprecates
// models over time — re-verify this is still current at
// console.groq.com/docs/models before the live demo; this sandbox's egress
// policy blocks api.groq.com so it could not be checked from here.
const GROQ_MODEL = 'llama-3.3-70b-versatile'

// Same deterministic logic as the mvp-shell's App.jsx — used as the fallback
// path when the AI recommendation fails a guardrail, so the user always sees
// SOMETHING reasonable rather than an error or a blank card.
function deterministicFallback(products, neverTriedCategories, deficit) {
  const candidates = products.filter((p) => neverTriedCategories.includes(p.category))
  if (candidates.length === 0) return null
  const scored = candidates.map((p) => ({
    product: p,
    score: Math.abs(p.price - deficit) + (p.price > deficit ? 5 : 0),
  }))
  scored.sort((a, b) => a.score - b.score)
  return scored[0].product
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'POST only' })
  }

  const { personaId, cartItems = [], deficit } = req.body || {}
  if (!personaId || typeof deficit !== 'number') {
    return res.status(400).json({ error: 'personaId and numeric deficit are required' })
  }

  try {
    // 1. Fetch persona
    const { data: persona, error: personaErr } = await supabase
      .from('personas')
      .select('*')
      .eq('id', personaId)
      .single()
    if (personaErr || !persona) {
      return res.status(404).json({ error: 'persona not found' })
    }

    const neverTriedCategories = persona.never_tried

    // 2. Retrieve candidate products (deterministic filter — this ALREADY
    //    guarantees category eligibility before the LLM even runs; the
    //    guardrail check afterward is defense in depth, not the only line
    //    of defense)
    const { data: candidateProducts } = await supabase
      .from('products')
      .select('*')
      .in('category', neverTriedCategories)

    if (!candidateProducts || candidateProducts.length === 0) {
      return res.status(200).json({
        product: null,
        reasoning: null,
        guardrail_status: 'NO_CANDIDATES',
      })
    }

    // 3. RAG retrieval — themes for those categories.
    //    NOTE: this is a category filter, not yet the hybrid vector +
    //    full-text search described in the blueprint's RAG design (E.1).
    //    That upgrade requires embedding the current cart/persona context
    //    and doing a real similarity search — worth doing once there's
    //    enough real theme volume to make ranking meaningful; with ~1-2
    //    placeholder themes per category right now, a category filter and
    //    a similarity search would return the same result.
    const { data: relevantThemes } = await supabase
      .from('themes')
      .select('*')
      .in('category', neverTriedCategories)

    if (!relevantThemes || relevantThemes.length === 0) {
      const fallback = deterministicFallback(candidateProducts, neverTriedCategories, deficit)
      return res.status(200).json({
        product: fallback,
        reasoning: 'No research themes available yet for this category — showing a price-matched suggestion instead.',
        evidence_ids: [],
        guardrail_status: 'NO_THEMES_FALLBACK',
      })
    }

    // 4. Build the grounded prompt. Strict instructions: pick ONLY from the
    //    provided product list, cite ONLY the provided evidence_ids.
    const systemPrompt = `You are a product recommendation assistant for a quick-commerce app.
You will be given a user's shopping profile, their current cart, a list of candidate products
they have never ordered before, and research themes (with evidence) about why users hesitate
or engage with those categories.

Pick EXACTLY ONE product from the candidate list that best fits this moment, and explain why
in one sentence, grounded in the provided research theme.

Rules:
- product_id MUST be exactly one of the candidate product IDs given to you. Never invent an ID.
- evidence_ids MUST be a subset of the evidence_ids from the theme you used. Never invent one.
- If a theme suggests a barrier (e.g. trust, awareness), your reasoning should address it
  directly rather than ignoring it — e.g. don't recommend pharmacy items without acknowledging
  an authenticity concern if that's what the theme says.
- Respond with ONLY this JSON, no other text:
{"product_id": "...", "reasoning": "...", "evidence_ids": ["..."]}`

    const userPrompt = JSON.stringify({
      persona: { name: persona.name, always_orders: persona.always_orders, never_tried: neverTriedCategories },
      current_cart: cartItems,
      deficit_amount: deficit,
      candidate_products: candidateProducts.map((p) => ({ id: p.id, name: p.name, category: p.category, price: p.price })),
      research_themes: relevantThemes.map((t) => ({
        category: t.category,
        theme_name: t.theme_name,
        description: t.description,
        evidence_ids: t.evidence_ids,
      })),
    })

    // 5. Call Groq. Wrapped in its own try/catch — a total call failure
    //    (network error, timeout, 429 after retries exhausted) must degrade
    //    to the same deterministic fallback as a guardrail failure, never
    //    reach the outer catch and 500 the whole request. See
    //    docs/GROQ_MIGRATION_AND_FAILPROOFING.md's fail-proofing checklist.
    let messageText
    try {
      const response = await groq.chat.completions.create({
        model: GROQ_MODEL,
        max_tokens: 300,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
      })
      messageText = response.choices?.[0]?.message?.content
    } catch (err) {
      console.error('recommend.js Groq call failed:', err)
      const fallback = deterministicFallback(candidateProducts, neverTriedCategories, deficit)
      return res.status(200).json({
        product: fallback,
        reasoning: 'AI recommendation is temporarily unavailable — showing a price-matched suggestion instead.',
        evidence_ids: [],
        guardrail_status: 'API_FAILURE_FALLBACK',
      })
    }

    let parsed
    try {
      parsed = JSON.parse(messageText)
    } catch (e) {
      // Malformed JSON from the model — guardrails.js would also catch this
      // shape issue, but we can't even run it without valid JSON, so fall
      // back immediately.
      const fallback = deterministicFallback(candidateProducts, neverTriedCategories, deficit)
      return res.status(200).json({
        product: fallback,
        reasoning: 'AI response could not be parsed — showing a price-matched suggestion instead.',
        evidence_ids: [],
        guardrail_status: 'PARSE_FAILURE_FALLBACK',
      })
    }

    // 6. GUARDRAILS — deterministic, see guardrails.js. This is the real
    //    safety net; steps above reduce the chance of a bad output but this
    //    is what actually blocks one from reaching the user.
    const guardrailResult = runGuardrails(parsed, {
      validProducts: candidateProducts,
      validThemes: relevantThemes,
      neverTriedCategories,
    })

    if (!guardrailResult.passed) {
      const fallback = deterministicFallback(candidateProducts, neverTriedCategories, deficit)
      return res.status(200).json({
        product: fallback,
        reasoning: 'Showing a price-matched suggestion instead — the AI recommendation did not pass a safety check.',
        evidence_ids: [],
        guardrail_status: 'GUARDRAIL_FAILED_FALLBACK',
        guardrail_failures: guardrailResult.failures, // useful in logs/dev, strip before showing to end users
      })
    }

    // 7. Passed — return the real AI recommendation. Case-insensitive
    //    lookup to stay consistent with guardrails.js's checkProductExists:
    //    if the guardrail accepted a case-flipped product_id, an exact-match
    //    find() here would return undefined — a broken card shipped with
    //    guardrail_status PASSED, which is worse than any fallback.
    const normId = (s) => (typeof s === 'string' ? s.trim().toLowerCase() : s)
    const product = candidateProducts.find((p) => normId(p.id) === normId(parsed.product_id))
    return res.status(200).json({
      product,
      reasoning: parsed.reasoning,
      evidence_ids: parsed.evidence_ids,
      guardrail_status: 'PASSED',
    })
  } catch (err) {
    console.error('recommend.js error:', err)
    return res.status(500).json({ error: 'internal error generating recommendation' })
  }
}
