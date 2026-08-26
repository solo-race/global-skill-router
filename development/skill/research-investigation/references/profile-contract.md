# Profile Contract

`profiles/<domain>.yaml` is part of the framework ABI: a versioned, machine-checkable extension
surface between the Core and a domain problem model. The Core reads only what this contract
defines; everything else in the file is profile-local guidance.

## Target shape

```yaml
profile_schema_version: 1
domain: <kebab-case>
subject_type: <string>
investigation_dimensions:
  - id: <stable-id>
    purpose: <why this dimension changes review>
concept_groups: {}        # map of group name -> term list; may be empty, type fixed
query_examples: []        # list of strings; may be empty, type fixed
vocabulary_authority: null   # null, or the name of a project binding
relevance: null           # null, or a review-hypothesis labeling block
packet_extensions: {}     # named extensions placed under review_packet.profile_extensions
pipeline_binding: null    # null => review_packet_only
project_bindings: {}      # each entry declares owner/required/when_unavailable (+ reference)
display: {}               # presentation hints; no semantic weight
```

## Field rules

Each rule is phrased for mechanical checking.

1. `profile_schema_version`: integer. Unknown version means stop loading — never guess forward
   compatibility.
2. `domain`: kebab-case string equal to the profile file slug.
3. `investigation_dimensions`: non-empty list; every entry carries a unique, stable `id` and a
   `purpose`. The Core knows no dimension names; dimensions are opaque to it.
4. `concept_groups` / `query_examples`: present with fixed types (mapping / list); may be empty.
5. `vocabulary_authority`: null or the name of an entry under `project_bindings`; when null, only
   profile vocabulary drives discovery.
6. `relevance`: null or a mapping defining qualitative review-hypothesis labels only — never
   scores, rankings, or decision thresholds.
7. `packet_extensions`: each named extension states where it sits (`profile_extensions.<key>`)
   and may only add fields there. Extensions must not redefine evidence states, the fixed
   `sources`/`findings` fields, or `manual_review_reasons`.
8. `pipeline_binding`: null (default behavior `review_packet_only`) or a mapping declaring `mode`
   plus its `reference_stages`, `consumes`, `produces`, and `never_promotes_to` boundaries.
   Stage names are caller topology labels, never Core constants.
9. `project_bindings`: every entry MUST declare `owner`, `required`, and `when_unavailable`.
   Bare paths or config references carry no implicit contract. `owner` names who resolves the
   referenced object (typically `consuming_project`). `required: true` is valid only where the
   caller explicitly selected a mode making that object a precondition. `when_unavailable` names
   the complete degraded behavior, e.g. `review_packet_only` or `use_profile_vocabulary_only`.
10. Unrecognized fields carrying apparent semantic weight cause a stop-and-confirm, not a silent
    skip: unknown load-bearing semantics are never ignored.

## Extra sections

Profiles may add top-level sections beyond the fixed set (language policy, domain models, and so
on). Such sections are profile-local guidance, must be self-documenting inline, and must not
redefine or override any Core semantic.

## Ownership and absence semantics

The framework owns none of the external objects a binding references — no schemas, stores,
configuration files, or pipeline stages. Missing bindings degrade; they never disable the Core.
With every binding unavailable, the framework still produces the complete review packet defined
in [output-schema.md](output-schema.md). Degradation targets come only from explicit
`when_unavailable` declarations.

## Mechanical enforcement status

Every rule above is mechanically checkable: version equality against known integers, kebab-case
pattern match, required-field presence, dimension id uniqueness, binding triple presence, enum-
style value membership, and placement checks on extensions. In P1 the platform validator does not
yet parse profiles; enforcement of these gates is deferred to the P3 lifecycle gate, where it must
exist before any profile-carrying skill can turn active. Until then this contract is normative for
authors and reviewers, and a profile passing only prose review must not be described as a fully
machine-validated ABI.
