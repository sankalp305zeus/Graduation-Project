import {
  Carrot, Cookie, SprayCan, Sparkles, Baby, PawPrint,
  Cable, CookingPot, BookOpen, Pill, Gift, ShoppingBasket,
} from 'lucide-react'

// One entry per category in mockProducts / supabase seed — all 11.
// `tint` is the tile background, `ink` the icon stroke. Both are muted enough
// to sit under the yellow/green brand without competing with the discovery
// card, which is the only element that should pull the eye.
export const CATEGORY_ICONS = {
  'Groceries & Fresh Produce': { Icon: Carrot, tint: '#EAF7EC', ink: '#128A3E' },
  'Snacks & Beverages': { Icon: Cookie, tint: '#FDF1DC', ink: '#B5730E' },
  'Household Essentials': { Icon: SprayCan, tint: '#E7F2FA', ink: '#1D6FA3' },
  'Personal Care & Beauty': { Icon: Sparkles, tint: '#FAECF4', ink: '#A63C77' },
  'Baby Care': { Icon: Baby, tint: '#FDEEE9', ink: '#C05621' },
  'Pet Supplies': { Icon: PawPrint, tint: '#F1EEFA', ink: '#5B45A8' },
  'Electronics Accessories': { Icon: Cable, tint: '#ECEFF3', ink: '#43505F' },
  'Home & Kitchen': { Icon: CookingPot, tint: '#EDF4EF', ink: '#3B6E52' },
  'Stationery & Books': { Icon: BookOpen, tint: '#E9F1F7', ink: '#2E5D80' },
  'Pharmacy & Health': { Icon: Pill, tint: '#EAF6F4', ink: '#12716B' },
  'Toys & Gifting': { Icon: Gift, tint: '#FBEDEE', ink: '#B23A44' },
}

// Falls back rather than crashing if a category ever arrives from Supabase
// that isn't in the map above — a missing icon shouldn't blank the grid.
export function iconFor(category) {
  return CATEGORY_ICONS[category] ?? { Icon: ShoppingBasket, tint: '#F1EFEA', ink: '#5A5A5A' }
}
