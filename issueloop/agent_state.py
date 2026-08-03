from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"


class TicketPriority(str, Enum):
    BLOCKING = "blocking"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class SubTask:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[dict[str, Any]] = None


@dataclass
class Ticket:
    id: str
    repo: str
    error_summary: str
    raw_log_ref: str
    priority: TicketPriority
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    escalation_summary: Optional[str] = None
    command: Optional[str] = None
    test_id: Optional[str] = None


@dataclass
class AgentState:
    allowed_commands: list[str] = field(default_factory=list)
    create_pr_permission: bool = False
    supabase_write_permission: bool = False
    repo: str = ""
    branch: str = ""
    current_task_id: str = ""
    current_task: Optional[SubTask] = None
    previous_task_and_result: Optional[dict[str, Any]] = None
    next_task_id: Optional[str] = None
    queue_independent_tasks: list[SubTask] = field(default_factory=list)
    queue_dependent_task: list[SubTask] = field(default_factory=list)
    active_tickets: list[Ticket] = field(default_factory=list)
    message_from_user: Optional[str] = None
    pending_confirmation: bool = False
    goal: str = ""
    what_to_do: list[str] = field(default_factory=list)
    what_not_to_do: list[str] = field(default_factory=list)
    overall_points: int = 0
    current_task_points: int = 0
    max_retries_per_ticket: int = 3
    log_cache_ref: str = ""
    last_error: Optional[str] = None


def new_run_state(repo: str, goal: str, allowed_commands: list[str]):
    return AgentState(repo=repo, goal=goal, allowed_commands=allowed_commands)