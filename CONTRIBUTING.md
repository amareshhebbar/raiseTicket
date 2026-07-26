# Contributing

## Setup

```bash
git clone https://github.com/onenot8/issueloop
cd issueloop
pip install -e .
pytest tests/ -v
```

All tests pass with zero external services running. If your change
needs ollama or Supabase, mock it or test against the local backend
instead — see `tests/test_ticket_store.py` and `tests/test_server.py`
for the pattern.

## Before opening a PR

- `pytest tests/ -v` — all green
- New behavior gets a new test, no exceptions
- If you touch `db/local_store.py` or `db/supabase_store.py`, both must
  keep passing the same interface tests (`db/base.py`)

## Scope

Detect, split, store, dispense. PRs adding fix-proposal, diff
application, or PR creation are out of scope — that's a different,
downstream project. Open an issue to discuss before building something
in that direction.

## Bugs

Open an issue: command run, expected result, actual result. Security
issues go through `SECURITY.md`, not a public issue.