import { useState, useEffect, useMemo } from 'react'
import { ShoppingCart } from 'lucide-react'
import PersonaSwitcher from './components/PersonaSwitcher'
import CategoryGrid from './components/CategoryGrid'
import CartPanel from './components/CartPanel'
import DiscoveryCard from './components/DiscoveryCard'
import DiscoveryRail from './components/DiscoveryRail'
import SeasonalRail from './components/SeasonalRail'
import { getSeasonalContext } from './data/seasonalContext'
import { fetchPersonas, fetchProducts, logEvent, isConfigured } from './supabaseClient'

const FREE_DELIVERY_THRESHOLD = 199
const DEFICIT_MIN = 40
const DEFICIT_MAX = 80

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

// PLACEHOLDER recommendation logic — deterministic, no AI/RAG call.
// Picks the eligible-category product whose price is closest to the
// current checkout deficit. Replace this function with a real API call
// (Vercel serverless -> Claude, RAG-grounded on discovery-engine themes)
// once that layer exists — everything else in the UI stays the same.
function pickRecommendation(products, persona, deficit) {
  const eligible = eligibleCategories(products, persona)
  const candidates = products.filter((p) => eligible.includes(p.category))
  if (candidates.length === 0) return null
  const scored = candidates.map((p) => ({
    product: p,
    score: Math.abs(p.price - deficit) + (p.price > deficit ? 5 : 0),
  }))
  scored.sort((a, b) => a.score - b.score)
  return scored[0].product
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

function pickRail(products, persona, exclude, deficit) {
  const ceiling = Math.round(deficit * RAIL_PRICE_CEILING_MULTIPLIER)
  const eligible = eligibleCategories(products, persona)
  const pool = products.filter(
    (p) => eligible.includes(p.category) && p.id !== exclude?.id && p.price <= ceiling
  )

  // Order categories by how well their best item fits the gap, NOT by catalog
  // insertion order. Insertion order meant the rail always drew the same first
  // three categories for every persona, leaving everything later in the
  // catalog (including any newly added category) permanently invisible.
  // Sorting by fit keeps this fully deterministic and reproducible for a demo,
  // while letting a new category compete on merit from the day it's added.
  const fit = (p) => Math.abs(p.price - deficit)
  const byCategory = eligible
    .map((c) => pool.filter((p) => p.category === c).sort((a, b) => fit(a) - fit(b)))
    .filter((bucket) => bucket.length > 0)
    .sort((a, b) => fit(a[0]) - fit(b[0]))

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

  const buckets = cats.map((c) => pool.filter((p) => p.category === c))
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

  const showDiscovery =
    Boolean(persona) &&
    deficit >= DEFICIT_MIN &&
    deficit <= DEFICIT_MAX &&
    dismissedAtSubtotal !== subtotal &&
    !justAccepted

  const recommendation = useMemo(() => {
    if (!showDiscovery || !persona) return null
    return pickRecommendation(products, persona, deficit)
  }, [showDiscovery, persona, products, deficit])

  const railProducts = useMemo(() => {
    if (!showDiscovery || !persona) return []
    return pickRail(products, persona, recommendation, deficit)
  }, [showDiscovery, persona, products, recommendation, deficit])

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

        <CartPanel
          cartItems={cart}
          subtotal={subtotal}
          threshold={FREE_DELIVERY_THRESHOLD}
          discoveryMin={DEFICIT_MIN}
          discoveryMax={DEFICIT_MAX}
        />

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
