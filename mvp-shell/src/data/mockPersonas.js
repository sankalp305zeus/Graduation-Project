// Mirrors supabase/seed.sql — kept in sync manually. This lets the app run
// and look correct before Supabase is wired up, and again as a fallback if
// the Supabase call fails for any reason.
export const mockPersonas = [
  {
    id: 'priya', name: 'Priya', age: 28, occupation: 'Working professional', city: 'Bangalore',
    bio: 'Orders groceries and snacks 3-4x a week, sticks to her routine list.',
    always_orders: ['Groceries & Fresh Produce', 'Snacks & Beverages'],
    never_tried: ['Personal Care & Beauty', 'Electronics Accessories'],
  },
  {
    id: 'rahul', name: 'Rahul', age: 32, occupation: 'New parent', city: 'Pune',
    bio: 'Baby care and groceries dominate his cart since his daughter was born.',
    always_orders: ['Baby Care', 'Groceries & Fresh Produce'],
    never_tried: ['Pet Supplies', 'Home & Kitchen'],
  },
  {
    id: 'ananya', name: 'Ananya', age: 24, occupation: 'Student', city: 'Delhi',
    bio: 'Snacks for late-night study sessions, stationery before exams.',
    always_orders: ['Snacks & Beverages', 'Stationery & Books'],
    never_tried: ['Personal Care & Beauty', 'Pharmacy & Health'],
  },
  {
    id: 'vikram', name: 'Vikram', age: 35, occupation: 'Pet owner', city: 'Mumbai',
    bio: 'Never misses a pet food order, groceries are an afterthought.',
    always_orders: ['Pet Supplies', 'Groceries & Fresh Produce'],
    never_tried: ['Electronics Accessories', 'Toys & Gifting'],
  },
  {
    id: 'sneha', name: 'Sneha', age: 29, occupation: 'Fitness-focused professional', city: 'Hyderabad',
    bio: 'Health-conscious — groceries and pharmacy items, nothing indulgent.',
    always_orders: ['Groceries & Fresh Produce', 'Pharmacy & Health'],
    never_tried: ['Personal Care & Beauty', 'Household Essentials'],
  },
  {
    id: 'arjun', name: 'Arjun', age: 38, occupation: 'Frequently hosts gatherings', city: 'Chennai',
    bio: 'Snacks and household essentials in bulk — always prepping for guests.',
    always_orders: ['Snacks & Beverages', 'Household Essentials'],
    never_tried: ['Electronics Accessories', 'Home & Kitchen'],
  },
]
