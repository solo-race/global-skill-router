# Verification Model Contract

This file defines the contract every adapter's verification model must satisfy. The filename persists from earlier platform planning, but the concept is adapter-defined: there is no universal verification ladder, and strength ordering is an adapter-local decision. Mechanical enforcement of this contract belongs to the platform lifecycle gate applied before an adapter is activated; until that gate exists, the contract is normative for adapter authors and reviewers.

## Model

Every adapter MUST declare:

```yaml
verification_model:
  kind: linear | partial_order | independent_checks
  states:
    - id: <stable-id>
      meaning: <what this state proves>
      required_evidence: [<observable evidence>]
      does_not_prove: [<explicit non-claims>]
  relations: []
  unsupported: []
```

Kind semantics:

- `linear` — states form one total order; achieving a state implies every weaker state.
- `partial_order` — some states are ordered, others incomparable; declared edges carry the only implications.
- `independent_checks` — no state implies another; every claim stands entirely on its own evidence.

## States

- `id`: stable identifier, reused verbatim in reports and logs.
- `meaning`: what reaching the state proves, in one sentence.
- `required_evidence`: observable artifacts a run must produce; each item names its source (operation result, reread output, observation record).
- `does_not_prove`: explicit non-claims. Enumerate the tempting over-readings (for example, that a syntax check proves runtime behavior); reports are held against this list.

## Evidence requirements

Evidence proves only the scope its state declares. Two states may share one evidence item only when the adapter declares that equivalence explicitly. A successful mutation is evidence solely for the mutation's own completion; it never substitutes for a downstream state's evidence. Precondition or permission failures trigger the adapter-declared downgrade or unverified outcome, and the original failure text is preserved verbatim in the report.

## Relations

For `linear`, the order itself implies implication; state the chain once. For `partial_order`, list directed edges explicitly; incomparable pairs prove nothing about each other. For `independent_checks`, `relations` is empty by construction.

## Unsupported states

A state the adapter cannot reach with its registered operations MUST appear in `unsupported` together with the reason. Unsupported is a reportable value, never an omission: claims about such a state are reported as unverified with the reason, and no alternate evidence may quietly promote them.

## Reporting

Iron rule: never report a higher or stronger verification state than the evidence actually achieved.

- `linear` models may report the single highest achieved level; weaker levels are implied by the declared order.
- `partial_order` and `independent_checks` models MUST report each state individually as achieved or unverified; collapsing them into one top-level claim is prohibited.
- Unsupported states are always named as such.
- Reports preserve original failure messages next to the achieved-state list.

Generic illustrations: a build-tool adapter may use linear `parsed < linked < exercised`; a release pipeline may use partial_order with `tested` and `scanned` both above `built` but incomparable to each other; a data migration may use independent checks `schema_valid`, `rows_migrated`, `postcondition_observed`, none implying another.

## Adapter instances

The first formal instance lives in `adapters/vba-office.md`: a `linear` model whose concrete states, required evidence, and unsupported declaration are defined there. Adapters with different kinds — including fully independent checks paired with transaction-rollback recovery — must fit this contract without modifying the Core; needing a Core edit signals an abstraction defect, not an adapter requirement.
