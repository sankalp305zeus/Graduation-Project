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
//
// `months` is backend-only — it decides which rule fires and is never shown.
// The UI displays the occasion, not the date.
export const SEASONAL_RULES = [
  {
    id: 'ganesh-chaturthi',
    label: 'Ganesh Chaturthi',
    months: [8, 9],
    cities: ['Mumbai', 'Pune'], // strongest observance of the personas' cities
    categories: ['Home & Kitchen', 'Snacks & Beverages', 'Toys & Gifting'],
    rationale: 'Home preparation, guests and gifting all peak around the festival.',
  },
  {
    id: 'raksha-bandhan',
    label: 'Raksha Bandhan',
    months: [8],
    cities: null, // null = applies to every city
    categories: ['Toys & Gifting', 'Snacks & Beverages', 'Personal Care & Beauty'],
    rationale: 'A gifting occasion — one of the rare moments non-habitual categories get considered.',
  },
  {
    id: 'diwali',
    label: 'Diwali',
    // Lunar calendar, so the date shifts year to year and can fall in either
    // month. Both are included rather than faking precision we don't have.
    months: [10, 11],
    cities: null,
    categories: ['Home & Kitchen', 'Toys & Gifting', 'Personal Care & Beauty', 'Snacks & Beverages'],
    rationale: 'Home decoration, gifting and hosting peak across the festival week.',
  },
  {
    id: 'valentines',
    label: "Valentine's week",
    months: [2],
    cities: null,
    categories: ['Personal Care & Beauty', 'Toys & Gifting', 'Snacks & Beverages'],
    rationale: 'Gifting week — chocolates, cards and self-care see a sharp, short spike.',
  },
  {
    id: 'cricket-season',
    label: 'Cricket season',
    months: [3, 4, 5],
    cities: null,
    categories: ['Snacks & Beverages', 'Electronics Accessories', 'Home & Kitchen', 'Sports & Fitness'],
    rationale: 'Match nights drive snacking, viewing setup and a spike of interest in playing too.',
  },
  {
    id: 'monsoon',
    label: 'Monsoon season',
    // August is covered by the festival rules above, which outrank this.
    months: [6, 7, 9],
    // Chennai is deliberately excluded: its main rains come from the
    // north-east monsoon (Oct–Dec), not the south-west one. Getting this
    // wrong is the kind of detail that makes a demo feel unconsidered.
    cities: ['Mumbai', 'Pune', 'Bangalore', 'Hyderabad', 'Delhi'],
    categories: ['Household Essentials', 'Pharmacy & Health', 'Home & Kitchen'],
    rationale: 'Wet weather drives umbrellas, drying and seasonal-illness needs.',
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
