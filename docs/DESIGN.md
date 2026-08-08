# Design decisions

Design rationale for the `mvp-shell` prototype, collected from where it
already lives — in code comments next to the thing it explains.

**This documents decisions already made. It is not a spec for new work**, and
nothing here was invented while writing it: every section cites the file the
reasoning came from, so the code stays the source of truth. Where the code and
this document disagree, the code is right and this document is stale.

A theme runs through most of it: the prototype makes claims about evidence, and
almost every design decision below exists to keep those claims honest — to stop
the interface implying something the data doesn't support.

---

## 1. Photo tiles, not stock photography

**Decided:** product tiles present the category icon as a product thumbnail
would be presented — larger, squared, soft shadow, subtle inner highlight — at
72px in the grid and 56px on cards. No photography is used.

**Why:** every product in the catalog is a real brand (Amul, Lays, Nivea,
Harpic, Britannia). A generic stock photo placed under a branded product name
is fabricated product imagery, and it would also introduce an external CDN
dependency the demo doesn't need.

> No stock photography: every product here is a real brand (Amul, Lays,
> Nivea…), so a generic Unsplash shot under a branded name would be fabricated
> product imagery. Instead the category icon is presented the way a product
> thumbnail would be […] so tiles read as imagery, not bare icons.

**Source:** [`mvp-shell/src/index.css`](../mvp-shell/src/index.css) — the
`.photo-tile` rule.

---

## 2. The demo-mode badge is green, not amber or red

**Decided:** the "Demo mode — mock data (Supabase not connected)" badge uses a
white pill with a small **green** dot (`--green`), not a warning colour.

**Why:** running on mock data is an intentional state of the prototype, not an
error. Styling it as a warning would misrepresent it. The constraint attached
to this decision matters as much as the colour: restyling must never make the
disclosure quieter *in substance* — the wording stays fully explicit.

> Deliberately NOT amber/red: this is an intentional state of the prototype,
> not an error. The wording stays fully explicit — restyling this must never
> make the disclosure quieter in substance.

**Source:** [`mvp-shell/src/index.css`](../mvp-shell/src/index.css) — the
`.demo-badge` rule.

---

## 3. The deterministic-logic line must never be trimmed

**Decided:** every "Why this?" panel — on the discovery card and on each rail
card — carries a line stating that the product was chosen by deterministic
matching, not by a model. It is not shortened or dropped for space.

**Why:** the panel above it cites review counts and prevalence percentages. A
reader who sees evidence and a recommendation together can reasonably infer the
model produced the recommendation. It did not. Without this line the interface
implies a capability the prototype doesn't have.

This has been lost once already — it disappeared during a merge and had to be
restored — which is why the warning is written into both the component and the
stylesheet.

> This is deliberate and must not be trimmed for space: without it a reader can
> reasonably infer a model chose these products. It didn't — the pick is
> arithmetic on price against the checkout gap.

**Sources:**
[`mvp-shell/src/components/DiscoveryRail.jsx`](../mvp-shell/src/components/DiscoveryRail.jsx)
(header comment) and [`mvp-shell/src/index.css`](../mvp-shell/src/index.css)
(above `.rail-why-caveat`).

---

## 4. Affinity from declared occupation, never inferred demographics

**Decided:** recommendation ranking is affinity first, price-fit second.
Affinity maps the persona's **occupation** — a field already printed on the
persona card and visible in the UI — to categories.

**Why it exists:** ranking on price-fit alone is persona-independent. The same
checkout gap produces the same "best fitting" product for everyone, which left
five of six personas seeing an identical card *and* an identical rail.

**Where the boundary sits:** nothing reads age, gender, or anything the persona
hasn't declared. This is the distinction `guardrails.js`'s
`checkNoSensitiveInference` exists to protect — inferring a personal attribute
is a different act from using a stated one. Keyed by occupation string rather
than persona id, so persona data and the Supabase schema stay untouched, and an
unrecognised occupation degrades to plain price-fit rather than a wrong boost.

> WHAT THIS IS NOT: it is not inference from age, gender, or anything else the
> persona hasn't declared. Occupation is stated on the card and shown in the
> UI; this maps that declared field to categories.

**Source:**
[`mvp-shell/src/data/personaAffinity.js`](../mvp-shell/src/data/personaAffinity.js).

---

## 5. Seasonal content is editorial, and labelled as such

**Decided:** the seasonal/festival calendar is hand-curated editorial content.
It is never presented as research output, and the UI carries a permanent
provenance line saying so.

**Why:** the calendar carries no `evidence_ids`, no prevalence, and no
hallucination rate, because those concepts don't apply to it. It was not
extracted by the n8n workflow and never passed the Evidence Validator. Placing
it beside the measured corpus figures without that distinction would let
editorial suggestions borrow credibility from validated data.

**Also decided:** no live weather feed. The demo must render identically
offline and months from now; a live dependency would fail in exactly the
setting the prototype gets shown in.

> Everywhere this surfaces in the UI it must stay visibly labelled as a
> seasonal/editorial suggestion, and must never be presented next to the
> measured corpus figures (67 reviews, 5.68% prevalence) in a way that implies
> shared provenance.

**Source:**
[`mvp-shell/src/data/seasonalContext.js`](../mvp-shell/src/data/seasonalContext.js)
— header block.

---

## 6. Design tokens as they actually stand

Read directly from
[`mvp-shell/src/index.css`](../mvp-shell/src/index.css). This section describes
what is true, including where the system is inconsistent.

### Colour — 9 variables in `:root`, all in active use

| Token | Value | Role |
|---|---|---|
| `--yellow` | `#F8CB46` | brand / header, discovery card border |
| `--yellow-soft` | `#FFF3D6` | discovery card background |
| `--green` | `#128A3E` | primary actions, progress fill, demo dot |
| `--green-dark` | `#0D6B2F` | pressed states, "measured" evidence tier |
| `--ink` | `#1A1A1A` | primary text |
| `--ink-soft` | `#5A5A5A` | secondary text |
| `--bg-warm` | `#FFFDF8` | app background inside the phone frame |
| `--card-bg` | `#FFFFFF` | card surfaces |
| `--border` | `#EFE9DC` | dividers and card borders |

### Type — a two-family split, not Inter alone

- **Poppins** (500/600/700) — `h1, h2, h3, .display`
- **Inter** (400/500/600) — body and everything else

Both are loaded from Google Fonts in
[`mvp-shell/index.html`](../mvp-shell/index.html), with
`-apple-system, sans-serif` as fallback.

### Radius — the tokens are dead

`--radius-sm: 8px`, `--radius-md: 14px` and `--radius-lg: 20px` are declared in
`:root` and referenced **zero times**. Successive refactors replaced every use
with hardcoded values, and the actual radii in the stylesheet are **12px**
(cards, tiles), **14px** (cart panel, large tiles) and **16px** (discovery
card), plus `999px` for pills.

Recorded as a known inconsistency rather than tidied away: either the tokens
should be adopted or deleted, and pretending they are in use would misdescribe
the codebase.

### Spacing — ad-hoc, not a scale

There are no spacing tokens. Padding and margin use **20 distinct pixel
values** (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 16, 18, 20, 22, 24, 26,
32). This is an accumulated set, not a designed scale, and is documented as
such rather than reverse-engineered into a system that was never decided.

---

## 7. The evidence-badge system — four tiers, not three

The most distinctive pattern in the product. Every claim the interface makes
is colour-coded by **where it came from**, so a reader can tell at a glance
what is measured, what is seeded, and what is neither.

| Tier | Class | Colour | Means |
|---|---|---|---|
| **Measured** | `.why-measured` | green (`--green-dark`) | Real corpus output — 67 reviews, 5.68% prevalence, evidence-validated |
| **Seeded** | `.evidence-flag` | amber (`#FDF3E3` / `#E8CFA0` / `#8A5B12`) | Placeholder theme, not from scraped reviews |
| **Mechanism** | `.why-caveat`, `.rail-why-caveat` | neutral grey (`#6E6A62`) | How the pick was made — deterministic, not a model call |
| **Editorial** | `.seasonal-provenance` | muted secondary | Curated calendar — not corpus-derived, not validated |

The colour choices are deliberate opposites, and the reasoning is recorded in
the stylesheet:

> Neutral grey against evidence-flag's amber and why-measured's green, because
> it is neither a warning nor a finding — it discloses the mechanism behind
> the pick.

**Note on tier count:** the first three tiers sit together inside the discovery
card's "Why this?" panel and are easy to read as a three-tier system. The
fourth, `.seasonal-provenance`, lives in a separate section but does the same
job for editorial content — so the pattern is **four-tier**, not three.
Anything added later that makes a claim should pick one of these four tiers
rather than introducing an unlabelled fifth style.

**Sources:**
[`mvp-shell/src/components/DiscoveryCard.jsx`](../mvp-shell/src/components/DiscoveryCard.jsx),
[`mvp-shell/src/components/DiscoveryRail.jsx`](../mvp-shell/src/components/DiscoveryRail.jsx),
[`mvp-shell/src/components/SeasonalRail.jsx`](../mvp-shell/src/components/SeasonalRail.jsx),
and the corresponding rules in
[`mvp-shell/src/index.css`](../mvp-shell/src/index.css).

---

## Related

- [`ai-limitations-and-mitigations.md`](ai-limitations-and-mitigations.md) — what the system deliberately does not claim
- [`ai-architecture.md`](ai-architecture.md) — pipeline and agent architecture
- [`../README.md`](../README.md) — what is real vs. mock in the current build
