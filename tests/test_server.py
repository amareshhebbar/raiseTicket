import json
import threading
import time
import urllib.request
import issueloop
from issueloop.agent_state import TicketPriority
from issueloop.db.local_store import LocalStore


def test_server_health_and_dispense(tmp_path, monkeypatch):
    from issueloop import server as server_module

    issueloop.use(database="local", database_path=str(tmp_path / "server_test.db"))

    from issueloop.config import get_config
    from issueloop.db import get_backend
    backend = get_backend("local", path=str(tmp_path / "server_test.db"))
    from issueloop.agent_state import Ticket
    backend.create_ticket(Ticket(id="", repo="fixture", error_summary="bug", raw_log_ref="ref",
                                  priority=TicketPriority.BLOCKING))

    port = 8799
    thread = threading.Thread(target=server_module.serve, kwargs={"port": port}, daemon=True)
    thread.start()
    time.sleep(0.3) 

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
            assert json.loads(r.read())["status"] == "ok"

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/errors/top?repo=fixture", timeout=2) as r:
            ticket = json.loads(r.read())
            assert ticket["repo"] == "fixture"
            assert ticket["priority"] == "blocking"

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/errors/top?repo=fixture", timeout=2) as r:
            assert json.loads(r.read()) == {}
    finally:
        pass