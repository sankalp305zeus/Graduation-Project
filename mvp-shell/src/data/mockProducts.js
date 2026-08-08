// Mirrors supabase/seed.sql — kept in sync manually.
//
// Product names are generic by design — real brand names would make stock
// product photography fabricated imagery for a named brand.
export const mockProducts = [
  { id: 'p01', name: 'Milk 1L', category: 'Groceries & Fresh Produce', price: 66, image_emoji: '🥛' },
  { id: 'p02', name: 'Fresh Bananas (dozen)', category: 'Groceries & Fresh Produce', price: 60, image_emoji: '🍌' },
  { id: 'p03', name: 'Tomatoes 1kg', category: 'Groceries & Fresh Produce', price: 40, image_emoji: '🍅' },

  { id: 'p04', name: 'Potato Chips Party Pack', category: 'Snacks & Beverages', price: 50, image_emoji: '🍟' },
  { id: 'p05', name: 'Cola 750ml', category: 'Snacks & Beverages', price: 45, image_emoji: '🥤' },
  { id: 'p06', name: 'Biscuits', category: 'Snacks & Beverages', price: 35, image_emoji: '🍪' },

  { id: 'p07', name: 'Dishwash Bar', category: 'Household Essentials', price: 25, image_emoji: '🧽' },
  { id: 'p08', name: 'Toilet Cleaner', category: 'Household Essentials', price: 55, image_emoji: '🧴' },
  { id: 'p09', name: 'Tissue Box', category: 'Household Essentials', price: 70, image_emoji: '🧻' },

  { id: 'p10', name: 'Face Wash 100ml', category: 'Personal Care & Beauty', price: 199, image_emoji: '🧴' },
  { id: 'p11', name: 'Travel-size Moisturizer 30ml', category: 'Personal Care & Beauty', price: 75, image_emoji: '🧴' },
  { id: 'p12', name: 'Lip Balm', category: 'Personal Care & Beauty', price: 45, image_emoji: '💄' },

  { id: 'p13', name: 'Diapers (small pack)', category: 'Baby Care', price: 249, image_emoji: '🍼' },
  { id: 'p14', name: 'Baby Wipes', category: 'Baby Care', price: 79, image_emoji: '🧴' },
  { id: 'p15', name: 'Baby Lotion 100ml', category: 'Baby Care', price: 65, image_emoji: '🧴' },

  { id: 'p16', name: 'Dog Food 1kg', category: 'Pet Supplies', price: 210, image_emoji: '🐕' },
  { id: 'p17', name: 'Cat Treats', category: 'Pet Supplies', price: 58, image_emoji: '🐱' },
  { id: 'p18', name: 'Pet Shampoo', category: 'Pet Supplies', price: 72, image_emoji: '🐾' },

  { id: 'p19', name: 'USB-C Charging Cable', category: 'Electronics Accessories', price: 249, image_emoji: '🔌' },
  { id: 'p20', name: 'Wired Earphones', category: 'Electronics Accessories', price: 68, image_emoji: '🎧' },
  { id: 'p21', name: 'Phone Stand', category: 'Electronics Accessories', price: 55, image_emoji: '📱' },

  { id: 'p22', name: 'Steel Storage Container', category: 'Home & Kitchen', price: 79, image_emoji: '🍱' },
  { id: 'p23', name: 'Kitchen Towel Set', category: 'Home & Kitchen', price: 62, image_emoji: '🧺' },
  { id: 'p24', name: 'Non-stick Ladle', category: 'Home & Kitchen', price: 45, image_emoji: '🥄' },

  { id: 'p25', name: 'Notebook Set', category: 'Stationery & Books', price: 60, image_emoji: '📓' },
  { id: 'p26', name: 'Gel Pen Pack', category: 'Stationery & Books', price: 40, image_emoji: '🖊️' },
  { id: 'p27', name: 'Sticky Notes', category: 'Stationery & Books', price: 35, image_emoji: '📝' },

  { id: 'p28', name: 'Multivitamin Strip', category: 'Pharmacy & Health', price: 75, image_emoji: '💊' },
  { id: 'p29', name: 'Hand Sanitizer 100ml', category: 'Pharmacy & Health', price: 49, image_emoji: '🧴' },
  { id: 'p30', name: 'Protein Bar Pack', category: 'Pharmacy & Health', price: 68, image_emoji: '🍫' },

  { id: 'p31', name: 'Gift Wrap Set', category: 'Toys & Gifting', price: 55, image_emoji: '🎁' },
  { id: 'p32', name: 'Small Puzzle Toy', category: 'Toys & Gifting', price: 79, image_emoji: '🧩' },
  { id: 'p33', name: 'Greeting Card', category: 'Toys & Gifting', price: 40, image_emoji: '💌' },

  // Demo catalog entries. No review-corpus evidence backs this category —
  // findThemeForCategory returns nothing for it, so the "Why this?" panel
  // correctly says no theme has been extracted rather than inventing one.
  //
  // PRICES CHOSEN FOR DEMO VISIBILITY, not from real pricing. The rail ranks
  // categories by how closely their best item matches the checkout gap, and
  // ties break toward whatever appears earlier in this file — which
  // permanently buried a category added last. 47/63/76 are unclaimed points
  // in the existing price ladder spread across the 40-80 discovery window, so
  // this category wins outright at those gaps instead of losing every tie.
  { id: 'p34', name: 'Electrolyte Hydration Sachets', category: 'Sports & Fitness', price: 47, image_emoji: '🥤' },
  { id: 'p35', name: 'Whey Protein Single Serve', category: 'Sports & Fitness', price: 63, image_emoji: '🥛' },
  { id: 'p36', name: 'Resistance Band (medium)', category: 'Sports & Fitness', price: 76, image_emoji: '🏋️' },

  // Occasion stock, so the seasonal section can surface something that
  // actually reads as festive. Before these existed, Diwali surfaced a steel
  // storage container — correct by category, meaningless as a suggestion.
  // Demo catalog data like everything else here; no corpus evidence behind it.
  { id: 'p37', name: 'Rakhi & Sweets Gift Box', category: 'Toys & Gifting', price: 85, image_emoji: '🎁', occasions: ['raksha-bandhan', 'diwali'] },
  { id: 'p38', name: 'Diya Set (12 pcs)', category: 'Home & Kitchen', price: 60, image_emoji: '🪔', occasions: ['diwali'] },
  { id: 'p39', name: 'Decorative String Lights', category: 'Home & Kitchen', price: 99, image_emoji: '✨', occasions: ['diwali'] },
  { id: 'p40', name: 'Festive Sweets Box', category: 'Snacks & Beverages', price: 120, image_emoji: '🍬', occasions: ['diwali', 'ganesh-chaturthi', 'raksha-bandhan'] },
  { id: 'p41', name: 'Chocolate Gift Box', category: 'Snacks & Beverages', price: 90, image_emoji: '🍫', occasions: ['valentines', 'raksha-bandhan'] },

  // Monsoon stock. Filed under Household Essentials rather than a new
  // category — umbrellas and raincoats are seasonal rather than a distinct
  // shopping category, and one more category would dilute the taxonomy.
  { id: 'p42', name: 'Compact Umbrella', category: 'Household Essentials', price: 95, image_emoji: '☂️', occasions: ['monsoon'] },
  { id: 'p43', name: 'Quick-dry Towel', category: 'Household Essentials', price: 74, image_emoji: '🧺', occasions: ['monsoon'] },
  { id: 'p44', name: 'Light Raincoat', category: 'Household Essentials', price: 149, image_emoji: '🧥', occasions: ['monsoon'] },
]
