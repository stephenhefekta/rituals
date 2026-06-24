-- Rituals — Supabase schema
-- Run this once in your Supabase project: Dashboard → SQL Editor → New query → paste → Run.

create table if not exists weeks (
    id          text primary key,              -- stable ISO week id, e.g. '2026-W23'
    week_start  date        not null,           -- Monday that starts the week
    created_at  timestamptz not null default now(),
    priorities  jsonb       not null default '[]'::jsonb
);

create table if not exists wins (
    id          text primary key,              -- one win per week, shares the week id
    week_start  date        not null,
    created_at  timestamptz not null default now(),
    text        text        not null
);

create table if not exists quarters (
    id            text primary key,            -- stable quarter id, e.g. '2026-Q2'
    quarter_start date        not null,         -- first day of the quarter
    created_at    timestamptz not null default now(),
    targets       jsonb       not null default '[]'::jsonb
);

-- The desktop app connects with the service_role key, which bypasses RLS.
-- Enabling RLS with no policies means the public anon key can do nothing,
-- so the data is locked down even if that key ever leaks.
alter table weeks    enable row level security;
alter table wins     enable row level security;
alter table quarters enable row level security;
