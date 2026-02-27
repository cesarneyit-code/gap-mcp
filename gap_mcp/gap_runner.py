"""
GAP process manager — maintains a persistent GAP subprocess.

Sends commands via stdin and reads output until a sentinel token,
avoiding the ~1s startup overhead on every call.
"""

import subprocess
import threading
import queue
import logging
import shutil
import os
from typing import Optional

logger = logging.getLogger(__name__)

SENTINEL = "__GAPDONE__"
SENTINEL_CMD = f'Print("{SENTINEL}\\n");\n'
ERROR_PREFIX = "Error,"


def find_gap_executable() -> str:
    """Find the GAP executable on this system."""
    candidates = [
        os.path.expanduser("~/opt/gap/gap"),
        "/usr/local/bin/gap",
        "/usr/bin/gap",
        "/opt/homebrew/bin/gap",
    ]
    # Check PATH first
    gap_in_path = shutil.which("gap")
    if gap_in_path:
        return gap_in_path
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError(
        "GAP executable not found. Install GAP or set GAP_EXECUTABLE env variable."
    )


class GAPRunner:
    """
    Manages a persistent GAP process.

    Usage:
        runner = GAPRunner()
        result = runner.execute("Order(SymmetricGroup(4));")
        runner.close()
    """

    def __init__(self, gap_executable: Optional[str] = None, timeout: int = 60):
        self.gap_executable = gap_executable or os.environ.get(
            "GAP_EXECUTABLE", find_gap_executable()
        )
        self.default_timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._start()

    def _start(self):
        """Start the GAP subprocess."""
        logger.info(f"Starting GAP process: {self.gap_executable}")
        self._process = subprocess.Popen(
            [self.gap_executable, "-q"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        # Background thread reads stdout continuously
        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True
        )
        self._reader_thread.start()
        # GAP needs time to load before accepting input
        import time
        time.sleep(2)
        # Warm up: wait for GAP to be ready
        self._send_sentinel(timeout=30)
        logger.info("GAP process ready.")

    def _read_output(self):
        """Background thread: read GAP stdout line by line into the queue."""
        for line in self._process.stdout:
            self._output_queue.put(line)
        self._output_queue.put(None)  # signal EOF

    def _send_sentinel(self, timeout: Optional[int] = None):
        """Send sentinel and collect output until it appears."""
        self._process.stdin.write(SENTINEL_CMD)
        self._process.stdin.flush()
        t = timeout or self.default_timeout
        lines = []
        while True:
            try:
                line = self._output_queue.get(timeout=t)
            except queue.Empty:
                raise TimeoutError(f"GAP did not respond within {t}s")
            if line is None:
                raise RuntimeError("GAP process terminated unexpectedly")
            stripped = line.rstrip("\n")
            if stripped == SENTINEL:
                break
            lines.append(stripped)
        return lines

    def execute(self, code: str, timeout: Optional[int] = None) -> dict:
        """
        Execute GAP code and return result.

        Returns:
            {
                "success": bool,
                "output": str,       # stdout lines joined
                "error": str | None  # stderr content if any
            }
        """
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                logger.warning("GAP process died — restarting.")
                self._start()

            # Send code + sentinel
            full_code = code.strip()
            if not full_code.endswith(";"):
                full_code += ";"
            self._process.stdin.write(full_code + "\n")
            self._process.stdin.flush()

            try:
                lines = self._send_sentinel(timeout)
            except TimeoutError as e:
                # Restart GAP after timeout
                self.close()
                self._start()
                return {"success": False, "output": "", "error": str(e)}
            except RuntimeError as e:
                self._process = None
                return {"success": False, "output": "", "error": str(e)}

            output = "\n".join(lines).strip()

            # Check stderr for errors (non-blocking)
            error = None
            stderr_data = self._read_stderr()
            if stderr_data and ERROR_PREFIX in stderr_data:
                error = stderr_data.strip()

            success = error is None
            return {"success": success, "output": output, "error": error}

    def _read_stderr(self) -> str:
        """Read any available stderr without blocking."""
        try:
            import select
            if select.select([self._process.stderr], [], [], 0.1)[0]:
                return self._process.stderr.read(4096)
        except Exception:
            pass
        return ""

    def reset(self) -> dict:
        """Restart the GAP process, clearing all state."""
        self.close()
        self._start()
        return {"success": True, "output": "GAP session reset.", "error": None}

    def close(self):
        """Terminate the GAP process."""
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.write("QUIT;\n")
                self._process.stdin.flush()
                self._process.wait(timeout=3)
            except Exception:
                self._process.kill()
        self._process = None
        logger.info("GAP process closed.")


# Module-level singleton — shared across all tool calls
_runner: Optional[GAPRunner] = None


def get_runner() -> GAPRunner:
    """Get or create the module-level GAP runner."""
    global _runner
    if _runner is None:
        _runner = GAPRunner()
    return _runner
