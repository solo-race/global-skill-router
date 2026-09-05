#!/usr/bin/env python3
"""Run pytest with a repository-local, per-process temporary directory."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parents[2]
    basetemp_root = repo_root / ".tmp" / "pytest"
    basetemp_root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=basetemp_root))

    command = [
        sys.executable,
        "-m",
        "pytest",
        *sys.argv[1:],
        "--basetemp",
        str(run_dir),
    ]
    try:
        completed = subprocess.run(command, cwd=repo_root)
        return completed.returncode
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
