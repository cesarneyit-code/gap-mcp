"""
GAP process manager — maintains a persistent GAP subprocess.

Sends commands via stdin and reads output until a sentinel token,
avoiding the ~2s startup overhead on every call.
"""

import logging
import os
import queue
import select
import shutil
import subprocess
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

SENTINEL = "__GAPDONE__"
SENTINEL_CMD = f'Print("{SENTINEL}\\n");\n'

# GAP error patterns to detect in stdout (GAP -q sends some errors to stdout)
ERROR_PATTERNS = [
    "Error,",
    "Syntax error:",
    "Variable: '",          # "Variable: 'X' must have a value"
    "no method found",
    "user interrupt",
]

# Dangerous GAP commands that could compromise the server
BLOCKED_PATTERNS = [
    "QUIT",
    "quit",
    "Exec(",
    "Process(",
    "IO_",
    "Filename(",
]


def find_gap_executable() -> str:
    """Find the GAP executable on this system."""
    candidates = [
        os.path.expanduser("~/opt/gap/gap"),
        "/usr/local/bin/gap",
        "/usr/bin/gap",
        "/opt/homebrew/bin/gap",
    ]
    gap_in_path = shutil.which("gap")
    if gap_in_path:
        return gap_in_path
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError(
        "GAP executable not found. Install GAP or set the GAP_EXECUTABLE "
        "environment variable to the full path of the gap binary."
    )


def _contains_blocked(code: str) -> Optional[str]:
    """Return the first blocked pattern found in code, or None."""
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return pattern
    return None


class GAPRunner:
    """
    Manages a persistent GAP process.

    Usage:
        runner = GAPRunner()
        result = runner.execute("Order(SymmetricGroup(4));")
        runner.close()
    """

    def __init__(
        self,
        gap_executable: Optional[str] = None,
        timeout: int = 60,
    ):
        # Resolve executable: explicit arg > env var > auto-detect
        self.gap_executable = (
            gap_executable
            or os.environ.get("GAP_EXECUTABLE")
            or find_gap_executable()
        )
        self.default_timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue()
        self._stderr_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._start()

    # ─────────────── lifecycle ───────────────

    def _start(self):
        """Start the GAP subprocess and wait until it is ready."""
        logger.info("Starting GAP process: %s", self.gap_executable)
        # Replace queues with fresh ones so any stale EOF signals from
        # the previous reader threads cannot leak into the new session.
        self._stdout_queue = queue.Queue()
        self._stderr_queue = queue.Queue()

        self._process = subprocess.Popen(
            [self.gap_executable, "-q"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        # Background threads read stdout and stderr continuously
        self._reader_thread = threading.Thread(
            target=self._read_stream,
            args=(self._process.stdout, self._stdout_queue),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self._process.stderr, self._stderr_queue),
            daemon=True,
        )
        self._reader_thread.start()
        self._stderr_thread.start()

        # Wait for GAP to become ready using the sentinel (no sleep needed)
        self._send_sentinel(timeout=30)
        logger.info("GAP process ready.")

    def _read_stream(self, stream, q: queue.Queue):
        """Background thread: read a stream line by line into a queue."""
        for line in stream:
            q.put(line)
        q.put(None)  # EOF signal

    def close(self):
        """Terminate the GAP process gracefully."""
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.write("QUIT;\n")
                self._process.stdin.flush()
                self._process.wait(timeout=3)
            except Exception:
                self._process.kill()
        self._process = None
        logger.info("GAP process closed.")

    def reset(self) -> dict:
        """Restart the GAP process, clearing all variable state."""
        with self._lock:
            self.close()
            self._start()
        return {"success": True, "output": "GAP session reset.", "error": None}

    # ─────────────── internal helpers ───────────────

    def _send_sentinel(self, timeout: Optional[int] = None) -> list:
        """
        Write the sentinel command to GAP stdin and collect output
        lines until the sentinel string appears.
        """
        self._process.stdin.write(SENTINEL_CMD)
        self._process.stdin.flush()
        t = timeout or self.default_timeout
        lines = []
        while True:
            try:
                line = self._stdout_queue.get(timeout=t)
            except queue.Empty:
                raise TimeoutError(
                    f"GAP did not respond within {t}s. "
                    "The computation may be too large; try gap_reset() and use a "
                    "smaller input, or increase the timeout parameter."
                )
            if line is None:
                raise RuntimeError("GAP process terminated unexpectedly.")
            stripped = line.rstrip("\n")
            if stripped == SENTINEL:
                break
            lines.append(stripped)
        return lines

    def _drain_stderr(self) -> str:
        """Collect all currently available stderr lines without blocking."""
        lines = []
        while True:
            try:
                line = self._stderr_queue.get_nowait()
                if line is None:
                    break
                lines.append(line.rstrip("\n"))
            except queue.Empty:
                break
        return "\n".join(lines)

    def _has_error(self, stdout: str, stderr: str) -> Optional[str]:
        """Return an error message if any error pattern is detected."""
        combined = stdout + "\n" + stderr
        for pattern in ERROR_PATTERNS:
            if pattern in combined:
                return combined.strip()
        return None

    # ─────────────── public API ───────────────

    def execute(self, code: str, timeout: Optional[int] = None) -> dict:
        """
        Execute GAP code and return a result dict.

        Returns:
            {
                "success": bool,
                "output":  str,          # stdout (may include error text)
                "error":   str | None    # error description if success=False
            }
        """
        # Safety check
        blocked = _contains_blocked(code)
        if blocked:
            return {
                "success": False,
                "output": "",
                "error": (
                    f"Blocked pattern '{blocked}' found in code. "
                    "Use gap_reset() to restart the session instead of QUIT."
                ),
            }

        with self._lock:
            if self._process is None or self._process.poll() is not None:
                logger.warning("GAP process is dead — restarting.")
                self._start()

            # Normalize code: strip trailing whitespace but do NOT blindly
            # append a semicolon — multiline constructs (for/od, if/fi) don't
            # need one and it would break them.
            full_code = code.strip() + "\n"
            try:
                self._process.stdin.write(full_code)
                self._process.stdin.flush()
                lines = self._send_sentinel(timeout)
            except TimeoutError as exc:
                # Restart so the server stays usable
                self.close()
                self._start()
                return {"success": False, "output": "", "error": str(exc)}
            except RuntimeError as exc:
                self._process = None
                return {"success": False, "output": "", "error": str(exc)}

            output = "\n".join(lines).strip()
            stderr = self._drain_stderr()
            error = self._has_error(output, stderr)

            return {
                "success": error is None,
                "output": output,
                "error": error,
            }


# ─── Module-level singleton with thread-safe initialization ───

_runner: Optional[GAPRunner] = None
_runner_lock = threading.Lock()


def get_runner() -> GAPRunner:
    """Get or create the shared module-level GAP runner (thread-safe)."""
    global _runner
    if _runner is None:
        with _runner_lock:
            if _runner is None:  # double-checked locking
                _runner = GAPRunner()
    return _runner
