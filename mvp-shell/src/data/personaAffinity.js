/**
 * Category affinity per persona, keyed off the occupation already printed on
 * the persona card.
 *
 * WHY THIS EXISTS: ranking purely by price-fit to the checkout gap is
 * persona-independent — the same gap produces the same "best fitting" product
 * for everybody, so five of six personas were getting an identical card and an
 * identical rail. Affinity restores variation without falling back on
 * demographic guessing.
 *
 * WHAT THIS IS NOT: it is not inference from age, gender, or anything else the
 * persona hasn't declared. Occupation is stated on the card and shown in the
 * UI; this maps that declared field to categories. Nothing here reads age, and
 * nothing infers a personal attribute — the distinction guardrails.js's
 * checkNoSensitiveInference exists to protect.
 *
 * Keyed by occupation string rather than by persona id so the persona data and
 * the Supabase schema both stay untouched.
 */
export const OCCUPATION_AFFINITY = {
  'Working professional': ['Electronics Accessories', 'Personal Care & Beauty'],
  'New parent': ['Household Essentials', 'Pharmacy & Health'],
  'Student': ['Stationery & Books', 'Snacks & Beverages', 'Electronics Accessories'],
  'Pet owner': ['Home & Kitchen', 'Household Essentials'],
  'Fitness-focused professional': ['Sports & Fitness', 'Pharmacy & Health'],
  'Frequently hosts gatherings': ['Home & Kitchen', 'Snacks & Beverages', 'Toys & Gifting'],
}

// Falls back to an empty list rather than guessing, so an unrecognised
// occupation degrades to plain price-fit ordering instead of a wrong boost.
export function getAffinity(occupation) {
  return OCCUPATION_AFFINITY[occupation] ?? []
}
