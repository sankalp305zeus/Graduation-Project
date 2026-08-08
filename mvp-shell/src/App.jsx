import { useState, useEffect, useMemo } from 'react'
import { ShoppingCart } from 'lucide-react'
import PersonaSwitcher from './components/PersonaSwitcher'
import CategoryGrid from './components/CategoryGrid'
import CartPanel from './components/CartPanel'
import DiscoveryCard from './components/DiscoveryCard'
import DiscoveryRail from './components/DiscoveryRail'
import SeasonalRail from './components/SeasonalRail'
import { getSeasonalContext } from './data/seasonalContext'
import { getAffinity } from './data/personaAffinity'
import { fetchPersonas, fetchProducts, logEvent, isConfigured } from './supabaseClient'

const FREE_DELIVERY_THRESHOLD = 199

// Discovery used to be gated to a 40-80 rupee deficit window. That window was
// invisible and easy to miss on both sides: one item and you never reached it,
// three and you sailed past — a cart 29 rupees short of free delivery showed
// nothing at all, with no explanation. Discovery now runs whenever the cart
// isn't empty, and the copy adapts to whether a gap still exists.
//
// With no gap left to size against, the rail falls back to a flat ceiling
// rather than ranking on a negative number.
const NO_GAP_PRICE_CEILING = 150

// Categories where need is binary and externally determined — you either
// have a baby or a pet or you don't. These aren't discovery opportunities:
// the barrier is need, not awareness, so surfacing them to someone without
// the need is noise (diapers to a 24-year-old student). Excluded from
// discovery entirely rather than gated on a demographic guess, which is
// both unsupported by our data and the kind of inference guardrails.js's
// checkNoSensitiveInference exists to discourage.
const NEED_GATED_CATEGORIES = ['Baby Care', 'Pet Supplies']

// Eligible discovery categories = everything outside the persona's habitual
// basket, minus the need-gated ones. Derived from the catalog rather than a
// hand-written never_tried list, so any category added later is immediately
// discoverable for every persona with no per-persona editing.
function eligibleCategories(products, persona) {
  const all = [...new Set(products.map((p) => p.category))]
  return all.filter(
    (c) => !persona.always_orders.includes(c) && !NEED_GATED_CATEGORIES.includes(c)
  )
}

// How well a product suits the moment. With a gap still open, closeness to
// that gap; once free delivery is reached there's no gap to match, so cheaper
// items simply rank first.
function priceFit(product, gapTarget) {
  return gapTarget != null ? Math.abs(product.price - gapTarget) : product.price
}

// PLACEHOLDER recommendation logic — deterministic, no AI/RAG call.
// Affinity first, then price fit. Affinity comes from the occupation printed
// on the persona card: ranking on price alone is persona-independent, which
// had five of six personas seeing an identical card and rail.
// Replace with a real API call (Vercel serverless -> Claude, RAG-grounded on
// discovery-engine themes) once that layer exists — the UI stays the same.
function pickRecommendation(products, persona, gapTarget) {
  const eligible = eligibleCategories(products, persona)
  const affinity = getAffinity(persona.occupation)
  const candidates = products.filter((p) => eligible.includes(p.category))
  if (candidates.length === 0) return null

  return candidates
    .map((p) => ({
      product: p,
      affinityRank: affinity.includes(p.category) ? 0 : 1,
      fit: priceFit(p, gapTarget) + (gapTarget != null && p.price > gapTarget ? 5 : 0),
    }))
    .sort((a, b) => a.affinityRank - b.affinityRank || a.fit - b.fit)[0].product
}

// The rail below the filler card. Also deterministic: same eligible pool,
// minus whatever the filler card already took, interleaved across categories
// so the rail shows more than one category tag rather than three cards from
// the same one.
//
// Price ceiling: the strongest real theme in the corpus is "Hidden or
// unexpected charges" (67 reviews) whose core job is completing a purchase
// without unexpected cost. Offering a 249-rupee item to someone 73 short
// would contradict that at the exact moment cost anxiety peaks, so the rail
// is capped relative to the gap instead of being price-blind.
const RAIL_SIZE = 3
const RAIL_PRICE_CEILING_MULTIPLIER = 1.5

function pickRail(products, persona, exclude, gapTarget) {
  const ceiling =
    gapTarget != null ? Math.round(gapTarget * RAIL_PRICE_CEILING_MULTIPLIER) : NO_GAP_PRICE_CEILING
  const eligible = eligibleCategories(products, persona)
  const affinity = getAffinity(persona.occupation)
  const pool = products.filter(
    (p) => eligible.includes(p.category) && p.id !== exclude?.id && p.price <= ceiling
  )

  // Order categories by affinity, then by how well their best item fits.
  // NOT by catalog insertion order — that made the rail draw the same first
  // three categories for everyone and left later categories (including newly
  // added ones) permanently invisible. Ranking on fit alone then made every
  // persona converge on the same products, since fit ignores who is shopping.
  // Affinity first, fit second, keeps it varied AND deterministic.
  const byCategory = eligible
    .map((c) => pool.filter((p) => p.category === c).sort((a, b) => priceFit(a, gapTarget) - priceFit(b, gapTarget)))
    .filter((bucket) => bucket.length > 0)
    .sort((a, b) => {
      const aAff = affinity.includes(a[0].category) ? 0 : 1
      const bAff = affinity.includes(b[0].category) ? 0 : 1
      return aAff - bAff || priceFit(a[0], gapTarget) - priceFit(b[0], gapTarget)
    })

  const rail = []
  for (let round = 0; rail.length < RAIL_SIZE; round += 1) {
    const before = rail.length
    for (const bucket of byCategory) {
      if (bucket[round] && rail.length < RAIL_SIZE) rail.push(bucket[round])
    }
    if (rail.length === before) break // pool exhausted
  }
  return rail
}

// Seasonal picks. Unlike the discovery card and rail, these are NOT gated on
// the checkout deficit — an occasion is a reason to surface a category
// regardless of how close the cart is to free delivery, and a cart past the
// threshold otherwise ends in silence.
//
// Still excludes need-gated categories (same reasoning as discovery) and
// de-duplicates against anything already in the cart or already shown above,
// so the same product never appears twice on one screen.
const SEASONAL_SIZE = 3
function pickSeasonal(products, persona, context, excludeIds) {
  if (!context || !persona) return []

  const pool = products.filter(
    (p) =>
      context.categories.includes(p.category) &&
      !NEED_GATED_CATEGORIES.includes(p.category) &&
      !excludeIds.has(p.id)
  )

  // Non-habitual categories first: the rationale on this section promises an
  // occasion where non-habitual categories get considered, so leading with
  // the persona's most-bought category would contradict the card's own copy.
  // Then interleave one product per category — taking the pool in catalog
  // order instead filled all three slots from whichever category happens to
  // be defined first, which is the same bug the discovery rail had.
  const cats = [...new Set(pool.map((p) => p.category))].sort((a, b) => {
    const aHabitual = persona.always_orders.includes(a) ? 1 : 0
    const bHabitual = persona.always_orders.includes(b) ? 1 : 0
    return aHabitual - bHabitual
  })

  // Within each category, an item explicitly tagged for THIS occasion wins.
  // Without this, Raksha Bandhan surfaced a generic Gift Wrap Set instead of
  // the Rakhi gift box, purely because the generic item appears earlier in the
  // catalog — the occasion stock would never have been seen.
  const taggedFirst = (a, b) => {
    const aTag = (a.occasions ?? []).includes(context.id) ? 0 : 1
    const bTag = (b.occasions ?? []).includes(context.id) ? 0 : 1
    return aTag - bTag
  }
  const buckets = cats.map((c) => pool.filter((p) => p.category === c).sort(taggedFirst))
  const out = []
  for (let round = 0; out.length < SEASONAL_SIZE; round += 1) {
    const before = out.length
    for (const bucket of buckets) {
      if (bucket[round] && out.length < SEASONAL_SIZE) out.push(bucket[round])
    }
    if (out.length === before) break // pool exhausted
  }
  return out
}

export default function App() {
  const [personas, setPersonas] = useState([])
  const [products, setProducts] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [cart, setCart] = useState([])
  const [dismissedAtSubtotal, setDismissedAtSubtotal] = useState(null)
  const [justAccepted, setJustAccepted] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const [p, pr] = await Promise.all([fetchPersonas(), fetchProducts()])
      setPersonas(p)
      setProducts(pr)
      setActiveId(p[0]?.id ?? null)
      setLoading(false)
    }
    load()
  }, [])

  const persona = personas.find((p) => p.id === activeId)

  const subtotal = cart.reduce((sum, item) => sum + item.price, 0)
  const deficit = FREE_DELIVERY_THRESHOLD - subtotal

  // null once free delivery is reached — there is no gap left to price against.
  const gapTarget = deficit > 0 ? deficit : null

  const showDiscovery =
    Boolean(persona) && cart.length > 0 && dismissedAtSubtotal !== subtotal && !justAccepted

  const recommendation = useMemo(() => {
    if (!showDiscovery || !persona) return null
    return pickRecommendation(products, persona, gapTarget)
  }, [showDiscovery, persona, products, gapTarget])

  const railProducts = useMemo(() => {
    if (!showDiscovery || !persona) return []
    return pickRail(products, persona, recommendation, gapTarget)
  }, [showDiscovery, persona, products, recommendation, gapTarget])

  const seasonalContext = useMemo(
    () => (persona ? getSeasonalContext(persona.city) : null),
    [persona]
  )

  const seasonalProducts = useMemo(() => {
    if (!persona || !seasonalContext) return []
    const shown = new Set([
      ...cart.map((c) => c.id),
      ...(recommendation ? [recommendation.id] : []),
      ...railProducts.map((p) => p.id),
    ])
    return pickSeasonal(products, persona, seasonalContext, shown)
  }, [persona, seasonalContext, products, cart, recommendation, railProducts])

  function handleSwitchPersona(id) {
    setActiveId(id)
    setCart([])
    setDismissedAtSubtotal(null)
    setJustAccepted(false)
  }

  function handleAdd(product) {
    setCart((c) => [...c, product])
    setJustAccepted(false)
    setDismissedAtSubtotal(null)
  }

  function handleAccept() {
    if (!recommendation || !persona) return
    setCart((c) => [...c, recommendation])
    logEvent({ personaId: persona.id, productId: recommendation.id, action: 'accepted' })
    setJustAccepted(true)
  }

  function handleDismiss() {
    if (!recommendation || !persona) return
    logEvent({ personaId: persona.id, productId: recommendation.id, action: 'dismissed' })
    setDismissedAtSubtotal(subtotal)
  }

  if (loading || !persona) {
    return (
      <div className="phone-frame">
        <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>Loading…</div>
      </div>
    )
  }

  return (
    <div className="phone-frame">
      <div className="app-scroll">
        <div className="app-header">
          <div className="brand">
            <ShoppingCart size={19} strokeWidth={2.5} aria-hidden="true" />
            QuickCart
          </div>
          <div className="subtitle">Discovery Concierge prototype</div>
          {/* Same message as before, restyled as a deliberate demo-mode
              indicator rather than an error. Wording must stay this explicit. */}
          {!isConfigured && (
            <span className="demo-badge">
              <span className="demo-dot" aria-hidden="true" />
              Demo mode — mock data (Supabase not connected)
            </span>
          )}
        </div>

        <PersonaSwitcher personas={personas} activeId={activeId} onSelect={handleSwitchPersona} />

        <CategoryGrid products={products} persona={persona} onAdd={handleAdd} />

        <CartPanel cartItems={cart} subtotal={subtotal} threshold={FREE_DELIVERY_THRESHOLD} />

        {justAccepted && (
          <div className="discovery-confirmation">
            Added! Explore more items above, or switch personas to see a different discovery moment.
          </div>
        )}

        {showDiscovery && recommendation && !justAccepted && (
          <DiscoveryCard
            product={recommendation}
            persona={persona}
            deficit={deficit}
            onAccept={handleAccept}
            onDismiss={handleDismiss}
          />
        )}

        {showDiscovery && recommendation && !justAccepted && (
          <DiscoveryRail products={railProducts} persona={persona} onAdd={handleAdd} />
        )}

        {/* Not gated on showDiscovery — deliberately still renders above the
            free-delivery threshold, where everything else has gone quiet. */}
        <SeasonalRail context={seasonalContext} products={seasonalProducts} />
      </div>
    </div>
  )
}
