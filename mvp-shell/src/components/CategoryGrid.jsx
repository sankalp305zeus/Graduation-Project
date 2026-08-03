import { getCategoryIcon } from '../data/categoryIcons'

export default function CategoryGrid({ products, persona, onAdd }) {
  // Show products from the active persona's usual categories — this is
  // their "home screen" as if the app already knows their habits.
  const visible = products.filter((p) => persona.always_orders.includes(p.category))

  return (
    <>
      <div className="section-label">{persona.name}'s usual picks</div>
      <div className="category-grid">
        {visible.map((p) => {
          const { Icon, fg, bg } = getCategoryIcon(p.category)
          return (
            <div className="product-card" key={p.id}>
              <div className="icon-tile" style={{ background: bg, color: fg }} aria-hidden="true">
                <Icon size={20} strokeWidth={2} />
              </div>
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
