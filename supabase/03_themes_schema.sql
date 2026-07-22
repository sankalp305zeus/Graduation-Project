-- Blinkit Discovery Concierge — AI engine schema extension
-- Run AFTER the mvp-shell's schema.sql (personas/products/event_log).
-- This adds the tables the RAG recommendation engine reads from.

create extension if not exists vector;

create table if not exists reviews (
  id text primary key,
  source text not null,              -- 'playstore' | 'appstore' | 'reddit'
  text text not null,
  rating int,
  category text,                     -- assigned during theme labeling, nullable until then
  embedding vector(384),              -- all-MiniLM-L6-v2 dimension (local sentence-transformers)
  created_at timestamptz not null default now()
);

create table if not exists themes (
  id text primary key,
  category text not null,            -- one of the 11-category taxonomy
  theme_name text not null,
  description text not null,
  evidence_ids text[] not null default '{}',   -- review IDs — see docs/ai-architecture.md
                                                -- on why this is FULL cluster membership,
                                                -- not just what the LLM sampled
  evidence_count int generated always as (array_length(evidence_ids, 1)) stored,
  support_pct numeric,                -- from eval D.2 (% of evidence_ids judged supporting)
  is_placeholder boolean not null default true, -- TRUE until real discovery-engine output replaces it
  created_at timestamptz not null default now()
);

create index if not exists idx_reviews_embedding on reviews
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists idx_themes_category on themes (category);

alter table reviews enable row level security;
alter table themes enable row level security;

create policy "public read reviews" on reviews for select using (true);
create policy "public read themes" on themes for select using (true);
