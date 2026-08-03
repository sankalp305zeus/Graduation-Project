import { useState } from 'react'
import { Sparkle } from 'lucide-react'
import { getCategoryIcon } from '../data/categoryIcons'
import { findThemeForCategory } from '../data/mockThemes'

export default function DiscoveryCard({ product, persona, deficit, onAccept, onDismiss }) {
  const [showWhy, setShowWhy] = useState(false)
  const { Icon, fg, bg } = getCategoryIcon(product.category)
  const theme = findThemeForCategory(product.category)
  const habit = persona.always_orders[0]

  return (
    <div className="discovery-card">
      <div className="discovery-eyebrow">
        <Sparkle size={13} strokeWidth={2.5} aria-hidden="true" />
        New category opportunity
      </div>

      <div className="discovery-headline">{product.category}</div>
      <div className="discovery-subline">
        {persona.name} orders {habit} regularly but has never tried this category.
        <span className="discovery-deficit">₹{deficit} from free delivery</span>
      </div>

      <div className="discovery-main">
        <div className="icon-tile lg" style={{ background: bg, color: fg }} aria-hidden="true">
          <Icon size={26} strokeWidth={1.9} />
        </div>
        <div>
          <div className="discovery-name">{product.name}</div>
          {theme && (
            <div className="discovery-reason">
              Research theme: <strong>{theme.theme_name}</strong>
            </div>
          )}
          <div className="discovery-price">₹{product.price}</div>
        </div>
      </div>

      <button className="why-toggle" onClick={() => setShowWhy((v) => !v)}>
        {showWhy ? 'Hide reason' : 'Why am I seeing this?'}
      </button>

      {showWhy && (
        <div className="why-body">
          {theme ? (
            <>
              <div className="why-theme">{theme.theme_name}</div>
              <p>{theme.description}</p>
              <div className="why-evidence">
                Cited from {theme.evidence_count} evidence review
                {theme.evidence_count === 1 ? '' : 's'} in the {product.category} cluster.
              </div>
              {theme.is_placeholder && (
                <div className="evidence-flag">
                  Placeholder theme — not yet from scraped reviews
                </div>
              )}
            </>
          ) : (
            <>
              <p>
                No research theme has been extracted for {product.category} yet, so this
                recommendation rests on the pricing fit alone (₹{product.price} against a
                ₹{deficit} delivery gap).
              </p>
              <div className="evidence-flag">No theme evidence available for this category</div>
            </>
          )}
        </div>
      )}

      <div className="discovery-actions">
        <button className="btn-accept" onClick={onAccept}>Add to cart</button>
        <button className="btn-dismiss" onClick={onDismiss}>Not now</button>
      </div>
    </div>
  )
}
