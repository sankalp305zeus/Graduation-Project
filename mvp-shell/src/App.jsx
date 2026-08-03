import { useState, useEffect, useMemo } from 'react'
import { ShoppingCart } from 'lucide-react'
import PersonaSwitcher from './components/PersonaSwitcher'
import CategoryGrid from './components/CategoryGrid'
import CartPanel from './components/CartPanel'
import DiscoveryCard from './components/DiscoveryCard'
import CategoryJourney from './components/CategoryJourney'
import { fetchPersonas, fetchProducts, logEvent, isConfigured } from './supabaseClient'

const FREE_DELIVERY_THRESHOLD = 199
const DEFICIT_MIN = 40
const DEFICIT_MAX = 80

// PLACEHOLDER recommendation logic — deterministic, no AI/RAG call.
// Picks the never-tried-category product whose price is closest to the
// current checkout deficit. Replace this function with a real API call
// (Vercel serverless -> Claude, RAG-grounded on discovery-engine themes)
// once that layer exists — everything else in the UI stays the same.
function pickRecommendation(products, persona, deficit) {
  const candidates = products.filter((p) => persona.never_tried.includes(p.category))
  if (candidates.length === 0) return null
  const scored = candidates.map((p) => ({
    product: p,
    score: Math.abs(p.price - deficit) + (p.price > deficit ? 5 : 0),
  }))
  scored.sort((a, b) => a.score - b.score)
  return scored[0].product
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
          <div className="subtitle">
            Discovery Concierge prototype{!isConfigured && ' — mock data (Supabase not connected)'}
          </div>
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

        {/* Sits below the discovery card. Illustrative projection only — the
            component labels itself as such, see CategoryJourney.jsx. */}
        <CategoryJourney persona={persona} recommendedCategory={recommendation?.category ?? null} />
      </div>
    </div>
  )
}
