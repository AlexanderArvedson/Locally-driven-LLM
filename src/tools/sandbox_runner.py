#!/usr/bin/env python3
"""Small runner used to execute a Python file with resource limits.

This script is intended to be invoked as a subprocess by the sandbox
helper. It sets CPU and address space limits via `resource.setrlimit`
and then executes the target file with `runpy.run_path`.

Usage: python3 sandbox_runner.py <target_file> <memory_mb> <cpu_seconds>
"""
from __future__ import annotations

import sys
import runpy

try:
    import resource
except Exception:
    resource = None


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 3:
        print("Usage: sandbox_runner.py <target_file> <memory_mb> <cpu_seconds>", file=sys.stderr)
        return 2

    target_file = argv[0]
    try:
        memory_mb = int(argv[1])
    except Exception:
        memory_mb = 200
    try:
        cpu_seconds = int(argv[2])
    except Exception:
        cpu_seconds = 5

    if resource is not None:
        try:
            mem_bytes = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            # Not fatal; proceed without AS limit if unsupported
            pass

        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except Exception:
            pass

    # Execute the target file as __main__ so top-level code runs normally.
    try:
        runpy.run_path(target_file, run_name="__main__")
        return 0
    except SystemExit as se:
        # propagate exit codes
        code = se.code if isinstance(se.code, int) else 1
        return code
    except Exception as exc:
        print(f"Sandbox execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
