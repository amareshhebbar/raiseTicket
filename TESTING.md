# Testing IssueLoop

Every command below has actually been run against this codebase, not just described. If any step fails for you, that's a real regression — file it.

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`[dev]` pulls in `pytest`, which is required for both the unit suite below and for testing any repo you point IssueLoop at.

## 2. Unit tests

```bash
pytest tests/ -v
```

Expected: `12 passed`. If you see `ModuleNotFoundError: No module named 'issueloop'`, the package wasn't actually installed into the environment you're running `pytest` from — re-run step 1 inside the same shell.

## 3. Fixture repo walkthrough (single bug, end to end)

`data/test_manifest.json` must exist first — it doesn't ship with the repo:

```bash
mkdir -p data
echo '{"repos": []}' > data/test_manifest.json
```

Then:

```bash
bash scripts/make_fixture_repo.sh
pip install pytest   

issueloop scan repos/fixture         
issueloop test fixture               
issueloop tickets fixture           
issueloop next fixture

bash scripts/clean_fixture_repo.sh
```

`fixture` is a hardcoded name inside `make_fixture_repo.sh`, not a placeholder.

## 4. LLM providers

`issueloop tickets` needs a real LLM call to triage failures. Default is local ollama:

```bash
ollama serve
ollama pull qwen2.5-coder:7b
```

Or configure anthropic/openai (single provider):

```python
issueloop.use(llm={"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-..."})
```

Or a priority list with automatic fallback — tries the first provider, falls through to the next on failure (timeout, auth error, rate limit):

```python
issueloop.use(llm={"providers": [
    {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-..."},
    {"provider": "ollama", "model": "qwen2.5-coder:7b"},
]})
```

`issueloop check-env` validates whichever providers are configured — checks all of them if you're using a priority list, and only fails the whole check if *none* of them are ready.

## 5. Live monitoring

Two modes. Mode A — IssueLoop spawns and owns the process:

```bash
issueloop watch <repo-name> --command "python3 main.py" --cwd /path/to/repo --debounce 3.0
# Ctrl+C to stop
```

Mode B — tail a log file an already-running process writes to:

```bash
issueloop watch <repo-name> --log-file /path/to/app.log --debounce 3.0
```

Both debounce detected error lines (default 3s of quiet) before writing one entry to `data/logs/run_<repo>.jsonl` — same schema the batch test runner produces, so `issueloop tickets <repo>` picks it up with no extra steps.

## 6. Fix-apply layer

Requires an explicit allowlist — nothing runs by default:

```yaml
# config/permission.yaml
global:
  allowed_exact: []
  allowed_patterns: []
per_repo:
  <repo-name>:
    allowed_patterns:
      - 'sed -i .* somefile\.py'
```

Then:

```python
issueloop.propose_fix(ticket_id, "sed -i 's/old/new/' somefile.py")
result = issueloop.apply_fix(ticket_id)
# result["status"] is one of: "resolved", "retry", "escalated", "denied"
```

`apply_fix` re-runs the ticket's associated test after applying the fix — it only resolves the ticket if the test actually passes afterward. On repeated failure it retries up to `max_retries` (default 3), then escalates to `needs_human`.

## 7. Full API smoke test

`scripts/demo_full_api.py` exercises all ~45 public functions against a real multi-bug project. See the script itself for setup — it needs a registered repo in `data/test_manifest.json` pointing at a real path.

## 8. Dedup and rotation sanity checks

```bash
# running tickets twice with no new failures should create 0 new tickets the second time
python3 -c "import issueloop; issueloop.use(database='local'); print(len(issueloop.create_tickets('<repo>')))"
python3 -c "import issueloop; issueloop.use(database='local'); print(len(issueloop.create_tickets('<repo>')))"  # should print 0
```

```python
issueloop.rotate_logs("<repo>", max_size_mb=10)  
issueloop.reap_stale_bugs(older_than_minutes=30) 
```