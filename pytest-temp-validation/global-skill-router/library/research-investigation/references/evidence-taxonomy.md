# Evidence Taxonomy

Mechanics of bounded discovery and source selection: what may be searched, in what order, and how
results relate to evidence. Domain concept groups and concrete query examples belong to the active
profile, never to this Core reference.

## Contents

- [Discovery versus evidence](#discovery-versus-evidence)
- [Bounded discovery discipline](#bounded-discovery-discipline)
- [Source kinds](#source-kinds)
- [Source hierarchy](#source-hierarchy)
- [Blocked and incomplete sources](#blocked-and-incomplete-sources)
- [Language expansion](#language-expansion)

## Discovery versus evidence

A query is a discovery action. Its result list, titles, rankings, snippets, and any provider-side
scoring are leads to source URLs only. Evidence begins when an underlying source body is retrieved
and assessed under [evidence-rules.md](evidence-rules.md).

## Bounded discovery discipline

- Build queries by combining resolved subject identity (name, official domain, registry
  identifier) with at most one or two concept terms drawn from the profile's concept groups.
- Query each relevant concept separately: a hit for one term never implies a hit for related
  terms.
- Stop searching a lane when additional queries return the same evidence; record saturation
  instead of accumulating volume.
- Follow search results only to the underlying pages, where access rules permit.

## Source kinds

The canonical source kinds are:

`official_webpage`, `official_pdf`, `government_record`, `company_announcement`,
`supplier_case_study`, `third_party`, `search_result`, and `other`.

`search_result` is discovery-only and can never carry an excerpt.

## Source hierarchy

Use the strongest relevant source available. Source strength and claim relevance are separate
dimensions: a strong source may be irrelevant to a claim, and relevance alone never promotes a
weak source.

1. Government, regulator, permit, procurement, statutory, or official registry records.
2. Subject-published technical documents, official webpages, formal announcements, and official
   social posts.
3. Named supplier, customer, engineering, or technology-partner case studies that identify the
   investigated subject.
4. Industry associations and reputable specialist publications.
5. Reputable news or trade reporting.
6. Corporate databases and directories.
7. Search results and weak secondary leads — discovery only.

Calibration: a registry entry can establish identity or an authorized activity without proving
current operation; a partner case study establishes an installed relationship only when it names
the investigated subject, the engagement, and the object involved; a vendor catalogue alone proves
none of these.

## Blocked and incomplete sources

When a preferred source is blocked or incomplete, record the coverage failure and continue with
the next relevant lane — for example regulatory records, official announcements, identified
partner case studies, or reputable specialist reporting. Never substitute an inaccessible primary
source with a snippet, and never report absence because one page did not load.

## Language expansion

Localized aliases are not executable vocabulary until they pass three gates:

1. explicit approval by the domain/profile owner;
2. translation review of each alias against its concept, not its label;
3. query testing before the alias enters any executed search path.

Until all three gates pass, the profile-declared base language remains the only executable
language. Record every language actually used as packet metadata. A language gap is always a
`manual_review_reasons` entry — it explains missing coverage and never becomes a finding.
