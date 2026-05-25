"""Centralized runtime artifact paths for deterministic CI and local runs.

All runtime artifacts are written under a single `.runtime/` directory so
CI and local runs share the exact same layout. Use these constants across the
codebase instead of hardcoded strings.
"""
from pathlib import Path

RUNTIME_DIR: Path = Path(".runtime")
RUNS_DIR: Path = RUNTIME_DIR / "runs"
FAILED_PATCHES_DIR: Path = RUNTIME_DIR / "failed_patches"
TRACES_DIR: Path = RUNTIME_DIR / "traces"
LOGS_DIR: Path = RUNTIME_DIR / "logs"


def ensure_runtime_dirs() -> None:
    """Create all required runtime directories if they don't exist.

    Uses `parents=True, exist_ok=True` so this is safe to call multiple times
    from both local runs and CI jobs.
    """
    for d in (RUNTIME_DIR, RUNS_DIR, FAILED_PATCHES_DIR, TRACES_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
