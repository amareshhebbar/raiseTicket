
create table if not exists tickets (
  id text primary key,
  repo text not null,
  error_summary text not null,
  raw_log_ref text,
  priority text not null check (priority in ('blocking', 'high', 'normal', 'low')),
  status text not null default 'pending' check (status in ('pending', 'in_progress', 'done', 'failed')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  command text,
  test_id text
);

create index if not exists tickets_repo_status_idx on tickets (repo, status);
create index if not exists tickets_created_at_idx on tickets (created_at);