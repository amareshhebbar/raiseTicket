import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from ..agent_state import TaskStatus, Ticket, TicketPriority
from .base import TicketStoreBackend

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    error_summary TEXT NOT NULL,
    raw_log_ref TEXT,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    command TEXT,
    test_id TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    escalation_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_repo_status ON tickets (repo, status);
CREATE INDEX IF NOT EXISTS idx_created_at ON tickets (created_at);
"""

_MIGRATION_COLUMNS = {
    "attempts": "INTEGER NOT NULL DEFAULT 0",
    "escalation_summary": "TEXT",
    "proposed_fix": "TEXT",
    "dispensed_at": "TEXT",
}

PRIORITY_ORDER = {"blocking": 0, "high": 1, "normal": 2, "low": 3}


class LocalStore(TicketStoreBackend):
    def __init__(self, db_path: Optional[Path] = None):
        default = Path(__file__).resolve().parent.parent.parent / "data" / "issueloop.db"
        self.db_path = Path(db_path) if db_path else default
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self):
        existing = {row["name"] for row in self._conn.execute("PRAGMA table_info(tickets)")}
        for column, coltype in _MIGRATION_COLUMNS.items():
            if column not in existing:
                self._conn.execute(f"ALTER TABLE tickets ADD COLUMN {column} {coltype}")
        self._conn.commit()

    def _row_to_ticket(self, row: sqlite3.Row):
        keys = row.keys()
        return Ticket(
            id=row["id"],
            repo=row["repo"],
            error_summary=row["error_summary"],
            raw_log_ref=row["raw_log_ref"],
            priority=TicketPriority(row["priority"]),
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
            command=row["command"],
            test_id=row["test_id"],
            attempts=row["attempts"] if "attempts" in keys else 0,
            escalation_summary=row["escalation_summary"] if "escalation_summary" in keys else None,
            proposed_fix=row["proposed_fix"] if "proposed_fix" in keys else None,
            dispensed_at=row["dispensed_at"] if "dispensed_at" in keys else None,
        )

    def create_ticket(self, ticket: Ticket):
        if not ticket.id:
            ticket.id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO tickets (id, repo, error_summary, raw_log_ref, priority, status, created_at, command, test_id, attempts, escalation_summary, proposed_fix) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket.id, ticket.repo, ticket.error_summary, ticket.raw_log_ref,
             ticket.priority.value, ticket.status.value,
             datetime.now(timezone.utc).isoformat(), ticket.command, ticket.test_id,
             ticket.attempts, ticket.escalation_summary, ticket.proposed_fix),
        )
        self._conn.commit()
        return ticket

    def update_ticket(self, ticket_id: str, **fields):
        clean = {k: (v.value if hasattr(v, "value") else v) for k, v in fields.items()}
        set_clause = ", ".join(f"{k} = ?" for k in clean)
        self._conn.execute(f"UPDATE tickets SET {set_clause} WHERE id = ?", (*clean.values(), ticket_id))
        self._conn.commit()

    def get_open_tickets(self, repo: Optional[str] = None):
        query = "SELECT * FROM tickets WHERE status NOT IN ('done', 'in_progress')"
        params: tuple = ()
        if repo:
            query += " AND repo = ?"
            params = (repo,)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_ticket(r) for r in rows]

    def get_all_tickets(self, repo: Optional[str] = None):
        query = "SELECT * FROM tickets"
        params: tuple = ()
        if repo:
            query += " WHERE repo = ?"
            params = (repo,)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_ticket(r) for r in rows]

    def get_ticket(self, ticket_id: str):
        row = self._conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._row_to_ticket(row) if row else None

    def dispense_next(self, repo: Optional[str] = None):
        candidates = self.get_open_tickets(repo)
        if not candidates:
            return None
        candidates.sort(key=lambda t: (PRIORITY_ORDER[t.priority.value], t.created_at))
        ticket = candidates[0]
        now = datetime.now(timezone.utc).isoformat()
        self.update_ticket(ticket.id, status=TaskStatus.IN_PROGRESS, dispensed_at=now)
        ticket.status = TaskStatus.IN_PROGRESS
        ticket.dispensed_at = now
        return ticket

    def reap_stale(self, older_than_minutes: int, repo: Optional[str] = None):
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)).isoformat()
        query = "SELECT * FROM tickets WHERE status = 'in_progress' AND dispensed_at IS NOT NULL AND dispensed_at < ?"
        params: tuple = (cutoff,)
        if repo:
            query += " AND repo = ?"
            params = (cutoff, repo)
        rows = self._conn.execute(query, params).fetchall()
        for row in rows:
            self.update_ticket(row["id"], status=TaskStatus.PENDING, dispensed_at=None)
        return len(rows)

    def purge_old(self, older_than_days: int, repo: Optional[str] = None, statuses=None):
        statuses = statuses or ["done", "failed"]
        placeholders = ", ".join("?" for _ in statuses)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        query = f"DELETE FROM tickets WHERE status IN ({placeholders}) AND created_at < ?"
        params: tuple = (*statuses, cutoff)
        if repo:
            query += " AND repo = ?"
            params = (*statuses, cutoff, repo)
        cur = self._conn.execute(query, params)
        self._conn.commit()
        return cur.rowcount

    def purge_repo(self, repo: str):
        cur = self._conn.execute("DELETE FROM tickets WHERE repo = ?", (repo,))
        self._conn.commit()
        return cur.rowcount

    def db_size_bytes(self) -> int:
        return self.db_path.stat().st_size if self.db_path.exists() else 0