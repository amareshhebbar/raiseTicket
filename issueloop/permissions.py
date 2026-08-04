import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from .config_paths import resolve_config_path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "test_manifest.json"
AUDIT_LOG = ROOT / "data" / "logs" / "permission_audit.jsonl"


class PermissionDenied(Exception):
    pass


def _load_config() -> dict:
    permission_path = resolve_config_path("permission.yaml")
    if not permission_path.exists():
        return {"global": {"allowed_exact": [], "allowed_patterns": []}, "per_repo": {}}
    return yaml.safe_load(permission_path.read_text()) or {}


def _test_manifest_commands(repo: str) -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    manifest = json.loads(MANIFEST_PATH.read_text())
    for entry in manifest.get("repos", []):
        if entry["name"] == repo:
            return {t["command"] for t in entry.get("test_types", [])}
    return set()


def _audit(event: str, repo: str, command: str, detail: str = "") -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "repo": repo,
            "command": command,
            "detail": detail,
        }) + "\n")


def check_permission(cmd: str, repo: str) -> bool:
    cfg = _load_config()
    g = cfg.get("global") or {}
    r = (cfg.get("per_repo") or {}).get(repo, {})

    allowed_exact = set(g.get("allowed_exact", [])) | set(r.get("allowed_exact", []))
    allowed_exact |= _test_manifest_commands(repo)
    allowed_patterns = list(g.get("allowed_patterns", [])) + list(r.get("allowed_patterns", []))

    if cmd in allowed_exact:
        _audit("allowed_exact", repo, cmd)
        return True

    for pattern in allowed_patterns:
        if re.fullmatch(pattern, cmd):
            _audit("allowed_pattern", repo, cmd, detail=pattern)
            return True

    _audit("denied", repo, cmd)
    return False


def run_guarded(cmd: str, repo: str, cwd: Optional[Path] = None, timeout: int = 600) -> subprocess.CompletedProcess:
    if not check_permission(cmd, repo):
        raise PermissionDenied(
            f"'{cmd}' is not allowlisted for repo '{repo}'. "
            f"Add it to config/permission.yaml if it should be allowed."
        )
    return subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def get_permission_audit_log(repo: Optional[str] = None, limit: int = 50) -> list:
    if not AUDIT_LOG.exists():
        return []
    entries = [json.loads(l) for l in AUDIT_LOG.read_text().splitlines() if l.strip()]
    if repo:
        entries = [e for e in entries if e["repo"] == repo]
    return entries[-limit:]