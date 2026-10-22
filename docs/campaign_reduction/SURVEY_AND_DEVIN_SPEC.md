# Campaign-wide AWS reduction and distribution analysis — authoritative Devin specification

**Decision date:** 2026-10-22 · **Survey source SHA:** `496a919ca3af4563da34b958db37e737b58bab4b` · **Status:** SPECIFICATION
ONLY; proposed reducer, paid AWS execution and durable Edison return **NOT YET IMPLEMENTED OR VERIFIED**. Repository source,
AWS resources and legacy evidence were not changed. No simulation, paid job, or cloud inventory was run here. I recommend
that Devin implement **and subsequently execute** an AWS-side, analysis-only reduction and bounded query workflow against
**existing** campaign artifacts; Kosmos will analyze the returned joint distributions. No new simulation is needed merely to
reduce existing data.


**Start here:** [copyable Devin tickets](DEVIN_HANDOFF.md) · [machine executive](EXECUTIVE_SUMMARY.json) · [canonical
CLI](CANONICAL_INTERFACE.json) · [full field contracts](FIELD_CONTRACTS.md) / [JSON](FIELD_CONTRACTS.json) · [scope
rows](CAMPAIGN_COVERAGE.csv) · [acceptance](ACCEPTANCE_MATRIX.json) · [package validation](VALIDATION.json).

## 1. Decision, authority and source-of-truth rules

**One public interface:** proposed `python3 scripts/campaign analysis
{plan,validate,preflight,inventory,quote,submit,status,resume,query,collect,acknowledge}`; **all operations above are NOT YET
IMPLEMENTED**. Extend the existing `scripts/campaign` and a reusable `picard_framework/analysis/campaign_reducer/` module
rather than creating a second campaign launcher. An internal `python3 -m picard_framework.analysis.campaign_reducer.worker`
is a module worker invoked by the existing image's Python entrypoint; it is **not** a new bespoke
`deploy/aws/*_entrypoint.py`. Retain `scripts/campaign run/submit` existing campaign semantics and `scripts/campaign readout` analysis/reuse semantics. The new analysis namespace must not call a simulation launcher; existing readout functions are reusable. See
`CANONICAL_INTERFACE.json` for exact proposed operation modes and argv. Neither the original AWS lane's
`scripts/campaign-reduce` nor the contracts lane's generic `reduce/export` endpoint is canonical.
`ALIAS_AND_AUTHORITY_MAP.json` explicitly resolves every overlap. Existing paths and flags below are marked **EXISTING**;
proposed ones cannot be copied and run against today's repo.

**Single schema authority:** `FIELD_CONTRACTS.json` (26 scientific tables retained verbatim from the scientific lane, plus
eight operational/provenance tables; 33 versioned scientific metric definitions); `TABLE_ROWS.schema.json`,
`QUERY.schema.json`, `REQUEST.schema.json`, and `BOOTSTRAP_REQUEST.schema.json`; `CAMPAIGN_COVERAGE.json` is the canonical
scope. A schema-valid request alone does *not* confer permission: semantic validation must check grain,
scope/admission/quote/price/resource identities and byte/API/compute/dollar ceilings. Proposed historical AWS
`summary_fields/timeseries/entities_events/legacy_scan/errors/lineage` map to these exact table names; do not deploy parallel
tables with divergent meaning. The original four lanes remain unmodified **evidence appendices**, not alternate production
CLIs or scientific contracts. Their tasks: census `5a55307f-1ca7-49f7-8239-35766240e0d1`, contracts
`3fb93646-7b9a-4677-99b9-ad9a679d2024`, tools review `ac2a58c2-b7f7-4f94-b8e0-56443ef0436c`, AWS review
`918769e3-de0c-450d-ac89-f26bb6eade47`. `INPUT_EVIDENCE_MANIFEST.json` freezes actual read files/hashes.

**Repository-policy reconciliation:**
[`AGENTS.md:81–90`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/AGENTS.md#L81-L90)
forbids *new* bespoke `deploy/aws/*_entrypoint.py`, `submit_*.sh`, `batch_job_definition_*.json`, `Dockerfile.*` and moving
an active legacy argv target. The earlier AWS draft proposed a new worker file, Dockerfile/job definition, and separate CLI;
**these proposals are superseded**, not evidence of deployed tools. Build a shared reducer package, MODIFY existing
`deploy/aws/Dockerfile.analysis` and existing launcher/job-binding path, and review one additive analysis-dispatch GitHub
workflow.
[`scripts/campaign:1–18,167–268`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/scripts/campaign#L1-L18)
is now directly available (extensionless file recovered), including its literal `containerOverrides.command` convention. **Do
not** use unexpanded `Ref::` parameters: that was an earlier draft.
[`Dockerfile.analysis:39–63`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/deploy/aws/Dockerfile.analysis#L39-L63)
copies analysis modules and scripts but omits `tools/`, and its ENTRYPOINT is `python3`; do not certify an image that has not
imported the scanner functions it needs. Modify this existing build recipe with locked `uv.lock` / wheels-only installation
and smoke-test the **actual built image** and literal module argv. The supplied 3,235 text-file snapshot **plus the
separately recovered extensionless launcher, 35 Dockerfiles and `uv.lock`** match their canonical Git blobs:
`CANONICAL_SOURCE_VERIFICATION.json` records **3,272 matches, zero failures**. This supersedes the AWS lane's initial
statement that launcher/Dockerfiles could not be inspected, **not** its caution that no deployed image, live branch or AWS
configuration was verified. Do not reclassify historical measurements as invalid merely from broad current
[`AGENTS.md:21–23`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/AGENTS.md#L21-L23)
commentary: measurement validity is scoped to actual image/SHA, target and evidence.


| Prior proposal / historical assertion | Authoritative resolution |
|---|---|
| AWS `scripts/campaign-reduce`, contracts `reduce/export/catalog/capabilities` | **NOT YET IMPLEMENTED:** extend `scripts/campaign analysis`; `submit --phase` reduces, `query` accesses catalog/capabilities and paged data, `collect/acknowledge` completes durable export. |
| AWS `deploy/aws/campaign_reduce_entrypoint.py` + new Dockerfile/jobdef | Superseded by shared package/module worker + **MODIFY** existing analysis image/launcher configuration, per `AGENTS.md:81–86`. |
| AWS `run_key/summary_fields/timeseries/entities_events/legacy_scan/errors/lineage` | One field dictionary: `runs.run_uid/run_scalars/epoch_metrics/events` plus role/agent/object/observation tables, native scan `assets`, `data_gaps/source_links`; no parallel schema. |
| AWS initial unavailable extensionless launcher/build files | Historical inspection limitation superseded **here** by direct recovered-file inspection and 3,272 canonical Git-blob checks; no claim the original agent inspected those files. |
| Earlier 'dispatch403/no downloader' blanket wording | Superseded only for the recorded PR1079 selected-manifest fetch; paid reducer dispatch and persistent automated return remain unverified. |
| 197 historical prefixes vs 21 registry campaigns | Keep218 typed records,198 distinct prefix names, exact overlap20; add fresh discoveries rather than treating either list as all history. |

**Status authority:** [namespaced status contract](STATUS_NAMESPACES.json) and [reading view](STATUS_NAMESPACES.md) distinguish source/read reasons, capability availability, metric value evidence, coverage, clinical censoring and job/scientific-approval lifecycles. Narrative `value_statuses_integrated` are aliases, not new `metrics.value_status` literals. Typed read failures map to compatible `assets.read_state` plus separate canonical `data_gaps.reason` and precise `data_gaps.detail`. Historical stopped attempts do not imply data loss; unknown source execution never implies completed. The original scientific enums/metric definitions are unchanged.

## 2. Complete survey scope: distinguish prefixes, objects, cells and runs

The **19 October** non-atomic `campaign/` metadata inventory (23:35:42–23:49:11 UTC, previous source
`e67a42dcc9f6566b0c4331550b2a063f0f067189`) lists **197 historical prefix rows, 447,190 physical object entries,
12,179,256,285,889 stored bytes (~12.179 TB decimal)**. This is not a current/live inventory and is **not** a run, cell,
seed, ZIP-member, raw-read requirement or validation count. `CAMPAIGN_COVERAGE.json/.csv` preserve every one of those **197**
rows and all **21** current registered specs, **218 records at two grains**. Union: **198 distinct prefix names**; 20
registry prefixes overlap exactly with October records, two separate AGE-FOOD paired rerun prefixes exist, and
`campaign/noro_age_food_01_mega/` is registered but absent from that dated list (not proof it is now empty). **169/197**
dated names occur as exact source tokens; 28 require explicit inferred or unknown linkage. The 19 program groups, 118
attempt/token families and 11 schema-adapter families are *indexes*, not independent replicates.
[`campaigns/README.md:85–93`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/campaigns/README.md#L85-L93)
documents the current registration path; the machine scope register supplies every individual record, original association,
ledger evidence and availability grade.

| Program group | Dated historical prefixes | Registered specs | Candidate schemas |
|---|---:|---:|---|
| `classmix_staged_feasibility_and_diagnostics` | 9 | 0 | `observation_jsonl` |
| `covid_crew_confinement_service_mechanisms` | 11 | 6 | `covid_screen_json` |
| `covid_mechanistic_parameter_diagnostics` | 34 | 0 | `covid_screen_json` |
| `covid_observation_funnel_hull_validation` | 11 | 3 | `covid_screen_json` |
| `cross_pathogen_leverage_perturbations` | 2 | 0 | `perturbation_json` |
| `influenza_open_voyage_age_visibility_response` | 7 | 3 | `flu_cell_json`, `unknown_legacy` |
| `norovirus_Morris_Sobol_screening` | 3 | 0 | `bounded_region_jsonl` |
| `norovirus_contact_architecture_counterfactuals` | 20 | 0 | `observation_jsonl` |
| `norovirus_dose_clock_containment` | 9 | 0 | `campaign_summary_zip`, `unknown_legacy` |
| `norovirus_flush_stage_parameter_sweeps` | 28 | 0 | `campaign_summary_zip` |
| `norovirus_food_object_growth_sweeps` | 10 | 6 | `campaign_summary_zip`, `growth_census_zip` |
| `norovirus_genotype_mixtures` | 7 | 0 | `campaign_summary_zip`, `unknown_legacy` |
| `norovirus_hand_fomite_diagnostics` | 6 | 1 | `fomite_diagnostic_gzip`, `growth_census_zip`, `unknown_legacy` |
| `norovirus_importation_incidence_venue_clock` | 16 | 0 | `campaign_summary_zip`, `growth_census_zip`, `unknown_legacy` |
| `norovirus_provisioned_source_PS01` | 2 | 2 | `growth_census_zip` |
| `norovirus_structural_and_posting_counterfactuals` | 16 | 0 | `campaign_summary_zip`, `observation_jsonl`, `unknown_legacy` |
| `sentinel_Stan_NUTS_validation` | 1 | 0 | `stan_nuts_json` |
| `sentinel_wastewater_operating_envelope` | 1 | 0 | `wastewater_campaign_zip` |
| `synthetic_recovery_and_observation_degradation` | 4 | 0 | `campaign_summary_zip` |

**Stage D5 must inventory AWS afresh** within authorized bounded roots, **not only `campaign/`**: discover other results
roots, new/unregistered prefixes, possible fit outputs, and registered-but-October-absent names; exclude `campaign/_derived/`
and preserve the dated delta. Record page continuations and gaps if access to other roots is denied. A complete 197-row cold
scope cannot establish that **all current campaigns** or all AWS data live under that prefix. Catalog absent, withdrawn,
failed, canary and planned attempts as such, rather than counting them as successful runs. Preserve cells, source objects,
ZIP logical members, original run executions, selected unique voyages, eligibility denominators, fit chains/draws and
exported query rows as separate units in `coverage_cells`, `source_objects`, `assets`, `runs` and
`coverage_cells.metric_scope_json`. Every cell reconciles
declared/landed/member/parsed/duplicate/conflict/selected/eligible/unsupported counts **only when comparable**; null
otherwise. No blanket 'all distributions available' claim follows from catalog inclusion.

**Eleven adapters / noninterchangeable science:** `growth_census_zip` (full versus lean saved telemetry),
`campaign_summary_zip` (flat, nested and fused), `covid_screen_json`, `flu_cell_json`, `bounded_region_jsonl` (Morris/Sobol
**simulation screens, not Stan**), `perturbation_json` (LEVERAGE simulation), `stan_nuts_json` (actual fit
diagnostics/posterior, not voyage AR), `fomite_diagnostic_gzip`, `unknown_legacy`, `wastewater_campaign_zip`, and
`observation_jsonl`. [SOURCE_FAMILIES.json](SOURCE_FAMILIES.json) gives each family's field capability and evidence; [EVIDENCE_REGISTER.json](EVIDENCE_REGISTER.json) retains source-lane IDs/grades and direct recovered-file correction anchors. Older writer/schema/engine SHA
and missing observational columns are **member/attempt-specific**, not inferred from the survey SHA or adjacent files.
Credible endpoint grades in the dated prefix census: AR documented-unverified **141**, unknown **56**; timing
documented-unverified **129**, unknown **68**; mechanism documented-unverified **141**, unknown **55**, known-saved **1**;
role documented-unverified **127**, unknown **70**. These are documentary classifications, not per-run AWS verification or
claims of endpoint comparability. `COVERAGE_COUNTS.json` and `census/CENSUS_REPORT.md` give exact distinctions.

## 3. Existing tools, proven edges and actual return path

[TOOLS_OVERVIEW.json](TOOLS_OVERVIEW.json) is the compact machine reuse/extend map; the full unchanged tool registry is linked there.

| EXACT EXISTING surface at surveyed SHA | Reuse / gap / disposition |
|---|---|
| [`tools/noro_diag/outbreak_anchor_readout.py:103–150`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/tools/noro_diag/outbreak_anchor_readout.py#L103-L150); `onset_curve_readout.py::_census_prefix` | Reuse S3 ranged central-directory/member lookup and prefix approach, then add immutable VersionId or every-read If-Match, bounded streaming, ZIP64, long comments, all nested/fused members, CRC and decoded-size checks. Existing four GETs are not pinned. Do not fork another unchecked ZIP parser. |
| [`tools/diag/readout_common.py:40–106,136–188`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/tools/diag/readout_common.py#L40-L106) | Reuse member helpers only with typed missing/corrupt/JSON/OSError outcomes; `wilson_centered(n<=0)` currently returns `(0,0,0)`, which must be **NA / no denominator**, not confident zero. |
| [`deploy/aws/aggregate_results.py:14–18,163–178`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/deploy/aws/aggregate_results.py#L14-L18); `analyze_campaign_curves.py`; [`campaign_bundle.py:37–88`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/picard_framework/analysis/campaign_bundle.py#L37-L88) | Reuse nested member grouping/curve/scalar logic, **not** global `run_id` dedup, first-summary-only read, external-timeseries-only assumption or loss of unknown scalar paths. The source may embed timeseries in `summary.json`. |
| `food_shapes_01_scan.py`, `food_score_01_scan.py`, `early_event_scan.py`, `outbreak_anchor_readout.py`, `food_shapes_01_report.py` | Reuse already saved `_scan_rows` columns with row-to-raw identity evidence; use targeted missing-member reads only. Current scans can overcount overlap or drop field-order variants and vacuous `off/ind` witnesses can print PASS at zero rows. Separate native scan rounding from exact raw fields and original analysis image identity. |
| [`deploy/aws/boundary_analysis_entrypoint.py:253–295`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/deploy/aws/boundary_analysis_entrypoint.py#L253-L295); campaign-specific postprocessors | Existing analysis precedence only. Some stages sync broad prefixes or fit Stan; reduction-only must not import or run them. Keep posterior chain/draw grain separate from voyage-run grain. |
| [`campaign_dispatch.yml:3–7,51–65`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/.github/workflows/campaign_dispatch.yml#L3-L7), [`campaign_collect.yml:96–199`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/.github/workflows/campaign_collect.yml#L96-L199) | Dispatch currently does describe/dry-run **only**; collector indexes bounded prefixes or fetches one exact `campaign/` object (default **50 MiB**), hashes it and emits a **30-day** artifact. It is neither an AWS reducer nor a paged joint-query return service. MODIFY collector for strictly bounded derived-receipt/manifest/page fetch while retaining exact-key legacy behavior. |

**Actual source-function regressions, not fixes:** tools lane ran **16 stdlib/synthetic probes**, including maximum ZIP
comment not found, corrupted CRC unchecked, all-crew adapter rejected for zero passenger complement, scan regex
duplicate/field-order losses, first-of-multiple summaries, embedded timeseries loss, vacuous witness PASS and floating 0.90
pp D1 endpoint rejection. All 16 asserted the observed behaviors as expected; **none certify that a new reducer passes
production tests**. `tools_review/OFFLINE_FIXTURE_RESULTS.json` retains the exact fixtures. `tools_review/TOOL_REGISTER.json`
covers 159 Python tool files; its 350 AST/lexical-only rows are screening, not line-by-line semantic audit.
`tools_review/GAP_REGISTER.json` defines 14 proposed fix/reuse actions.

**Historical selected-object access is narrower than the requested service:** the earlier PR1079 verification records an
Edison-initiated fetch of one selected **605,283-byte** manifest, SHA-256
`e2156fadb6e2e0c7bd36ac50732bcd26796d119d04b982ad968de08e33954ce9`, GitHub run `39338959409` under a 1 MiB choice. This
supersedes earlier blanket 'no downloader/dispatch 403' language **for that tested path**. It does **not** prove paid
analysis submit, automatic durable callback/polling, all-family queries, bounded Parquet readback or permanent Edison
ingestion. A separate undeployed Oct19 helper's 5 MiB hard limit is **not** the merged collector's limit; new 5 MiB query
export pages and 1 MiB indexes are proposed design ceilings only. Existing workflow concurrency can supersede pending
requests; serialize/correlate attempts and persist a cursor. Current `VersionId="null"` needs If-Match rather than treating
it as immutable. Current GitHub IAM templates allow Put on original `campaign/*` and need authorized role separation; a
`$500` notification is *not* a per-attempt spending cap. Consult `aws_review/evidence_register.json` and
`aws_review/AWS_EXECUTION_HANDOFF.md` for exact source and dated access evidence.

## 4. Proposed implementation — bounded AWS source-to-distribution pipeline

```text
Authorized scope/price + finite phase admission
  → bounded root/prefix LIST (dated frozen manifest; explicit delta and partial cursor)
  → HEAD (non-null VersionId or ETag) + conditional GET of selected member/ranges
  → typed stream/checksum/CRC/schema adapter (all nested logical runs and historical scans)
  → source_objects + assets + source_links + runs + capabilities + data_gaps
  → exact run_scalars/metrics/epoch_metrics and saved optional event/role/observation tables
  → immutable Parquet partitions + checksums + partition counts → catalog COMMIT
  → run/joint/censored/weighted analysis on AWS under frozen scientific query
  → bounded deterministic export pages + durable hashed receipt
  → GitHub collector → automatic durable Edison ingest/ack → Kosmos analysis
```

**Proposed storage:** `s3://crusherbucket-994254241749-us-east-1-an/campaign/_derived/reducer/v1/` from source-declared
bucket/region; **not asserted as deployed**. Preserve originals. Write immutable, attempt-fingerprinted/checkpointed
partitions and return pages; conditional create or collision check, COMMIT only after hash/row-count verification. ETag is an
opaque identity, not assumed MD5; hash selected bytes and logical members with explicitly recorded hash scope, and hash
derived files. Do not full-download originals just for cryptographic hashes or claim whole-object SHA after a range read.
Snapshot ListObjects is non-atomic, and version-aware HEAD pins follow listing; a 412/change is `SOURCE_CHANGED` and starts a
new snapshot/attempt, never mixed bytes. Handle ZIP64/long comments, supported stored/deflate, duplicate member names, CRC
errors, corrupt/unavailable/archive-class sources, bounded decompression and spool. Paged LIST/HEAD/GET budgets and
row-size/central-directory ceilings must be enforced **across retries and shards**, not merely per call. Unsupported
compression/schemas and missing historical objects become typed coverage/errors, never silent omit, fake 0 or invented runs.
Restrict object writes to own derived subtree and never restore originals as an accidental fallback.

**Capabilities and lifecycle:** `available`, `documented_unverified`, `not_saved`, `counted_not_retained`, `not_observed`,
`not_applicable`, `zero_denominator`, `unsupported`, `corrupt`, `source_changed`, `access_blocked`, `resource_blocked`,
`unknown` are **different**. Preserve source/full/lean retention and clock/role observability at *run/member/metric* grain. A
float `0`, bool `false`, null, failed/censored and empty eligible set are not interchangeable. `source_links` captures exact
object→member→scan row→logical execution→selected run→metric→figure/query lineage; never deduplicate on basename, seed,
run_id alone, or duplicate canary/production entries without proving execution equivalence. Same exact seed on different
hulls, input/engine images, attempts or nondeterministic hosts is not an independent equivalence claim. Reconcile scan reuse
on exact covered keys, member paths, missing fields and source identities; apply new targeted reads only where permitted and
needed. No rerun is needed to repair aggregation; if a field was never retained it cannot be recovered from a marginal.

**Use the frozen 34-table model, not 34 separate exports:** core scientific tables are `campaign_catalog, attempts, runs,
assets, capabilities, data_gaps, design_values, pair_links, role_dictionary, population_intervals, run_scalars, metrics,
epoch_metrics, times_to_event, weights, distributions, aggregate_estimates, external_targets, analysis_artifacts`;
conditional saved detail is `agents, memberships, events, event_participants, mechanism_objects, observations` and true fit
`posterior_draws`. Operational tables are `source_objects, source_links, coverage_cells, catalog_partitions,
reduction_attempts, receipts, query_pages, acknowledgments`. **26 scientific tables + 8 operational**; see
`FIELD_CONTRACTS.json` for **all 505 fields**, exact types, grains, IDs and allowed nulls (original 382 scientific fields
preserved, 123 new operational fields). Store complete native scalar paths (`run_scalars`) and denominator-bearing per-run
derived metrics, not preselected quantiles/histograms; preserve valid joint row keys/parameters for future questions.
Optional agent-level exports are only produced **if actual agent IDs, directed roles/events and permissions exist**. Large
event payloads remain S3-side; arbitrary valid column/filter selected joint pages, not Cartesian preexports, go to Edison.

**Scientific validity is independent of extraction:** persist source engine SHA/image digest, reducer SHA/image digest,
adapter, scan image if known, stage, hull/vessel, seed namespace, code/run/input hashes when available. Never substitute
survey SHA for historic image or current source for old analyzer. Four validity axes — hull, fleet weighting, total
population, crew/passenger composition — remain independent with evidence grade and per-claim quarantine; a successful parse
is **not** campaign validity, posterior validity, causal evidence or paper release. External biological data and published
calibration are separately versioned and attributed.

## 5. Exact analytic contracts: AR, timing, mechanism and participation

**Attack rate (AR)** means *one explicit numerator/denominator, population, endpoint domain, clock/window and metric
version*. `FIELD_CONTRACTS.json.metric_definitions` contains **33** fully enumerated definitions and their sources; examples
below are noninterchangeable:

| Versioned estimand / source | Numerator / denominator and required distinction |
|---|---|
| `infection_ever_person_risk.v1`, `infection_aboard_person_risk.v1`, `infection_import_person_fraction.v1` | Unique infected/eligible people, aboard-acquired/explicit susceptible-at-risk and import-specific populations; do not use `(I+R)/N` unless that proxy's closure and no-reinfection assumptions are established. Episodes/person-hour incidence is a **different** `infection_episode_incidence_rate.v1`. |
| `symptomatic_course_risk.v1`, `symptomatic_onboard_person_risk.v1`, `symptomatic_onboard_burden.v1` | Symptomatic-ever cohort versus actual symptomatic while aboard versus symptomatic person-hours/person-hours. Do not convert ever-ill course counts or `symptomatic_epochs` into exact onset time. |
| `reported_true_person_risk.v1`, `report_capture_given_symptoms.v1`, `reported_noise_count.v1`, `tested_person_fraction.v1`, `lab_confirmed_person_fraction.v1`, `test_positive_assay_fraction.v1` | Distinct true case/report IDs, false/noise IDs, persons tested and positive **assays** each have separate eligible denominators. Repeated specimens, pending assays, feedback from observed response and truth-vs-report distinction must remain visible. |
| `posting_probability.v1`, `outbreak_probability.v1`, `conditional_metric.v1` | Exactly versioned either passenger-or-crew reported threshold / eligible complete voyages, not infected-any/outbreak predicate. For conditional posted AR, report unconditional distribution, `P(post)`, selected and unselected group counts and missingness. Empty eligible/zero denominator gives NA, not false 0 or PASS. |
| `case_entry_channel_fraction.v1`, `case_dominant_route_fraction.v1`, `route_dose_share.v1`, `mechanism_event_rate.v1` | Entry provenance, dominant case route, route-specific dose and events/exposure-opportunity are different grains. `reported_cases_by_channel` supply-vs-aboard classification follows dominant acquired dose mass in the current writer; it is **not proven infection causality**. |
| `role_participation_fraction.v1`, `role_participation_rate.v1`, `source_realization_probability.v1` | Distinct eligible role members who acted/received versus role-specific participations per eligible person-hour versus realized stations/voyages. Occupation, active duty, caregiver/tending, cleanup responder, source-eligible, infected/ill/tested and primary passenger/crew cannot collapse into a crew proxy. |
| `response_delay.v1`, `surveillance_detection_probability.v1`, `economic_cost_per_case_averted.v1` | Named event time origin and competing/censored endpoint; detected eligible units / truth risk set at a stated grain; paired incremental cost/year/currency divided by valid paired cases averted, including zero/negative denominator status. |

**Clocks and event censoring:** preserve configured *and effective* epoch duration, `legacy_epoch_day` clock mode (can imply
**24 hours/epoch** despite configuration), origin and UTC only if saved, epoch-zero import rules, actual follow-up and
delayed entry. `outbreak_anchor_readout._progression` calls first new infection index `onset_epoch`; it is **infection-onset
index**, not clinical onset, and sparse series index may not equal explicit epoch. Keep infection, symptomatic illness,
specimen collected, lab result available, report, action and peak separate; `peak_epoch - detection_epoch` is time-to-peak,
not onset-to-detection. `times_to_event` stores right/left/interval censoring, competing departure/recovery/death, structural
not-at-risk and exact event atoms. Use risk sets/survival or competing-risk methods when assumptions support them; a
never-posted voyage is not 'event time = final horizon'. Legacy burst48 maximizes onboard **acquisition** count in a
**closed** `[t,t+48 epochs]`, `epoch_acquired>0`; proposed clinical-onset burst in a **half-open physical-hours** `[t,t+W)`
is a **different** ID and only computable if actual onsets were saved. Preserve ties, endpoint rule, count, risk denominator
and native empty-zero separately from new undefined/no-events.

**Mechanism and participation:** directed chain: import/provisioning source → object/station/source opportunity → exposure
and acquired dose by compatible route/unit → infection establishment/person → symptom course/aboard disease →
observation/report/test/response. Emit event source vs recipient IDs, role and site at event time, occupancy/exposure
opportunities, object identity and dose units; do not sum incompatible pathogen/unit doses. Role membership can change and
axes overlap: explicit primary passenger/crew/unresolved, job (food employee is crew with service-zone work), current duty
(food handler actually on schedule/work zone), caregiver/tending, response cleanup, source eligibility; noninfected crew can
be active participants.
[`covid_specimen_timing_probe.py:77–113`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/tools/covid_specimen_timing_probe.py#L77-L113)
conflates missing onset with one pre-onset class and some roles fall back to passenger: keep
unknown/censored/permanently-asymptomatic only as actually supported, and flag unresolved roles. Do not blanket-delete old
all-crew diagnostic rows: inspect original role/replay lineage, and fix the zero-passenger adapter semantics. If agent event
identities or a complete roster were not retained, mark **irrecoverable historical joint**; do not reconstruct
actor-recipient or participation correlations from aggregate role marginals.

**Exact distributions, dependence and weighting:** primary scalar store retains *every available exact per-run value*, seed,
design coordinate, image and denominator. In S3 build exact empirical cumulative distribution function (ECDF) mass at every
observed atom, including zero/no-event mass, tails and missingness counts. For weights \(w_i\), \(F(x)=\sum_i
w_i\mathbf1[X_i\le x]/\sum_iw_i\); the inverse-ECDF quantile uses smallest supported \(x\) at/above target probability.
**Voyage-mean** \(\sum w_i(n_i/d_i)/\sum w_i\) and **pooled-person** \(\sum w_i n_i/\sum w_i d_i\) differ; never average a
mix of percentages or sum ARs. Report target, positive nonmissing weights, denominator/risk cohort, support and selection; no
external fraction changes simulated norovirus AR. Pair only justified identical design/seed/image namespaces, then use paired
seed-block or hierarchical uncertainty for arms/hulls/stages rather than treating multiple shards, posterior draws, technical
wastewater replicates or correlated replays as independent voyages. Examine joint covariance, onset tail and rare modes (not
just four quantiles); weight fleets only to a *named, dataset-dated* validated fleet target or explicit externally bounded
vessel class, with four axes assessed separately. Associations of hull, source route and role are **descriptive**, not causal
effects without a justified contrast and sensitivity to geometry/population, time and intervention allocation.
Sensitivity/design analyses use nominal and realized covariates, blocked seed/hull/stage interactions and Monte Carlo
intervals; do not tune hull sizes, complements or source parameters to make observed AR fit, or retroactively change the
confirmatory selection/metric without an explicit new analysis version.

## 6. Four-hull PS01 and independent external target

First real bounded reducer pilot should prioritize all **four PS01 hulls**, while adapter/catalog architecture and subsequent
execution cover **all** historical/discovered campaigns. [`PS01 parent
LEDGER:406–519`](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/campaigns/noro/provisioned_source_01/LEDGER.md#L406-L519)
reports **46,000 main cells** at production image SHA `a9f4a517b37baf6b1f18a623e6d0c33bac83b407`, image digest
`sha256:97d99be4c1abf362af1f9914f476740bd1086e7b73491b371f8741bfb1ac95de`, plus ~128 separately tagged canary cells.
Expedition's seed range differs from classic/spirit/mega; each arm/hull had 1,000 seed targets, with 12 arms on each small
hull and **10 mega arms**; mega fiat ship/mint arms were **not included**, not zero. Eight PS arms are only a subset. This
controlling later ledger **supersedes older headings**; recovering unique exact row counts remains a validation step, not
reopening declared completion. Current survey SHA is *not* production or historical analysis SHA. Historical original
scanner/reporter image/SHA remain **unresolved**: do not infer them from current scanner, PR text or job definition tag.

Preserve D1 as exact **0.004–0.009 probability-unit** paired posting increase (0.4–0.9 percentage points) and handle
inclusive integer endpoints; floating 0.90 pp rejection in current reporter is a fixture. For D2 produce **both** frozen
median posted passenger AR relative to matching `ind` (**0.5–2×**) and operational absolute ≥0.04 separately. For D3 the
frozen 'converted passenger AR among posted' definition lacks a stable numerator/denominator: **PI definition approval
required; BLOCKED_DEFINITION**. Operational excursion→posting conversion vs `ind` is a **different** ID, never a substitute.
D4 mega acquisition burst48 may be recoverable from saved census/original scan even though later report omits it; source with
absent spirit data stays unreadable and mega originally had no frozen discriminator. No retrospective threshold or blanket
zero for empty excursion. Source §4 timing distinctions apply to 'onset' labels. <20 object-carrying voyages is vacuous for a
frozen gate verdict, not evidence of its failure. Retain arm rare-event uncertainty, native cutoffs, four separate hull axes,
image lineage and canary exclusions. Four-hull first-paper requirement is **not** relaxed to three hulls; no replacement
campaign is authorized by this spec.

The pinned repo also contains the merged PR #1081 [etiologic-fraction
discussion](https://github.com/bckirkup/Crusher_to_the_Bridge/blob/496a919ca3af4563da34b958db37e737b58bab4b/docs/literature/consensus_tranche_53_fleet_age_norovirus_share.md#L112-L139).
Those are repository-transcribed, **not independently audited here**. An etiology-determined AGE **outbreak** share and
**within-outbreak case** share have distinct denominators; neither is a native simulated norovirus case/AR multiplier or a
value for all shipboard AGE cases. Register independent external source/version, eligibility/date, error/sensitivity and
compare only matching observed endpoints. Does not affect non-AGE pathogens or require a new simulation for reduction.

## 7. AWS admission, cost and reliable automatic return

**Two deliberately different request gates:** `plan` and `validate` perform **zero network/cloud/spend**, using
`BLOCKED_REQUEST.template.json` only as an invalid-null illustration. Bounded `BOOTSTRAP_REQUEST.schema.json` admits metadata
`preflight/inventory/status` and readback `collect/acknowledge` under an already approved scope/budget envelope, real price snapshot, finite
API/time/dollar limits: it **cannot** submit Batch or fetch source payloads. A paid pilot/materialization/finalization/query
requires `REQUEST.schema.json`, filled exact job role, queue, job-definition revision, digest-pinned verified reducer image,
worker resources, frozen inventory, adapter and request hash, admissible quote with measured bytes/representative classes,
deadline and a valid parent-envelope approval. All **23** resource/API/byte/job/retry/cost/reserve fields are explicit and finite; zero
retries allowed, unknown prices/resources/credentials/permissions/quote/admission produce **blocked nonzero** state, never a
`None` unlimited default. Preflight cannot authorize a paid inventory by accident; a future pilot requires a **new** measured
quote and automatic machine reservation within that envelope (not a new manual approval). Quote budgets for compressed ranges **and** decoded/spool bytes, API/LIST/HEAD/GET, output/checkpoints,
retries/concurrency, vCPU/memory/wall/queue wait and bounded return; no hard-coded unknown size or unverified active AWS ARN.
Existing source stack's $500 notification is not the attempt cap. Every stop writes a durable failure/continuation receipt if
available.

**Automatic in-envelope admission:** Reserve remaining budget automatically for ordinary queries, pages, resumes, phases and campaigns, retaining the parent envelope ID, scope/quote bindings and ledger/receipt. Do not require routine per-operation PI approval or a fresh manual token. Escalate only for new scientific scope, budget-envelope exceptions or credential/permission exceptions. Missing/expired envelope, exhausted ceilings or inaccessible credentials fail nonzero. This survey authorizes **no AWS execution**; Devin must implement and subsequently execute the approved existing-data reductions, not execute them here.

**Permissions:** dedicated logical analysis dispatcher accepts only approved reducer job revisions, owns its tagged job
stops, cannot run simulations/register infrastructure. Reducer app role reads approved originals and can conditional-write
*only* derived attempt paths; no original writes/deletes/restores. Builder/deployer separately handles scoped PassRole/ECR;
collector reads only reviewed original-manifest keys and derived receipts/exports, no Batch submits. Execution role handles
exact image/logs, conditional KMS access only if live keys require it. Inspect actual live
queue/resource/jobdef/IAM/architecture/network at deployment, not template-only declarations. Do not create new queues,
buckets, VMs or uncontrolled permissions as fallback. Existing analysis image copies no `tools/`: either include reviewed
modules via **modification of existing Dockerfile.analysis** or extract shared functions into already copied package with
fixture parity. Test actual image/entrypoint/import, not just source import. A reducer-specific minimal build target may be added inside the **existing** Dockerfile.analysis, keeping legacy analysis defaults/active image contracts intact; dependency locking must not require CmdStan execution or fitting on the reduction path.

**Proposed automatic durable return:** analysis workflow `.github/workflows/campaign_reduction.yml` (new only after review)
emits attempt-scoped URI/hash/job IDs/coverage/continuation; extend **existing** collector for strictly allowlisted selected
immutable manifest/page fetches, **not** bulk raw export. Proposed hard ceilings: receipt 256 KiB, issue envelope 32 KiB,
summary/index page 1 MiB, each export 5 MiB, **20 files / 50 MiB per collect**, ≤10,000 rows per query page; all are design
candidates validated against actual infrastructure. Large receipt job/error lists become pinned child pages. Edison
automation obtains durable callback **if demonstrated** or runs a persistent bounded GitHub Actions poller with
cursor/backoff. It verifies hashes and page sequence, stores project assets+query index, writes idempotent `acknowledgments`
for `(attempt,query,page,hash)` and resumes on interruption/expiry by recollecting S3, no signed URLs or credentials logged.
An inaccessible integration, missing receipt/trigger, insufficient permissions or 403 is **RETURN_PATH_BLOCKED** with
assigned owner and fallback; never 'ask PI to forward ZIP/CSV each time'. Humans approve scientific scope/budget and
exceptional access, not routinely transfer files. Existing single-manifest download is proof of narrow access only;
**automatic re-entry is an acceptance test**, not assumed.

**Query is a bounded structured filter AST, not shell/SQL:** `QUERY.schema.json` fixes frozen catalog, versioned metric,
grain and declared joins, filtered columns/grouping/ordering, nonmissing weight/target, explicit scan/time/cost and output
ceilings. One-to-many joins must state intended resulting grain; incompatible agent→run/posterior joins fail
`unsupported_join`, not multiply rows. Parquet projection/partition/row-group pruning reduces actual scan charge, not just
bytes delivered. Every page has stable order/continuation tied to catalog+query hash, `returned/scanned/remaining`
accounting, `complete` only at final null cursor; a row above page cap yields `ROW_TOO_LARGE` with narrower-column option. S3
retains full Parquet and all unique scalar rows; Kosmos receives exact selected joint pages and derived figure
inputs/covariance/survival tables, not only histograms or summary values. Output issue comments carry pointers/status, not
datasets. Operational statuses/exit codes in `CANONICAL_INTERFACE.json` distinguish invalid contract, access blocked,
admission required, budget stopped/checkpointed, changed source, quarantine, partial coverage and return blocked.

## 8. Devin implementation **and execution** tickets / acceptance

`PHASED_TICKETS.json` is the one machine ticket source; `DEVIN_HANDOFF.md` is its concise copyable dispatch. Ordered
dependency: **D0** canonical shared-CLI/contract/no-cloud dry plan → **D1** source identity/bounded readers/adapters → **D2**
Parquet/coverage/metric/query/resume → **D3** reviewed live deployment/role/image/collector bindings → **D4** automatic
Edison success+failure return canary → **D5** fresh bounded all-197-plus-root discovery → **D6** representative
*existing-object* pilot, PS01 four hulls first, measured quote → **D7** admit/execute staged all-family materialization →
**D8** Kosmos exact paged joint analyses/readback with Devin operational repair. Pilot selection is **adaptive by adapter,
observability, size and error class**: regular summary, full and lean census, embedded time series, nested/fused/legacy,
clinical non-AGE, old scan reuse/PS01 and unsupported/missing witness; include as many additional classes as coverage
requires, **not an arbitrary fixed six**. Do not force a 12 TB read, new model runs or reanalysis of fully qualified outputs.
Stage continuation is keyed to input/adapter/worker/fingerprint, quota and receipt; later SHA evidence remains post-pin until
independently checked.

**Separate prospective producer ticket:** `FUTURE-T1` in `PHASED_TICKETS.json` specifies future-only
role/denominator/event/clock/retention/source-identity telemetry. It is **not an old-data reduction prerequisite**, does not
reconstruct missing historical joints, and does not authorize rerunning old campaigns or starting new ones. Keep old-data
unavailability explicit and scope any future producer change independently.

**Production test requirements — ALL NOT YET RUN:** `ACCEPTANCE_MATRIX.json` carries all **26** scientific P-series fixtures
(`P01`–`P26`) and sixteen observed source-probe names. Verify stored/deflate/ZIP64/long-comment/duplicate/corrupt/oversized
members; conditional non-null/null version on **every** read; scan-field-order/overlap, embedded timeseries, all fused
members, partial/lean/missing and 0/false/null; source/actor/recipient and all-crew role ambiguity; infection versus symptom
clocks, censor/competing event, rare tail and NA empty groups; exact D1–D4/PS01 four hull; posterior vs voyage grain,
model-specific clinical/non-AGE, bounded fleet weights, units and four independent validity axes;
source-change/kill/retry/at-limit/off-by-one budget and idempotent recovery; real connector denial, interruption and
pagination. Compare a **small authorized archive golden sample** and independently selected saved member rows to adapter
output; original scanner identity/equivalence must be proved or tagged unresolved. Under fixtures, every source object
accounted (including quarantines), every parsed run represented once under explicit selection, every available requested
metric has valid numerator/denominator/clock and joint row link, and every incomplete metric has reason/evidence. Data
catalog valid at source/attempt/hull/grain; never substitute all-history = all-metrics-covered. Collect two or more query
pages, verify concatenated joint rows/correlations/zeros/nulls equal independent expected selection, automatic Edison durable
acknowledgment and real interruption recovery. Do not mark production pass from **41** local synthetic scientific reference
tests, **135** contract consistency checks or **16** old-source edge probes; these passed only their offline
reference/diagnostic scope.

**Deliver after execution, not instead of execution:** implementation SHA plus source/worker/image/adapter digests; live
role/queue/image/dependency verification; finite approved quote and phase requests; frozen inventory with dated 197-row
reconciliation, additive roots and scope deltas; pilot timings/bytes/member/schema; immutable per-job
checkpoint/status/cost/error receipts; SHA-256 derived partition manifest and COMMIT catalog; per-family per-metric coverage,
all selected run scalar counts and optional detail; bounded query pages/figure inputs and **durable Edison acknowledgment
receipts**. Until those artifacts are returned, all-campaign distribution access is **NOT CERTIFIED**. Kosmos interprets
distribution/sensitivity results and scientific validity; Devin owns tool creation, AWS execution and repairs. PI resolves D3
scientific definition, scope and exceptional paid/permission decisions, not routine file movement.


## 9. Evidence appendices and reading order

- **Canonical scope and adapter index:** [all218 typed rows](CAMPAIGN_COVERAGE.json), [CSV](CAMPAIGN_COVERAGE.csv), [counts](COVERAGE_COUNTS.json), [19 program groups](FAMILY_GROUP_REGISTER.json), [118 attempt/token families](ATTEMPT_FAMILY_MAP.json), [11 source schema families](SOURCE_FAMILIES.json).
- **Full production contract:** [505-field reading view](FIELD_CONTRACTS.md), [machine dictionary](FIELD_CONTRACTS.json), [row schema](TABLE_ROWS.schema.json), [query schema](QUERY.schema.json), [execution-request schema](REQUEST.schema.json), [metadata bootstrap schema](BOOTSTRAP_REQUEST.schema.json), [invalid blocked request](BLOCKED_REQUEST.template.json), [invalid blocked bootstrap](BLOCKED_BOOTSTRAP.template.json), [structural-only blocked joint query](QUERY.blocked_example.json). The example's small numeric caps are illustrative ceilings, not measured source sizes, a cost quote or permission to run; unresolved catalog/analysis/weights placeholders make it semantically blocked.
- **One implementation/execution path:** [canonical interface](CANONICAL_INTERFACE.json), [explicit aliases/authority](ALIAS_AND_AUTHORITY_MAP.json), [phased tickets](PHASED_TICKETS.json), [acceptance matrix](ACCEPTANCE_MATRIX.json), [Devin dispatch](DEVIN_HANDOFF.md).
- **Unchanged lane evidence appendices — not alternate canonical interfaces:** [census report](../census/CENSUS_REPORT.md), [scientific contract lane](../contracts/FIELD_CONTRACT.md), [analysis recipe](../contracts/analysis_recipe.json), [tool review](../tools_review/TOOLS_REVIEW.md), [full tool register](../tools_review/TOOL_REGISTER.json), [old-source probes](../tools_review/OFFLINE_FIXTURE_RESULTS.json), [AWS draft](../aws_review/AWS_EXECUTION_HANDOFF.md), [dated access artifacts](../aws_review/evidence/oct19_access/pr1079/VERIFICATION.md). Any competing proposed paths/schema in these files are superseded **only** by the explicit integrated alias map; original detailed evidence is preserved.
- **Source pin and reproducibility:** [orchestrator checks](../ORCHESTRATOR_SOURCE_CHECKS.md), [37 recovered text files](../SOURCE_SUPPLEMENT_INVENTORY.json), [canonical3,272 Git-blob checks](../CANONICAL_SOURCE_VERIFICATION.json), [final independent source verification](FINAL_SOURCE_VERIFICATION.json), [input evidence manifest](INPUT_EVIDENCE_MANIFEST.json), [package checks](VALIDATION.json), [non-self-referential artifact hashes](SHA256SUMS.json), [primary repository BibTeX](references.bib).

### Source, limits and discretionary analytical decisions

I used the pinned repository snapshot [primary software source, `crusher2026reductionsource`](references.bib), direct line
permalinks above, dated October AWS metadata/access evidence and four original lane artifacts.
`CANONICAL_SOURCE_VERIFICATION.json` reports 3,272 canonical blob matches. I did not open all historical ZIP payloads,
independently verify external AGE literature or current AWS access, execute a reducer, build a production image, certify all
registered campaign images, or confirm durable Edison automation; these are **gates**, not implied successes.

- I selected one extension of the repo's shared launcher/analysis image rather than the AWS lane's separate new entrypoint, because `AGENTS.md:81–86` explicitly freezes the bespoke layout; the original lane command is retained only in `ALIAS_AND_AUTHORITY_MAP.json`.
- I chose the final census's **218 typed records** as scope authority rather than simply concatenating two registers; the overlap gives **198 union prefix names**, not 218 distinct experimental families, while future AWS discovery may add further roots and names.
- I adopted the contracts lane's 26-table scientific dictionary/33 definitions and added eight operational tables to distinguish physical objects, provenance links, scoped coverage, immutable attempts/receipts and durable query-page acknowledgments; AWS lane shorthand table labels remain explicit aliases.
- I made exact per-run native scalars mandatory and rich agent/event details conditional on what actually survived; precomputed arm quantiles and marginals cannot recover within-voyage joint distributions or validate denominators.
- I separated metadata bootstrap from paid execution admission so the need for a pilot cost quote does not cause a circular or unlimited launch; resources/prices/permissions and real data volumes must be measured, not guessed.
- I treated PS01 four-hull production completion as a **ledger claim at its original image**, not a claim that frozen D3, scanner identity, fleet validity or durable distribution access have passed; no three-hull first paper and no automatic resimulation.
