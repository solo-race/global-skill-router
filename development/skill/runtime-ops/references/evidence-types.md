# Knowledge Evidence Types

Every knowledge claim carries exactly one evidence classification. The taxonomy is epistemic, not domain-specific: it travels across hosts unchanged, while adapters instantiate their own concrete source ladders beneath it.

## Types

### documented_fact

Directly supported by the domain's primary authorities (vendor references, specifications, standards). Cite authority, document title, object/member, and last-verified date.

### evidence_based_inference

Derived from documented facts plus observed code or state. Never present an inference as though the authority stated it explicitly.

### verified_empirical_behavior

Observed in a controlled reproduction where documentation is incomplete or silent. Record environment, versions, fixture, and conditions; the observation is valid only within them.

### project_convention

Specific to one consuming project. Never promoted to a general rule without additional evidence.

### community_guidance

Useful for discovering candidate issues or solutions. Must not become a normative rule without primary-source support or a controlled reproduction.

## Source priority template

For any claim, prefer sources in this order:

1. primary authority for the domain — whoever owns the authoritative documentation for the subject;
2. adjacent authority, only when applicable — a second authority whose scope genuinely overlaps the claim;
3. controlled experiments run against recorded fixtures with registered tools;
4. generic static or tool-derived evidence — structure and diagnostics, never runtime state;
5. community sources, for discovery only.

Adapters instantiate this template with named authorities (for example, which vendor reference ranks first). Binding rules:

> A lower-priority source never overrides a higher-priority one for the same claim.

> Add information only when it is likely to change an agent's decision.

If a candidate entry fails the admission threshold, drop it regardless of how interesting it is.

## Controlled-experiment discipline

Record: environment and version/build; fixture identity and path; objects or members exercised; exact tool inputs and outputs; dialog or intervention actions; observed result; evidence type; verification level reached; applicability boundary. One experiment under one configuration never generalizes beyond its recorded boundary; extending a claim requires another experiment or a primary source.

## Entry shape

Separate, inside each entry: documented behavior → engineering inference → development guidance. State the claim, its single evidence type, its source, and what the agent must do differently because of it.
