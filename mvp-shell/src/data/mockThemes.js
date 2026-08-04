// Mirrors supabase/04_seed_themes.sql — keep both in sync manually, same
// convention as mockPersonas.js / mockProducts.js.
//
// IMPORTANT: every row here is is_placeholder = true in the database. These
// theme names are grounded in this project's own research patterns, but they
// are NOT derived from real scraped review text. The DiscoveryCard surfaces
// `evidence_count` next to each one, and labels the panel as placeholder
// evidence, so a demo viewer is never led to believe these are measured
// findings. When the real n8n theme extraction lands (is_placeholder=false),
// this file is replaced by a live read through /api/recommend.
export const mockThemes = [
  {
    id: 'th_001',
    category: 'Personal Care & Beauty',
    theme_name: 'Seal/expiry anxiety blocks beauty trial',
    description:
      'Users hesitate to order personal care items because they cannot verify freshness or seal integrity before paying, unlike groceries where this concern is lower.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_002',
    category: 'Electronics Accessories',
    theme_name: 'Return friction after early failure',
    description:
      'Users report electronics accessories failing shortly after purchase and describe difficulty getting a refund or replacement, eroding trust in the category.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_003',
    category: 'Pet Supplies',
    theme_name: 'Low awareness of pet supplies category',
    description:
      'Multiple users were unaware the app carried pet supplies at all, defaulting to a separate specialized app out of habit rather than distrust.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_004',
    category: 'Home & Kitchen',
    theme_name: 'Fragile-item packaging doubt',
    description:
      'Users trust the app for durable kitchen basics but doubt its packaging can protect fragile or breakable home items.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_005',
    category: 'Pharmacy & Health',
    theme_name: 'Authenticity concern limits health category to basics',
    description:
      'Users restrict pharmacy purchases to low-stakes hygiene items, citing packaging differences from trusted pharmacy sources as a reason to avoid medicine.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_006',
    category: 'Household Essentials',
    theme_name: 'Partial awareness of essentials range',
    description:
      'Some users default to routine snack/grocery orders and are surprised to learn a fuller household essentials range exists.',
    evidence_count: 2,
    is_placeholder: true,
  },
  {
    id: 'th_007',
    category: 'Toys & Gifting',
    theme_name: 'Occasion-triggered, not habitual',
    description:
      'Gifting-category orders happen almost exclusively under time pressure before a specific event, not as routine browsing — an occasion-timing opportunity, not a trust barrier.',
    evidence_count: 2,
    is_placeholder: true,
  },
]

export function findThemeForCategory(category) {
  return mockThemes.find((t) => t.category === category) ?? null
}
