import { useState } from 'react'

export default function DiscoveryCard({ product, persona, deficit, onAccept, onDismiss }) {
  const [showWhy, setShowWhy] = useState(false)

  return (
    <div className="discovery-card">
      <div className="discovery-eyebrow">You're ₹{deficit} from free delivery</div>

      <div className="discovery-main">
        <div className="discovery-emoji">{product.image_emoji}</div>
        <div>
          <div className="discovery-name">{product.name}</div>
          <div className="discovery-reason">
            From {product.category} — a category {persona.name} hasn't tried yet
          </div>
          <div className="discovery-price">₹{product.price}</div>
        </div>
      </div>

      <button className="why-toggle" onClick={() => setShowWhy((v) => !v)}>
        {showWhy ? 'Hide reason' : 'Why am I seeing this?'}
      </button>

      {showWhy && (
        <div className="why-body">
          {/* PLACEHOLDER — replace with a real citation once the discovery
              engine's theme data is wired in, e.g.:
              "Users like {persona.name} who buy {persona.always_orders[0]}
              regularly are 3x more likely to try {product.category} when
              it's offered at checkout. Based on {N} evidenced reviews." */}
          Mock reasoning for the prototype: this product is priced close to
          your delivery-fee gap and comes from a category {persona.name}
          hasn't ordered before. Once the discovery engine is connected,
          this will cite a real research theme with supporting review evidence.
        </div>
      )}

      <div className="discovery-actions">
        <button className="btn-accept" onClick={onAccept}>Add to cart</button>
        <button className="btn-dismiss" onClick={onDismiss}>Not now</button>
      </div>
    </div>
  )
}
