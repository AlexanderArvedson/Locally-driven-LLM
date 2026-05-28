"""Helper API to run untrusted/generated Python code in a subprocess sandbox.

This module provides `run_code_in_sandbox` which writes the provided code
to a temporary file and executes it via `sandbox_runner.py` with resource
limits. It returns a tuple `(returncode, stdout, stderr)` similar to
`subprocess.run`.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Tuple


SANDBOX_RUNNER = Path(__file__).parent / "sandbox_runner.py"


def run_code_in_sandbox(code: str, timeout: int = 5, memory_mb: int = 200, cpu_seconds: int = 5) -> Tuple[int, str, str]:
    """Run `code` in a subprocess with limits.

    Args:
        code: Python source to execute.
        timeout: wall-clock timeout in seconds for the subprocess.
        memory_mb: address-space limit in megabytes (best-effort).
        cpu_seconds: RLIMIT_CPU seconds limit (best-effort).

    Returns:
        (returncode, stdout, stderr)
    """
    # Ensure sandbox runner exists
    if not SANDBOX_RUNNER.exists():
        raise FileNotFoundError(f"Sandbox runner not found: {SANDBOX_RUNNER}")

    # Write code to a temporary file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(textwrap.dedent(code))
        tf.flush()
        tmp_path = tf.name

    try:
        proc = subprocess.run(
            [sys.executable, str(SANDBOX_RUNNER), tmp_path, str(memory_mb), str(cpu_seconds)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass
