import { Sparkles } from 'lucide-react'
import { getCategoryIcon } from '../data/categoryIcons'

/**
 * The discovery card only fires while the checkout deficit sits inside
 * [discoveryMin, discoveryMax] — App.jsx's DEFICIT_MIN/MAX. Outside a demo
 * walkthrough, that's a narrow, easy-to-miss window: add one item and you're
 * still far short; add three and you can sail straight past it without ever
 * seeing a recommendation, with no explanation why.
 *
 * zoneState turns that invisible window into something the bar can show:
 *   'before'   — nothing shown yet, still approaching the zone
 *   'active'   — inside it; the discovery card is on screen below
 *   'after'    — overshot it without landing inside; explains a silent miss
 *   'unlocked' — free delivery reached
 * Bounds come from the same constants that gate the real card (passed down
 * as props from App.jsx), not re-derived here, so the marker can't drift out
 * of sync with the logic it's describing.
 */
function getZoneState(subtotal, threshold, deficit, discoveryMin, discoveryMax) {
  if (subtotal >= threshold) return 'unlocked'
  if (deficit > discoveryMax) return 'before'
  if (deficit >= discoveryMin) return 'active'
  return 'after'
}

export default function CartPanel({ cartItems, subtotal, threshold, discoveryMin, discoveryMax }) {
  const deficit = Math.max(0, threshold - subtotal)
  const pct = Math.min(100, Math.round((subtotal / threshold) * 100))
  const hasZone = discoveryMin != null && discoveryMax != null

  const zoneState = hasZone
    ? getZoneState(subtotal, threshold, deficit, discoveryMin, discoveryMax)
    : 'none'

  // Zone position as a % of the bar, from the same deficit bounds — e.g.
  // discoveryMax=80 on a ₹199 threshold starts the band at (199-80)/199 ≈ 60%.
  const zoneStartPct = hasZone ? clampPct(((threshold - discoveryMax) / threshold) * 100) : null
  const zoneEndPct = hasZone ? clampPct(((threshold - discoveryMin) / threshold) * 100) : null

  return (
    <div className="cart-panel">
      <h3>Your cart</h3>
      {cartItems.length === 0 ? (
        <div className="cart-empty">
          Nothing added yet — tap "Add" on an item above. Keep shopping and a
          personalized pick may appear as you near free delivery.
        </div>
      ) : (
        cartItems.map((item, i) => {
          const { Icon, fg, bg } = getCategoryIcon(item.category)
          return (
            <div className="cart-item-row" key={`${item.id}-${i}`}>
              <span className="cart-item-label">
                <span className="icon-tile sm" style={{ background: bg, color: fg }} aria-hidden="true">
                  <Icon size={13} strokeWidth={2.25} />
                </span>
                {item.name}
              </span>
              <span>₹{item.price}</span>
            </div>
          )
        })
      )}

      {/* Marker lives in this wrapper, not inside the track — the track keeps
          overflow:hidden so the fill's square edge is clipped to its rounded
          corners, which would also clip the marker if it were a child there. */}
      <div className="threshold-bar-wrap">
        <div className="threshold-bar-track">
          {hasZone && zoneState !== 'unlocked' && (
            <div
              className="zone-band"
              style={{ left: `${zoneStartPct}%`, width: `${zoneEndPct - zoneStartPct}%` }}
              aria-hidden="true"
            />
          )}
          <div className="threshold-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        {hasZone && zoneState !== 'unlocked' && (
          <span
            className={`zone-marker zone-marker-${zoneState}`}
            style={{ left: `${(zoneStartPct + zoneEndPct) / 2}%` }}
            aria-hidden="true"
          >
            <Sparkles size={10} strokeWidth={2.5} />
          </span>
        )}
      </div>

      <div className="threshold-msg">
        {deficit > 0
          ? `Add ₹${deficit} more for free delivery`
          : 'Free delivery unlocked 🎉'}
      </div>

      {/* Only the two states where the discovery card ISN'T already visible
          need explaining — 'active' speaks for itself once the card renders
          below, and cart-empty already carries the same message above. */}
      {cartItems.length > 0 && zoneState === 'before' && (
        <div className="zone-hint">
          <Sparkles size={12} strokeWidth={2.25} aria-hidden="true" />
          A personalized pick unlocks as you get closer to free delivery
        </div>
      )}
      {zoneState === 'after' && (
        <div className="zone-hint zone-hint-muted">
          This cart passed the personalized-pick moment — remove an item to bring it back
        </div>
      )}

      <div className="cart-total-row">
        <span>Subtotal</span>
        <span>₹{subtotal}</span>
      </div>
    </div>
  )
}

function clampPct(n) {
  return Math.max(0, Math.min(100, n))
}
