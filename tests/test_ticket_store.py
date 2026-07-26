from issueloop.agent_state import TicketPriority
from issueloop.db.local_store import LocalStore

def _store(tmp_path):
    return LocalStore(db_path=tmp_path / "test.db")


def test_dispense_claims_and_does_not_repeat(tmp_path):
    store = _store(tmp_path)
    t = store.create_ticket(_new_ticket("fixture", "some bug", TicketPriority.BLOCKING))

    first = store.dispense_next("fixture")
    assert first is not None
    assert first.id == t.id
    assert first.status.value == "in_progress"

    second = store.dispense_next("fixture")
    assert second is None  


def test_dispense_respects_priority_order(tmp_path):
    store = _store(tmp_path)
    low = store.create_ticket(_new_ticket("fixture", "minor", TicketPriority.LOW))
    blocking = store.create_ticket(_new_ticket("fixture", "critical", TicketPriority.BLOCKING))

    dispensed = store.dispense_next("fixture")
    assert dispensed.id == blocking.id  


def test_local_store_accepts_string_path(tmp_path):
    store = LocalStore(db_path=str(tmp_path / "string_path_test.db"))
    t = store.create_ticket(_new_ticket("fixture", "bug", TicketPriority.LOW))
    assert store.dispense_next("fixture").id == t.id


def test_purge_old_removes_only_resolved_past_cutoff(tmp_path):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    store = _store(tmp_path)
    old_done = store.create_ticket(_new_ticket("fixture", "old fixed bug", TicketPriority.LOW))
    store.update_ticket(old_done.id, status="done")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    conn = sqlite3.connect(str(store.db_path))
    conn.execute("UPDATE tickets SET created_at = ? WHERE id = ?", (old_ts, old_done.id))
    conn.commit()
    conn.close()

    recent_open = store.create_ticket(_new_ticket("fixture", "still open", TicketPriority.LOW))

    removed = store.purge_old(older_than_days=30, repo="fixture")
    assert removed == 1

    remaining_ids = {t.id for t in store.get_open_tickets("fixture")}
    assert recent_open.id in remaining_ids
    assert old_done.id not in remaining_ids


def _new_ticket(repo, summary, priority):
    from issueloop.agent_state import Ticket
    return Ticket(id="", repo=repo, error_summary=summary, raw_log_ref="ref", priority=priority)