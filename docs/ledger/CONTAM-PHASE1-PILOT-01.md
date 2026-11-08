# CONTAM-PHASE1-PILOT-01
**Date:** 2026-11-08
**Commit:** a3dab46fcf50ee4c51b5962d9139c27a3f76e0f3
**Pathogens:** all
**Status:** measured
**Measured at:** a3dab46fcf50ee4c51b5962d9139c27a3f76e0f3

Phase 1 CONTAM HVAC tracer cost pilot under Benjamin's Option A amendment:
the 11 E/P ContamX fields were generated locally, `field_cache.json` was
uploaded to S3, and only the `missouri_bb63_e` trajectory block ran on AWS
Batch. No local trajectory runs were performed; the 20-child Batch array is
the canary/pilot cell.

## Execution record

- Field cache: `cell.py --mode field-cache` at repo SHA `a3dab46f`, using
  official NIST ContamX `3.4.0.3 64 bit` (`third_party/contamx/contamx3`,
  SHA256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`;
  NIST Contam is U.S. public domain, 17 U.S.C. §105). Artifact schema
  `contam_phase1_hvac_tracer_field_cache_v1`, 11 fields (6 E + 5 P; Fletcher is
  E-only), 2,015,906 bytes, SHA256
  `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5`, uploaded
  to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json`.
- Manifest: `design/phase1_hvac_tracer_design.json` mirrored byte-identically
  to `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/manifest.json`
  before submit.
- Image: root `Dockerfile` + `deploy/aws/Dockerfile.campaign` overlay built at
  `a3dab46f`; ECR tag `contam-phase1-hvac-tracer-01`, digest
  `sha256:8956cf37e530e9ccda1f349580727f0a51e95fe052206bf7d1170827cfd4d42f`
  (1,269,649,299 bytes). In-container check confirmed `deploy/aws/`, `tools/`,
  and `campaigns/` are present and the campaign spec has 17 trajectory blocks
  with no Batch `field_cache` block.
- Batch: jobdef `picard-contam-phase1-hvac-tracer-01:1`, queue
  `picard-campaign-queue`, resources 1 vCPU / 2048 MiB, array size 20.
  Parent job `3d8d615c-b35d-4a23-a96b-b2f384c12345`
  (`picard-contam-phase1-hvac-tracer-01-missouri_bb63_e-20261108-155628`)
  reached SUCCEEDED with 20/20 children; artifacts landed at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/missouri_bb63_e/cell_{1..20}.json`.

## Frozen threshold readout

Readout: `campaigns/contam/phase1_hvac_tracer_01/readout.py` over the 20 pilot
cells plus `field_cache.json`; `pilot_gate.go = True`, all ten pass flags true.

| Gate | Measured | Limit | Result |
|---|---:|---:|---|
| Pilot cell SUCCEEDED, no `BLOCKED_ENGINE_FALLBACK` | 20/20 SUCCEEDED; `field_source=field_cache`; fallback count 0 | 0 fallback | pass |
| E field solve wall-clock | 0.240678 s (`missouri_bb63:E`; max of 11 fields also 0.240678 s) | ≤ 30 s | pass |
| Per-trajectory wall-clock p95 | 2.597248 s | ≤ 60 s | pass |
| Pilot array wall-clock | 2.199567 min | ≤ 30 min | pass |
| Pilot total CPU-time | 0.0131034 CPU-h | ≤ 1.0 CPU-h | pass |
| Peak RSS | 100.894531 MiB | ≤ 1792 MiB | pass |
| Pilot artifacts | 892,670 bytes | ≤ 25 MiB | pass |
| Dropped endpoints / unknown real zones / alias collisions | 0 / 0 / 0 | 0 each | pass |
| Seed coverage | 20/20 expected seeds present | complete | pass |

## Conservative full-panel extrapolation

The frozen note bounds the full panel at ≤ 12 × the pilot cell because
Missouri is the cost-pilot hull and E is the solver-cost lane. Using field
entry counts as the transport-work proxy: pilot cell work is
`20 seeds × 2248 missouri_bb63:E entries = 44,960` units. The size-proportional
full-panel estimate is 150,300 units = **3.343× pilot** (N lanes charged at
their native HVAC/cross-zone/adjacency link counts; E/P lanes at their field
entry counts). An ultra-conservative bound that charges every N-lane
trajectory at the largest ContamX field size is 407,000 units = **9.052×
pilot**. Both are ≤ 12×. Scaling the measured pilot CPU estimate gives roughly
0.0438–0.1186 CPU-h for the full panel, versus 12 × pilot = 0.15724 CPU-h;
the 11 local field solves sum to 0.797858 s with max 0.240678 s.

## Decision

**GO** for the remaining 320-trajectory panel decision: every frozen §7
threshold passed and the conservative extrapolation is within the 12× pilot
bound. This is a recommendation only; the full panel remains Benjamin's
decision and no further blocks were submitted.
