export default function PersonaSwitcher({ personas, activeId, onSelect }) {
  const active = personas.find((p) => p.id === activeId)

  return (
    <div className="persona-block">
      {active && (
        <div className="persona-pill">
          <span className="persona-pill-initial" aria-hidden="true">
            {active.name.charAt(0)}
          </span>
          <span className="persona-pill-text">
            <span className="persona-pill-name">{active.name}, {active.age}</span>
            <span className="persona-pill-meta">{active.occupation} · {active.city}</span>
          </span>
        </div>
      )}

      <div className="persona-row" role="tablist" aria-label="Choose a persona">
        {personas.map((p) => (
          <button
            key={p.id}
            className={`persona-chip${p.id === activeId ? ' active' : ''}`}
            onClick={() => onSelect(p.id)}
            role="tab"
            aria-selected={p.id === activeId}
          >
            {p.name}
          </button>
        ))}
      </div>
    </div>
  )
}
