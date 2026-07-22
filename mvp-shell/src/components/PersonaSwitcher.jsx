export default function PersonaSwitcher({ personas, activeId, onSelect }) {
  return (
    <div className="persona-row" role="tablist" aria-label="Choose a persona">
      {personas.map((p) => (
        <button
          key={p.id}
          className={`persona-chip${p.id === activeId ? ' active' : ''}`}
          onClick={() => onSelect(p.id)}
          role="tab"
          aria-selected={p.id === activeId}
        >
          <div className="p-name">{p.name}, {p.age}</div>
          <div className="p-meta">{p.occupation} · {p.city}</div>
        </button>
      ))}
    </div>
  )
}
