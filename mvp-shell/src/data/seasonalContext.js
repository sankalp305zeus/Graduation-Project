/**
 * Seasonal and festival context rules.
 *
 * ⚠️ PROVENANCE — READ BEFORE EXTENDING OR CITING THIS FILE.
 *
 * This is EDITORIAL CONTENT: a hand-curated calendar written for the
 * prototype. It is NOT derived from the review corpus, not extracted by the
 * n8n workflow, and not validated by the Evidence Validator. Nothing here
 * carries evidence_ids, prevalence, or a hallucination rate, because none of
 * those concepts apply to it.
 *
 * Everywhere this surfaces in the UI it must stay visibly labelled as a
 * seasonal/editorial suggestion, and must never be presented next to the
 * measured corpus figures (67 reviews, 5.68% prevalence) in a way that
 * implies shared provenance. The whole project's credibility rests on that
 * line staying clean — see docs/ai-limitations-and-mitigations.md.
 *
 * Live weather feeds are deliberately not used: the demo must render
 * identically offline and months from now, and a live dependency would make
 * the prototype fail in exactly the setting it's shown in.
 */

// Ordered most-specific first. The first rule matching city + month wins, so
// a city-specific festival outranks a national one, which outranks weather.
export const SEASONAL_RULES = [
  {
    id: 'ganesh-chaturthi',
    label: 'Ganesh Chaturthi',
    window: 'Aug–Sep',
    months: [8, 9],
    cities: ['Mumbai', 'Pune'], // strongest observance of the personas' cities
    categories: ['Home & Kitchen', 'Snacks & Beverages', 'Toys & Gifting'],
    rationale: 'Home preparation, guests and gifting peak around the festival.',
  },
  {
    id: 'raksha-bandhan',
    label: 'Raksha Bandhan',
    window: 'August',
    months: [8],
    cities: null, // null = applies to every city
    categories: ['Toys & Gifting', 'Snacks & Beverages', 'Personal Care & Beauty'],
    rationale: 'Gifting occasion — a rare moment when non-habitual categories get considered.',
  },
  {
    id: 'sw-monsoon',
    label: 'Monsoon season',
    window: 'Jun–Sep',
    months: [6, 7, 8, 9],
    // Chennai is deliberately excluded: its main rains come from the
    // north-east monsoon (Oct–Dec), not the south-west one. Getting this
    // wrong is the kind of detail that makes a demo feel unconsidered.
    cities: ['Mumbai', 'Pune', 'Bangalore', 'Hyderabad', 'Delhi'],
    categories: ['Household Essentials', 'Pharmacy & Health', 'Home & Kitchen'],
    rationale: 'Damp weather drives cleaning, drying and seasonal-illness needs.',
  },
  {
    id: 'ne-monsoon',
    label: 'North-east monsoon',
    window: 'Oct–Dec',
    months: [10, 11, 12],
    cities: ['Chennai'],
    categories: ['Household Essentials', 'Pharmacy & Health', 'Home & Kitchen'],
    rationale: 'Chennai’s main rainy season, offset from the rest of the country.',
  },
  {
    id: 'winter',
    label: 'Winter',
    window: 'Dec–Jan',
    months: [12, 1],
    cities: ['Delhi'],
    categories: ['Personal Care & Beauty', 'Pharmacy & Health', 'Home & Kitchen'],
    rationale: 'Dry cold drives skincare and seasonal-health demand.',
  },
]

/**
 * Returns the single most specific active rule for a city and date, or null.
 * Date is injectable so this stays testable and reviewable rather than being
 * silently coupled to whenever the page happens to be opened.
 */
export function getSeasonalContext(city, date = new Date()) {
  const month = date.getMonth() + 1
  return (
    SEASONAL_RULES.find(
      (r) => r.months.includes(month) && (r.cities === null || r.cities.includes(city))
    ) ?? null
  )
}
