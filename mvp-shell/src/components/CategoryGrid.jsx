import { getCategoryIcon } from '../data/categoryIcons'

export default function CategoryGrid({ products, persona, onAdd }) {
  // Show products from the active persona's usual categories — this is
  // their "home screen" as if the app already knows their habits.
  const visible = products.filter((p) => persona.always_orders.includes(p.category))

  return (
    <>
      <div className="section-label">{persona.name}'s usual picks</div>
      <div className="category-grid">
        {visible.map((p, i) => {
          const { Icon, fg, bg, short } = getCategoryIcon(p.category)
          return (
            <div
              className="product-card"
              key={p.id}
              /* Staggered entrance; capped so a long grid doesn't crawl. */
              style={{ animationDelay: `${Math.min(i, 8) * 35}ms` }}
            >
              <div className="photo-tile" style={{ background: bg, color: fg }} aria-hidden="true">
                <Icon size={26} strokeWidth={1.75} />
              </div>
              {/* Short label, full name for assistive tech and hover. */}
              <span className="cat-chip" style={{ background: bg, color: fg }} title={p.category}>
                {short}
              </span>
              <div className="p-name">{p.name}</div>
              <div className="p-price">₹{p.price}</div>
              <button className="add-btn" onClick={() => onAdd(p)}>Add</button>
            </div>
          )
        })}
      </div>
    </>
  )
}
