# IssueLoop

Finds failing tests. Splits failures into independent tickets. Stores
them. Hands them out one at a time.

Nothing else. No fixing, no PRs, no auto-anything past detection.

![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![status](https://img.shields.io/badge/status-alpha-orange)

---

## Why this exists

Bugs sit unfixed because someone has to notice them first. IssueLoop
skips that step — it reads the test suite directly. A failing test is
the bug report. No human has to spot it.

## Install

```bash
git clone https://github.com/onenot8/issueloop
cd issueloop
pip install -e .
```

Local backend, zero setup. No database account, no API key, works
immediately.

## Use it in code

```python
import issueloop

issueloop.use(
    database="local",              # or "supabase" for a hosted backup
    llm={
        "provider": "anthropic",   # or "ollama" (free, local, default) / "openai"
        "model": "claude-sonnet-4-6",
        "apiKey": "sk-...",
        "tokenSize": 1024,
    },
    notify={"webhook": "https://your-endpoint"},  # fires if IssueLoop itself breaks
)

issueloop.scan_repo("repos/myrepo")
issueloop.run_tests("myrepo")
issueloop.create_tickets("myrepo")

ticket = issueloop.get_top_error("myrepo")   # claims one, marks in_progress
issueloop.get_all_errors("myrepo")           # peek, no claim
issueloop.resolve(ticket["id"])              # your side fixed it
issueloop.fail(ticket["id"])                 # your side couldn't
issueloop.cleanup(older_than_days=30)        # deletes old resolved tickets
```

## Use it from the CLI

```bash
issueloop check-env
issueloop scan repos/myrepo
issueloop test myrepo
issueloop tickets myrepo
issueloop next myrepo
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

```go
resp, _ := http.Get("http://localhost:8787/errors/top?repo=myrepo")
```

No native npm or Go package — that would mean rewriting this logic
twice more, in two languages, and keeping all three in sync forever.
The HTTP bridge is one process, zero porting, works from anything that
can make a request. `serve` is localhost-only, no auth — put it behind
your own gateway if you ever expose it further.

## Config — every option

| Field | Values | Default |
|---|---|---|
| `database` | `"local"`, `"supabase"` | `"local"` |
| `database_path` | any path | `data/issueloop.db` |
| `retention_days` | int | `30` |
| `llm.provider` | `"ollama"`, `"anthropic"`, `"openai"` | `"ollama"` |
| `llm.apiKey` | string | none (required for anthropic/openai) |
| `llm.tokenSize` | int | `1024` |
| `notify.webhook` | URL | none |

Both `apiKey`/`api_key` and `tokenSize`/`token_size` work — camelCase
or snake_case, your call.

## Footprint

The `issueloop` package itself: **78 KB**. Measured, not estimated —
`du` on the installed package directory in a clean virtualenv.

Full install including dependencies (`requests`, `pyyaml`, `pathspec`,
and `requests`' own transitive deps — `certifi`, `urllib3`, `idna`,
`charset-normalizer`, all things most Python environments already
have): **~23 MB** in a totally empty venv. That's the honest number,
not a rounded-down one — if you were expecting sub-1MB total, that's
not achievable with `requests` in the dependency tree, and swapping it
for a smaller HTTP client wasn't worth the tradeoff for this version.

Choosing `database="supabase"` adds `supabase-py` and its own
dependency tree on top of that — only if you opt in
(`pip install -e ".[supabase]"`). The local backend never touches it.

## Why trust this

- Every module has a test, and the tests run against real behavior —
  a real SQLite file, a real HTTP server on a real socket — not just
  mocks pretending things work.
- Two real bugs were caught and fixed by actually running this code,
  not by reading it: `scan` once silently failed to write its output
  file, and the local backend once crashed on a string path. Both have
  regression tests now so they can't come back quietly.
- Local-first by default. Nothing phones home, nothing requires an
  account to try.
- Read the code — it's small enough to actually read. That's on
  purpose.

## Testing

```bash
pytest tests/ -v
bash scripts/make_fixture_repo.sh   # disposable repo, one known bug
bash scripts/clean_fixture_repo.sh
```

Full walkthrough: `TESTING.md`. File-by-file build order: `BUILD_ORDER.md`.

## License

MIT — see `LICENSE`.