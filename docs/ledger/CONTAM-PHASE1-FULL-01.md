# CONTAM-PHASE1-FULL-01
**Date:** 2026-11-08
**Commit:** 801ea44c83cb6c9230bc0d7e78bd3cf8fb378f80
**Pathogens:** all
**Status:** measured
**Measured at:** 801ea44c83cb6c9230bc0d7e78bd3cf8fb378f80

Phase 1 CONTAM HVAC tracer full panel executed after the Missouri lane-E pilot
GO. Benjamin's "go ahead" authorized the remaining 320 trajectories; the
Option A pre-staged field cache was reused, no local trajectory runs were
performed, and no `engines/` or `tools/` code changed. This is a
transport-correctness / source-realization panel only: it does not select
publication claims, couple epidemiology, or package an Edison data return.

## Execution record

- Inputs: `field_cache.json` schema `contam_phase1_hvac_tracer_field_cache_v1`,
  11 fields (6 E + 5 P), 2,015,906 bytes, SHA256
  `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5` at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json`;
  design manifest byte-identical at `.../manifest.json`. ContamX provenance is
  recorded in `CONTAM-PHASE1-PILOT-01`.
- Image/jobdef: `picard-campaign:contam-phase1-hvac-tracer-01@sha256:8956cf37e530e9ccda1f349580727f0a51e95fe052206bf7d1170827cfd4d42f`
  (built at `a3dab46fcf50ee4c51b5962d9139c27a3f76e0f3`; PR #1179 only pinned the
  digest and wrote ledgers). Pilot used jobdef `picard-contam-phase1-hvac-tracer-01:1`;
  the 16 full-panel block submits used revisions `:2` through `:17`.
- S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/<block>/cell_{1..20}.json`;
  the pilot block is `missouri_bb63_e`, and the 16 full-panel blocks are all
  other trajectory blocks in `campaign.json`.

| block | jobdef rev | Batch job ID | status | array wall-clock (min) |
|---|---:|---|---|---:|
| `missouri_bb63_e` | `1` | `3d8d615c-b35d-4a23-a96b-b2f384c12345` | SUCCEEDED | 2.199567 |
| `destroyer_baseline_e` | `2` | `8b04ef68-5286-41c9-883c-7d406f792bb7` | SUCCEEDED | 3.106750 |
| `destroyer_baseline_n` | `3` | `15412fc1-2a48-44e1-80cd-6920b2cd88b5` | SUCCEEDED | 3.166333 |
| `destroyer_baseline_p` | `4` | `10f954b4-56d7-40d7-8d41-fc0c136dfe07` | SUCCEEDED | 3.155833 |
| `expedition_cruise_450_e` | `5` | `e9901463-038a-410b-aa5c-5206e2998aba` | SUCCEEDED | 3.130750 |
| `expedition_cruise_450_n` | `6` | `e4a7a116-dd4b-45d3-97f6-182cc97da8df` | SUCCEEDED | 3.099567 |
| `expedition_cruise_450_p` | `7` | `ba551def-8fe4-4940-9563-7573a1902f1f` | SUCCEEDED | 3.047917 |
| `fletcher_class_destroyer_e` | `8` | `1ecebc72-8d2f-40a1-8422-5ac92f237081` | SUCCEEDED | 3.072733 |
| `fletcher_class_destroyer_n` | `9` | `352cc549-0a87-4228-b6c3-5a91a9ba27c4` | SUCCEEDED | 3.017833 |
| `lexington_cv2_e` | `10` | `f72fd714-f220-4136-afe2-020ccd714ccf` | SUCCEEDED | 3.444083 |
| `lexington_cv2_n` | `11` | `41137e1e-1f55-4d3c-abd2-a9820556946e` | SUCCEEDED | 3.415433 |
| `lexington_cv2_p` | `12` | `86e04691-f76c-4167-b954-4df62d6baab8` | SUCCEEDED | 2.943467 |
| `missouri_bb63_n` | `13` | `0a6bbd53-3e0b-451d-9ba1-3002d668c5e7` | SUCCEEDED | 3.500983 |
| `missouri_bb63_p` | `14` | `8ca713d9-dbe7-4d22-a725-d324f32017e7` | SUCCEEDED | 3.463567 |
| `saratoga_cv3_e` | `15` | `76ee160d-ad04-4043-bbd7-08e694c3a533` | SUCCEEDED | 3.429867 |
| `saratoga_cv3_n` | `16` | `41e15ac4-d809-412a-b902-714cd8a7773b` | SUCCEEDED | 2.952300 |
| `saratoga_cv3_p` | `17` | `f25fa4b9-10f8-415f-bb81-27c2e388feb0` | SUCCEEDED | 2.925783 |

## Readout and acceptance

`readout.py` was run against the campaign S3 prefix with the field cache:
coverage is **340/340 cells, 0 missing**; every hull×lane has 20 observed seeds;
paired N−E and P−N contrasts have `n=20` for all six hulls. `field_source`
counts are `field_cache=220` (all E/P cells) and `native_layout=120` (all N
cells); `BLOCKED_ENGINE_FALLBACK` count is 0; dropped-endpoint, unknown-zone,
and alias-collision counts are all 0. The frozen pilot gate remains `go=True`.

Full-panel cost audit from the 340 cell artifacts:

| Measure | Measured | Pilot/frozen reference | Result |
|---|---:|---:|---|
| Cells | 340 | 340 expected | pass |
| Missing cells | 0 | 0 | pass |
| `BLOCKED_ENGINE_FALLBACK` | 0 | 0 | pass |
| Trajectory wall p95 | 2.454948 s | ≤ 60 s pilot threshold | pass |
| Trajectory wall max | 2.878910 s | report-only diagnostic | — |
| Peak RSS max | 100.894531 MiB | ≤ 1792 MiB pilot threshold | pass |
| Artifact bytes total | 10,505,015 (≈10.02 MiB) | ≤ 25 MiB pilot threshold | pass |
| Trajectory CPU-hours | 0.141446 | ≤ 1.0 CPU-h pilot threshold; < 12× pilot bound 0.157241 | pass |
| Trajectory + field-load CPU-hours | 0.178728 | report-only diagnostic | — |
| Audit counts (dropped / unknown / alias) | 0 / 0 / 0 | 0 each | pass |
| Full-panel remaining Batch wall-clock | 3.842567 min | 16 arrays, per-array 2.925783–3.500983 min | pass |

The 55.667133 min span from the pilot submit to the last full-panel array
terminal is not a compute cost; it includes the interval between the pilot
readout and Benjamin's full-panel authorization.

## Decision

**Phase 1 panel complete.** Coverage, pairing, metrics, paired N−E/P−N seed
contrasts, and report-only diagnostics satisfy manifest §8 as executed by
`readout.py`. Per-hull×lane medians and paired contrasts are in the regenerated
readout (`readout.py` against the S3 prefix above); this entry records the
execution, cost audit, and acceptance state. Coupled epidemiology — norovirus
null and respiratory epidemiology/environmental detection — remains the Phase 3
decision gate and was not run here.
