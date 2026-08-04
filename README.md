# IssueLoop

Finds failing tests (batch or live). Splits failures into independent
tickets via an LLM, with automatic priority fallback across providers.
Stores them. Hands them out one at a time. Optionally proposes and
applies fixes under an explicit, auditable permission allowlist.

![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![status](https://img.shields.io/badge/status-phase--2-orange)

---

## Why this exists

Bugs sit unfixed because someone has to notice them first. IssueLoop
reads the test suite directly — a failing test is the bug report. It
can also watch a live-running process or log file, for bugs that only
show up outside a test run. No human has to spot it, and no human has
to manually triage which failures are actually distinct problems.

## Install

Not yet on PyPI — install from git:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "git+https://github.com/onenot8/issueLoop@phase-2"
```

Or for local development:

```bash
git clone https://github.com/onenot8/issueLoop
cd issueLoop
pip install -e ".[dev]"
```

Local SQLite backend, zero setup. No database account, no API key required to try it.

## Quickstart

```python
import issueloop

issueloop.use(
    database="local",                     # or "supabase" for a hosted backup
    llm={"providers": [                   # priority list — falls back automatically
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-..."},
        {"provider": "ollama", "model": "qwen2.5-coder:7b"},   # free, local, default if omitted
    ]},
    notify={"webhook": "https://your-endpoint"},   # fires if IssueLoop itself breaks
)

issueloop.scan_repo("repos/myrepo")
issueloop.run_tests("myrepo")
issueloop.create_tickets("myrepo")

ticket = issueloop.get_top_error("myrepo")   # claims one, marks in_progress
issueloop.resolve(ticket["id"])              # your side fixed it
```

## Live monitoring

Watch a process IssueLoop spawns itself, or tail a log file an
already-running process writes to:

```python
from issueloop import watch_process, watch_log_file, stop_watch

handle = watch_process("myrepo", "python3 main.py", cwd="/path/to/repo", debounce_seconds=3.0)
# ...
stop_watch(handle)
```

Or from the CLI, in the foreground:

```bash
issueloop watch myrepo --command "python3 main.py" --cwd /path/to/repo --debounce 3.0
issueloop watch myrepo --log-file /path/to/app.log --debounce 3.0
```

Errors are debounced (default 3s of quiet) so a single multi-line
traceback becomes one ticket, not dozens. Detected errors land in the
same log format the batch test runner uses — `issueloop tickets` picks
them up with no extra steps.

## Fix-apply layer

Off by default — every command needs an explicit allowlist entry:

```yaml
# config/permission.yaml
per_repo:
  myrepo:
    allowed_patterns:
      - 'sed -i .* somefile\.py'
```

```python
issueloop.propose_fix(ticket_id, "sed -i 's/old/new/' somefile.py")
result = issueloop.apply_fix(ticket_id)
# {"status": "resolved" | "retry" | "escalated" | "denied", ...}
```

`apply_fix` re-runs the ticket's associated test after applying the
fix and only resolves it if the test actually passes. Failures retry
up to a configurable limit, then escalate to `needs_human`. Every
permission decision is audited — `issueloop.get_permission_audit_log()`.

## Use it from the CLI

```bash
issueloop check-env
issueloop scan repos/myrepo
issueloop test myrepo
issueloop tickets myrepo
issueloop next myrepo
issueloop watch myrepo --command "..." | --log-file ...
issueloop cleanup --days 30
```

## Use it from Node, Go, or anything else

```bash
issueloop serve --port 8787
```

```js
const r = await fetch("http://localhost:8787/errors/top?repo=myrepo");
const ticket = await r.json();
```

`serve` is localhost-only, no auth — put it behind your own gateway if
you ever expose it further.

## Full API

Bug query — `get_all_bugs`, `get_unresolved_bugs`, `get_resolved_bugs`,
`get_failed_bugs`, `get_bugs_needing_human`, `get_bugs_by_status`,
`get_bugs_by_priority`, `get_bug`, `get_bug_count`,
`get_bug_count_by_status`, `search_bugs`, `get_oldest_bug`, `get_newest_bug`

Lifecycle — `get_top_error`, `get_all_errors`, `resolve`, `fail`,
`escalate`, `reassign`, `retry_bug`, `get_bug_attempts`, `bulk_resolve`

Fix-apply — `propose_fix`, `apply_fix`, `check_permission`,
`get_permission_audit_log`

Scan / test — `scan_repo`, `get_file_inventory`, `run_tests`,
`run_single_test`, `create_tickets`

Live monitoring — `watch_process`, `watch_log_file`, `stop_watch`,
`list_active_watchers`

LLM / tokens — `get_token_consumption`,
`get_token_consumption_by_provider`, `get_llm_call_history`,
`get_llm_provider_status`

Database — `cleanup`, `purge_repo`, `get_database_stats`,
`export_bugs`, `reap_stale_bugs`, `rotate_logs`

Notifications — `get_crash_log`, `get_notification_config`

Config / utility — `use`, `get_config`, `list_repos`, `health_check`

## Config — every option

| Field                 | Values                                | Default              |
| ---------------------- | -------------------------------------- | --------------------- |
| `database`             | `"local"`, `"supabase"`                | `"local"`             |
| `database_path`        | any path                               | `data/issueloop.db`   |
| `retention_days`       | int                                    | `30`                  |
| `llm.providers`        | list of provider dicts, priority order | single ollama default |
| `llm.provider`         | `"ollama"`, `"anthropic"`, `"openai"`  | `"ollama"`             |
| `llm.apiKey`           | string                                 | none (required for anthropic/openai) |
| `llm.tokenSize`        | int                                    | `1024`                |
| `notify.webhook`       | URL                                    | none                  |

Both `apiKey`/`api_key` and `tokenSize`/`token_size` work — camelCase
or snake_case, your call. A single `llm={...}` dict still works exactly
as before; wrap multiple in `llm={"providers": [...]}` for automatic
fallback.

Config files (`config/permission.yaml`, `config/provider_config.yaml`)
resolve in this order: an explicit env var
(`ISSUELOOP_PERMISSION_PATH` / `ISSUELOOP_PROVIDER_CONFIG_PATH`) →
`./config/` relative to your current directory → `config/` in the
IssueLoop checkout → bundled package defaults. This means a real
`pip install` (not just `-e .`) still works correctly even without a
project-local `config/` directory.

## Why trust this

- Every module has a test, and the tests run against real behavior —
  a real SQLite file, a real HTTP server on a real socket — not just
  mocks pretending things work.
- Real bugs were caught and fixed by actually running this code, not
  by reading it — including a prompt that only ever sent `stderr`
  to the LLM triage step while pytest (and most test runners) report
  failures on `stdout`, and a config-bundling gap that made the
  permission system silently deny everything under a real (non-editable)
  install. Both have regression coverage now.
- Local-first by default. Nothing phones home, nothing requires an
  account to try.
- Read the code — it's small enough to actually read. That's on
  purpose. File-by-file build order: `BUILD_ORDER.md`.

## Testing

```bash
pytest tests/ -v
```

Full walkthrough, including live monitoring and the fix-apply layer: `TESTING.md`.

## License

MIT — see `LICENSE`.