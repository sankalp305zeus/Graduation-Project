import { iconFor } from '../data/categoryIcons'

export default function CartPanel({ cartItems, subtotal, threshold }) {
  const deficit = Math.max(0, threshold - subtotal)
  const pct = Math.min(100, Math.round((subtotal / threshold) * 100))

  return (
    <div className="cart-panel">
      <h3>Your cart</h3>
      {cartItems.length === 0 ? (
        <div className="cart-empty">Nothing added yet — tap "Add" on an item above.</div>
      ) : (
        // Keyed by index too: the same product can legitimately be added
        // twice, and item.id alone made React warn about duplicate keys.
        cartItems.map((item, i) => {
          const { Icon, ink } = iconFor(item.category)
          return (
            <div className="cart-item-row" key={`${item.id}-${i}`}>
              <span className="cart-item-name">
                <Icon size={14} color={ink} strokeWidth={2} aria-hidden="true" />
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
