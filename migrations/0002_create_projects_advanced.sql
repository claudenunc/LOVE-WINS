-- ============================================
-- PROJECTS TABLE (Missing Piece)
-- High-level containers for work
-- ============================================
create extension if not exists pgcrypto;

create table if not exists public.projects (
  id uuid default gen_random_uuid() primary key,
  created_at timestamptz default timezone('utc'::text, now()) not null,
  updated_at timestamptz default timezone('utc'::text, now()) not null,
  name text not null,
  description text,
  status text default 'planning' check (status in ('planning', 'active', 'paused', 'completed', 'archived')),
  priority text default 'medium' check (priority in ('critical', 'high', 'medium', 'low')),
  settings jsonb default '{}'::jsonb,
  tags text[]
);

create index if not exists projects_status_idx on public.projects(status);
create index if not exists projects_created_idx on public.projects(created_at desc);

-- RLS: match existing "Allow all" dev pattern
alter table public.projects enable row level security;
create policy "Allow all" on public.projects for all using (true);

-- Seed data
insert into public.projects (name, description, status, settings)
values (
  'ENVY Self-Evolution',
  'The primary project for ENVY''s own development and capabilities expansion.',
  'active',
  '{"auto_reflect": true}'
)
on conflict do nothing;

-- Optionally link existing tables (uncomment if desired)
-- alter table if exists public.tasks add column if not exists project_id uuid references public.projects(id);
-- create index if not exists tasks_project_idx on public.tasks(project_id);
-- alter table if exists public.agents add column if not exists project_id uuid references public.projects(id);

-- Reload PostgREST schema cache so API recognizes new tables immediately
NOTIFY pgrst, 'reload config';
