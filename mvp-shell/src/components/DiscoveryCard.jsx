import { useState } from 'react'
import { iconFor } from '../data/categoryIcons'
import { GROUNDING_THEME, CORPUS } from '../data/groundingTheme'

export default function DiscoveryCard({ product, persona, deficit, onAccept, onDismiss }) {
  const [showWhy, setShowWhy] = useState(false)
  const { Icon, tint, ink } = iconFor(product.category)
  const habit = persona.always_orders[0]

  return (
    <div className="discovery-card">
      <div className="discovery-eyebrow">New category opportunity: {product.category}</div>

      <div className="discovery-main">
        <div className="discovery-icon" style={{ background: tint }}>
          <Icon size={26} color={ink} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <div>
          <div className="discovery-name">{product.name}</div>
          <div className="discovery-reason">
            {persona.name} orders {habit} on repeat but has never opened{' '}
            {product.category} — this is the first moment in the journey where
            trying it costs nothing extra.
          </div>
          <div className="discovery-price">₹{product.price}</div>
        </div>
      </div>

      <div className="discovery-secondary">
        Checkout gap: ₹{deficit} from free delivery
      </div>

      <button className="why-toggle" onClick={() => setShowWhy((v) => !v)}>
        {showWhy ? 'Hide reason' : 'Why am I seeing this?'}
      </button>

      {showWhy && (
        <div className="why-body">
          <p className="why-line">
            <strong>Grounded in real review evidence.</strong> The strongest theme
            in our corpus is “{GROUNDING_THEME.theme_name}” —{' '}
            <strong>{GROUNDING_THEME.evidence_count} reviews</strong>,{' '}
            {GROUNDING_THEME.prevalence_pct}% of {GROUNDING_THEME.corpus_total.toLocaleString()}{' '}
            analyzed. Its trigger is “{GROUNDING_THEME.trigger}”, and the job
            behind it is to “{GROUNDING_THEME.core_job}”. That is exactly this
            moment — so a nudge here has to make the bill feel smaller, never
            larger.
          </p>
          <p className="why-line why-caveat">
            <strong>Prototype logic:</strong> which product gets picked is
            deterministic matching on {persona.name}'s never-tried categories
            against the checkout gap — not a model call. Our {CORPUS.themes_extracted}{' '}
            extracted themes cover delivery, pricing and service quality; none of
            them evidence per-category discovery, so we don't claim one here.
          </p>
        </div>
      )}

      <div className="discovery-actions">
        <button className="btn-accept" onClick={onAccept}>Add to cart</button>
        <button className="btn-dismiss" onClick={onDismiss}>Not now</button>
      </div>
    </div>
  )
}
