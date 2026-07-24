import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from supabase import create_client
from .agent_state import TaskStatus, Ticket, TicketPriority

load_dotenv()
TABLE="tickets"
_client=None

AUDIT_LOG=Path(__file__).resolve().parent.parent/"data"/"logs"/"tickets_audit.jsonl"

PRIORITY_ORDER={
    TicketPriority.BLOCKING: 0,
    TicketPriority.HIGH: 1, 
    TicketPriority.NORMAL: 2,
    TicketPriority.LOW: 3
}

def _get_client():
    global _client
    if _client is None:
        url=os.environ.get("SUPABASE_URL")
        key=os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "ISSUELOOP:: SUPABASE_URL / SUPABASE_KEY not set. Copy .env.example to .env and fill them in."
            )
        _client=create_client(url, key)
    return _client

def _audit(event: str, ticket_id: str, detail:dict):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "ticket_id": ticket_id,
            **detail
        }) + "\n")
        
def _row_to_ticket(row: dict):
    return Ticket(
        id=row["id"],
        repo=row["repo"],
        error_summary=row["error_summary"],
        raw_log_ref=row["raw_log_ref"],
        priority=TicketPriority(row["priority"]),
        status=TaskStatus(row["status"]),
        created_at=row.get("created_at") or datetime.now(timezone.utc).isoformat(),
        resolved_at=row.get("resolved_at"),
        command=row.get("command"),
        test_id=row.get("test_id")
    )
    
def new_ticket(repo: str, error_summary: str ,raw_log_ref: str,
               priority: TicketPriority, command: str=None, test_id:str=None):
    return Ticket(id=str(uuid.uuid4()), repo=repo, error_summary=error_summary, 
                  raw_log_ref=raw_log_ref, priority=priority, command=command, test_id=test_id)

def update_ticket(ticket_id: str, **fields):
    clean={k: (v.value if hasattr(v, "value")else v) for k, v in fields.items()}
    _get_client().table(TABLE).update(clean).eq("id", ticket_id).execute()
    _audit("updated", ticket_id, clean)
    
def get_top_ticket(repo: Optional[str]=None):
    candidates=get_open_tickets(repo)
    if not candidates:
        return None
    candidates.sort(key=lambda t: (PRIORITY_ORDER[t.priority], t.created_at))
    return candidates[0]

def get_open_tickets(repo: Optional[str]=None):
    q=_get_client.table(TABLE).select("*")
    if repo:
        q=q.eq("repo", repo)
    rows=q.execute().data
    return [_row_to_ticket(r) for r in rows if r["status"] not in (TaskStatus.DONE.value, TaskStatus.IN_PROGRESS.value)]

def dispense_next(repo: Optional[str]=None):
    ticket=get_top_ticket(repo)
    if ticket is None:
        return None
    update_ticket(ticket.id, status-TaskStatus.IN_PROGRESS)
    ticket.status=TaskStatus.IN_PROGRESS
    return ticket
    
def create_ticket(ticket:Ticket):
    row={
        "id": ticket.id,
        "repo": ticket.repo,
        "error_summary": ticket.error_summary, 
        "raw_log_ref": ticket.raw_log_ref,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "command": ticket.command,
        "test_id": ticket.test_id
    }
    _get_client().table(TABLE).insert(row).execute()
    _audit("created", ticket.id, {"priority": ticket.priority.value, 
                                  "error_summary": ticket.error_summary})
    return ticket
