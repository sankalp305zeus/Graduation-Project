-- Blinkit Discovery Concierge — schema
-- Run this in the Supabase SQL editor (Project → SQL Editor → New Query) before seed.sql

create table if not exists personas (
  id text primary key,
  name text not null,
  age int,
  occupation text,
  city text,
  bio text,
  always_orders text[] not null default '{}',
  never_tried text[] not null default '{}'
);

create table if not exists products (
  id text primary key,
  name text not null,
  category text not null,
  price numeric not null,
  image_emoji text default '📦',  -- placeholder "image" — swap for real product photos later
  -- Occasion tags used by the seasonal/festival rail to prefer festive stock
  -- over generic stock inside the same category. Empty for everyday items.
  -- Mirrors the optional `occasions` field in mvp-shell/src/data/mockProducts.js.
  occasions text[] not null default '{}'
);

-- NOTE for an existing database: `create table if not exists` will NOT add the
-- occasions column to a products table that already exists. Run this once:
--   alter table products add column if not exists occasions text[] not null default '{}';

create table if not exists event_log (
  id bigint generated always as identity primary key,
  persona_id text references personas(id),
  product_id text references products(id),
  action text not null check (action in ('accepted', 'dismissed')),
  created_at timestamptz not null default now()
);

-- Row-Level Security: this is a public demo, so allow anonymous read on
-- personas/products and anonymous insert on event_log. Tighten this before
-- putting any real user data behind it.
alter table personas enable row level security;
alter table products enable row level security;
alter table event_log enable row level security;

create policy "public read personas" on personas for select using (true);
create policy "public read products" on products for select using (true);
create policy "public insert event_log" on event_log for insert with check (true);
create policy "public read event_log" on event_log for select using (true);
