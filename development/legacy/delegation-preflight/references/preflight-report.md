# Preflight report contract

## Purpose and scope

Static readiness only: preflight never issues inference requests, reads
credentials, or changes state. Catalog checks cannot prove execution/identity.

## Schema and envelope

`schema_version` is the literal `preflight_report/1`; incompatible field or enum
changes require a new version.

The JSON envelope contains `schema_version`, `bootstrap`, `bootstrap_failure`,
`provenance`, `roles`, and `error`. `roles` covers every requested identity.
`error` is null or a redacted `{code, message}` execution error;
`bootstrap_failure` is null or a category below. Each role's `evidence` contains
all six independent states; bootstrap reflects the envelope state.

| Field | Exact values |
| --- | --- |
| `bootstrap` | `ready`, `blocked`, `unknown` |
| `configuration` | `consistent`, `conflict`, `unknown` |
| `catalog` | `present`, `missing`, `ambiguous`, `unchecked`, `error` |
| `delegation` | `supported`, `unsupported`, `unknown` |
| `endpoint` | `reachable`, `unreachable`, `unchecked` |
| `runtime_route` | `verified`, `unverified`, `mismatch` |

Static preflight never produces `verified`; `runtime_route` defaults to
`unverified`. Only scoped passive runtime evidence supplies verification.
The verification context, expected-route mapping and evaluation order are
defined in [runtime-receipt.md](runtime-receipt.md).

## Per-role record

Include all fields. Unknown scalars are null with `unresolved_layers` entries.

| Field | Required content |
| --- | --- |
| `role_id` | Exact requested identity. |
| `registration_source` | Redacted source/key; runtime roles, not templates, are authoritative. |
| `profile_path`, `profile_hash` | Logical/redacted path and SHA-256 of inspected profile bytes, or unknown. |
| `declared_model_slug` | Exact slug; no alias/provider inference. |
| `declared_overrides` | Model/provider overrides; distinguish absent from unreadable. |
| `inherited_configuration` | Inherited values, layers and limitations. |
| `effective_values` | Values established by supported effective-config evidence/host semantics only. |
| `codex_provider_identity` | Codex-facing identity, not upstream identity. |
| `endpoint_classification` | Loopback/remote/unknown shape, no raw URL. Loopback does not identify OpenCodex. |
| `delegation_evidence` | v1/v2 interface, host/version/baseline if known, feature state, registration, catalog capability and supplied passive child evidence. |
| `router_evidence` | Router identity/version and narrow redacted mapping evidence, otherwise unknown. |
| `evidence` | Six states above. |
| `unresolved_layers` | Unresolved layers/scope, including unsupplied CLI, project, policy or session overrides. |
| `reason_codes` | Stable failure/uncertainty codes. |

Evaluate overrides. Direct/router paths need distinct evidence. v1 does not
require v2; removing a v2 gate does not establish v1 support.

## Route and interface resolution

Each role's effective provider is its own `model_provider`, else the active
config's, else `openai`. A loopback http(s) `/v1` base URL is a **router** route;
a remote http(s) base URL is a **direct** route; no resolvable provider or URL is
**unresolvable**. Direct and router routes are distinct evidence, and neither is
an error by itself.

The host's selected interface is `v2` when `features.multi_agent_v2.enabled` is
true, else `v1` when `features.multi_agent` is true, else `none`. Delegation is
`supported` when the catalog entry's advertised `multi_agent_version` equals the
selected interface, `unsupported` when the host has delegation disabled, and
`unknown` when the entry is absent, ambiguous or advertises a different
interface. A mismatch is unverified evidence, never a block: a route is never
required to advertise `v2` because the host uses `v1`, and `v1` support is never
assumed for an entry that does not advertise it.
Endpoint evidence is gathered for router routes only: `--check-local-router`
probes the loopback catalog alone, so a direct route's endpoint stays `unchecked`.

## Bootstrap failures and reason codes

Exact bootstrap categories: `interpreter_not_found`,
`interpreter_too_old`, `dependency_unavailable`, `execution_denied`,
`probe_timeout`, and `helper_failed`. They describe execution, not provider
availability. Execution denial stops the affected operation.

The bootstrap-failure envelope carries exactly `schema_version`, `bootstrap`,
`bootstrap_failure`, `provenance`, `roles`, and `error`: the schema literal,
`bootstrap: blocked`, one category above, redacted bootstrap provenance,
`roles: []` because no role inspection ran, and a redacted execution error.
Consumers must treat the nonzero exit as failure while still reading the category.

Use stable lowercase `snake_case` codes; never repurpose meanings.

| Code | Meaning |
| --- | --- |
| `role_not_registered` | Unregistered identity. |
| `profile_missing` | Absent profile. |
| `profile_unreadable` | Unreadable/unparseable profile. |
| `catalog_missing` | Absent catalog. |
| `catalog_entry_missing` | No exact-slug entry. |
| `catalog_entry_ambiguous` | Multiple exact-slug entries. |
| `catalog_malformed` | Unparseable/unsupported structure. |
| `provider_override_unknown` | Unresolved override path. |
| `provider_route_unsupported` | Known unsupported route. |
| `session_override_unknown` | Unresolved session overrides. |
| `router_mapping_unknown` | Inadequate mapping evidence. |
| `bootstrap_blocked` | Bootstrap prevents inspection. |
| `endpoint_unreachable` | Endpoint check failed. |
| `config_unreadable` | Active Codex config absent or unparseable. |
| `catalog_unchecked` | No model catalog configured for the active profile. |
| `profile_name_mismatch` | Profile `name` differs from the registered identity. |
| `delegation_disabled` | Sub-agent delegation is disabled in the active config. |
| `delegation_interface_mismatch` | Catalog entry does not advertise the host's selected interface. |
| `internal_error` | Helper failed unexpectedly; detail withheld. |
| `interrupted` | Inspection interrupted; exit `130`. |
| `receipt_stale` | Supplied receipt no longer binds to the current config, catalog or profile. |
| `receipt_mismatch` | Supplied receipt disagrees with the resolved route class, declared slug or expected upstream pair. |
| `receipt_other_session` | Supplied receipt belongs to another session and is history only. |
| `receipt_expired` | Supplied receipt is outside the configured retention window and is history only. |
| `receipt_invalid` | Receipt input is missing required invocation context, unreadable, unsupported or malformed; exit is nonzero. |

## Exit semantics

`0`: complete report produced; consumers must still read readiness fields.
Nonzero: bootstrap/internal execution failure; machine-readable error when
possible. `130`: interrupted.

`--role` selects each requested identity, repeated once per identity; the report
covers exactly those identities and defaults to `scout`, `implementer` and
`tester`. When the active config cannot be read, or the helper fails
unexpectedly, the envelope carries an `error` code and one all-unknown record per
requested identity with a nonzero exit. A bootstrap failure and an interrupt
emit an empty `roles` list instead: bootstrap runs before inspection, and an
interrupt may occur at any point. An unusable supplied receipt reports
`receipt_invalid` with a nonzero exit while still emitting each role's static
record.

## Consumer dispatch decision

Compute eligibility per role per operation from current scoped evidence and
explicit operation requirements. Apply in order:

| Condition | May dispatch? |
| --- | --- |
| Bootstrap not ready, unregistered/unusable role, configuration conflict, delegation unsupported or runtime mismatch | No. |
| Configuration/delegation unknown, or required evidence missing, ambiguous, unchecked, erroneous or stale | No; obtain evidence. |
| Required endpoint unreachable or required runtime verification unverified | No. |
| Bootstrap ready, registered usable role, configuration consistent, delegation supported and all required catalog/endpoint/runtime evidence satisfied | Yes, within existing authorization for that operation/identity. |

Omitting endpoint/runtime requirements never upgrades evidence. A retained
legacy `available` boolean means eligibility for the recorded operation and
requirements only: convenience-only, never runtime verification. An active
inference probe is separate and requires explicit approval.

`available` is computed from the six evidence states plus registration:
`configuration: consistent`, `delegation: supported`, `catalog: present`, no
`endpoint: unreachable`, and no missing required live route. It never replaces
`runtime_route`.

`reason_codes` carries only concrete failures or uncertainties for that role;
unobservable CLI, project and host-policy layers are recorded in
`unresolved_layers`. An unresolved session override is reported as
`session_override_unknown`.

## Invalidation and provenance

`provenance` records time, roles, operation/requirements, input references,
interpreter version/redacted executable, host/session context, scope and limits.
Attribute role inputs. Passive receipts correlate role/session, request ID,
timestamp, slug, route decision and upstream provider/model; record attribution
limits. Timestamps or markers alone are insufficient. Apply a receipt only in
the verification context defined by [runtime-receipt.md](runtime-receipt.md),
including its session, retention, current-byte bindings and sourced route
mapping; out-of-scope receipts are history only.

Retain evidence only within scope. Invalidate stale success when role,
configuration, catalog or router identity changes. Do not reuse a prior
session's success without matching context. Transient failure invalidates
only affected roles/evidence, never permanently bans an identity for the session.
Never fall back implicitly to another identity/model; changes remain explicit
under the owner's approval policy.

## Redaction

No credentials, environment values, absolute repository paths or usernames in
reports/errors. Use sanitized logical references, never raw exceptions/URLs or
broad router configuration. Missing safe evidence remains unknown.
