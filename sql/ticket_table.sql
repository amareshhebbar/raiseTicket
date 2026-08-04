create table if not exists tickets (
  id text primary key,
  repo text not null,
  error_summary text not null,
  raw_log_ref text,
  priority text not null check (priority in ('blocking', 'high', 'normal', 'low')),
  status text not null default 'pending' check (status in ('pending', 'in_progress', 'blocked', 'done', 'failed', 'needs_human')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  command text,
  test_id text,
  attempts integer not null default 0,
  escalation_summary text,
  proposed_fix text,
  dispensed_at timestamptz
);

create index if not exists tickets_repo_status_idx on tickets (repo, status);
create index if not exists tickets_created_at_idx on tickets (created_at);

-- migration for an existing table created before attempts/escalation_summary/proposed_fix/dispensed_at existed:
-- alter table tickets add column if not exists attempts integer not null default 0;
-- alter table tickets add column if not exists escalation_summary text;
-- alter table tickets add column if not exists proposed_fix text;
-- alter table tickets add column if not exists dispensed_at timestamptz;