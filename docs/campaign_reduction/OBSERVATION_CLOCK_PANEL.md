# first_paper_observation_clock — observation/clock sidecar: specimen panel + extraction quote

**Status: draft-for-gate — profile implemented and panel-verified; the full
run waits on the explicit envelope approval (the $100 envelope is declared,
not yet admitted for this reduction).**

Sidecar for the `red-fps01-b` cohort (Edison's "red-fps01-b2" — same 8,000
declared executions, `sources_sha256`
`1b992296…2dc1`). One wide row per execution, joined by exact existing
execution/source identity — `source_key` (zip object key) is the only join
key; hull/seed disagreement is a typed conflict, never first-row-wins
(same rule as `first_paper_scalar`).

## Panel (measured 2026-10-31, picard profile)

16 ranged-read specimens = first two seeds per cell × 4 hulls × {off,
ps_ship} + 8 scan-row heads. 96 requests / 1.46 MB total.

| measurement | value |
|---|---|
| `parameters.engine_git_sha` | `a9f4a517` on all 16 (producing image `noro-provisioned-source01@sha256:97d99be4…`) |
| producing→current drift on report paths | none — only `eb2c6495` (mechanical S3776 split) between `a9f4a517` and HEAD on the five report-semantics files |
| `timeseries` retained | 288 rows, epoch index contiguous 0..287, on all 16 |
| `num_epochs` (top-level) vs `parameters.num_epochs` | 288 vs 288 — the emitted value IS `meta.epochs` = the configured horizon, never observed |
| `natural_history_clock` | `hours` → epoch index = hour since voyage start; embarkation date lives in the campaign manifest (`noro_provisioned_source_01_manifest.json`), not the run archive |
| terminal ts counters vs summary block | equal on all 16 (noise 195/185/44/48/700/690/698/333/290…) |
| `trigger_status` enum | `ALERT` baseline → `SUSPECTED` (detection) → `CONFIRMED`; `derived.detection_epoch` equals first non-ALERT epoch (verified 262) |
| `*_reported_case_rate_exceeded` | never fired in the 16 specimens → `vsp_either_channel_first_epoch` null + `not_crossed_in_window` (distinct from `timeseries_absent`) |
| route-sum arithmetic | `infections_by_dominant_route` sum = `n_acquired` (111 = 111); `n_imports + n_acquired` = `cumulative_ever_infected` (40+111 = 151) — Edison's correction verified in the data |

## What the counts represent (producing code, verified)

- `cumulative_reported_cases{,_passenger,_crew}` = distinct persons with a
  symptomatic presentation that epoch ∩ `syn_result.true_positive_ids`
  (own sick-call hazard, caregiver channel, `report_sick_call` override).
  Crew-screening reports enter `sick_call_ids` only — **not** this set.
- `cumulative_reported_noise_cases` = distinct non-presenting persons who
  reported via FRED background-noise categories — **fleet total only, no
  role split exists anywhere in the archive**.
- The two sets are disjoint within an epoch by construction (presenting
  vs non-presenting partition) but **not across epochs** — FIELD_CONTRACTS
  union-not-sum applies; the ID sets are never serialized (only `len()`),
  so overlap/union emit typed-unavailable, never inferred.
- `summary.sick_call_count` / `onset_observation_count` are **last-epoch**
  values, not voyage cumulatives (emitted as `last_epoch_*` columns).

## Availability matrix

| Edison field | state | evidence |
|---|---|---|
| etiologic reports pax/crew/total + denominators | available | `summary` block + terminal ts (cross-checked) |
| noise reports total | available | total-only scalar |
| noise reports per role | `not_recorded` — `role_split_never_emitted` | `_summary_counts` emits no role split; proportions are not inference |
| etiologic∩noise overlap, union | `not_recoverable` — `person_id_sets_not_serialized` | sets live only in `SimulationState`; compact history drops `syn_result`; census payload is transmission-chain only |
| observed terminal epoch + retained coverage | available | `timeseries` last index + row count vs `parameters.num_epochs` |
| first pax/crew/etiologic/noise report, VSP either-channel, detection, confirmation, symptomatic/quarantine/isolation firsts | available | per-epoch cumulative counters + `*_exceeded` flags + `trigger_status` |
| scanner key/hull/seed + provenance | available | full-key scan join + `source_key`, `engine_git_sha`, `image_digest`, `definition_sha256` |
| embarkation wall-clock date | `not_recorded_in_run_archive` — `date_anchor_is_campaign_manifest_level` | `initiation.manifest.boarding_epoch` is per-pathogen epoch only |
| per-epoch sick-call rosters / first_detection_events / onset_observations | `not_recoverable` — `compact_history_drops_rosters` | dropped by the compact-history filter |

## Validation-definition corrections applied

1. `infections_by_route_consistent` compared acquired-route sums against
   imports+acquired — it diverges by exactly `n_imports` on every run
   with imports. Split per Edison: `infections_by_route_vs_acquired_consistent`
   (route sums vs `census_n_acquired`) + `imports_plus_acquired_vs_ever_infected_consistent`
   (new `operand_sum_checks` kind). The old flag is still emitted, tagged
   `historical_evidence` in provenance.
2. `follow_up_status` renamed `scan_posted_status` — it is the scanner's
   `posted` rollup only, not evidence of follow-up completeness.
   (`first_paper_scalar` bumped to `/1.2.0`.)

## Extraction quote (`first_paper_observation_clock`)

Read side: ~3 ranged GETs per zip (HEAD-pin, CD tail, member body —
panel measured ~6/run incl. scan-file reads) plus one whole read per
scan file. Compute side: same `summary.json` member as
`first_paper_scalar`; the profile adds the embedded 288-row series
parse (~×1.5 row width).

| term | 8,000 runs (off + ps_ship × 4 hulls) |
|---|---|
| **requests** | ~40k ranged GETs + 8 scan reads + ~150 partition PUTs |
| **bytes read** | ~0.3 GB (8k × ~22 kB member + 24 MB scan) |
| **compute** | parse ~3.4 GB JSON: ~30–50 vCPU-min; peak RSS < 1 GiB |
| **storage (derived)** | `first_paper_observation_clock_vectors` ~8k wide rows ≈ 200 MB JSONL (~60 MB gz) + base tables + ~125 shard checkpoints |
| **export** | ~60 MB gz out of S3 |
| **direct AWS cost estimate** | S3 ≈ $0.02; Batch compute < $1 (one job, minutes) — far inside the $100 envelope and under the ~$5 census-read threshold; `growth_census.json.gz` (~50 MB/zip) is never touched |

Worker path: identical machinery to `red-fps01-b` —
`campaign_reduction.yml` workflow_dispatch → `aws batch submit-job` on
`picard-analysis-queue`/`picard-analysis-memory-queue`. The new profile
is new code in the image → **new image push (picard role) + one jobdef
re-registration line under the owner's profile (iam:PassRole)** before
dispatch; the dispatch itself waits on the `aws-campaign` environment
approval click.

## Reproduce

Panel script: ranged-GET `_scan_rows/fl_{hull}_12d_scr_{arm}.jsonl`
heads, take first two `key`s per file, `open_pinned` → `index_zip` →
`read_member(summary.json)`; profile extraction verified by running
`observation_clock.vector_rows` directly on the decoded member (all
fields above emitted, zero missing except typed-availability columns).
