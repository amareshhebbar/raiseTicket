
from pathlib import Path
from typing import Optional

from .config import use, get_config
from .db import get_backend
from .agent_state import TaskStatus
from . import folder_reader, test_runner,ticket_creator


def _backend():
    cfg = get_config()
    return get_backend(cfg.database, path=cfg.database_path)


def scan_repo(repo_path: str):
    out_file = folder_reader.write_inventory(Path(repo_path).resolve())
    import json
    return json.loads(out_file.read_text())


def run_tests(repo_name: str):
    return test_runner.run_tests(repo_name)


def create_tickets(repo_name: str):
    tickets = ticket_creator.create_tickets_for_repo(repo_name)
    return [_ticket_to_dict(t) for t in tickets]


def get_top_error(repo_name: str):
    ticket = _backend().dispense_next(repo_name)
    return _ticket_to_dict(ticket) if ticket else None


def get_all_errors(repo_name: Optional[str] = None):
    return [_ticket_to_dict(t) for t in _backend().get_open_tickets(repo_name)]


def resolve(ticket_id: str):
    _backend().update_ticket(ticket_id, status=TaskStatus.DONE)


def fail(ticket_id: str):
    _backend().update_ticket(ticket_id, status=TaskStatus.FAILED)


def cleanup(older_than_days: Optional[int] = None, repo: Optional[str] = None):
    days = older_than_days if older_than_days is not None else get_config().retention_days
    return _backend().purge_old(days, repo)


def _ticket_to_dict(ticket):
    return {
        "id": ticket.id,
        "repo": ticket.repo,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "error_summary": ticket.error_summary,
        "raw_log_ref": ticket.raw_log_ref,
        "command": ticket.command,
        "test_id": ticket.test_id,
        "created_at": str(ticket.created_at),
    }


__all__ = [
    "use", "get_config",
    "scan_repo", "run_tests", "create_tickets",
    "get_top_error", "get_all_errors", "resolve", "fail", "cleanup",
]