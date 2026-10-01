#!/bin/sh
# Thin bootstrap launcher for the development-delegation preflight helper.
#
# Purpose: discover and validate an existing Python >=3.11 interpreter that
# provides tomllib, then exec the sibling router_preflight.py with it. This
# launcher carries no preflight logic of its own: it selects an interpreter,
# classifies bootstrap failures, and forwards the helper's exit status.
#
# Discovery order, first qualifying candidate wins:
#   1. --python PATH            (explicit)
#   2. $GLOBAL_SKILL_PYTHON     (explicit)
#   3. python3
#   4. python
# An explicit candidate that is unusable is reported and stops the launcher
# without falling through. Ordinary candidates that are missing, too old or
# otherwise unusable fall through to the next one. A Windows-style path (drive
# letter or backslash) is never a valid interpreter here, and a Windows
# interpreter or Codex config path is never assumed to apply to WSL.
#
# Qualification probe (bounded by coreutils timeout, a hard dependency):
#   Imports tomllib and records version, platform and executable.
#   timeout -k 2 bounds the grace period even when a probe ignores TERM.
# Categories, all describing execution rather than provider availability:
#   interpreter_not_found, interpreter_too_old, dependency_unavailable,
#   execution_denied, probe_timeout, helper_failed
# A permission denial while launching a candidate or the helper is reported as
# execution_denied and stops the launcher instead of being worked around.
# Missing/unreadable helpers and other helper start failures are helper_failed.
#
# Failure output is one JSON document on stdout (schema preflight_report/1,
# bootstrap \"blocked" no absolute paths, usernames, environment values or
# captured stderr text) plus one short line on stderr. Exit status is the
# helper's own status on success, 3 when no interpreter qualified or the helper
# could not be started, 2 for a usage error, and 0 for --help.
#
# This launcher never installs packages, downloads an interpreter, creates a
# virtual environment, or writes repository state.

set -u

PROBE_TIMEOUT=10
PROBE="import sys;ok=sys.version_info[:2]>=(3,11) and bool(__import__('tomllib'));print('BOOTSTRAP_OK' if ok else 'BOOTSTRAP_TOO_OLD',sys.version_info[0],sys.version_info[1],sys.platform,sys.executable)"

EXPLICIT=0
EXPLICIT_PYTHON=
attempted=0
notes=
last_category=interpreter_not_found
selected=
explicit=0
failure_message="interpreter qualification or helper startup failed"
resolved_major=
resolved_minor=
resolved_platform=
resolved_executable=

usage() {
    printf '%s\n' "usage: bootstrap.sh [--python PATH] [-t SECONDS] [--] [helper arguments...]" >&2
}

emit_report() {
    category=$1
    generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null) || generated_at=unknown
    printf "{\"schema_version\": \"preflight_report/1\", \"bootstrap\": \"blocked\", \"bootstrap_failure\": \"%s\", \"provenance\": {\"generated_at\": \"%s\", \"roles\": [], \"operation\": \"preflight_bootstrap\", \"requirements\": [], \"inputs\": [\"bootstrap.sh\"], \"interpreter\": null, \"host\": {\"platform\": \"posix\", \"shell\": \"sh\"}, \"scope\": \"bootstrap\", \"limits\": \"no interpreter candidate satisfied >=3.11 with tomllib\"}, \"roles\": [], \"error\": {\"code\": \"bootstrap_blocked\", \"message\": \"%s; attempted %s: %s\"}}\n" "$category" "$generated_at" "$failure_message" "$attempted" "$notes"
    printf "%s\n" "bootstrap: blocked ($category)" >&2
    exit 3
}

note() {
    attempted=$((attempted + 1))
    last_category=$2
    if [ -z "$notes" ]; then
        notes="$1=$2"
    else
        notes="$notes, $1=$2"
    fi
}

explicit_fail() {
    if [ "$explicit" -eq 1 ]; then
        emit_report "$last_category"
    fi
    return 1
}

try_interpreter() {
    name=$1
    spec=$2
    explicit=$3
    resolved=
    out=
    status=0
    failure_message="interpreter qualification failed"

    case $spec in
        [A-Za-z]:[\\/]*|*\\*)
            failure_message="a Windows interpreter is not valid in this environment"
            printf '%s\n' "bootstrap.sh: $failure_message" >&2
            note "$name" interpreter_not_found
            explicit_fail
            return 1
            ;;
    esac

    case $spec in
        */*)
            if [ -x "$spec" ]; then
                resolved=$spec
            elif [ -e "$spec" ]; then
                note "$name" execution_denied
                emit_report execution_denied
            fi
            ;;
        *)
            resolved=$(command -v -- "$spec" 2>/dev/null) || resolved=
            ;;
    esac

    if [ -z "$resolved" ]; then
        note "$name" interpreter_not_found
        explicit_fail
        return 1
    fi

    out=$(timeout -k 2 "$PROBE_TIMEOUT" "$resolved" -c "$PROBE" 2>/dev/null)
    status=$?
    case $status in
        124|137)
            note "$name" probe_timeout
            explicit_fail
            return 1
            ;;
        126)
            printf '%s\n' "bootstrap.sh: permission denied while starting an interpreter candidate" >&2
            note "$name" execution_denied
            emit_report execution_denied
            ;;
        127)
            note "$name" interpreter_not_found
            explicit_fail
            return 1
            ;;
    esac

    if [ "$status" -ne 0 ]; then
        note "$name" dependency_unavailable
        explicit_fail
        return 1
    fi

    # read preserves spaces in the final executable field; keep this internal
    # record out of reports because it may contain a username or absolute path.
    IFS=' ' read -r probe_token resolved_major resolved_minor resolved_platform resolved_executable <<EOF
$out
EOF
    case $probe_token in
        BOOTSTRAP_OK)
            if [ -z "$resolved_major" ] || [ -z "$resolved_minor" ] ||
               [ -z "$resolved_platform" ] || [ -z "$resolved_executable" ]; then
                note "$name" dependency_unavailable
                explicit_fail
                return 1
            fi
            if [ "$resolved_platform" = win32 ]; then
                failure_message="a Windows interpreter is not valid in this environment"
                note "$name" interpreter_not_found
                explicit_fail
                return 1
            fi
            selected=$resolved
            return 0
            ;;
        BOOTSTRAP_TOO_OLD)
            note "$name" interpreter_too_old
            ;;
        *)
            note "$name" dependency_unavailable
            ;;
    esac
    explicit_fail
    return 1
}

while [ "$#" -gt 0 ]; do
    case $1 in
        --python)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            EXPLICIT_PYTHON=$2
            EXPLICIT=1
            shift 2
            ;;
        --python=*)
            EXPLICIT_PYTHON=${1#--python=}
            EXPLICIT=1
            shift
            ;;
        -t)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            PROBE_TIMEOUT=$2
            shift 2
            ;;
        -t*)
            PROBE_TIMEOUT=${1#-t}
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            printf '%s\n' "bootstrap.sh: unexpected argument" >&2
            usage
            exit 2
            ;;
    esac
done

case $PROBE_TIMEOUT in
    ''|*[!0-9]*)
        printf '%s\n' "bootstrap.sh: -t requires a positive integer number of seconds" >&2
        exit 2
        ;;
esac
if [ "$PROBE_TIMEOUT" -le 0 ]; then
    printf '%s\n' "bootstrap.sh: -t requires a positive integer number of seconds" >&2
    exit 2
fi

case $0 in
    */*)
        launcher_target=$0
        ;;
    *)
        launcher_target=$(command -v -- "$0" 2>/dev/null) || launcher_target=$0
        ;;
esac
launcher_dir=$(CDPATH= cd -- "$(dirname -- "$launcher_target")" && pwd -P) || {
    printf '%s\n' "bootstrap.sh: cannot resolve the launcher directory" >&2
    exit 3
}
helper=$launcher_dir/router_preflight.py

if [ ! -r "$helper" ]; then
    notes="helper=helper_failed"
    attempted=1
    last_category=helper_failed
    printf '%s\n' "bootstrap.sh: router_preflight.py is not readable beside this launcher" >&2
    emit_report helper_failed
fi

if ! command -v timeout >/dev/null 2>&1; then
    notes="timeout=helper_failed"
    attempted=1
    last_category=helper_failed
    printf '%s\n' "bootstrap.sh: coreutils timeout is required for the bounded probe" >&2
    emit_report helper_failed
fi

if [ "$EXPLICIT" -eq 1 ]; then
    try_interpreter explicit "$EXPLICIT_PYTHON" 1
elif [ -n "${GLOBAL_SKILL_PYTHON:-}" ]; then
    try_interpreter explicit "$GLOBAL_SKILL_PYTHON" 1
fi

if [ -z "$selected" ]; then
    try_interpreter python3 python3 0
fi
if [ -z "$selected" ]; then
    try_interpreter python python 0
fi

if [ -z "$selected" ]; then
    emit_report "$last_category"
fi

# A successful exec replaces the shell and discards this trap, preserving the
# helper's own exit status (including 126). Only a failed exec reaches it.
trap '
    status=$?
    case $status in
        126) category=execution_denied ;;
        *) category=helper_failed ;;
    esac
    failure_message="helper could not be started"
    note helper "$category"
    emit_report "$category"
' 0
exec "$selected" "$helper" "$@"
