import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
MANIFEST_PATH=ROOT/"data"/"test_manifest.json"

def load_repo_manifest(repo_name: str):
    manifest=json.loads(MANIFEST_PATH.read_text())
    for entry in manifest["repos"]:
        if entry["name"]==repo_name:
            return entry
    raise ValueError(f"RAISETICKET:: no manifest entry for repo '{repo_name}' in {MANIFEST_PATH}")

_load_repo_manifest=load_repo_manifest

def _run_one(test: dict, repo_name: str, repo_path: Path, log_path: Path):
    proc=subprocess.run(
        test["command"], shell=True, cwd=str(repo_path),
        capture_output=True, text=True, timeout=600
    )
    result={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": repo_name,
        "command": test["command"],
        "test_id": test["id"],
        "blocking": test["blocking"],
        "exit_code": proc.stdout[-2000:],
        "stdout_tail": proc.stdout[-2000: ],
        "stderr_tail": proc.stderr[-2000:]
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(result) + "\n")
    return result

def run_tests(repo_name: str, stop_on_first_blocking_failure: bool = False) -> list[dict]:
    entry = load_repo_manifest(repo_name)
    repo_path = ROOT / entry["local_path"]
    log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"

    results = []
    for test in sorted(entry["test_types"], key=lambda t: t["priority"]):
        result = _run_one(test, repo_name, repo_path, log_path)
        results.append(result)
        if result["exit_code"] != 0 and test["blocking"] and stop_on_first_blocking_failure:
            break

    return results

def run_single_test(repo_name: str, test_id: str):
    entry=load_repo_manifest(repo_name)
    test=next((t for t in entry["test_types"] if t["id"] == test_id), None)
    if test is None:
        raise ValueError(f"RAISETICKET:: test_id '{test_id}' not found in manifest for repo '{repo_name}'")
    repo_path=ROOT/entry["local_path"]
    log_path=ROOT/"data"/"logs"/f"run_{repo_name}.jsonl"
    return _run_one(test, repo_name, repo_path, log_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("RAISETICKET:: usage: python -m issueloop.test_runner <repo_name>")
        sys.exit(1)
    for r in run_tests(sys.argv[1]):
        status = "OK" if r["exit_code"] == 0 else "FAIL"
        print(f"[{status}] {r['test_id']} (exit {r['exit_code']})")