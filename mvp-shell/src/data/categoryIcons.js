import {
  Apple,
  Cookie,
  SprayCan,
  Sparkles,
  Baby,
  PawPrint,
  Cable,
  CookingPot,
  Pill,
  NotebookPen,
  Gift,
  Dumbbell,
  Package,
} from 'lucide-react'

// One icon + tile colour per category in the taxonomy (the same strings used
// in supabase/02_seed.sql and mockProducts.js — keep in sync).
// Colours are tints of the existing brand palette in index.css rather than a
// new palette, so the tiles read as part of the same app.
//
// `short` is the label shown in the category chip on product cards. Grid cards
// give a chip only ~80px of inner width, and just 1 of the 12 full category
// names fits in that — "Groceries & Fresh Produce" alone needs 155px. Full
// names would ellipsis to nonsense ("Grocer…"), and wrapping would give some
// cards a two-line chip and others one line, breaking the grid's rhythm.
// These short forms all fit on one line at the narrowest card. Keep any new
// entry under ~80px at 11px/600, or the chip will start truncating again.
export const CATEGORY_ICONS = {
  'Groceries & Fresh Produce': { Icon: Apple, fg: '#128A3E', bg: '#E4F6EA' , short: 'Groceries' },
  'Snacks & Beverages': { Icon: Cookie, fg: '#B26A00', bg: '#FFF1D6' , short: 'Snacks' },
  'Household Essentials': { Icon: SprayCan, fg: '#0F6E86', bg: '#E1F4F8' , short: 'Household' },
  // "Personal" not "Beauty": beauty drops soap, shampoo and hygiene, which is
  // most of what this category actually holds.
  'Personal Care & Beauty': { Icon: Sparkles, fg: '#A63D7B', bg: '#FBE8F3' , short: 'Personal' },
  'Baby Care': { Icon: Baby, fg: '#C2683C', bg: '#FDEDE3' , short: 'Baby Care' },
  'Pet Supplies': { Icon: PawPrint, fg: '#7A5AA8', bg: '#F0EAFA' , short: 'Pet Supplies' },
  'Electronics Accessories': { Icon: Cable, fg: '#345BA8', bg: '#E6EDFB' , short: 'Electronics' },
  'Home & Kitchen': { Icon: CookingPot, fg: '#8A6A1F', bg: '#F7EFDA' , short: 'Home' },
  'Pharmacy & Health': { Icon: Pill, fg: '#B23A48', bg: '#FCE9EB' , short: 'Pharmacy' },
  'Stationery & Books': { Icon: NotebookPen, fg: '#3F6C5F', bg: '#E8F2EE' , short: 'Stationery' },
  'Toys & Gifting': { Icon: Gift, fg: '#C2456B', bg: '#FCE7EE' , short: 'Gifting' },
  'Sports & Fitness': { Icon: Dumbbell, fg: '#1F6F6B', bg: '#E4F3F2' , short: 'Fitness' },
}

// Unknown category -> neutral tile rather than a crash or an empty gap.
export const FALLBACK_ICON = { Icon: Package, fg: '#5A5A5A', bg: '#F0EDE6', short: 'Other' }

export function getCategoryIcon(category) {
  return CATEGORY_ICONS[category] ?? FALLBACK_ICON
}
