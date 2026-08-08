import { CalendarDays } from 'lucide-react'
import { getCategoryIcon } from '../data/categoryIcons'

/**
 * Seasonal / festival suggestions.
 *
 * Renders independently of the free-delivery discovery window — including
 * above the threshold, where the discovery card has nothing to say but the
 * occasion still does. That's the point: a cart past ₹199 currently ends in
 * silence, and an occasion is a legitimate reason to surface a category that
 * price-fit logic can't reach.
 *
 * The provenance label is not decoration. These come from a hand-curated
 * calendar (data/seasonalContext.js), not the review corpus, and the UI has
 * to say so — see the header comment in that file.
 */
export default function SeasonalRail({ context, products }) {
  if (!context || !products || products.length === 0) return null

  return (
    <section className="seasonal-section" aria-labelledby="seasonal-heading">
      <div className="seasonal-head">
        <div className="seasonal-title-row">
          <CalendarDays size={14} strokeWidth={2.2} aria-hidden="true" />
          {/* Occasion only — the month that triggered this stays backend-side. */}
          <h3 id="seasonal-heading" className="seasonal-title">
            {context.label}
          </h3>
        </div>
        <p className="seasonal-rationale">{context.rationale}</p>
      </div>

      <div className="seasonal-rail">
        {products.map((p, i) => {
          const { Icon, fg, bg, short } = getCategoryIcon(p.category)
          return (
            <div
              className="seasonal-card"
              key={p.id}
              style={{ animationDelay: `${i * 55}ms` }}
            >
              <div className="photo-tile lg" style={{ background: bg, color: fg }} aria-hidden="true">
                <Icon size={26} strokeWidth={1.75} />
              </div>
              <span className="cat-chip" style={{ background: bg, color: fg }} title={p.category}>
                {short}
              </span>
              <div className="rail-name">{p.name}</div>
              <div className="rail-price">₹{p.price}</div>
            </div>
          )
        })}
      </div>

      {/* Provenance. Deliberately plain and always visible — this is the line
          that keeps editorial suggestions distinguishable from the measured
          corpus evidence shown on the discovery card above. */}
      <p className="seasonal-provenance">
        Seasonal suggestion from a curated calendar — not from the review corpus,
        and not evidence-validated.
      </p>
    </section>
  )
}
