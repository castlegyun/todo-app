-- Supabase 대시보드 > SQL Editor 에 붙여 넣고 한 번 실행합니다.

create table if not exists public.todo (
  id           bigint generated always as identity primary key,
  -- 소유 사용자. 로그인한 사용자의 id가 자동으로 기록됩니다(백엔드가 직접 넣지 않음).
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title        text not null check (char_length(title) between 1 and 200),
  is_done      boolean not null default false,
  due_date     date,
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_todo_user_due on public.todo (user_id, due_date);

-- RLS 켜기: 정책에 맞는 행만 보이고 바꿀 수 있습니다.
alter table public.todo enable row level security;

-- 로그인하지 않은 사용자(anon)는 이 표에 아무 권한이 없습니다.
revoke all on public.todo from anon;
grant select, insert, update, delete on public.todo to authenticated;

drop policy if exists "todo_select_own" on public.todo;
drop policy if exists "todo_insert_own" on public.todo;
drop policy if exists "todo_update_own" on public.todo;
drop policy if exists "todo_delete_own" on public.todo;

create policy "todo_select_own" on public.todo
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy "todo_insert_own" on public.todo
  for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy "todo_update_own" on public.todo
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "todo_delete_own" on public.todo
  for delete to authenticated
  using (user_id = (select auth.uid()));
