#!/usr/bin/env python3
"""Contract tests for the POSIX/WSL bootstrap launcher (bootstrap.sh).

The covered artifact is a shell script, so these are subprocess contract tests
rather than unit tests: stub interpreters are staged inside WSL on a
controlled PATH, and the launcher's stdout, exit status and forwarded
arguments are asserted against the frozen bootstrap contract.
"""

import json
import re
import shlex
import shutil
import subprocess
import time
from functools import lru_cache
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("bootstrap.sh")
WSL_START_TIMEOUT = 90
WSL_TIMEOUT = 30
CATEGORIES = {
    "interpreter_not_found",
    "interpreter_too_old",
    "dependency_unavailable",
    "execution_denied",
    "probe_timeout",
    "helper_failed",
}
ENVELOPE_KEYS = ["schema_version", "bootstrap", "bootstrap_failure", "provenance", "roles", "error"]
STUB_TOOLS = ("timeout", "dirname", "date", "sleep")

STUB_OK = """#!/bin/sh
if [ "$1" != "-c" ]; then
    printf '%s\\n' "$@" > "$STUB_ARGV_FILE"
fi
printf '%s\\n' 'BOOTSTRAP_OK 3 11 linux /stub/python3'
exit 0
"""

STUB_TOO_OLD = """#!/bin/sh
printf '%s\\n' 'BOOTSTRAP_TOO_OLD 3 10 linux /stub/python3'
exit 0
"""

STUB_NO_TOMLLIB = """#!/bin/sh
printf '%s\\n' BOOTSTRAP_NO_TOMLLIB
exit 0
"""

STUB_HANG = """#!/bin/sh
sleep 30
"""

STUB_EXIT_7 = """#!/bin/sh
if [ "$1" != "-c" ]; then
    exit 7
fi
printf '%s\\n' 'BOOTSTRAP_OK 3 11 linux /stub/python3'
exit 0
"""


def _wsl(args, timeout=WSL_TIMEOUT):
    return subprocess.run(["wsl.exe", "-e", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def _wsl_sh(script, *args, timeout=WSL_TIMEOUT):
    command = ["wsl.exe", "-e", "/bin/sh", "-c", script, "sh", *args]
    return subprocess.run(command, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


@lru_cache(maxsize=None)
def _to_wsl(win_path):
    result = _wsl(["wslpath", "-a", "-u", str(win_path)])
    if result.returncode != 0 or not result.stdout.strip():
        pytest.fail(f"wslpath failed for {win_path}: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module", autouse=True)
def wsl_available():
    if shutil.which("wsl.exe") is None:
        pytest.skip("wsl.exe is not available")
    try:
        probe = _wsl(["sh", "-c", "echo wsl-ok"], timeout=WSL_START_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"wsl.exe did not respond: {exc}")
    if probe.returncode != 0 or "wsl-ok" not in probe.stdout:
        pytest.skip(f"wsl.exe unusable (rc={probe.returncode}): {probe.stderr.strip()}")
    yield


def _stage(tmp_path, body, names=("python3", "python")):
    """Stage a stub interpreter plus tool links inside WSL; return its PATH dir."""
    source = tmp_path / "stub"
    source.write_bytes(body.encode("utf-8"))
    result = _wsl_sh("d=$(mktemp -d) || exit 1; printf \"%s\\n\" \"$d\"")
    if result.returncode != 0 or not result.stdout.strip():
        pytest.fail(f"mktemp failed in WSL: {result.stderr.strip()}")
    stub_dir = result.stdout.strip()
    script = (
        "set -e\n"
        "src=$1\n"
        "dst=$2\n"
        "shift 2\n"
        "for tool in " + " ".join(STUB_TOOLS) + '; do ln -sf "/usr/bin/$tool" "$dst/$tool"; done\n'
        'for name in "$@"; do cp "$src" "$dst/$name"; chmod 755 "$dst/$name"; done\n'
    )
    result = _wsl_sh(script, _to_wsl(source), stub_dir, *names)
    if result.returncode != 0:
        pytest.fail(f"stub staging failed: {result.stderr.strip()}")
    return stub_dir


def _run_launcher(args, *, bin_path, env=None, workdir=None, timeout=WSL_TIMEOUT):
    assignments = ["PATH=" + bin_path]
    for key, value in (env or {}).items():
        assignments.append(f"{key}={value}")
    command = [
        "/usr/bin/env",
        "-i",
        *[shlex.quote(item) for item in assignments],
        "/bin/sh",
        shlex.quote(_to_wsl(SCRIPT)),
        *[shlex.quote(arg) for arg in args],
    ]
    inner = " ".join(command)
    if workdir is not None:
        inner = f"cd {shlex.quote(workdir)} && exec {inner}"
    return _wsl_sh(inner, timeout=timeout)


def _report(proc):
    assert proc.stdout.strip(), f"empty stdout (rc={proc.returncode}): {proc.stderr.strip()}"
    report = json.loads(proc.stdout)
    assert list(report) == ENVELOPE_KEYS
    assert report["schema_version"] == "preflight_report/1"
    for banned in ("/mnt/", "/usr/", "/tmp", "/home/"):
        assert banned not in proc.stdout
    return report


def _attempted(report):
    pairs = re.findall(r"([a-z0-9_ -]+)=([a-z_]+)", report["error"]["message"])
    return {key.strip(): value for key, value in pairs}


def _assert_blocked(proc, category):
    assert proc.returncode == 3, (proc.returncode, proc.stdout, proc.stderr)
    report = _report(proc)
    assert report["bootstrap"] == "blocked"
    assert report["roles"] == []
    assert report["error"]["code"] == "bootstrap_blocked"
    assert report["bootstrap_failure"] in CATEGORIES
    assert report["bootstrap_failure"] == category
    assert report["provenance"]["operation"] == "preflight_bootstrap"
    assert report["provenance"]["host"] == {"platform": "posix", "shell": "sh"}
    return report


def test_launcher_passes_a_shell_syntax_check():
    result = _wsl_sh("exec /bin/sh -n \"$1\"", _to_wsl(SCRIPT))
    assert result.returncode == 0, result.stderr


def test_no_candidate_reports_interpreter_not_found(tmp_path):
    stub_dir = _stage(tmp_path, STUB_OK, names=())
    proc = _run_launcher([], bin_path=stub_dir)
    report = _assert_blocked(proc, "interpreter_not_found")
    assert _attempted(report) == {"python3": "interpreter_not_found", "python": "interpreter_not_found"}


def test_too_old_interpreter_is_classified(tmp_path):
    stub_dir = _stage(tmp_path, STUB_TOO_OLD)
    proc = _run_launcher([], bin_path=stub_dir)
    report = _assert_blocked(proc, "interpreter_too_old")
    assert _attempted(report) == {"python3": "interpreter_too_old", "python": "interpreter_too_old"}


def test_missing_tomllib_is_classified_as_dependency_unavailable(tmp_path):
    stub_dir = _stage(tmp_path, STUB_NO_TOMLLIB)
    proc = _run_launcher([], bin_path=stub_dir)
    report = _assert_blocked(proc, "dependency_unavailable")
    assert _attempted(report) == {"python3": "dependency_unavailable", "python": "dependency_unavailable"}


def test_hanging_probe_is_bounded_and_classified(tmp_path):
    stub_dir = _stage(tmp_path, STUB_HANG)
    started = time.monotonic()
    proc = _run_launcher(["-t", "2"], bin_path=stub_dir, timeout=45)
    elapsed = time.monotonic() - started
    report = _assert_blocked(proc, "probe_timeout")
    assert _attempted(report) == {"python3": "probe_timeout", "python": "probe_timeout"}
    assert elapsed < 30


def test_probe_permission_denial_stops_without_fallthrough(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    denied = stub_dir + "/denied-python"
    setup = _wsl_sh('mkdir "$1" && command -v "$1"', denied)
    assert setup.returncode == 0, setup.stderr
    assert setup.stdout.strip() == denied
    probe = _wsl(["timeout", "2", denied, "-c", "ignored"])
    assert probe.returncode == 126, probe.stderr
    proc = _run_launcher(
        ["--python", denied],
        bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    report = _assert_blocked(proc, "execution_denied")
    assert _attempted(report) == {"explicit": "execution_denied"}
    assert not argv_file.exists(), "a permission denial must not fall through"


def test_term_resistant_probe_has_a_kill_deadline(tmp_path):
    stub_dir = _stage(tmp_path, "#!/bin/sh\ntrap '' TERM\nsleep 60\n")
    started = time.monotonic()
    proc = _run_launcher(
        ["--python", stub_dir + "/python3", "-t", "1"],
        bin_path=stub_dir, timeout=20,
    )
    elapsed = time.monotonic() - started
    report = _assert_blocked(proc, "probe_timeout")
    assert _attempted(report) == {"explicit": "probe_timeout"}
    assert elapsed < 15


def test_mounted_windows_interpreter_is_rejected_without_fallthrough(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    # A mounted stub supplies the Windows probe record without relying on a
    # particular Windows Python installation or WSL interop configuration.
    candidate = tmp_path / "python.exe"
    candidate.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'BOOTSTRAP_OK 3 11 win32 C:\\stub\\python.exe'\n",
        encoding="utf-8", newline="\n",
    )
    mounted = _to_wsl(candidate)
    setup = _wsl_sh('chmod 755 "$1" && test -x "$1"', mounted)
    assert setup.returncode == 0, setup.stderr
    proc = _run_launcher(
        ["--python", mounted], bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    report = _assert_blocked(proc, "interpreter_not_found")
    assert _attempted(report) == {"explicit": "interpreter_not_found"}
    assert "Windows interpreter is not valid in this environment" in report["error"]["message"]
    assert not argv_file.exists()


def test_explicit_non_executable_file_is_denied_without_fallthrough(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    candidate = stub_dir + "/denied-python"
    setup = _wsl_sh('cp "$1/python3" "$2" && chmod 644 "$2" && test ! -x "$2"',
                    stub_dir, candidate)
    assert setup.returncode == 0, setup.stderr
    proc = _run_launcher(
        ["--python", candidate], bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    report = _assert_blocked(proc, "execution_denied")
    assert _attempted(report) == {"explicit": "execution_denied"}
    assert not argv_file.exists()


def test_ok_token_with_nonzero_probe_exit_is_rejected(tmp_path):
    stub_dir = _stage(tmp_path, STUB_OK.replace("exit 0", "exit 7"))
    proc = _run_launcher(["--python", stub_dir + "/python3"], bin_path=stub_dir)
    report = _assert_blocked(proc, "dependency_unavailable")
    assert _attempted(report) == {"explicit": "dependency_unavailable"}


def test_valid_interpreter_receives_absolute_helper_path_and_arguments(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    proc = _run_launcher(
        ["--", "--check-local-router"],
        bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
        workdir="/tmp",
    )
    assert proc.returncode == 0, proc.stderr
    assert argv_file.is_file(), "the resolved interpreter never ran"
    recorded = argv_file.read_text(encoding="utf-8").split()
    assert recorded[0].startswith("/"), recorded
    assert recorded[0].endswith("development-delegation/scripts/router_preflight.py")
    assert recorded[1:] == ["--check-local-router"]


def test_global_skill_python_record_is_honoured(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    proc = _run_launcher(
        [],
        bin_path=stub_dir,
        env={"GLOBAL_SKILL_PYTHON": stub_dir + "/python3", "STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    assert proc.returncode == 0, proc.stderr
    assert argv_file.is_file(), "the configured interpreter record was ignored"


def test_helper_exit_status_is_forwarded(tmp_path):
    stub_dir = _stage(tmp_path, STUB_EXIT_7)
    proc = _run_launcher([], bin_path=stub_dir)
    assert proc.returncode == 7, (proc.returncode, proc.stdout, proc.stderr)


def test_explicit_windows_path_is_rejected_without_fallthrough(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    proc = _run_launcher(
        ["--python", r"C:\Python312\python.exe"],
        bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    report = _assert_blocked(proc, "interpreter_not_found")
    assert _attempted(report) == {"explicit": "interpreter_not_found"}
    assert not argv_file.exists(), "an explicit failure must not fall through"


def test_explicit_missing_path_is_reported_without_fallthrough(tmp_path):
    argv_file = tmp_path / "argv.txt"
    stub_dir = _stage(tmp_path, STUB_OK)
    proc = _run_launcher(
        ["--python", "/nonexistent/python3"],
        bin_path=stub_dir,
        env={"STUB_ARGV_FILE": _to_wsl(argv_file)},
    )
    report = _assert_blocked(proc, "interpreter_not_found")
    assert _attempted(report) == {"explicit": "interpreter_not_found"}
    assert not argv_file.exists(), "an explicit failure must not fall through"
