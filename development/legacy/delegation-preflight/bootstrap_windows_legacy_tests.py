"""Contract tests for the bootstrap.ps1 thin launcher.

The artifact under test is a shell script, so these are subprocess-level tests
rather than importable-module unit tests. Stub interpreters are inert .cmd files
placed on a controlled PATH, so interpreter discovery is deterministic and no
real interpreter is exercised.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
LAUNCHER = SCRIPTS_DIR / "bootstrap.ps1"
HELPER = SCRIPTS_DIR / "router_preflight.py"

PASSTHROUGH_ENVIRONMENT = frozenset(
    name.upper()
    for name in (
        "SystemRoot",
        "WINDIR",
        "SYSTEMDRIVE",
        "PATHEXT",
        "TEMP",
        "TMP",
        "PROCESSOR_ARCHITECTURE",
        "COMPUTERNAME",
        "USERPROFILE",
    )
)


def _powershell_host():
    for name in ("pwsh", "powershell.exe", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    return None


@pytest.fixture(scope="session")
def shell():
    host = _powershell_host()
    if host is None:
        pytest.skip("no PowerShell host (pwsh/powershell.exe) resolvable on PATH")
    return host


def _environment(stub_directory, argv_file=None, extra=None):
    environment = {}
    for key, value in os.environ.items():
        if key.upper() in PASSTHROUGH_ENVIRONMENT:
            environment[key] = value
    environment["PATH"] = str(stub_directory)
    environment.pop("GLOBAL_SKILL_PYTHON", None)
    if argv_file is not None:
        environment["STUB_ARGV_FILE"] = str(argv_file)
    if extra:
        environment.update(extra)
    return environment


def _write_stub(directory, name, token=None, exit_code=None, hang=False, probe_exit_code=0):
    lines = ["@echo off", 'if defined STUB_ARGV_FILE echo %* >> "%STUB_ARGV_FILE%"']
    if token is not None:
        record = token
        if token in ("BOOTSTRAP_OK", "BOOTSTRAP_TOO_OLD"):
            record += ' 3 11 win32 C:\\stub\\python.exe'
        lines.append("echo " + record)
    if hang:
        lines.append("%SystemRoot%\\System32\\ping.exe -n 10 127.0.0.1 >nul")
    lines.extend([
        'if "%~1"=="-c" exit /b ' + str(probe_exit_code),
        'if "%~2"=="-c" exit /b ' + str(probe_exit_code),
    ])
    if exit_code is not None:
        lines.append("exit /b " + str(exit_code))
    path = directory / (name + ".cmd")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
    return path


def _write_all_stubs(directory, token=None, exit_code=None, hang=False, probe_exit_code=0):
    return [
        _write_stub(directory, name, token=token, exit_code=exit_code, hang=hang,
                    probe_exit_code=probe_exit_code)
        for name in ("py", "python", "python3")
    ]


def _run(shell, arguments, environment, cwd, expression=None, timeout=120):
    if expression is None:
        command = [shell, "-NoProfile", "-NonInteractive", "-File", str(LAUNCHER)]
    else:
        command = [shell, "-NoProfile", "-NonInteractive", "-Command", expression]
    return subprocess.run(
        command + list(arguments),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        cwd=str(cwd),
        timeout=timeout,
    )


def _report(result):
    return json.loads(result.stdout)


def _recorded_arguments(argv_file):
    if not argv_file.exists():
        return []
    return [line.strip() for line in argv_file.read_text(encoding="ascii").splitlines() if line.strip()]


def _first_token(line):
    return line.split()[0].strip('"')


def _forwarded_arguments(recorded):
    """Arguments the launcher passed to the helper, after its absolute path."""
    tokens = [token.strip('"') for token in recorded[-1].split()]
    assert str(HELPER) in tokens, tokens
    return tokens[tokens.index(str(HELPER)) + 1:]


def test_no_candidate_produces_classified_report(shell, tmp_path):
    stub_directory = tmp_path / "empty"
    stub_directory.mkdir()

    result = _run(shell, [], _environment(stub_directory), tmp_path)

    assert result.returncode == 3
    report = _report(result)
    assert report["schema_version"] == "preflight_report/1"
    assert report["bootstrap"] == "blocked"
    assert report["bootstrap_failure"] == "interpreter_not_found"
    assert report["roles"] == []
    assert report["error"]["code"] == "bootstrap_blocked"
    assert "attempted 3" in report["error"]["message"]
    assert result.stderr.strip()


def test_py_launcher_candidate_is_preferred_and_gets_version_flag(shell, tmp_path):
    stub_directory = tmp_path / "pyonly"
    stub_directory.mkdir()
    _write_stub(stub_directory, "py", token="BOOTSTRAP_OK")
    argv_file = tmp_path / "argv.txt"

    result = _run(shell, [], _environment(stub_directory, argv_file), tmp_path)

    assert result.returncode == 0, result.stderr
    recorded = _recorded_arguments(argv_file)
    assert len(recorded) == 2
    assert recorded[0].startswith("-3 ")
    assert _forwarded_arguments(recorded) == []


@pytest.mark.parametrize(
    "token, expected",
    [
        ("BOOTSTRAP_TOO_OLD", "interpreter_too_old"),
        ("BOOTSTRAP_NO_TOMLLIB", "dependency_unavailable"),
    ],
)
def test_probe_token_categories(shell, tmp_path, token, expected):
    stub_directory = tmp_path / ("stubs " + expected)
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token=token)

    result = _run(shell, [], _environment(stub_directory), tmp_path)

    assert result.returncode == 3
    report = _report(result)
    assert report["bootstrap_failure"] == expected
    assert "attempted 3" in report["error"]["message"]


def test_probe_timeout_is_bounded(shell, tmp_path):
    stub_directory = tmp_path / "hanging"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, hang=True)

    started = time.monotonic()
    result = _run(shell, ["-ProbeTimeoutSeconds", "2"], _environment(stub_directory), tmp_path, timeout=90)
    elapsed = time.monotonic() - started

    assert result.returncode == 3
    assert _report(result)["bootstrap_failure"] == "probe_timeout"
    assert elapsed < 45


def test_helper_is_resolved_beside_launcher_from_unrelated_cwd(shell, tmp_path):
    stub_directory = tmp_path / "valid"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token="BOOTSTRAP_OK")
    argv_file = tmp_path / "argv.txt"
    unrelated_cwd = tmp_path / "elsewhere"
    unrelated_cwd.mkdir()

    result = _run(shell, ["-HelperArguments", "alpha"], _environment(stub_directory, argv_file), unrelated_cwd)

    assert result.returncode == 0, result.stderr
    recorded = _recorded_arguments(argv_file)
    assert _forwarded_arguments(recorded) == ["alpha"]


def test_helper_arguments_array_is_forwarded_in_order(shell, tmp_path):
    stub_directory = tmp_path / "valid array"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token="BOOTSTRAP_OK")
    argv_file = tmp_path / "argv.txt"

    expression = "& '{}' -HelperArguments @('alpha','beta')".format(LAUNCHER)
    result = _run(shell, [], _environment(stub_directory, argv_file), tmp_path, expression=expression)

    assert result.returncode == 0, result.stderr
    recorded = _recorded_arguments(argv_file)
    assert _forwarded_arguments(recorded) == ["alpha", "beta"]


def test_helper_exit_code_is_forwarded(shell, tmp_path):
    stub_directory = tmp_path / "exiting"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token="BOOTSTRAP_OK", exit_code=7)

    result = _run(shell, [], _environment(stub_directory), tmp_path)

    assert result.returncode == 7


def test_ok_token_with_nonzero_probe_exit_is_rejected(shell, tmp_path):
    stub_directory = tmp_path / "failed probe"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token="BOOTSTRAP_OK", probe_exit_code=7)
    argv_file = tmp_path / "argv.txt"

    result = _run(shell, [], _environment(stub_directory, argv_file), tmp_path)

    assert result.returncode == 3
    assert _report(result)["bootstrap_failure"] == "dependency_unavailable"
    assert "attempted 3" in _report(result)["error"]["message"]
    assert len(_recorded_arguments(argv_file)) == 3


def test_explicit_interpreter_failure_does_not_fall_through(shell, tmp_path):
    stub_directory = tmp_path / "valid fallback"
    stub_directory.mkdir()
    _write_all_stubs(stub_directory, token="BOOTSTRAP_OK")
    argv_file = tmp_path / "argv.txt"

    result = _run(
        shell,
        ["-PythonPath", str(tmp_path / "missing" / "python.exe")],
        _environment(stub_directory, argv_file),
        tmp_path,
    )

    assert result.returncode == 3
    report = _report(result)
    assert report["bootstrap_failure"] == "interpreter_not_found"
    assert report["error"]["message"].startswith("no candidate qualified; attempted 1:")
    assert _recorded_arguments(argv_file) == []


def test_environment_interpreter_record_is_used(shell, tmp_path):
    stub_directory = tmp_path / "path with space"
    stub_directory.mkdir()
    stub = _write_stub(stub_directory, "from_environment", token="BOOTSTRAP_OK")
    argv_file = tmp_path / "argv.txt"
    empty = tmp_path / "empty"
    empty.mkdir()

    environment = _environment(empty, argv_file, extra={"GLOBAL_SKILL_PYTHON": str(stub)})
    result = _run(shell, [], environment, tmp_path)

    assert result.returncode == 0, result.stderr
    recorded = _recorded_arguments(argv_file)
    assert _first_token(recorded[-1]) == str(HELPER)


def test_install_controls_disable_installation_only_in_children(shell, tmp_path, monkeypatch):
    controls = ("PYLAUNCHER_ALLOW_INSTALL", "PYLAUNCHER_ALWAYS_INSTALL")
    manager_control = "PYTHON_MANAGER_AUTOMATIC_INSTALL"
    monkeypatch.setenv(manager_control, "true")
    for name in controls:
        monkeypatch.setenv(name, "1")
    stub_directory = tmp_path / "installed runtime"
    stub_directory.mkdir()
    argv_file = tmp_path / "argv.txt"
    environment_file = tmp_path / "child-environment"
    stub = stub_directory / "py.cmd"
    stub.write_text(
        "\r\n".join([
            "@echo off",
            'echo %* >> "%STUB_ARGV_FILE%"',
            "set phase=helper",
            'if "%~2"=="-c" set phase=probe',
            'set > "%STUB_ENV_FILE%.%phase%"',
            "echo BOOTSTRAP_OK 3 11 win32 C:\\stub\\python.exe",
            "exit /b 0",
        ]) + "\r\n",
        encoding="ascii",
    )
    inherited = {name: os.environ[name] for name in (*controls, manager_control)}
    environment = _environment(stub_directory, argv_file, extra={
        **inherited,
        "STUB_ENV_FILE": str(environment_file),
        "STUB_INHERITED_VALUE": "preserved",
    })

    result = _run(shell, [], environment, tmp_path)

    assert result.returncode == 0, result.stderr
    recorded = _recorded_arguments(argv_file)
    assert len(recorded) == 2
    assert recorded[0].startswith("-3 ")
    assert _forwarded_arguments(recorded) == []
    for phase in ("probe", "helper"):
        child = dict(
            line.split("=", 1)
            for line in Path(str(environment_file) + "." + phase)
            .read_text(encoding="utf-8", errors="replace").splitlines()
            if "=" in line
        )
        child = {name.upper(): value for name, value in child.items()}
        assert all(name not in child for name in controls)
        assert child[manager_control] == "false"
        assert child["STUB_INHERITED_VALUE"] == "preserved"
        assert str(stub_directory) in child["PATH"].split(os.pathsep)
    assert {name: os.environ[name] for name in inherited} == inherited
