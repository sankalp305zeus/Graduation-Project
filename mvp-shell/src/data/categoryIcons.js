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

// One icon + tile colour per category in the 11-category taxonomy (the same
// strings used in supabase/02_seed.sql and mockProducts.js — keep in sync).
// Colours are tints of the existing brand palette in index.css rather than a
// new palette, so the tiles read as part of the same app.
export const CATEGORY_ICONS = {
  'Groceries & Fresh Produce': { Icon: Apple, fg: '#128A3E', bg: '#E4F6EA' },
  'Snacks & Beverages': { Icon: Cookie, fg: '#B26A00', bg: '#FFF1D6' },
  'Household Essentials': { Icon: SprayCan, fg: '#0F6E86', bg: '#E1F4F8' },
  'Personal Care & Beauty': { Icon: Sparkles, fg: '#A63D7B', bg: '#FBE8F3' },
  'Baby Care': { Icon: Baby, fg: '#C2683C', bg: '#FDEDE3' },
  'Pet Supplies': { Icon: PawPrint, fg: '#7A5AA8', bg: '#F0EAFA' },
  'Electronics Accessories': { Icon: Cable, fg: '#345BA8', bg: '#E6EDFB' },
  'Home & Kitchen': { Icon: CookingPot, fg: '#8A6A1F', bg: '#F7EFDA' },
  'Pharmacy & Health': { Icon: Pill, fg: '#B23A48', bg: '#FCE9EB' },
  'Stationery & Books': { Icon: NotebookPen, fg: '#3F6C5F', bg: '#E8F2EE' },
  'Toys & Gifting': { Icon: Gift, fg: '#C2456B', bg: '#FCE7EE' },
  'Sports & Fitness': { Icon: Dumbbell, fg: '#1F6F6B', bg: '#E4F3F2' },
}

// Unknown category -> neutral tile rather than a crash or an empty gap.
export const FALLBACK_ICON = { Icon: Package, fg: '#5A5A5A', bg: '#F0EDE6' }

export function getCategoryIcon(category) {
  return CATEGORY_ICONS[category] ?? FALLBACK_ICON
}
