# Knowledge Sources

This file governs VBA knowledge provenance. Paths in this bundle resolve from
the `runtime-ops` root. Provider ABI and execution policy remain owned by
`adapters/vba-office.md`.

## Source Priority

The authoritative source for a claim is the Microsoft reference that
documents the object or member owning the claim. Rank candidate sources
by claim type:

### Host-specific claims (Access or Excel behavior)

1. the owning host's object-model reference (Microsoft Access VBA Object
   Model Reference for Access claims, Microsoft Excel VBA Object Model
   Reference for Excel claims);
2. the component-library reference for the embedded object family
   (Microsoft DAO Reference for DAO data access; Microsoft Forms/MSForms
   reference for UserForm controls);
3. Microsoft VBA Language Reference.

Example: form synchronization through `Form.RecordsetClone` resolves to the
Access reference; the `FindFirst`/`NoMatch` contract resolves to the DAO
Reference.

### Language/runtime-generic claims

1. Microsoft VBA Language Reference;
2. host references, only where a host documents modified generic behavior.

### Fallbacks (both tracks, below every documentation tier)

- controlled experiments on identified synthetic/dev fixtures through the
  vba-doctor tools;
- vba-lint generic static analysis (generic VBA only, never runtime state);
- community sources for discovery only.

Within a track, a lower-ranked source never overrides a higher-ranked one
for the same claim. When an interaction spans two layers (a host object
plus a component library), each reference governs its own layer; an
apparent conflict between them is settled by controlled experiment, not
by rank.

## Evidence Types

Every knowledge entry carries exactly one classification:

### `documented_fact`

Directly supported by a Microsoft documentation tier from the applicable
priority list above.

### `evidence_based_inference`

Derived from documented facts plus observed code or state.

Do not present an inference as if Microsoft explicitly documented it.

### `verified_empirical_behavior`

Observed in a controlled reproduction where documentation is incomplete.

Record the relevant environment (host application, version, fixture) and test conditions.

### `project_convention`

Specific to one consuming project.

Never promote it to a generic rule without evidence.

### `community_guidance`

Useful for discovering candidate issues or solutions.

It must not become a normative rule without primary-source support or a controlled reproduction.

## Knowledge Entry Principle

Separate, inside each entry:

```text
documented behavior
        |
        v
engineering inference
        |
        v
development guidance
```

Example:

```text
Documented fact:
.Text requires control focus.

Inference:
Reading .Text after focus moves may fail.

Guidance:
Use .Value when committed value is intended, while preserving .Text
when in-progress focused text is actually required.
```

## Entry Metadata Template

Each entry in a reference file uses:

```markdown
### <claim>

Behavior: <one-paragraph description of the behavior>

Evidence: <evidence type>

Source: <authority> - <document title> - <object/member> (<URL>, last verified YYYY-MM-DD)

Guidance: <what the agent must do differently>
```

For entries sourced from controlled experiments, name the fixture used
(a controlled `.accdb` or `.xlsm`, with its recorded local path) and the
vba-doctor tool sequence.

## Adding Knowledge

Before adding an entry, ask whether it will change an agent's decision.
If not, do not add it. Migrated project conventions retain their original
classification; migration does not turn them into independently verified facts.
