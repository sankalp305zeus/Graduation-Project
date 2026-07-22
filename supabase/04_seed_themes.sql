-- PLACEHOLDER DATA — run after themes_schema.sql.
-- Every row here has is_placeholder = true. This exists so the RAG
-- recommendation engine has something real to query and can be built/tested
-- END TO END right now, without waiting for the real scraping + n8n theme
-- extraction pipeline to finish. When 02-theme-extraction.json produces real
-- output, insert it with is_placeholder = false and either delete these rows
-- or leave them — the recommend.js query already filters we'll add later.
--
-- The content below is grounded in patterns already surfaced by this
-- project's own research (the checkout-friction/trust/occasion themes from
-- the reworked blueprint and the survey), not invented from nothing — but
-- it is NOT derived from real review text, so treat it as a structural
-- stand-in only, never as a citable finding.

truncate table themes, reviews cascade;

insert into reviews (id, source, text, rating, category) values
('rev_001', 'playstore', 'Ordered a face wash once but was worried it might be expired since I could not check the seal before paying', 3, 'Personal Care & Beauty'),
('rev_002', 'playstore', 'Wish I could see the expiry date before ordering skincare stuff, groceries feel safer to order blind', 4, 'Personal Care & Beauty'),
('rev_003', 'reddit', 'Never buy earphones or chargers on these apps, if it breaks in two days good luck getting a refund', 2, 'Electronics Accessories'),
('rev_004', 'playstore', 'Ordered a charging cable, worked for a week then stopped, support just said to buy a new one', 2, 'Electronics Accessories'),
('rev_005', 'appstore', 'Did not know they even sold pet food until a friend mentioned it, been ordering from a separate app for a year', 5, 'Pet Supplies'),
('rev_006', 'reddit', 'Pet supplies section is buried, I only found it by accident while searching for something else', 4, 'Pet Supplies'),
('rev_007', 'playstore', 'Kitchen storage containers arrived cracked, packaging clearly not built for anything breakable', 2, 'Home & Kitchen'),
('rev_008', 'appstore', 'Good for basic kitchen stuff like ladles and towels, would not trust anything more fragile', 3, 'Home & Kitchen'),
('rev_009', 'reddit', 'Ordered vitamins once, seal looked slightly different from the pharmacy version, got paranoid and stopped', 3, 'Pharmacy & Health'),
('rev_010', 'playstore', 'For actual medicine I still go to the pharmacy, only trust this app for basic hygiene stuff', 4, 'Pharmacy & Health'),
('rev_011', 'playstore', 'Tissue and cleaning stuff is fine but I stock up once a month elsewhere for the bigger essentials', 4, 'Household Essentials'),
('rev_012', 'reddit', 'Did not realize they had a proper household essentials section, always just order snacks', 5, 'Household Essentials'),
('rev_013', 'appstore', 'Ordered a gift wrap set last minute before a birthday, worked out fine actually', 5, 'Toys & Gifting'),
('rev_014', 'playstore', 'Would not think to buy a gift here normally, only did it because I was out of time before a party', 4, 'Toys & Gifting');

insert into themes (id, category, theme_name, description, evidence_ids, support_pct, is_placeholder) values
('th_001', 'Personal Care & Beauty', 'Seal/expiry anxiety blocks beauty trial',
  'Users hesitate to order personal care items because they cannot verify freshness or seal integrity before paying, unlike groceries where this concern is lower.',
  array['rev_001', 'rev_002'], null, true),

('th_002', 'Electronics Accessories', 'Return friction after early failure',
  'Users report electronics accessories failing shortly after purchase and describe difficulty getting a refund or replacement, eroding trust in the category.',
  array['rev_003', 'rev_004'], null, true),

('th_003', 'Pet Supplies', 'Low awareness of pet supplies category',
  'Multiple users were unaware the app carried pet supplies at all, defaulting to a separate specialized app out of habit rather than distrust.',
  array['rev_005', 'rev_006'], null, true),

('th_004', 'Home & Kitchen', 'Fragile-item packaging doubt',
  'Users trust the app for durable kitchen basics but doubt its packaging can protect fragile or breakable home items.',
  array['rev_007', 'rev_008'], null, true),

('th_005', 'Pharmacy & Health', 'Authenticity concern limits health category to basics',
  'Users restrict pharmacy purchases to low-stakes hygiene items, citing packaging differences from trusted pharmacy sources as a reason to avoid medicine.',
  array['rev_009', 'rev_010'], null, true),

('th_006', 'Household Essentials', 'Partial awareness of essentials range',
  'Some users default to routine snack/grocery orders and are surprised to learn a fuller household essentials range exists.',
  array['rev_011', 'rev_012'], null, true),

('th_007', 'Toys & Gifting', 'Occasion-triggered, not habitual',
  'Gifting-category orders happen almost exclusively under time pressure before a specific event, not as routine browsing — an occasion-timing opportunity, not a trust barrier.',
  array['rev_013', 'rev_014'], null, true);
