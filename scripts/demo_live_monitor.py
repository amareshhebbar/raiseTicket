import time
import json
from pathlib import Path

from issueloop.live_monitor import watch_process

REPO = "livecheck"
LOG_PATH = Path("data/logs") / f"run_{REPO}.jsonl"
LOG_PATH.unlink(missing_ok=True)

print(f"watching: python3 -m pytest test_calc.py -q  (cwd=repos/fixture)")
watcher = watch_process(
    REPO,
    "python3 -m pytest test_calc.py -q",
    cwd="repos/fixture",
    debounce_seconds=2.0,
)

time.sleep(4)
watcher.stop()

if not LOG_PATH.exists():
    print("NOTHING FLUSHED — test_calc.py must be passing (no bug) or debounce needs more time")
else:
    print(f"--- {LOG_PATH} ---")
    for line in LOG_PATH.read_text().splitlines():
        entry = json.loads(line)
        print(f"[{entry['test_id']}] blocking={entry['blocking']} exit_code={entry['exit_code']}")
        print(entry["stderr_tail"])
        print("---")