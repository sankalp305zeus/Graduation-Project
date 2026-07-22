-- Blinkit Discovery Concierge — seed data
-- Run AFTER schema.sql. Re-runnable: clears existing rows first.

truncate table event_log, products, personas cascade;

insert into personas (id, name, age, occupation, city, bio, always_orders, never_tried) values
('priya',  'Priya',  28, 'Working professional', 'Bangalore',
  'Orders groceries and snacks 3-4x a week, sticks to her routine list.',
  array['Groceries & Fresh Produce', 'Snacks & Beverages'],
  array['Personal Care & Beauty', 'Electronics Accessories']),

('rahul',  'Rahul',  32, 'New parent', 'Pune',
  'Baby care and groceries dominate his cart since his daughter was born.',
  array['Baby Care', 'Groceries & Fresh Produce'],
  array['Pet Supplies', 'Home & Kitchen']),

('ananya', 'Ananya', 24, 'Student', 'Delhi',
  'Snacks for late-night study sessions, stationery before exams.',
  array['Snacks & Beverages', 'Stationery & Books'],
  array['Personal Care & Beauty', 'Pharmacy & Health']),

('vikram', 'Vikram', 35, 'Pet owner', 'Mumbai',
  'Never misses a pet food order, groceries are an afterthought.',
  array['Pet Supplies', 'Groceries & Fresh Produce'],
  array['Electronics Accessories', 'Toys & Gifting']),

('sneha',  'Sneha',  29, 'Fitness-focused professional', 'Hyderabad',
  'Health-conscious — groceries and pharmacy items, nothing indulgent.',
  array['Groceries & Fresh Produce', 'Pharmacy & Health'],
  array['Personal Care & Beauty', 'Household Essentials']),

('arjun',  'Arjun',  38, 'Frequently hosts gatherings', 'Chennai',
  'Snacks and household essentials in bulk — always prepping for guests.',
  array['Snacks & Beverages', 'Household Essentials'],
  array['Electronics Accessories', 'Home & Kitchen']);

-- Products: 2-3 per category across all 11 categories.
-- Prices deliberately include some in the ₹40-80 range so the discovery
-- card has realistic candidates to match against a checkout deficit.

insert into products (id, name, category, price, image_emoji) values
-- Groceries & Fresh Produce
('p01', 'Amul Milk 1L', 'Groceries & Fresh Produce', 66, '🥛'),
('p02', 'Fresh Bananas (dozen)', 'Groceries & Fresh Produce', 60, '🍌'),
('p03', 'Tomatoes 1kg', 'Groceries & Fresh Produce', 40, '🍅'),

-- Snacks & Beverages
('p04', 'Lays Chips Party Pack', 'Snacks & Beverages', 50, '🍟'),
('p05', 'Coca-Cola 750ml', 'Snacks & Beverages', 45, '🥤'),
('p06', 'Britannia Cookies', 'Snacks & Beverages', 35, '🍪'),

-- Household Essentials
('p07', 'Vim Dishwash Bar', 'Household Essentials', 25, '🧽'),
('p08', 'Harpic Toilet Cleaner', 'Household Essentials', 55, '🧴'),
('p09', 'Tissue Box', 'Household Essentials', 70, '🧻'),

-- Personal Care & Beauty
('p10', 'Nivea Face Wash 100ml', 'Personal Care & Beauty', 199, '🧴'),
('p11', 'Travel-size Moisturizer 30ml', 'Personal Care & Beauty', 75, '🧴'),
('p12', 'Lip Balm', 'Personal Care & Beauty', 45, '💄'),

-- Baby Care
('p13', 'Pampers Diapers (small pack)', 'Baby Care', 249, '🍼'),
('p14', 'Baby Wipes', 'Baby Care', 79, '🧴'),
('p15', 'Baby Lotion 100ml', 'Baby Care', 65, '🧴'),

-- Pet Supplies
('p16', 'Pedigree Dog Food 1kg', 'Pet Supplies', 210, '🐕'),
('p17', 'Cat Treats', 'Pet Supplies', 58, '🐱'),
('p18', 'Pet Shampoo', 'Pet Supplies', 72, '🐾'),

-- Electronics Accessories
('p19', 'USB-C Charging Cable', 'Electronics Accessories', 249, '🔌'),
('p20', 'Wired Earphones', 'Electronics Accessories', 68, '🎧'),
('p21', 'Phone Stand', 'Electronics Accessories', 55, '📱'),

-- Home & Kitchen
('p22', 'Steel Storage Container', 'Home & Kitchen', 79, '🍱'),
('p23', 'Kitchen Towel Set', 'Home & Kitchen', 62, '🧺'),
('p24', 'Non-stick Ladle', 'Home & Kitchen', 45, '🥄'),

-- Stationery & Books
('p25', 'Notebook Set', 'Stationery & Books', 60, '📓'),
('p26', 'Gel Pen Pack', 'Stationery & Books', 40, '🖊️'),
('p27', 'Sticky Notes', 'Stationery & Books', 35, '📝'),

-- Pharmacy & Health
('p28', 'Multivitamin Strip', 'Pharmacy & Health', 75, '💊'),
('p29', 'Hand Sanitizer 100ml', 'Pharmacy & Health', 49, '🧴'),
('p30', 'Protein Bar Pack', 'Pharmacy & Health', 68, '🍫'),

-- Toys & Gifting
('p31', 'Gift Wrap Set', 'Toys & Gifting', 55, '🎁'),
('p32', 'Small Puzzle Toy', 'Toys & Gifting', 79, '🧩'),
('p33', 'Greeting Card', 'Toys & Gifting', 40, '💌');
