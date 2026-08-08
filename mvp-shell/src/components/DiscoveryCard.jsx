import { useState } from 'react'
import { Sparkle } from 'lucide-react'
import { getCategoryIcon } from '../data/categoryIcons'
import { findThemeForCategory } from '../data/mockThemes'
import { GROUNDING_THEME, CORPUS } from '../data/groundingTheme'

export default function DiscoveryCard({ product, persona, deficit, onAccept, onDismiss }) {
  const [showWhy, setShowWhy] = useState(false)
  const { Icon, fg, bg } = getCategoryIcon(product.category)
  const theme = findThemeForCategory(product.category)
  const habit = persona.always_orders[0]

  return (
    <div className="discovery-card">
      <div className="discovery-eyebrow">
        <Sparkle size={13} strokeWidth={2.5} aria-hidden="true" />
        New category opportunity
      </div>

      <div className="discovery-headline">{product.category}</div>
      <div className="discovery-subline">
        {persona.name} orders {habit} regularly — this category isn't part of that usual basket.
        {/* Only meaningful while a gap remains; past the threshold the card
            stands on the category opportunity alone. */}
        {deficit > 0 && (
          <span className="discovery-deficit">₹{deficit} from free delivery</span>
        )}
      </div>

      <div className="discovery-main">
        <div className="icon-tile lg" style={{ background: bg, color: fg }} aria-hidden="true">
          <Icon size={26} strokeWidth={1.9} />
        </div>
        <div>
          <div className="discovery-name">{product.name}</div>
          {theme && (
            <div className="discovery-reason">
              Research theme: <strong>{theme.theme_name}</strong>
            </div>
          )}
          <div className="discovery-price">₹{product.price}</div>
        </div>
      </div>

      <button
        className="why-toggle"
        onClick={() => setShowWhy((v) => !v)}
        aria-expanded={showWhy}
      >
        {showWhy ? 'Hide reason' : 'Why am I seeing this?'}
      </button>

      {showWhy && (
        <div className="why-body">
          {theme ? (
            <>
              <div className="why-theme">{theme.theme_name}</div>
              <p>{theme.description}</p>
              <div className="why-evidence">
                Cited from {theme.evidence_count} evidence review
                {theme.evidence_count === 1 ? '' : 's'} in the {product.category} cluster.
              </div>
              {theme.is_placeholder && (
                <>
                  <div className="evidence-flag">
                    Seeded theme — not from scraped reviews
                  </div>
                  {/* Explains the badge directly above it, rather than being
                      appended to the mechanism disclosure at the bottom where
                      it read as an apology for the work. */}
                  <p className="evidence-flag-note">
                    Review corpora capture what went wrong, not what a user never
                    considered — so category-level evidence comes from primary
                    research rather than scraped reviews.
                  </p>
                </>
              )}
            </>
          ) : (
            <>
              <p>
                No research theme has been extracted for {product.category} yet, so this
                recommendation rests on the pricing fit alone (₹{product.price} against a
                ₹{deficit} delivery gap).
              </p>
              <div className="evidence-flag">No theme evidence available for this category</div>
            </>
          )}

          {/* Everything above is per-category and placeholder. This block is
              the measured half: real output from the n8n extraction run, so
              the panel always shows at least one number that was actually
              observed rather than authored. See data/groundingTheme.js. */}
          <div className="why-measured">
            <div className="why-measured-label">Measured in the real corpus</div>
            <p>
              The strongest theme across {CORPUS.reviews_analyzed.toLocaleString()}{' '}
              analyzed reviews is “{GROUNDING_THEME.theme_name}” —{' '}
              <strong>{GROUNDING_THEME.evidence_count} reviews</strong>,{' '}
              {GROUNDING_THEME.prevalence_pct}% prevalence. Its trigger is “
              {GROUNDING_THEME.trigger}”, which is this exact moment — so a nudge
              here has to make the bill feel smaller, never larger.
            </p>
          </div>

          {/* Third and last block: how the product itself was chosen. Kept
              separate from both evidence blocks above, because neither of
              them justifies the pick — without this line a reader can
              reasonably infer a model made the choice. It did not. */}
          <div className="why-caveat">
            <strong>How this pick was made:</strong>{' '}
            {deficit > 0
              ? `deterministic price-fit against the ₹${deficit} checkout gap, weighted toward ${persona.name}'s stated interests`
              : `deterministic ranking weighted toward ${persona.name}'s stated interests`}
            , limited to categories outside their usual basket — prototype
            logic, not a model call.
          </div>
        </div>
      )}

      <div className="discovery-actions">
        <button className="btn-accept" onClick={onAccept}>Add to cart</button>
        <button className="btn-dismiss" onClick={onDismiss}>Not now</button>
      </div>
    </div>
  )
}
