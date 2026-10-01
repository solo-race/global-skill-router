# Passive runtime receipt contract

A passive runtime receipt is sanitized routing evidence a session already
observed: which route a child took and which upstream model the router reported.
It is the only evidence that can mark a role's `runtime_route` as `verified`.
A receipt is routing evidence, not proof of the remote model's identity, and
supplying one never triggers a probe or an inference request.

## Schema

`schema_version` is the literal `runtime_receipt/1`. Unknown extra keys are
ignored; every key below is required.

| Key | Content |
| --- | --- |
| `role_id` | Registered identity the receipt belongs to. |
| `session_id` | Session that observed it; must equal the current `--session-id`. |
| `request_id` | Request identifier from the routing layer. |
| `requested_slug` | Exact model slug the child requested. |
| `route_decision` | Constrained token `router` or `direct`. |
| `upstream_provider` | Provider the router reported. |
| `upstream_model` | Upstream model the router reported. |
| `observed_at` | Parseable UTC ISO-8601 timestamp. |
| `bindings.config_sha256` | SHA-256 of the active `config.toml` bytes. |
| `bindings.catalog_sha256` | SHA-256 of the configured catalog bytes, or null when none is configured. |
| `bindings.profile_sha256` | SHA-256 of that role's profile bytes. |
| `source` | Short label for where the receipt came from. |

## Verification context and expected route

Pass receipts with `--receipt PATH`, repeatable, together with the current
`--session-id ID`. Supplying a receipt without a session ID is an input error.
`--receipt-max-age-seconds` sets the retention window and defaults to 86400.
Receipts from another session or older than that window are history only: they
are not applied as evidence. `request_id` remains attribution evidence because
a static check cannot observe the current request ID.

The expected upstream pair is always sourced from the resolved route:

- For a `router` route, resolve the role's exact declared slug to its catalog
  entry. Its `opencodex_capability_provenance` must be an object with non-empty
  `provider` and `model_id` values; those values are the expected upstream
  provider and model.
- If that router catalog entry has absent, null, empty or incomplete
  provenance, the mapping is unsourced. Keep `runtime_route` unverified and
  record `router_mapping_unknown`.
- For a `direct` route, the expected pair is the effective provider key and the
  declared slug, sourced from `config.toml` and the role profile. No router
  transforms the slug on a direct route.

Never infer or guess an upstream mapping. A missing, ambiguous, unchecked or
erroneous catalog entry retains its existing catalog/delegation evidence and
cannot receive receipt verification.

## Matching and precedence

Receipt input is rejected as `receipt_invalid` if it is unreadable, has an
unsupported schema, uses a `route_decision` other than `router` or `direct`, or
has an `observed_at` value that is not a parseable UTC ISO-8601 timestamp. No
receipt evidence is applied after an input error. Only receipts whose `role_id`
equals the role are considered for it, and each is evaluated in this order:

1. `session_id` differs from the current session: `receipt_other_session`;
   the receipt is history only.
2. `observed_at` is older than the retention window: `receipt_expired`; the
   receipt is history only.
3. Any binding differs from the current config, catalog or profile bytes:
   `receipt_stale`; the receipt is not applied.
4. `route_decision` differs from the role's resolved route class:
   `receipt_mismatch`.
5. `requested_slug` differs from the role's declared slug:
   `receipt_mismatch`.
6. The reported upstream provider/model pair differs from the sourced expected
   pair: `runtime_route` is `mismatch` and `receipt_mismatch` is recorded.
7. Otherwise `runtime_route` is `verified`, and the receipt's session,
   request, timestamp, slug, route decision and upstream are recorded as
   attribution evidence in `delegation_evidence.passive_child_evidence`.

Verification therefore requires the current session, an in-window timestamp,
all three current-byte bindings, the declared slug, the resolved route class,
and the complete sourced upstream pair to match. `mismatch` outranks
`verified`, and the newest `observed_at` wins among verified receipts.

Supplying `--receipt` adds `runtime` to `provenance.requirements`, so a role
is eligible only while its `runtime_route` is `verified`. A receipt never
upgrades another missing evidence state: configuration, catalog and delegation
must still satisfy the dispatch decision in
[preflight-report.md](preflight-report.md).

A receipt input error reports `receipt_invalid`, applies no receipt evidence,
still emits every requested role record with its static evidence, and exits
nonzero.

## Boundaries

Passive receipts are the only runtime evidence preflight consumes. An active
child probe is a separate opt-in action that requires explicit operator
approval, bounded scope and a stated cost and uncertainty, and it is never added
to a session automatically. A unique response marker proves association only,
never model identity, and static preflight never issues inference.
