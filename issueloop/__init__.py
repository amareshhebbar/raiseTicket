import json
from pathlib import Path
from typing import Optional

from .config import use, get_config
from .db import get_backend
from .agent_state import TaskStatus, TicketPriority
from . import folder_reader, test_runner, ticket_creator, live_monitor, notify, permissions
from . import llm as _llm

DEFAULT_MAX_RETRIES = 3


def _backend():
    cfg = get_config()
    return get_backend(cfg.database, path=cfg.database_path)


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
        "attempts": ticket.attempts,
        "escalation_summary": ticket.escalation_summary,
        "proposed_fix": ticket.proposed_fix,
        "created_at": str(ticket.created_at),
        "resolved_at": str(ticket.resolved_at) if ticket.resolved_at else None,
        "dispensed_at": str(ticket.dispensed_at) if ticket.dispensed_at else None,
    }


# ---------------------------------------------------------------------------
# Scan / Test
# ---------------------------------------------------------------------------

def scan_repo(repo_path: str):
    out_file = folder_reader.write_inventory(Path(repo_path).resolve())
    return json.loads(out_file.read_text())


def get_file_inventory(repo_name: str):
    out_file = Path(__file__).resolve().parent.parent / "data" / "logs" / f"{repo_name}_files.json"
    if not out_file.exists():
        return None
    return json.loads(out_file.read_text())


def run_tests(repo_name: str):
    return test_runner.run_tests(repo_name)


def run_single_test(repo_name: str, test_id: str):
    return test_runner.run_single_test(repo_name, test_id)


def create_tickets(repo_name: str):
    tickets = ticket_creator.create_tickets_for_repo(repo_name)
    return [_ticket_to_dict(t) for t in tickets]


# ---------------------------------------------------------------------------
# Bug query
# ---------------------------------------------------------------------------

def get_all_bugs(repo: Optional[str] = None):
    return [_ticket_to_dict(t) for t in _backend().get_all_tickets(repo)]


def get_unresolved_bugs(repo: Optional[str] = None):
    statuses = {TaskStatus.PENDING.value, TaskStatus.BLOCKED.value, TaskStatus.IN_PROGRESS.value, TaskStatus.NEEDS_HUMAN.value}
    return [_ticket_to_dict(t) for t in _backend().get_all_tickets(repo) if t.status.value in statuses]


def get_resolved_bugs(repo: Optional[str] = None):
    return get_bugs_by_status(TaskStatus.DONE.value, repo)


def get_failed_bugs(repo: Optional[str] = None):
    return get_bugs_by_status(TaskStatus.FAILED.value, repo)


def get_bugs_needing_human(repo: Optional[str] = None):
    return get_bugs_by_status(TaskStatus.NEEDS_HUMAN.value, repo)


def get_bugs_by_status(status: str, repo: Optional[str] = None):
    return [_ticket_to_dict(t) for t in _backend().get_all_tickets(repo) if t.status.value == status]


def get_bugs_by_priority(priority: str, repo: Optional[str] = None):
    return [_ticket_to_dict(t) for t in _backend().get_all_tickets(repo) if t.priority.value == priority]


def get_bug(ticket_id: str):
    ticket = _backend().get_ticket(ticket_id)
    return _ticket_to_dict(ticket) if ticket else None


def get_bug_count(repo: Optional[str] = None):
    return len(_backend().get_all_tickets(repo))


def get_bug_count_by_status(repo: Optional[str] = None):
    counts = {s.value: 0 for s in TaskStatus}
    for t in _backend().get_all_tickets(repo):
        counts[t.status.value] += 1
    return counts


def search_bugs(query: str, repo: Optional[str] = None):
    q = query.lower()
    return [_ticket_to_dict(t) for t in _backend().get_all_tickets(repo) if q in t.error_summary.lower()]


def get_oldest_bug(repo: Optional[str] = None):
    tickets = _backend().get_all_tickets(repo)
    if not tickets:
        return None
    return _ticket_to_dict(min(tickets, key=lambda t: t.created_at))


def get_newest_bug(repo: Optional[str] = None):
    tickets = _backend().get_all_tickets(repo)
    if not tickets:
        return None
    return _ticket_to_dict(max(tickets, key=lambda t: t.created_at))


# ---------------------------------------------------------------------------
# Ticket lifecycle
# ---------------------------------------------------------------------------

def get_top_error(repo_name: str):
    ticket = _backend().dispense_next(repo_name)
    return _ticket_to_dict(ticket) if ticket else None


def get_all_errors(repo_name: Optional[str] = None):
    return [_ticket_to_dict(t) for t in _backend().get_open_tickets(repo_name)]


def resolve(ticket_id: str):
    _backend().update_ticket(ticket_id, status=TaskStatus.DONE)


def fail(ticket_id: str):
    _backend().update_ticket(ticket_id, status=TaskStatus.FAILED)


def escalate(ticket_id: str, reason: str = ""):
    _backend().update_ticket(ticket_id, status=TaskStatus.NEEDS_HUMAN, escalation_summary=reason)
    ticket = _backend().get_ticket(ticket_id)
    if ticket:
        notify.report_error("ticket.escalate", Exception(reason or "escalated without reason"))
    return _ticket_to_dict(ticket) if ticket else None


def reassign(ticket_id: str):
    _backend().update_ticket(ticket_id, status=TaskStatus.PENDING)
    ticket = _backend().get_ticket(ticket_id)
    return _ticket_to_dict(ticket) if ticket else None


def retry_bug(ticket_id: str):
    ticket = _backend().get_ticket(ticket_id)
    if not ticket:
        return None
    _backend().update_ticket(ticket_id, status=TaskStatus.PENDING, attempts=ticket.attempts + 1)
    return _ticket_to_dict(_backend().get_ticket(ticket_id))


def get_bug_attempts(ticket_id: str):
    ticket = _backend().get_ticket(ticket_id)
    return ticket.attempts if ticket else None


def bulk_resolve(ticket_ids: list):
    for tid in ticket_ids:
        resolve(tid)
    return len(ticket_ids)


# ---------------------------------------------------------------------------
# Fix-apply / permissions
# ---------------------------------------------------------------------------

def _get_repo_local_path(repo_name: str):
    manifest_path = Path(__file__).resolve().parent.parent / "data" / "test_manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest.get("repos", []):
        if entry["name"] == repo_name:
            return entry.get("local_path")
    return None


def propose_fix(ticket_id: str, patch_or_command: str):
    backend = _backend()
    backend.update_ticket(ticket_id, proposed_fix=patch_or_command)
    ticket = backend.get_ticket(ticket_id)
    return _ticket_to_dict(ticket) if ticket else None


def check_permission(cmd: str, repo: str) -> bool:
    return permissions.check_permission(cmd, repo)


def get_permission_audit_log(repo: Optional[str] = None, limit: int = 50):
    return permissions.get_permission_audit_log(repo, limit)


def apply_fix(ticket_id: str, max_retries: int = DEFAULT_MAX_RETRIES, timeout: int = 600):
    backend = _backend()
    ticket = backend.get_ticket(ticket_id)
    if ticket is None:
        return None
    if not ticket.proposed_fix:
        raise ValueError(f"no fix proposed for ticket '{ticket_id}' — call propose_fix() first")

    repo_path = _get_repo_local_path(ticket.repo)

    try:
        run_result = permissions.run_guarded(ticket.proposed_fix, ticket.repo, cwd=repo_path, timeout=timeout)
    except permissions.PermissionDenied as e:
        return {"status": "denied", "ticket_id": ticket_id, "reason": str(e)}

    if ticket.test_id:
        test_result = test_runner.run_single_test(ticket.repo, ticket.test_id)
        passed = test_result["exit_code"] == 0
    else:
        passed = run_result.returncode == 0

    if passed:
        resolve(ticket_id)
        return {"status": "resolved", "ticket_id": ticket_id, "attempts": ticket.attempts}

    new_attempts = ticket.attempts + 1
    if new_attempts >= max_retries:
        escalate(ticket_id, reason=f"fix attempt failed after {new_attempts} tries: {ticket.proposed_fix}")
        return {"status": "escalated", "ticket_id": ticket_id, "attempts": new_attempts}

    backend.update_ticket(ticket_id, status=TaskStatus.PENDING, attempts=new_attempts)
    return {"status": "retry", "ticket_id": ticket_id, "attempts": new_attempts}


# ---------------------------------------------------------------------------
# Live monitoring
# ---------------------------------------------------------------------------

_active_watchers: dict = {}


def watch_process(repo_name: str, command: str, cwd: Optional[str] = None, **kwargs):
    watcher = live_monitor.watch_process(repo_name, command, cwd=cwd, **kwargs)
    _active_watchers[id(watcher)] = watcher
    return id(watcher)


def watch_log_file(repo_name: str, log_path: str, **kwargs):
    watcher = live_monitor.watch_log_file(repo_name, log_path, **kwargs)
    _active_watchers[id(watcher)] = watcher
    return id(watcher)


def stop_watch(handle: int):
    watcher = _active_watchers.pop(handle, None)
    if watcher is None:
        raise KeyError(f"no active watcher with handle {handle}")
    watcher.stop()
    return True


def list_active_watchers():
    return [
        {"handle": h, "repo": w.repo_name, "command": w.command_label}
        for h, w in _active_watchers.items()
    ]


# ---------------------------------------------------------------------------
# LLM / token usage
# ---------------------------------------------------------------------------

def get_token_consumption(provider: Optional[str] = None):
    return _llm.get_token_consumption(provider)


def get_token_consumption_by_provider():
    return _llm.get_token_consumption_by_provider()


def get_llm_call_history(limit: int = 50):
    return _llm.get_llm_call_history(limit)


def get_llm_provider_status():
    cfg = get_config()
    providers = cfg.llm_providers if cfg.llm_providers else [cfg.llm]
    return {
        "priority_order": [
            {"provider": p.provider, "model": p.model, "has_api_key": bool(p.api_key)}
            for p in providers
        ],
        "primary": providers[0].provider if providers else None,
        "fallback_count": max(0, len(providers) - 1),
    }


# ---------------------------------------------------------------------------
# Database maintenance
# ---------------------------------------------------------------------------

def cleanup(older_than_days: Optional[int] = None, repo: Optional[str] = None, statuses: Optional[list] = None):
    days = older_than_days if older_than_days is not None else get_config().retention_days
    return _backend().purge_old(days, repo, statuses=statuses)


def reap_stale_bugs(older_than_minutes: int = 30, repo: Optional[str] = None):
    return _backend().reap_stale(older_than_minutes, repo)


def rotate_logs(repo_name: Optional[str] = None, max_size_mb: float = 10.0):
    from . import log_reader
    if repo_name:
        return {repo_name: log_reader.rotate_if_large(repo_name, max_size_mb)}
    results = {}
    for name in list_repos():
        results[name] = log_reader.rotate_if_large(name, max_size_mb)
    return results


def purge_repo(repo: str):
    return _backend().purge_repo(repo)


def get_database_stats(repo: Optional[str] = None):
    backend = _backend()
    tickets = backend.get_all_tickets(repo)
    stats = {
        "database": get_config().database,
        "total_bugs": len(tickets),
        "by_status": {},
    }
    for t in tickets:
        stats["by_status"][t.status.value] = stats["by_status"].get(t.status.value, 0) + 1
    if hasattr(backend, "db_size_bytes"):
        stats["db_size_bytes"] = backend.db_size_bytes()
    return stats


def export_bugs(repo: Optional[str] = None, path: Optional[str] = None):
    bugs = get_all_bugs(repo)
    out_path = Path(path) if path else Path(__file__).resolve().parent.parent / "data" / "logs" / "bug_export.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bugs, indent=2))
    return str(out_path)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def get_crash_log(limit: int = 50):
    path = Path(__file__).resolve().parent.parent / "data" / "logs" / "crashes.jsonl"
    if not path.exists():
        return []
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return lines[-limit:]


def get_notification_config():
    cfg = get_config().notify
    return {"email": cfg.email, "webhook": cfg.webhook}


# ---------------------------------------------------------------------------
# Config / utility
# ---------------------------------------------------------------------------

def list_repos():
    manifest_path = Path(__file__).resolve().parent.parent / "data" / "test_manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text())
    return [r["name"] for r in manifest.get("repos", [])]


def health_check():
    cfg = get_config()
    result = {"database": cfg.database, "llm_provider": cfg.llm.provider, "ok": True, "issues": []}
    try:
        _backend()
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"database backend error: {e}")
    return result


__all__ = [
    "use", "get_config",
    "scan_repo", "get_file_inventory", "run_tests", "run_single_test", "create_tickets",
    "get_all_bugs", "get_unresolved_bugs", "get_resolved_bugs", "get_failed_bugs",
    "get_bugs_needing_human", "get_bugs_by_status", "get_bugs_by_priority", "get_bug",
    "get_bug_count", "get_bug_count_by_status", "search_bugs", "get_oldest_bug", "get_newest_bug",
    "get_top_error", "get_all_errors", "resolve", "fail", "escalate", "reassign",
    "retry_bug", "get_bug_attempts", "bulk_resolve",
    "propose_fix", "apply_fix", "check_permission", "get_permission_audit_log",
    "watch_process", "watch_log_file", "stop_watch", "list_active_watchers",
    "get_token_consumption", "get_token_consumption_by_provider", "get_llm_call_history", "get_llm_provider_status",
    "cleanup", "purge_repo", "get_database_stats", "export_bugs",
    "reap_stale_bugs", "rotate_logs",
    "get_crash_log", "get_notification_config",
    "list_repos", "health_check",
]