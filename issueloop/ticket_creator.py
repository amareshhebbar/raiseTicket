import json
import re
import sys
import uuid

from . import llm, log_reader
from .agent_state import Ticket, TicketPriority
from .config import get_config
from .db import get_backend

SPLIT_PROMPT = """You are triaging a failed command's output. Decide if it \
represents ONE error or SEVERAL independent, unrelated errors bundled \
together. Respond ONLY with a JSON list, one object per independent \
error, each with a single field "summary" (one sentence, plain English, \
no stack trace dump, no markdown).

Command: {command}
Exit code: {exit_code}
Stderr (tail): {stderr_tail}
"""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_code_fences(raw: str) -> str:
    return _FENCE_RE.sub("", raw).strip()


def _fallback_summary(entry: dict) -> str:
    return f"'{entry['command']}' failed with exit code {entry['exit_code']}"


def _split_errors(entry: dict):
    prompt = SPLIT_PROMPT.format(
        command=entry["command"], exit_code=entry["exit_code"], stderr_tail=entry["stderr_tail"],
    )
    raw = llm.chat(prompt)
    cleaned = _strip_code_fences(raw)
    try:
        parsed = json.loads(cleaned)
        summaries = [
            item["summary"]
            for item in parsed
            if isinstance(item, dict) and item.get("summary")
        ]
        if summaries:
            return summaries
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return [_fallback_summary(entry)]


def create_tickets_for_repo(repo_name: str):
    cfg = get_config()
    backend = get_backend(cfg.database, path=cfg.database_path)

    created = []
    for entry in log_reader.read_errors(repo_name):
        summaries = _split_errors(entry)
        priority = TicketPriority.BLOCKING if entry["blocking"] else TicketPriority.NORMAL
        for summary in summaries:
            ticket = Ticket(
                id=str(uuid.uuid4()),
                repo=repo_name,
                error_summary=summary,
                raw_log_ref=f"run_{repo_name}.jsonl:{entry['test_id']}:{entry['timestamp']}",
                priority=priority,
                command=entry["command"],
                test_id=entry["test_id"],
            )
            backend.create_ticket(ticket)
            created.append(ticket)
    return created


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m issueloop.ticket_creator <repo_name>")
        sys.exit(1)
    tickets = create_tickets_for_repo(sys.argv[1])
    print(f"created {len(tickets)} ticket(s)")
    for t in tickets:
        print(f"  [{t.priority.value}] {t.error_summary}")