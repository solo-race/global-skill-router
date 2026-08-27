# Profile Contract

`profiles/<domain>.yaml` is part of the framework ABI: a closed, versioned, machine-checkable
extension surface between the Core and a domain problem model. The Core reads only what this
contract defines. The fixed field set below is closed: an unknown top-level key fails the
mechanical gate rather than being tolerated as prose.

## Target shape

```yaml
profile_schema_version: 1
domain: <kebab-case>              # equals the profile file slug
subject_type: <string>            # the profile's subject model headline
investigation_dimensions:
  - id: <stable-id>
    purpose: <why this dimension changes review>
concept_groups: {}                # map of group name -> term list; may be empty, type fixed
query_examples: []                # list of strings; may be empty, type fixed
vocabulary_authority: null        # null, or the name of a project binding
relevance: null                   # null, or a review-hypothesis labeling block
packet_extensions: {}             # named extensions placed under review_packet.profile_extensions
pipeline_binding: null            # null => review_packet_only
project_bindings: {}              # each entry declares owner/required/when_unavailable (+ reference)
profile_guidance: {}              # named profile-owned guidance blocks; the only home of
                                  # load-bearing profile-local semantics
display: {}                       # presentation hints only; no semantic weight
```

## Field rules

Each rule is phrased for mechanical checking.

1. `profile_schema_version`: integer. Unsupported versions fail the gate and stop loading — never
   guess forward compatibility.
2. `domain`: kebab-case string equal to the profile file slug.
3. `subject_type`: non-empty string naming the kind of subject this profile models.
4. `investigation_dimensions`: non-empty list; every entry carries a unique, stable `id` and a
   `purpose`. The Core knows no dimension names; dimensions are opaque to it.
5. `concept_groups` / `query_examples`: present with fixed types (mapping / list); may be empty.
6. `vocabulary_authority`: null or the name of an entry under `project_bindings`; when null, only
   profile vocabulary drives discovery. Anti-drift: when consuming-project vocabulary authority
   is intended, the field must reference that binding key — a defined binding that is never
   referenced cannot take effect.
7. `relevance`: null or a mapping defining qualitative review-hypothesis labels only — never
   scores, rankings, or decision thresholds.
8. `packet_extensions`: each named extension states where it sits (`profile_extensions.<key>`)
   and may only add fields there. Extensions must not redefine evidence states, the fixed
   `sources`/`findings`/`evidence_gaps` fields, or `manual_review_reasons`.
9. `pipeline_binding`: null (default behavior `review_packet_only`) or a mapping declaring `mode`
   plus `reference_stages`, `consumes`, `produces`, and `never_promotes_to` boundaries.
   Stage names are caller topology labels, never Core constants.
10. `project_bindings`: every entry MUST declare `owner`, `required`, and `when_unavailable`.
    Bare paths or config references carry no implicit contract. `owner` names who resolves the
    referenced object (typically `consuming_project`). `required: true` is valid only where the
    caller explicitly selected a mode making that object a precondition. `when_unavailable` names
    the complete degraded behavior, e.g. `review_packet_only` or `use_profile_vocabulary_only`.
11. `profile_guidance`: mapping of named, self-documenting guidance blocks. This namespace is the
    only allowed home of load-bearing profile-local semantics: anything that changes agent
    decisions (approved languages, domain lenses, consumer term mappings) belongs here. Blocks
    are profile-owned and typed by the profile; the gate checks only that the namespace is a
    mapping. Blocks must not redefine or override any Core semantic, evidence state, output
    field, or the human-review terminal boundary.
12. Unknown top-level keys are a contract violation: unknown load-bearing semantics are never
    silently ignored and never guessed. Presentation-only hints go under `display`.

## Registered guidance blocks

These block names are recognized by the Core workflow and carry the semantics below. New block
names are permitted; they are profile-owned and do not extend the Core ABI beyond this namespace.

| Block | Responsibility |
|---|---|
| `language_policy` | Which languages and aliases are executable, and under which approval gates (consumed by the Core's bounded-discovery/language-expansion step and the language gates in [evidence-taxonomy.md](evidence-taxonomy.md)). |
| `domain_model` | Optional interpretive lens for organizing queries (e.g. a processing chain); a lens only — findings stay organized by `investigation_dimensions`, and it never defines or replaces Core semantics. |
| `terminology_map` | Mapping of consuming-project terms to framework concepts; identifiers it names remain copy-only, never derived. |

## Ownership and absence semantics

The framework owns none of the external objects a binding references — no schemas, stores,
configuration files, or pipeline stages. Missing bindings degrade; they never disable the Core.
With every binding unavailable, the framework still produces the complete review packet defined
in [output-schema.md](output-schema.md). Degradation targets come only from explicit
`when_unavailable` declarations.

## Mechanical enforcement status

The gate is implemented in `development/tools/validate_skills.py` (`profile_errors`) and runs
automatically for every manifest entry (active or planned) whose skill directory contains a
`profiles/` directory. It checks mechanically: schema version equality (a missing or unsupported
version fails and blocks activation), domain slug equality and kebab-case, non-empty
`subject_type`, non-empty and unique dimension ids, `concept_groups`/`query_examples` container
types, binding triple presence and `required` boolean type, `vocabulary_authority` resolution
against `project_bindings`, packet extension placement under `profile_extensions.*`,
`pipeline_binding` shape, the closed top-level field set, and `profile_guidance`/`display`
container types.

The gate does NOT check whether externally referenced binding objects (e.g. a consuming
project's schema or config files) exist: that is runtime/binding resolution, not structural
validation. A profile passing the gate is machine-validated for its ABI, not for the existence
of any consuming-project resource.
