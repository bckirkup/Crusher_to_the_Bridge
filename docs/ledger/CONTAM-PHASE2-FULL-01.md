# CONTAM-PHASE2-FULL-01
**Date:** 2026-11-08
**Commit:** 03a264be6f502dadbddd3a0286ddbb5222f2ff77
**Pathogens:** all
**Status:** measured
**Measured at:** 03a264be6f502dadbddd3a0286ddbb5222f2ff77

Phase 2 CONTAM four-cruise contrast full panel executed after Benjamin's
2026-11-08 approval of the §7 stratified amendment (#1193). The already
complete pilot block `mega_cruise_5000_e_baseline` was not resubmitted; the
other 59 trajectory blocks (1,180 trajectories) ran on AWS Batch against the
frozen S3 field cache and manifest. This is a transport-correctness /
source-realization panel only: no occupant dose, breathing rate, attack rate,
or anchor enters the readout, and no epidemiology was run.

## Execution record

- Frozen-state verification: `campaign.json`,
  `design/phase2_cruise_contrasts_design.json`, `cell.py`, `entry.py`, and
  `readout.py` had an empty `git diff db95a4f2..03a264be`; S3
  `manifest.json` SHA256 `abce9949f2169ffa21535db9be828183c05270fa9c54b6d4dbfaa5e178db3cf0`
  and `field_cache/field_cache.json` SHA256
  `e8d61dd4703ee6c2a7e5624db35d8c80f3f034c6f76ac533e91a5bfdd74fc6c6` matched the
  frozen values; ECR tag `contam-phase2-cruise-contrasts-01` resolved to digest
  `sha256:7a8a92bba521efb5b6add9760ba124cc9b51faa7459776b6634e0e2ceb66a1d7`;
  jobdef `picard-contam-phase2-cruise-contrasts-01:1` was ACTIVE with that
  digest-pinned image and 1 vCPU / 2048 MiB.
- Preflight: `scripts/campaign submit contam/phase2_cruise_contrasts_01
  --block <block> --dry-run --account 994254241749 --bucket
  crusherbucket-994254241749-us-east-1-an --profile picard` rendered all 59
  remaining blocks with `arrayProperties.size = 20` (59 × 20 = 1,180
  trajectories). The campaign CLI's non-dry-run path registers a fresh jobdef
  revision, so the rendered argv payloads were submitted with
  `jobDefinition` pinned to `picard-contam-phase2-cruise-contrasts-01:1`.
- Batch: 59 array jobs on `picard-campaign-queue`, job names
  `picard-contam-phase2-cruise-contrasts-01-<block>-20261108-214034`, all
  reached SUCCEEDED; children SUCCEEDED 1,180/1,180 with 0 FAILED. Pilot job
  `7e82041b-2abb-42d5-8f4d-2eecf1040011` remained the only
  `mega_cruise_5000_e_baseline` array.
- Readout: `campaigns/contam/phase2_cruise_contrasts_01/readout.py` was run
  against `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/`
  with `--field-cache` set to the S3 field cache and
  `--array-wall-clock-minutes 3.468983` (the pilot array wall recorded in
  `CONTAM-PHASE2-PILOT-01`). The machine-readable report was written to `/tmp`
  for this audit and is not committed here; the committed readout results are
  the next session's deliverable.

## Transport-correctness base and §8 gates

`PYTHONPATH=. .venv/bin/python -m pytest tests/test_contam_analytic_fixtures.py -q`
→ 34 passed at `03a264be`.

| §8 gate | Measured | Result |
|---|---|---|
| Coverage | 1,200/1,200 cells observed, 0 missing; `BLOCKED_ENGINE_FALLBACK=0`; field sources `field_cache=640` (all E/P) and `native_layout=560` (all N); dropped/unknown/alias audit counts 0/0/0 | pass |
| Pairing | N−E paired contrasts have `n=20` for all 4 hulls × 7 arms; P−N baseline has `n=20` for all 4 hulls; arm−baseline contrasts have `n=20` | pass |
| Phase 1 bridge | `expedition_cruise_450` baseline N/E/P seeds 1–20: 60/60 cells bit-identical to the Phase 1 cells on `retained_fraction_curve`, `volume_weighted_concentration_burden_h`, and `zone_stats`; 0 mismatches | pass |
| Arm realization | 1,200/1,200 cell `arm_record`s match the frozen ops, engine args, filter efficiency, OA fraction, realized per-group settings, and supply gains; group ops change exactly the supply groups and filter-only arms change 0 groups; `ach_150_supply` DC04 `r_low` is feasible at 0.1 on every supply group | pass |
| Metrics emitted | `readout.py` emitted 60 hull:lane:arm metric rows, lane and arm−baseline paired contrasts, DC01/DC02/DC04/DC05/DC07 tables, DC05 realized AHS flow tables, and report-only diagnostics; DC01 ordering passed 20/20 on all 8 N/E lane controls with 0 per-zone violation seeds | pass |
| Report-only diagnostics | timing/RSS, path inventory, field-solve/load seconds, field audit counts, injection connectivity, Phase 1 cache byte comparison, and the Edison 5-pp tie band are emitted as diagnostics only | pass |
| No epidemiology | cells and readout contain tracer transport quantities only; no occupant dose, breathing rate, attack rate, or anchor enters the readout | pass |

## Cost audit

Full-panel totals from the 1,200 S3 cell artifacts (`cell_{seed}.json`) and
Batch job records:

| Measure | Measured | Reference | Result |
|---|---:|---:|---|
| Cells | 1,200 | 1,200 expected | pass |
| Missing cells | 0 | 0 | pass |
| `BLOCKED_ENGINE_FALLBACK` | 0 | 0 | pass |
| Field-source counts | `field_cache=640`, `native_layout=560` | E/P cached, N native | pass |
| Trajectory wall p95 | 8.248256591 s | ≤ 60 s pilot threshold | pass |
| Trajectory wall mean / max | 2.774334396 s / 9.815462612 s | report-only diagnostic | — |
| Peak RSS max | 120.667969 MiB | ≤ 1792 MiB pilot threshold | pass |
| Artifact bytes total | 71,790,882 bytes (≈68.465 MiB) | report-only diagnostic | — |
| Trajectory CPU-hours | 0.9247781320 | compare below | pass |
| Trajectory + field-load CPU-hours | 1.0517494962 | report-only diagnostic | — |
| Audit counts (dropped / unknown / alias) | 0 / 0 / 0 | 0 each | pass |
| Batch arrays | 60/60 SUCCEEDED; children 1,200/1,200 | 60 blocks × 20 | pass |
| Array wall-clock | per-array 3.397617–4.050800 min; remaining-59 submit→terminal span 5.402350 min | report-only diagnostic | — |

Per-hull trajectory cost:

| Hull | Cells | Trajectory CPU-h | Artifact bytes |
|---|---:|---:|---:|
| `expedition_cruise_450` | 300 | 0.0860798114 | 8,702,494 |
| `classic_cruise_1900` | 300 | 0.1208859353 | 13,203,386 |
| `spirit_cruise_3000` | 300 | 0.1636002205 | 18,675,541 |
| `mega_cruise_5000` | 300 | 0.5542121648 | 31,209,461 |
| **Total** | **1,200** | **0.9247781320** | **71,790,882** |

## Amended-expectation comparison

| Measure | Measured | Stratified point estimate | ×1.5 expectation | Historical uniform bound | Result |
|---|---:|---:|---:|---:|---|
| Full-panel trajectory CPU-hours | 0.9247781320 | 1.216761 | 1.825142 | 2.1140694828 | below point, expectation, and uniform bound |
| Full-panel artifact bytes | 71,790,882 | 93,133,925 | 139,700,888 | 131,855,220 | below point, expectation, and uniform bound |

Even including the field-cache load CPU as a diagnostic
(1.0517494962 CPU-hours total), the panel remains below the stratified point
estimate, the ×1.5 expectation, and the historical uniform bound. The measured
totals are also far below the 2× amended-expectation sanity stop.

## Decision

**Phase 2 panel complete.** Coverage, pairing, the Phase 1 bridge, arm
realization, §8 metric/contrast emission, report-only diagnostics, and the
no-epidemiology boundary all pass; the measured cost is below the amended §7
expectation and the historical uniform bound. The pilot NO-GO under the
original frozen uniform extrapolation remains recorded in
`CONTAM-PHASE2-PILOT-01`; panel scope is governed by the approved §7
stratified amendment. Committing the canonical readout results
(`readout/phase2_readout.json` / `READOUT.md` equivalent) is the next
session's deliverable.
