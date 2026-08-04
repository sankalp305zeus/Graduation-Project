import { useState } from 'react'
import { getCategoryIcon } from '../data/categoryIcons'
import { findThemeForCategory } from '../data/mockThemes'

/**
 * Horizontally-scrolling rail of never-tried-category products, sitting below
 * the amber threshold-filler card.
 *
 * Every card's "Why this?" panel carries the deterministic-logic line. That is
 * deliberate and must not be trimmed for space: without it a reader can
 * reasonably infer a model chose these products. It didn't — the pick is
 * arithmetic on price against the checkout gap.
 */
function RailCard({ product, persona, onAdd }) {
  const [showWhy, setShowWhy] = useState(false)
  const { Icon, fg, bg } = getCategoryIcon(product.category)
  const theme = findThemeForCategory(product.category)

  return (
    <div className="rail-card">
      <span className="cat-tag" style={{ background: bg, color: fg }}>
        {product.category}
      </span>

      <div className="icon-tile lg rail-icon" style={{ background: bg, color: fg }} aria-hidden="true">
        <Icon size={24} strokeWidth={1.9} />
      </div>

      <div className="rail-name">{product.name}</div>
      <div className="rail-price">₹{product.price}</div>

      <div className="rail-actions">
        <button className="rail-add" onClick={() => onAdd(product)}>Add</button>
        <button
          className="why-link"
          onClick={() => setShowWhy((v) => !v)}
          aria-expanded={showWhy}
        >
          {showWhy ? 'Hide' : 'Why this?'}
        </button>
      </div>

      {showWhy && (
        <div className="rail-why">
          {theme ? (
            <>
              <p className="rail-why-line">
                Research theme: <strong>{theme.theme_name}</strong> — cited from{' '}
                {theme.evidence_count} evidence review
                {theme.evidence_count === 1 ? '' : 's'}.
              </p>
              {theme.is_placeholder && (
                <p className="rail-why-flag">Placeholder theme — not yet from scraped reviews</p>
              )}
            </>
          ) : (
            <p className="rail-why-line">
              No research theme extracted for {product.category} yet.
            </p>
          )}
          <p className="rail-why-caveat">
            Chosen by deterministic matching on {persona.name}'s never-tried
            categories against the checkout gap — not a model call.
          </p>
        </div>
      )}
    </div>
  )
}

export default function DiscoveryRail({ products, persona, onAdd }) {
  if (!products || products.length === 0) return null

  return (
    <section className="rail-section" aria-labelledby="rail-heading">
      <div className="rail-head">
        <h3 id="rail-heading" className="rail-title">More you haven't tried</h3>
        <span className="rail-hint">Scroll for more</span>
      </div>

      <div className="discovery-rail">
        {products.map((p) => (
          <RailCard key={p.id} product={p} persona={persona} onAdd={onAdd} />
        ))}
      </div>
    </section>
  )
}
