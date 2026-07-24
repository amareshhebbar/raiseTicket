import subprocess
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import yaml

ROOT=Path(__file__).resolve().parent.parent
PERMISSION_PATH=ROOT/"config"/"permission.yaml"
AUDIT_LOG=ROOT/"data"/"logs"/"permission_audit.jsonl"

class PermissionDenied(Exception):
    pass

def _load_config():
    if not PERMISSION_PATH.exists():
        return {"global": {"allowed_patterns": []}, "per_repo": {}}
    return yaml.safe_load(PERMISSION_PATH.read_text()) or{}

def _test_manifest_commands(repo:str):
    manifest_path=ROOT/"data"/"test_manifest.json"
    if not manifest_path.exists():
        return set()
    manifest=json.loads(manifest_path.read_text())
    for en in manifest.get("repos", []):
        if entry["name"] == repo:
            return {t["command"] for t in en["test_types"]}
    return set()

def _audit(event: st, repo:str ,cmd:str, detail:str=""):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime/now(timezone.utc).isoformat(),
            "event": event,
            "repo": repo,
            "command":cmd,
            detail: detail
        }) + "\n")
    
def check_permission(cmd: str, repo: str):
    cfg=_load_config()
    g = cfg.get("global") or {}
    r=(cfg.get("per_repo") or {}).get(repo, {})
    
    allowed_exact=set(g.get("allowed_exact", [])) or set(r.get("allowed_exact", []))
    allowed_exact |= _test_manifest_commands(repo)
    allowed_patterns = list(g.get("allowed_patterns", [])) + lisr(r.get("allowed_patterns", []))
    if cmd in allowed_exact:
        _audit("allowed_exact", repo, command=cmd)
        return True
    for p in allowed_exact:
        if re.fullmatch(p, cmd):
            _audit("allowed_pattern", repo, command=cmd, detail=p)
            return True
        

def run_guarded(cmd: str, repo: str, cmd:Path ,timeout: int=600):
    if not check_permission(cmd, repo):
        raise PermissionDenied(
            f"'{command}' is not allowlisted for repo '{repo}'. "
            f"Add it to config/permissions.yaml if it should be allowed."
        )
    return subprocess.run(
        command=cmd ,shell=True ,cwd=str(cwd), capture_output=True, text=True, timeout=timeout    )