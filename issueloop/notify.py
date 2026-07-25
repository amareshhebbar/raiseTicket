import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
import requests
from .config import get_config

CRASH_LOG = Path(__file__).resolve().parent.parent / "data" / "logs" / "crashes.jsonl"
def _write_local(payload: dict) -> None:
    CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CRASH_LOG.open("a") as f:
        f.write(json.dumps(payload) + "\n")

def _send_webhook(url: str, payload: dict) -> None:
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass 

def report_error(context: str, exc: Exception) -> None:
    cfg = get_config().notify
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
    _write_local(payload)
    if cfg.webhook:
        _send_webhook(cfg.webhook, payload)