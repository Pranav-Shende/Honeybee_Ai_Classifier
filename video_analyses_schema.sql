-- -- Honeybee AI: saved video-analysis history
-- -- Run this in Supabase Dashboard > SQL Editor.
-- create table if not exists public.video_analyses (
--     id uuid primary key default gen_random_uuid(),
--     user_id uuid not null references auth.users(id) on delete cascade,
--     created_at timestamptz not null default now(),
--     video_name text not null,
--     processed_frames integer not null default 0,
--     source_frames integer not null default 0,
--     processing_seconds numeric not null default 0,
--     processing_fps numeric not null default 0,
--     unique_tracks_seen integer not null default 0,
--     detection_totals jsonb not null default '{}'::jsonb,
--     unique_tracks_by_class jsonb not null default '{}'::jsonb,
--     crossings jsonb not null default '{}'::jsonb,
--     result_url text,
--     note text
-- );

-- create index if not exists video_analyses_user_created_idx
--     on public.video_analyses (user_id, created_at desc);

-- alter table public.video_analyses enable row level security;

-- drop policy if exists "Users can read their own video analyses" on public.video_analyses;
-- create policy "Users can read their own video analyses"
--     on public.video_analyses for select
--     to authenticated
--     using (auth.uid() = user_id);

-- drop policy if exists "Users can insert their own video analyses" on public.video_analyses;
-- create policy "Users can insert their own video analyses"
--     on public.video_analyses for insert
--     to authenticated
--     with check (auth.uid() = user_id);
