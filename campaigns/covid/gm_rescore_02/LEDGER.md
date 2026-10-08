# LEDGER — covid_gm_rescore_02

Campaign mechanics for COVID-GM-RESCORE-02: the held-out Greg Mortimer
re-score under post-DP-era physics. Frozen design:
`picard_framework/runs/covid_gm_rescore_v2_design.json` (+ the imports:3
sibling `covid_gm_rescore_v2_imports3_design.json`). Grammar inherited
verbatim from COVID-GM-RESCORE-01 (`docs/ledger/COVID-GM-RESCORE-01.md`,
measured at `591d21b1`): H1 campaign positives vs 128/217, H2 asymptomatic
share 0.8125 ± 0.10, takeoff ≥10 recorded onsets, seeds 20200205–254.

## 1. Spec

| Field | Value |
|---|---|
| Queue | `picard-analysis-queue` (Fargate `picard-analysis-fargate-queue` per the drought playbook) |
| Jobdef | `picard-covid-gm-rescore-02` (+ `-fargate` if needed) |
| Image tag | `covid-gm-rescore-02` |
| S3 prefix | `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_gm_rescore_02/` |
| Resources | 1 vCPU / 2048 MB |
| Designs | `picard_framework/runs/covid_gm_rescore_v2{,_imports3}_design.json` |

## 2. Blocks

`{theta, arm_id}` cells resolved inside the design JSON's enumeration —
`entry.py` translates (block args, seed) into the cell worker argv and
picks the design (imports3 block overrides `args.design`).

| Block | θ | Arm | Seeds | Notes |
|---|---|---|---|---|
| `canary_t2e11_hygiene` | 2.37e11 | hygiene_cycle | 20200205–224 (20) | CANARY — anchor row prefix; STOP after readout |
| `t1e11_hygiene` | 1e11 | hygiene_cycle | 50 | |
| `t1e11_spike` | 1e11 | spike_decay | 50 | |
| `t2e11_hygiene` | 2.37e11 | hygiene_cycle | 20200225–254 (30) | fleet continuation of the anchor row |
| `t2e11_spike` | 2.37e11 | spike_decay | 50 | |
| `t1e12_hygiene` | 1e12 | hygiene_cycle | 50 | |
| `t1e12_spike` | 1e12 | spike_decay | 50 | |
| `imports3_hygiene` | 2.37e11 | hygiene_cycle | 50 | imports:3 diagnostic design |

Total: 350 cells (20 canary + 330 fleet = 300 scoring + 50 diagnostic).
The anchor row's 50 payloads pool `canary_t2e11_hygiene/` +
`t2e11_hygiene/` — payloads carry (theta, arm_id, seed) so the readout
merge is coordinate-safe.

## 3. Runs

| Date | Block | Seeds | Cells | Job | SHA | Digest | Wall | Result |
|---|---|---|---|---|---|---|---|---|
| 2026-10-08 | declared | — | 0 | — | — | — | — | design frozen pre-run (v2 lattice + grammar verbatim from RESCORE-01) |
| 2026-10-08 | gate | — | — | — | 6bb0e996 | sha256:c8325d40 | — | PR #970 merged at 6bb0e996; image built+in-container verified (design/campaign/entrypoint present, one full cell through campaign_entrypoint --local); `picard-covid-gm-rescore-02:1` registered; log group + queue confirmed |
| 2026-10-08 | canary_t2e11_hygiene (single) | 20200205 | 1 | 143e6ed8-0669-4e0c-8632-0b158b3aca09 (analysis) | 6bb0e996 | sha256:c8325d40 | ~3m | contract PASS: payload bit-identical to dev-venv local cell (58 onsets, 123/217 pos, asym 0.252, 187 inf, witnesses all echoed) |
| 2026-10-08 | canary_t2e11_hygiene | 20200205–224 | 20 | 2d485e4d-2cf8-4841-b157-aca84709883e (analysis array, rev :2) | 6bb0e996 | sha256:c8325d40 | ~4m | 20/20 SUCCEEDED, 0 audit failures, witness set clean: **P(takeoff) 1.00, positives med 116 [56,133], H1 lands; asym med 0.252 [0.168,0.333], H2 still misses ~3×** — ledger `docs/ledger/COVID-GM-RESCORE-02.md`; STOP per the gate |

## 4. Notes

- v2 audit invariants add the post-591d21b1 shipped-echo witnesses:
  `delivery.caregiver` resolved block (R3 service door-drops),
  `delivery.participation_propensity` resolved (PROPENSITY-V1),
  `delivery.presentation_draw_mode == "once_per_course"` (PRESENT-SHARE-01)
  — on top of the carried v1 set (hand_reservoir_mode echo, seed_ring,
  aboard 223).
- The v2-vs-v1 read is distribution-level per (θ, arm) row on identical
  seed lists; per-seed bit-pairing is not claimed (drift re-rolls RNG
  streams wherever new machinery reaches).
- `readout.py` pools block prefixes (boto3 `--prefix` or `--dir`) into the
  flat staging dirs `tools/covid_gm_rescore_readout.py` expects, then runs
  it for both designs with each as the other's `--pair-cells`.
- Report-immediately triggers carried from the design: anchor row loses
  H1 vs v1, P(takeoff)≈0, asym share lands H2, or spike−hygiene deltas
  go materially nonzero.
