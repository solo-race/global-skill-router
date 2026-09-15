# Evidence Rules

Admissibility and epistemic control for investigation findings. Use this reference when deciding
whether an observation may support a finding and when assigning its evidence state. The default
output remains a human-review packet; these rules never create canonical facts inside the skill.

## Contents

- [State vocabulary](#state-vocabulary)
- [Prohibited parallel states](#prohibited-parallel-states)
- [Source admissibility](#source-admissibility)
- [Subject and claim matching](#subject-and-claim-matching)
- [Coverage failures and gaps](#coverage-failures-and-gaps)
- [Conflicts and negative claims](#conflicts-and-negative-claims)
- [Mandatory review triggers](#mandatory-review-triggers)

## State vocabulary

Assess every material question with exactly one of these four states:

| State | Use when | Required handling |
|---|---|---|
| `confirmed` | An accessible, original or authoritative source explicitly states the claim and directly identifies the subject, site, or project context. | Preserve a bounded excerpt and full source citation. |
| `inferred` | Relevant accessible evidence supports a reasoned conclusion but does not state it explicitly. | Preserve reasoning, supporting excerpts, and mandatory human review. |
| `unknown` | The reviewed coverage contains no adequate support. | Leave the value unresolved; record what was searched and why it remains unknown. |
| `conflicting` | Two or more accessible sources identifying the same subject make materially incompatible claims. | Preserve all incompatible values and excerpts; never select a winner silently. |

Routing: `confirmed`, `inferred`, and `conflicting` assessments become `findings[]` entries.
`unknown` never becomes a finding: a question without adequate support is recorded once, in
`evidence_gaps[]`, with state `unknown`, what was searched, and why support remains inadequate.
`unknown` is an epistemic state — it never means "no", "does not exist", or "not relevant".

## Prohibited parallel states

Never use `probable`, `not_verified`, `not_found`, `contradicted`, `yes`, or `no` as parallel
status values. Express those situations through `inferred`, `unknown`, or `conflicting` plus an
explicit reason. `unknown` never means "no", "does not exist", or "not relevant".

## Source admissibility

An evidence excerpt must come from a retrievable source body or document. Keep these fields when
available:

- URL and title;
- canonical source kind (see [evidence-taxonomy.md](evidence-taxonomy.md));
- `retrieval_status`: `accessible`, `partial`, or `failed`;
- access time and publication date;
- bounded excerpt and locator;
- `direct`, `indirect`, or `ambiguous` subject match;
- a review reason whenever the source is incomplete or inaccessible.

`search_result` is discovery-only. A title, snippet, ranking position, provider score, candidate
profile, or model-generated statement is never a fact excerpt. When the underlying page cannot be
accessed, retain the lead, mark the claim unresolved or review-required, and move on.

Only an identifier already minted by the caller's canonical pipeline may be copied into canonical
output. Never derive an identifier by hashing a URL and never fabricate one following any pattern.

## Subject and claim matching

Before assigning `confirmed`, check that:

- the source names or unmistakably identifies the investigated subject, one of its aliases, or its
  specific site/scope — not merely a group, family, category, or similarly named party;
- a parent-group statement is not attributed to a member unit without support;
- the excerpt describes actual status or behavior, not only aspiration, registration, a product
  category, or a service offered to others;
- the claim's scope matches the excerpt's scope: aspect, location, time period, and the
  internal/outsourced or owned/delegated boundary;
- visual similarity alone never establishes identity, branding, or process without textual or
  named-project evidence.

Use `direct` when the excerpt names or unmistakably identifies the subject. Use `indirect` only
for reasoned support. Use `ambiguous` as a review signal; never use it alone for confirmation.

## Coverage failures and gaps

Coverage failure stays visible. When a preferred source is blocked, dynamic, or partially
extracted, record the failure and continue with the next relevant lane; never silently substitute
an inaccessible primary source with a snippet, and never claim absence because a page did not
load.

Failed and partial retrievals remain audit information: they may explain why a question enters
`evidence_gaps[]` with state `unknown`, but they cannot support a negative about the subject.
Stop retrying blocked endpoints.

## Conflicts and negative claims

When accessible sources disagree — for example, one describes a capability as performed internally
while another describes it as delegated — retain both observations and mark the finding
`conflicting` until a reviewer resolves scope, time, or attribution. Never discard an older source
merely because a newer promotional page is easier to use.

Use bounded language such as "not found in the reviewed coverage", "the source reports X", or
"status remains unresolved". Never write definitive negatives solely because a search failed or
evidence was absent.

## Mandatory review triggers

Record a `manual_review_reasons` entry for every occurrence of:

- an access failure or a blocked, partial, or dynamic source;
- partial, sparse, or too-narrow coverage for a question that could change the assessment;
- a language gap;
- a material finding inferred rather than explicitly stated;
- a retained conflict;
- an unresolved subject or site match;
- any claim whose classification would flip if one more accessible source appeared.

Review reasons are never stripped from a finished packet.
