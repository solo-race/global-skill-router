# Output Schema

Shape of the default human-review packet and of the gated canonical-candidate mode. The core
packet is domain-neutral: industry relevance, process chains, classifications, and similar
extensions enter only through `profile_extensions`, named and interpreted by the active profile
under [profile-contract.md](profile-contract.md).

## Contents

- [Core review packet](#core-review-packet)
- [sources entries](#sources-entries)
- [findings entries](#findings-entries)
- [Evidence gaps](#evidence-gaps)
- [Canonical candidates (gated)](#canonical-candidates-gated)
- [Profile extensions](#profile-extensions)
- [Forbidden output](#forbidden-output)

## Core review packet

```yaml
review_packet:
  subject:
    type: ""             # the profile's subject_type
    name: ""
    identifiers: {}      # caller-supplied canonical IDs only; empty standalone
    locations: []
  metadata:
    investigated_at: "YYYY-MM-DD"
    languages_used: []
    coverage_summary: ""
    manual_review_reasons: []
  sources: []
  findings: []
  evidence_gaps: []
  profile_extensions: {}
```

This packet is complete on its own. It requires no external store, schema, or pipeline to be
valid.

## sources entries

Each `sources[*]` records exactly:

| Field | Meaning |
|---|---|
| `url` | Retrieved source location; review reference, not a canonical ID |
| `source_kind` | One taxonomy kind from evidence-taxonomy.md |
| `retrieval_status` | `accessible` / `partial` / `failed` |
| `title` | Source title when available |
| `publication_date` | Null when unknown; never guessed |
| `accessed_at` | Retrieval timestamp |
| `excerpt` | Bounded text quoted from the retrieved body only |
| `locator` | Paragraph/section pointer when available |
| `subject_match` | `direct` / `indirect` / `ambiguous` |
| `discovery_only` | True for unretrieved leads such as bare search hits |

## findings entries

Each `findings[*]` records exactly:

- `fact_type` — profile-meaningful claim category;
- `claim` — the reconstructed statement;
- `evidence_state` — one of the four states;
- `source_urls` — must point at entries in `sources`;
- `reasoning` — interpretation lives here, never inside excerpts;
- `review_required`.

Rules: `discovery_only` URLs cannot support `confirmed`. `partial`/`failed` records may explain
gaps but cannot support `confirmed` or `inferred` claims. A finding is a review candidate, not an
exported canonical fact.

## Evidence gaps

Each `evidence_gaps[*]` carries `question`, `state` (one of the four states), and `reason`.
Failed or partial retrieval explains a gap; it never resolves one.

## Canonical candidates (gated)

Canonical Fact candidates exist only when the caller supplies canonical source records carrying
stable identifiers that the active pipeline binding declares usable. Then:

- copy identifiers exactly; never compute, hash, rename, or generate them;
- keep the same four-state vocabulary and excerpt discipline;
- candidates propose promotion for a later stage — this skill never advances a stage itself and
  never writes into a project fact store.

Without caller-supplied canonical records this section is inert, and the core packet above is the
complete output. The Core declares no consumer schema names; any mapping to consumer schemas or
identifiers belongs to the profile's project bindings.

## Profile extensions

Profiles place domain extensions exclusively under `profile_extensions`. Extensions may add
fields but must not redefine the four evidence states, the fixed `sources`/`findings` fields, or
`manual_review_reasons`.

## Forbidden output

Never emit:

- a finding with no source-bound evidence path;
- a confirmed claim supported only by a snippet, result title, model output, or visual guess;
- a negative derived from missing or failed retrieval;
- a fabricated identifier, date, quantity, relationship, or affiliation;
- numeric scores, recommendation bands, automatic exclusions, or final verdicts.
