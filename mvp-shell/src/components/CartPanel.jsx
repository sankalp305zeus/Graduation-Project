import { getCategoryIcon } from '../data/categoryIcons'

/**
 * The zone marker that used to live on this bar showed where the discovery
 * window sat, because that window was narrow and invisible. Discovery now runs
 * whenever the cart isn't empty, so there is no window to point at and the
 * marker, its band and its "you passed the moment" hint are all gone with it.
 */
export default function CartPanel({ cartItems, subtotal, threshold }) {
  const deficit = Math.max(0, threshold - subtotal)
  const pct = Math.min(100, Math.round((subtotal / threshold) * 100))

  return (
    <div className="cart-panel">
      <h3>Your cart</h3>
      {cartItems.length === 0 ? (
        <div className="cart-empty">
          Nothing added yet — tap "Add" on an item above, and a personalized pick
          appears below straight away.
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

      <div className="threshold-bar-track">
        <div className="threshold-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="threshold-msg">
        {deficit > 0
          ? `Add ₹${deficit} more for free delivery`
          : 'Free delivery unlocked 🎉'}
      </div>

      <div className="cart-total-row">
        <span>Subtotal</span>
        <span>₹{subtotal}</span>
      </div>
    </div>
  )
}
