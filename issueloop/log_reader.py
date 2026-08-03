import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_errors(repo_name: str):
    log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"
    if not log_path.exists():
        return
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry["exit_code"] != 0:
            yield entry