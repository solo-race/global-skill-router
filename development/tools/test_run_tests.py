"""Unit tests for the repository-local pytest runner."""

import importlib.util
import sys
from pathlib import Path

import pytest


RUNNER_PATH = Path(__file__).with_name("run_tests.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_tests_under_test", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_main_invokes_current_python_from_repo_root_and_cleans_run_dir(monkeypatch, tmp_path):
    runner = _load_runner()
    run_dir = tmp_path / "run-unique"
    calls = {}

    def fake_mkdtemp(prefix, dir):
        calls["mkdtemp"] = (prefix, dir)
        return str(run_dir)

    monkeypatch.setattr(runner.tempfile, "mkdtemp", fake_mkdtemp)

    def fake_run(command, cwd):
        calls["command"] = command
        calls["cwd"] = cwd
        return type("Completed", (), {"returncode": 7})()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        runner.shutil,
        "rmtree",
        lambda path, ignore_errors: calls.setdefault("removed", (path, ignore_errors)),
    )
    monkeypatch.setattr(sys, "argv", [str(RUNNER_PATH), "tests/example.py", "-q"])

    assert runner.main() == 7

    assert calls["mkdtemp"] == (
        "run-",
        RUNNER_PATH.resolve().parents[2] / ".tmp" / "pytest",
    )
    assert calls["command"] == [
        sys.executable,
        "-m",
        "pytest",
        "tests/example.py",
        "-q",
        "--basetemp",
        str(run_dir),
    ]
    assert calls["cwd"] == RUNNER_PATH.resolve().parents[2]
    assert calls["removed"] == (run_dir, True)


def test_main_cleans_run_dir_when_pytest_process_fails(monkeypatch, tmp_path):
    runner = _load_runner()
    run_dir = tmp_path / "run-failed"
    removed = []

    monkeypatch.setattr(runner.tempfile, "mkdtemp", lambda prefix, dir: str(run_dir))

    def fake_run(command, cwd):
        raise OSError("pytest process unavailable")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        runner.shutil,
        "rmtree",
        lambda path, ignore_errors: removed.append((path, ignore_errors)),
    )
    monkeypatch.setattr(sys, "argv", [str(RUNNER_PATH), "-k", "runner_contract"])

    with pytest.raises(OSError, match="pytest process unavailable"):
        runner.main()

    assert removed == [(run_dir, True)]
