import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_ERROR_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"\w*exception\w*", re.IGNORECASE),
    re.compile(r"\w*error\w*", re.IGNORECASE),
    re.compile(r"^FAILED\b"),
    re.compile(r"\bfatal\b", re.IGNORECASE),
    re.compile(r"panic:"),
    re.compile(r"\bpanicked at\b"),
]


def _matches_error(line: str, patterns) -> bool:
    return any(p.search(line) for p in patterns)


def _log_path(repo_name: str) -> Path:
    path = ROOT / "data" / "logs" / f"run_{repo_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class LiveWatcher:
    def __init__(
        self,
        repo_name: str,
        command_label: str,
        error_patterns=None,
        debounce_seconds: float = 3.0,
        on_flush: Optional[Callable[[dict], None]] = None,
    ):
        self.repo_name = repo_name
        self.command_label = command_label
        self.error_patterns = error_patterns or DEFAULT_ERROR_PATTERNS
        self.debounce_seconds = debounce_seconds
        self.on_flush = on_flush

        self._buffer: list[str] = []
        self._buffer_lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _flush(self):
        with self._buffer_lock:
            if not self._buffer:
                return
            block = "\n".join(self._buffer)
            self._buffer = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repo": self.repo_name,
            "command": self.command_label,
            "test_id": f"live_{uuid.uuid4().hex[:8]}",
            "blocking": True,
            "exit_code": 1,
            "stdout_tail": "",
            "stderr_tail": block[-2000:],
        }

        log_path = _log_path(self.repo_name)
        with log_path.open("a") as f:
            f.write(__import__("json").dumps(entry) + "\n")

        if self.on_flush:
            self.on_flush(entry)

    def _reset_timer(self):
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _handle_line(self, line: str):
        with self._buffer_lock:
            if self._buffer or _matches_error(line, self.error_patterns):
                self._buffer.append(line)
        if self._buffer:
            self._reset_timer()

    def stop(self):
        self._stop_event.set()
        if self._timer is not None:
            self._timer.cancel()
        self._flush()


class ProcessWatcher(LiveWatcher):
    def __init__(self, repo_name: str, command: str, cwd: Optional[str] = None, **kwargs):
        super().__init__(repo_name, command_label=command, **kwargs)
        self.command = command
        self.cwd = cwd
        self._proc: Optional[subprocess.Popen] = None

    def start(self):
        self._proc = subprocess.Popen(
            self.command,
            shell=True,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _reader():
            for line in self._proc.stdout:
                if self._stop_event.is_set():
                    break
                self._handle_line(line.rstrip("\n"))
            self._proc.stdout.close()
            self._flush()

        self._thread = threading.Thread(target=_reader, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        super().stop()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None


class LogFileWatcher(LiveWatcher):
    def __init__(self, repo_name: str, log_path: str, command_label: str = "", **kwargs):
        super().__init__(repo_name, command_label=command_label or f"tail:{log_path}", **kwargs)
        self.log_path = Path(log_path)

    def start(self):
        def _reader():
            while not self.log_path.exists() and not self._stop_event.is_set():
                time.sleep(0.5)
            if self._stop_event.is_set():
                return
            with self.log_path.open("r") as f:
                f.seek(0, 2)
                while not self._stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    self._handle_line(line.rstrip("\n"))

        self._thread = threading.Thread(target=_reader, daemon=True)
        self._thread.start()
        return self


def watch_process(repo_name: str, command: str, cwd: Optional[str] = None, **kwargs) -> ProcessWatcher:
    return ProcessWatcher(repo_name, command, cwd=cwd, **kwargs).start()


def watch_log_file(repo_name: str, log_path: str, command_label: str = "", **kwargs) -> LogFileWatcher:
    return LogFileWatcher(repo_name, log_path, command_label=command_label, **kwargs).start()