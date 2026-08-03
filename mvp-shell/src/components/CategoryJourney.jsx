import { getCategoryIcon } from '../data/categoryIcons'

// SIMULATED PROJECTION — NOT TELEMETRY.
//
// This component illustrates how a persona's category mix could widen over
// time if the discovery recommendation is accepted. There is no longitudinal
// event data behind it: the earlier markers are the persona's declared
// always_orders (from seed data) spread across the last few months, and the
// final marker is whatever the recommender is surfacing right now. The UI
// says "Simulated projection" on the card itself so this is never read as a
// measured user history. Replace with real `events` table aggregates if and
// when the prototype accumulates actual usage.

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

// Labels for the last `count` months, oldest first, ending on the current month.
function recentMonths(count, now = new Date()) {
  const out = []
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    out.push(MONTH_NAMES[d.getMonth()])
  }
  return out
}

export default function CategoryJourney({ persona, recommendedCategory }) {
  // Established categories come straight from the persona's habits; cap at 3
  // so the timeline stays at the 3-4 markers the layout is designed for.
  const established = persona.always_orders.slice(0, 3)
  const projected = recommendedCategory ?? persona.never_tried[0] ?? null

  const steps = [
    ...established.map((category) => ({ category, kind: 'established' })),
    ...(projected
      ? [{ category: projected, kind: recommendedCategory ? 'recommended' : 'projected' }]
      : []),
  ]

  if (steps.length < 2) return null

  const months = recentMonths(steps.length)

  return (
    <div className="journey-card">
      <div className="journey-head">
        <div className="journey-title">{persona.name}'s category journey</div>
        <span className="journey-sim-badge">Simulated projection</span>
      </div>

      <div className="journey-track" role="list">
        {steps.map((step, i) => {
          const { Icon, fg, bg } = getCategoryIcon(step.category)
          const isLast = i === steps.length - 1
          return (
            <div
              className={`journey-step${isLast ? ' is-latest' : ''}`}
              role="listitem"
              key={`${step.category}-${i}`}
            >
              <div
                className="icon-tile journey-dot"
                style={{ background: bg, color: fg }}
                aria-hidden="true"
              >
                <Icon size={16} strokeWidth={2} />
              </div>
              <div className="journey-month">{months[i]}</div>
              <div className="journey-cat">{step.category}</div>
              {isLast && (
                <div className="journey-tag">
                  {step.kind === 'recommended'
                    ? 'Added via AI recommendation'
                    : 'Projected next unlock'}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="journey-note">
        Illustrative only — built from this persona's seeded habits, not from
        recorded user activity.
      </div>
    </div>
  )
}
