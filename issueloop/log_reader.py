import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _cursor_path(repo_name: str) -> Path:
    return ROOT / "data" / "logs" / f".cursor_{repo_name}"


def _read_cursor(repo_name: str) -> int:
    path = _cursor_path(repo_name)
    if not path.exists():
        return 0
    try:
        return int(path.read_text().strip())
    except ValueError:
        return 0


def _write_cursor(repo_name: str, offset: int) -> None:
    path = _cursor_path(repo_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(offset))


def reset_cursor(repo_name: str) -> None:
    path = _cursor_path(repo_name)
    if path.exists():
        path.unlink()


def read_errors(repo_name: str, consume: bool = True):
    log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"
    if not log_path.exists():
        return

    start_offset = _read_cursor(repo_name) if consume else 0
    end_offset = start_offset

    with log_path.open("r") as f:
        f.seek(start_offset)
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry["exit_code"] != 0:
                yield entry
        end_offset = f.tell()

    if consume:
        _write_cursor(repo_name, end_offset)


def rotate_if_large(repo_name: str, max_size_mb: float = 10.0) -> bool:
    log_path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"
    if not log_path.exists():
        return False
    if log_path.stat().st_size < max_size_mb * 1024 * 1024:
        return False

    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = log_path.with_name(f"run_{repo_name}.{stamp}.jsonl.bak")
    log_path.rename(archive_path)
    reset_cursor(repo_name)
    return True