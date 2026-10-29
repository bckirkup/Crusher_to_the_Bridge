# Campaign reduction — program home

**Status:** SPECIFICATION ONLY (2026-10-22). The reducer artifact does not exist
yet; implementation proceeds through tickets D0–D8 in `PHASED_TICKETS.json`.
Nothing in this directory describes current behaviour.

This home carries the authoritative Edison survey + specification for the
campaign-wide AWS reduction and distribution-analysis program: extracting
scientific distributions from the ~197 historical `campaign/` S3 prefixes
(~447k objects, ~12.2 TB as of the dated 2026-10-19 inventory) plus the 21
registered campaign specs, without running any new simulation.

## Canonical authority

| File | Role |
|---|---|
| `SURVEY_AND_DEVIN_SPEC.md` | Main specification — decision, scope, analytic contracts, AWS admission/cost rules, acceptance |
| `DEVIN_HANDOFF.md` | Copyable dispatch: D0–D8 tickets with acceptance evidence |
| `PHASED_TICKETS.json` | Machine ticket source (dependency order D0→D8, `FUTURE-T1` optional producer telemetry) |
| `ACCEPTANCE_MATRIX.json` | 26 scientific + 10 operational production fixtures (all unrun) |
| `EXECUTIVE_SUMMARY.json` | Machine executive summary (scope counts, readiness states) |
| `ALIAS_AND_AUTHORITY_MAP.json` | Resolves every overlap between the four original lane proposals |
| `SOURCE_FAMILIES.json` | 11 source-schema families and their field capabilities |
| `FAMILY_GROUP_REGISTER.json` | 19 program groups over the 218 scope records |
| `ATTEMPT_FAMILY_MAP.json` | 118 attempt/token families |
| `TOOLS_OVERVIEW.json` | Existing-tool reuse/extend map |
| `COVERAGE_COUNTS.json` / `CAMPAIGN_COVERAGE.csv` | Scope-register counts / human-readable 218-row register |
| `EVIDENCE_REGISTER.json` | Source-lane evidence IDs, grades and correction anchors |
| `INPUT_EVIDENCE_MANIFEST.json` | Frozen list of files/hashes the survey read |
| `VALIDATION.json` / `SHA256SUMS.json` | Package self-validation results + artifact hashes |
| `FIELD_CONTRACTS.md` / `STATUS_NAMESPACES.md` | Reading views of the machine contracts |
| `references.bib` | Primary repository BibTeX |
| `D6_MEASURED_COST_BENEFIT.md` | Measured pilot cost-benefit (run 40802806913 + `quote-5a98544c742ef4a4`): the live-measured quote that gates the D7 envelope decision |

## Machine contracts (code-facing)

The JSONs the implementation must conform to live with the code, so they ride
into the analysis image: `picard_framework/analysis/campaign_reducer/contracts/`
— `FIELD_CONTRACTS.json` (34 tables / 505 fields / 33 metric definitions),
`TABLE_ROWS.schema.json`, `QUERY.schema.json`, `REQUEST.schema.json`,
`BOOTSTRAP_REQUEST.schema.json`, `CANONICAL_INTERFACE.json`,
`STATUS_NAMESPACES.json`, `CAMPAIGN_COVERAGE.json` (the dated 218-record cold
scope), plus the three `BLOCKED*`/`blocked_example` invalid-request fixtures.
`SOURCE_FAMILIES.json`, `ATTEMPT_FAMILY_MAP.json`, `FAMILY_GROUP_REGISTER.json`
and `COVERAGE_COUNTS.json` are also mirrored there byte-for-byte (hashes in
`SHA256SUMS.json`) so the adapter index travels with the code into the image;
this directory's copies remain the canonical survey artifacts.

## Program rules carried forward

- One public interface: `python3 scripts/campaign analysis
  {plan,validate,preflight,inventory,quote,submit,status,resume,query,collect,acknowledge}`.
  The internal worker is `python3 -m picard_framework.analysis.campaign_reducer.worker`
  under the existing `Dockerfile.analysis` `ENTRYPOINT ["python3"]`.
- No new `deploy/aws/*_entrypoint.py`, Dockerfile, jobdef JSON or submit script
  (frozen legacy layout); modify the existing `Dockerfile.analysis`.
- Analysis-only: no simulations, Stan fits, or reruns; originals immutable;
  derived output under `campaign/_derived/reducer/v1/`.
- `plan`/`validate` are zero-network; paid phases require measured quotes,
  finite budgets and admission; PS01 all four hulls is the first real pilot.
