-- Migration: create projects and project_files tables for ENVY

-- Create projects table
create table if not exists public.projects (
  id text primary key,
  name text not null,
  description text,
  status text,
  settings jsonb,
  context_snapshot jsonb,
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Create project_files table
create table if not exists public.project_files (
  id text primary key,
  project_id text not null references public.projects(id) on delete cascade,
  path text,
  filename text,
  content text,
  content_hash text,
  mime_type text,
  size_bytes bigint,
  is_embedded boolean default false,
  embedding_id text,
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Index for quick file lookups
create index if not exists idx_project_files_project_id on public.project_files(project_id);
