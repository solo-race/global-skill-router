# Delegation preflight (retired)

Retired: 2026-10-01.

OpenCodex live experiments showed that normal delegated execution does not need a
separate static route-readiness gate. The active `development-delegation` Skill now
relies on native Codex/OpenCodex role registration and native dispatch, so this
implementation is kept only as a historical artifact.

Contents:

- `router_preflight.py` and `bootstrap.ps1` / `bootstrap.sh` — the static route and
  launcher implementation.
- `references/preflight-report.md` and `references/runtime-receipt.md` — the report and
  receipt contract it produced.
- `*_legacy_tests.py` — the original suites, renamed so they are not collected by the
  default pytest surface.

`development/legacy/` is never part of the managed Skill payload. Reconnecting any of
this code to the active runtime requires a new explicit requirement and review.
