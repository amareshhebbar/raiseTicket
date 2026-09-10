# import json
# import subprocess
# import sys
# from datetime import datetime, timezone
# from pathlib import Path

# ROOT = Path(__file__).resolve().parent.parent
# MANIFEST_PATH = ROOT / "data" / "test_manifest.json"


# def load_repo_manifest(repo_name: str):
#     manifest = json.loads(MANIFEST_PATH.read_text())
#     for entry in manifest["repos"]:
#         if entry["name"] == repo_name:
#             return entry
#     raise ValueError(f"no manifest entry for repo '{repo_name}' in {MANIFEST_PATH}")


# _load_repo_manifest = load_repo_manifest  


# def _run_one(test: dict, repo_name: str, repo_path: Path, log_path: Path):
#     proc = subprocess.run(
#         test["command"], shell=True, cwd=str(repo_path),
#         capture_output=True, text=True, timeout=600,
#     )
#     result = {
#         "timestamp": datetime.now(timezone.utc).isoformat(),
#         "repo": repo_name,
#         "command": test["command"],
#         "test_id": test["id"],
#         "blocking": test["blocking"],
#         "exit_code": proc.returncode,
#         "stdout_tail": proc.stdout[-2000:],
#         "stderr_tail": proc.stderr[-2000:],
#     }
#     log_path.parent.mkdir(parents=True, exist_ok=True)
#     with log_path.open("a") as f:
#         f.write(json.dumps(result) + "\n")
#     return result


# def run_tests(repo_name: str, stop_on_first_blocking_failure: bool = False):
#     entry = load_repo_manifest(repo_name)
#     repo_path = ROOT / entry["local_path"]
#     log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"

# def _split_errors(entry: dict):
#     prompt = SPLIT_PROMPT.format(
#         command=entry["command"],
#         exit_code=entry["exit_code"],
#         stdout_tail=entry.get("stdout_tail", ""),
#         stderr_tail=entry.get("stderr_tail", ""),
#     )
#     raw = llm.chat(prompt)
#     cleaned = _strip_code_fences(raw)
#     try:
#         parsed = json.loads(cleaned)
#         summaries = [
#             item["summary"]
#             for item in parsed
#             if isinstance(item, dict) and item.get("summary")
#         ]
#         if summaries:
#             return summaries
#     except (json.JSONDecodeError, KeyError, TypeError):
#         pass
#     return [_fallback_summary(entry)]

#     return results


# def run_single_test(repo_name: str, test_id: str):
#     entry = load_repo_manifest(repo_name)
#     test = next((t for t in entry["test_types"] if t["id"] == test_id), None)
#     if test is None:
#         raise ValueError(f"test_id '{test_id}' not found in manifest for repo '{repo_name}'")
#     repo_path = ROOT / entry["local_path"]
#     log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"
#     return _run_one(test, repo_name, repo_path, log_path)


# if __name__ == "__main__":
#     if len(sys.argv) != 2:
#         print("usage: python -m issueloop.test_runner <repo_name>")
#         sys.exit(1)
#     for r in run_tests(sys.argv[1]):
#         status = "OK" if r["exit_code"] == 0 else "FAIL"
#         print(f"[{status}] {r['test_id']} (exit {r['exit_code']})")



import json
import uuid

from . import llm, test_runner
from .agent_state import Ticket, TicketPriority
from .config import get_config
from .db import get_backend

SPLIT_PROMPT = (
    "A test command failed. Split the failure output into one or more "
    "distinct, independent bugs.\n"
    "Command: {command}\n"
    "Exit code: {exit_code}\n"
    "STDOUT (tail):\n{stdout_tail}\n"
    "STDERR (tail):\n{stderr_tail}\n\n"
    "Return a JSON array of objects, each with a single field \"summary\" "
    "containing a short one-sentence description of one distinct bug. "
    "If there is only one bug, return an array with one object."
)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _fallback_summary(entry: dict) -> str:
    tail = (entry.get("stderr_tail") or entry.get("stdout_tail") or "").strip().splitlines()
    last_line = tail[-1] if tail else "unknown error"
    return f"{entry['command']} failed (exit {entry['exit_code']}): {last_line}"


def _split_errors(entry: dict):
    prompt = SPLIT_PROMPT.format(
        command=entry["command"],
        exit_code=entry["exit_code"],
        stdout_tail=entry.get("stdout_tail", ""),
        stderr_tail=entry.get("stderr_tail", ""),
    )
    try:
        raw = llm.chat(prompt)
        cleaned = _strip_code_fences(raw)
        parsed = json.loads(cleaned)
        summaries = [
            item["summary"]
            for item in parsed
            if isinstance(item, dict) and item.get("summary")
        ]
        if summaries:
            return summaries
    except Exception:
        pass
    return [_fallback_summary(entry)]


def create_tickets_for_repo(repo_name: str, stop_on_first_blocking_failure: bool = False):
    results = test_runner.run_tests(repo_name, stop_on_first_blocking_failure=stop_on_first_blocking_failure)
    cfg = get_config()
    backend = get_backend(cfg.database, path=cfg.database_path)

    created = []
    for entry in results:
        if entry["exit_code"] == 0:
            continue
        priority = TicketPriority.BLOCKING if entry.get("blocking") else TicketPriority.NORMAL
        for summary in _split_errors(entry):
            ticket = Ticket(
                id=str(uuid.uuid4()),
                repo=repo_name,
                error_summary=summary,
                raw_log_ref=json.dumps(entry)[-2000:],
                priority=priority,
                command=entry["command"],
                test_id=entry["test_id"],
            )
            backend.create_ticket(ticket)
            created.append(ticket)
    return created