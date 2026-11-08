# CONTAM-PHASE2-PILOT-01
**Date:** 2026-11-08
**Commit:** db95a4f2b63c3dc115100c7421e1261fcf61bfd7
**Pathogens:** all
**Status:** measured
**Measured at:** db95a4f2b63c3dc115100c7421e1261fcf61bfd7

Phase 2 CONTAM four-cruise contrast cost pilot under the frozen Option A
pre-stage: the 32 ContamX fields were generated locally, `field_cache.json`
and the design manifest were uploaded to S3, and only the
`mega_cruise_5000_e_baseline` trajectory block ran on AWS Batch. No local
trajectory runs were performed; the 20-child Batch array is the canary/pilot
cell. No other block was submitted.

## Execution record

- Field cache: `cell.py --mode field-cache` at repo SHA `db95a4f2`, using
  official NIST ContamX `3.4.0.3 64 bit` (`third_party/contamx/contamx3`,
  SHA256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`;
  NIST Contam is U.S. public domain, 17 U.S.C. §105). Artifact schema
  `contam_phase2_cruise_contrasts_field_cache_v1`, 32 fields (28 commissioned
  E exports + 4 committed-PRJ P baselines), 12,209,971 bytes, SHA256
  `e8d61dd4703ee6c2a7e5624db35d8c80f3f034c6f76ac533e91a5bfdd74fc6c6`, uploaded
  to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/field_cache/field_cache.json`.
  Max field solve 0.453761105 s; pilot field `mega_cruise_5000:E:baseline`
  0.315229132 s. The two Phase 1 reusable controls
  (`expedition_cruise_450:E:baseline`, `expedition_cruise_450:P:baseline`)
  compared byte-identical to the Phase 1 cache.
- Manifest: `design/phase2_cruise_contrasts_design.json` mirrored
  byte-identically (SHA256
  `abce9949f2169ffa21535db9be828183c05270fa9c54b6d4dbfaa5e178db3cf0`) to
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/manifest.json`.
- Image/jobdef: root `Dockerfile` + `deploy/aws/Dockerfile.campaign` overlay
  built at `db95a4f2`; ECR tag `contam-phase2-cruise-contrasts-01`, digest
  `sha256:7a8a92bba521efb5b6add9760ba124cc9b51faa7459776b6634e0e2ceb66a1d7`.
  In-container check confirmed `deploy/aws/`, `tools/`, and `campaigns/` are
  present and the campaign spec has 60 trajectory blocks with no Batch
  `field_cache` block. Jobdef `picard-contam-phase2-cruise-contrasts-01:1`,
  queue `picard-campaign-queue`, resources 1 vCPU / 2048 MiB, array size 20.
- Batch: parent job `7e82041b-2abb-42d5-8f4d-2eecf1040011`
  (`picard-contam-phase2-cruise-contrasts-01-mega_cruise_5000_e_baseline-20261108-210106`)
  reached SUCCEEDED with 20/20 children; artifacts landed at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/mega_cruise_5000_e_baseline/cell_{1..20}.json`.

## Frozen threshold readout

Readout: `campaigns/contam/phase2_cruise_contrasts_01/readout.py` over the S3
prefix with `field_cache.json`; `pilot_gate.go = false`. Campaign-wide
coverage is 20/1,200 observed with 1,180 missing because only the pilot block
was submitted; the pilot block itself has 20/20 seeds and `missing_seeds=[]`.

| Gate | Measured | Limit | Result |
|---|---:|---:|---|
| Pilot cell SUCCEEDED, no `BLOCKED_ENGINE_FALLBACK` | 20/20 SUCCEEDED; fallback count 0 | 0 fallback | pass |
| Pilot seed coverage | 20/20 seeds, `missing_seeds=[]` | complete | pass |
| E field solve wall-clock | 0.315229132 s (`mega_cruise_5000:E:baseline`); max of 32 fields 0.453761105 s | ≤ 30 s | pass |
| Per-trajectory wall-clock p95 | 6.798478769 s | ≤ 60 s | pass |
| Pilot array wall-clock | 3.468983 min | ≤ 30 min | pass |
| Pilot total CPU-time | 0.0353220550 CPU-h | ≤ 1.0 CPU-h | pass |
| Peak RSS | 120.667969 MiB | ≤ 1792 MiB | pass |
| Pilot artifacts | 2,197,587 bytes (≈2.10 MiB) | ≤ 25 MiB | pass |
| Dropped endpoints / unknown real zones / alias collisions | 0 / 0 / 0 | 0 each | pass |
| Extrapolated full-panel trajectory CPU | 2.1140694828 CPU-h | ≤ 1.697352 CPU-h | fail |
| Extrapolated full-panel artifact bytes | 131,855,220 bytes | ≤ 126,060,180 bytes | fail |

## Cost audit

| Measure | Measured | Pilot/frozen reference | Result |
|---|---:|---:|---|
| Pilot cells | 20 | 20 expected | pass |
| Pilot missing seeds | 0 | 0 | pass |
| `BLOCKED_ENGINE_FALLBACK` | 0 | 0 | pass |
| Trajectory wall p95 | 6.798478769 s | ≤ 60 s | pass |
| Trajectory mean wall | 6.342208448 s | report-only diagnostic | — |
| Peak RSS max | 120.667969 MiB | ≤ 1792 MiB | pass |
| Artifact bytes total | 2,197,587 (≈2.10 MiB) | ≤ 25 MiB | pass |
| Trajectory CPU-hours | 0.0352344914 | < 1.0 CPU-h pilot bound | pass |
| Trajectory + pilot-field CPU-hours | 0.0353220550 | ≤ 1.0 CPU-h pilot bound | pass |
| Audit counts (dropped / unknown / alias) | 0 / 0 / 0 | 0 each | pass |
| Pilot array wall-clock | 3.468983 min | ≤ 30 min | pass |
| Field solves | 32/32, max 0.453761105 s | ≤ 30 s each | pass |

The readout's frozen extrapolation is the uniform full-panel scaling of the
pilot cell: `1200 × trajectory_mean_seconds / 3600 = 2.1140694828` CPU-h and
`1200 × artifact_bytes_total / 20 = 131,855,220` bytes. Both exceed the
manifest §7 bounds (12 × the measured Phase 1 full panel), so the pilot gate
is `go=false`.

## Decision

**NO-GO** for the full 1,200-trajectory Phase 2 panel as frozen: every
per-pilot operational threshold passed, but the two frozen §7 full-panel
extrapolation bounds failed. This is a measurement, not a design change; the
full panel remains Benjamin's decision and no further blocks were submitted.
