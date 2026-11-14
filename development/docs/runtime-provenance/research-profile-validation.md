# Research profile validation

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
