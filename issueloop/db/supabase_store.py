import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from supabase import create_client 

from ..agent_state import TaskStatus, Ticket, TicketPriority
from .base import TicketStoreBackend

TABLE = "tickets"
AUDIT_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "logs" / "tickets_audit.jsonl"

PRIORITY_ORDER = {"blocking": 0, "high": 1, "normal": 2, "low": 3}


class SupabaseStore(TicketStoreBackend):
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY not set. Copy .env.example to .env and fill them in, "
                "or pass issueloop.use(database='local') instead."
            )
        self._client = create_client(url, key)

    def _audit(self, event: str, ticket_id: str, detail: dict):
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event, "ticket_id": ticket_id, **detail,
            }) + "\n")

    def _row_to_ticket(self, row: dict):
        return Ticket(
            id=row["id"], repo=row["repo"], error_summary=row["error_summary"],
            raw_log_ref=row["raw_log_ref"], priority=TicketPriority(row["priority"]),
            status=TaskStatus(row["status"]),
            created_at=row.get("created_at") or datetime.now(timezone.utc).isoformat(),
            resolved_at=row.get("resolved_at"), command=row.get("command"), test_id=row.get("test_id"),
        )

    def create_ticket(self, ticket: Ticket):
        row = {
            "id": ticket.id, "repo": ticket.repo, "error_summary": ticket.error_summary,
            "raw_log_ref": ticket.raw_log_ref, "priority": ticket.priority.value,
            "status": ticket.status.value, "command": ticket.command, "test_id": ticket.test_id,
        }
        self._client.table(TABLE).insert(row).execute()
        self._audit("created", ticket.id, {"priority": ticket.priority.value, "error_summary": ticket.error_summary})
        return ticket

    def update_ticket(self, ticket_id: str, **fields):
        clean = {k: (v.value if hasattr(v, "value") else v) for k, v in fields.items()}
        self._client.table(TABLE).update(clean).eq("id", ticket_id).execute()
        self._audit("updated", ticket_id, clean)

    def get_open_tickets(self, repo: Optional[str] = None):
        q = self._client.table(TABLE).select("*")
        if repo:
            q = q.eq("repo", repo)
        rows = q.execute().data
        return [self._row_to_ticket(r) for r in rows if r["status"] not in ("done", "in_progress")]

    def dispense_next(self, repo: Optional[str] = None):
        candidates = self.get_open_tickets(repo)
        if not candidates:
            return None
        candidates.sort(key=lambda t: (PRIORITY_ORDER[t.priority.value], t.created_at))
        ticket = candidates[0]
        self.update_ticket(ticket.id, status=TaskStatus.IN_PROGRESS)
        ticket.status = TaskStatus.IN_PROGRESS
        return ticket

    def purge_old(self, older_than_days: int, repo: Optional[str] = None):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        q = self._client.table(TABLE).select("id").in_("status", ["done", "failed"]).lt("created_at", cutoff)
        if repo:
            q = q.eq("repo", repo)
        rows = q.execute().data
        ids = [r["id"] for r in rows]
        for tid in ids:
            self._client.table(TABLE).delete().eq("id", tid).execute()
        return len(ids)