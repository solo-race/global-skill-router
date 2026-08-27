---
name: research-investigation
description: Evidence-first framework for reconstructing reviewable claims about externally documented entities, facilities, organizations, or projects from bounded accessible sources. Use when a task requires source admissibility, explicit confirmed/inferred/unknown/conflicting states, visible coverage gaps, conflict preservation, and a profile-defined investigation model before human review.
---

# Research Investigation

Reconstruct reviewable claims about externally documented subjects — entities, facilities,
organizations, or projects — from bounded, accessible sources. The default terminal artifact is a
human-review packet. Canonical pipeline mode exists only when the caller supplies a valid binding
and the canonical inputs that binding names.

## Scope

- This is an evidence-reconstruction and investigation control plane: it decides how findings may
  be formed from sources, never what a domain investigates.
- Applicable when identity, attributes, relationships, status, or change must be rebuilt from
  public or authorized-access material with traceable evidence and human review.
- Not a scorer, ranker, recommender, generic academic researcher, or automatic decision maker.
- The investigation model — dimensions, vocabulary, relevance labels — comes entirely from the
  loaded profile. This Core fixes no domain model and no pipeline topology.

## Contract

Non-configurable in every run:

1. Search results, snippets, candidate profiles, model output, and provider scores are discovery
   context, never fact excerpts.
2. A material claim binds only to an accessible original or authoritative source body or document.
   When nothing accessible supports it, the claim becomes an `evidence_gaps` entry (`state:
   unknown`) or a review reason — never a finding.
3. Never invent source, fact, resource, or evidence identifiers. Copy only canonical identifiers
   the caller already provided and the active binding declares usable.
4. `unknown`, partial coverage, blocked pages, and failed retrievals must never be transcribed
   into negative facts about the subject.
5. Never adjudicate a conflict silently. Incompatible observations and their sources remain
   visible together.
6. Do not bypass login walls, CAPTCHAs, robots rules, paywalls, rate limits, or other access
   controls. Stop repeated attempts against a failing endpoint.
7. Default output contains no numeric score, automatic exclusion, subject deletion, or final
   recommendation. A profile may define qualitative relevance labels reserved for human review;
   this never moves the terminal boundary.
8. Coverage gaps, language gaps, inferences, conflicts, and unresolved subject matches stay
   recorded in `manual_review_reasons`.

## Workflow

1. **Define the material question.** Identify the subject, jurisdiction/context, and the questions
   whose answers could change the review outcome.
2. **Load the profile.** Read the subject model, investigation dimensions, approved vocabulary,
   and optional project bindings from `profiles/<domain>.yaml`. If the profile violates or omits
   contract-required semantics, stop; never guess missing semantics.
3. **Resolve the subject.** Collect the identity keys, aliases, and site/scope markers the profile
   requires. Do not merge same-named subjects without evidence.
4. **Plan bounded discovery.** Generate the minimal query set from the dimensions and concept
   groups the current question touches. Extend across languages only under the profile's approval
   rules.
5. **Acquire admissible sources.** Prefer accessible original or authoritative sources. Record
   URL, title, dates, source kind, retrieval status, bounded excerpt, locator, and subject match
   for each acquisition.
6. **Reconstruct findings.** Organize claims along the profile-defined dimensions. Do not assume
   any fixed chain shape such as input → operation → output.
7. **Assign evidence state and prepare the packet.** Apply
   [evidence-rules.md](references/evidence-rules.md) and
   [output-schema.md](references/output-schema.md). In canonical mode, copy only caller-supplied
   identifiers; never advance a pipeline stage yourself.

## Evidence handling

Exactly four evidence states exist: `confirmed`, `inferred`, `unknown`, `conflicting`.
Admissibility, subject-match tiers, conflict preservation, and mandatory review triggers live in
[evidence-rules.md](references/evidence-rules.md). Source hierarchy, bounded discovery, and
language discipline live in [evidence-taxonomy.md](references/evidence-taxonomy.md).

## Profiles

A profile (`profiles/<domain>.yaml`) is agent-loaded guidance, not an environment-managed resource:
no tool reads it automatically. This Core depends on the profile contract in
[profile-contract.md](references/profile-contract.md), not on any specific dimension name or
domain vocabulary. Load exactly one domain profile per investigation and ignore unrelated sibling
directories. Load-bearing profile-local guidance lives only under `profile_guidance`; `display`
is presentation-only.

## Output boundary

Default: the review packet defined in [output-schema.md](references/output-schema.md). Canonical
Fact candidates may be produced only when the profile's `pipeline_binding.mode` admits them and
the caller supplies the canonical source records the binding names. Even then, nothing is written
automatically into any project fact store or scoring stage.

## Prohibited behaviors

- Promoting a search hit, snippet, or model answer into a finding without retrieving an admissible
  source body.
- Emitting a negative fact because retrieval failed, coverage was partial, or the subject was
  unreachable.
- Fabricating or deriving any identifier, date, quantity, relationship, or affiliation not stated
  by an accessible source.
- Hard-coding domain vocabulary, dimension names, or project paths into this Core.
- Treating a missing profile field as license to continue with assumed defaults.
- Claiming a consuming project's schema paths, stores, or configuration as framework-owned
  resources.
- Silently discarding older conflicting sources because newer ones are easier to quote.
