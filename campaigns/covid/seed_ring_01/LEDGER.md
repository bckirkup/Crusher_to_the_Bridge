# covid_seed_ring_01 — ledger

Seam-probe campaign executing the frozen
`picard_framework/runs/covid_seed_ring_01_design.json`
(COVID-SEED-RING-01, declared in COVID-IGNITION-01): does declaring the
index's boarding-window footprint — dining assignment to the embarkation
surge buffet, `seed_patch.placement.dining_service_type: "buffet"` — lift
the founder-pool draw to the record-implied level and land the trajectory
clause with θ and every constant unchanged?

1 theta × 2 arms × 20 seeds = 40 declared-replay cells on the verbatim
DP contract. Follows `campaigns/covid/quar_tail_01/` as the working
template: 2 blocks (arm) × 20 seeds; `entry.py` translates block args +
seed into `cell.py` argv; `run_cell`/`merge_screen` reused unmodified.
One engine delta: `initiation.explicit_seeds[].placement` (the
`dining_service_type` pool constraint) ships with this campaign and is
inert on every undeclared seed.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell → `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — frozen three-leg verdict grammar (founder median ≥10 →
  ign ≤9 → trajectory clause) + placement audit invariants + committed
  `dp_theta_8p50` drift witness.
- Block order in campaign.json is cell-order: arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-11-21 — registration

- Spec registered: `campaigns/covid/seed_ring_01/`, queue
  `picard-analysis-queue`, image tag `covid-seed-ring-01`, resources
  1 vCPU / 4096 MB (matching the QUAR-TAIL-01 jobdef).
- Arms: D0_declared (boxed_s1s2 verbatim; pairing base + drift witness),
  PLACEMENT_BUFFET (boxed + `seed_patch.placement.dining_service_type
  "buffet"` — the canary block).
- Canary per the campaign-preflight gate: `t8p50_placement_buffet`
  (20 cells) read out before the D0 drift-witness block submits.

## 2026-11-21 — build + canary

- Image built at merged main `87e8e3bb` (ENGINE_GIT_SHA), pushed as
  `picard-campaign:covid-seed-ring-01`, digest
  `sha256:87bc852a27f52cf476d09e417df6845a4c66aa9485490785d40b9d1a160b4773`.
- Jobdef `picard-covid-seed-ring-01:1` registered; in-container check
  confirmed design + worker + entrypoint present and the seed→argv
  translation (seed 20200205 → `--arm PLACEMENT_BUFFET`).
- Canary child submitted: job `fc6753b4-3f50-4681-833c-2618264fb9f6`
  (t8p50_placement_buffet, index 0 = seed 20200205). SUCCEEDED ~20:57 UTC;
  artifact inspected — `seed_spec.placement.dining_service_type="buffet"`
  echoed, index is a Windjammer diner, scored contract complete
  (128 recorded onsets, 3 before split).
- Full block submitted: array job
  `6044952d-5273-4e32-bd95-746fdb1b3d60` (20 cells, jobdef rev :3 —
  each non-dry-run submit registers a new revision: :2 canary, :3 array).
  Queue `picard-analysis-queue` (maxvCpus 256, all 20 cells concurrent);
  ETA ≈ 25 min from submit.

## 2026-11-21 — canary verdict: NULL-PLACEMENT

- All 20 `t8p50_placement_buffet` cells SUCCEEDED (~60 min array wall clock,
  long tail on founder-rich cells); artifacts under
  `campaign/covid_seed_ring_01/t8p50_placement_buffet/`.
- Readout (image `87e8e3bb`, seeds 20200205-20200224): founder median
  2.0 takeoff-conditional (2.0 all cells) vs committed drawn 2.5 — the
  frozen >=10 leg fails; verdict NULL-PLACEMENT, the Arm-B reading:
  dining placement is not the operative declaration; the embarkation-day
  crowd/muster geometry itself is under-declared.
- Audit invariants clean; placement was exercised (17/20 Windjammer
  indices, plus Pool_Bar_Grill and CafeBakery buffet venues); 17/20
  takeoff; ignition median 21 on ignited cells.
- Measured heterogeneity inside the null: seeds 20200214/20200215 did
  produce record-class pools (19 and 25 founders, day-0 bursts 16 and 0);
  the draw can reach the record footprint through this venue but the
  median does not move — surge participation is rare, not absent.
- Drift witness not yet run: `t8p50_d0` block unsubmitted, pending the
  canary-gate decision.
- User approved the D0 block 21:54 UTC; array
  `0f5fe819-c14f-425f-b63a-3a5f9e7841d7` submitted (20 cells, jobdef
  rev :4).

## 2026-11-21 — campaign complete

- `t8p50_d0` array landed 20/20 (~70 min wall clock); full readout at
  `seed_ring_01_readout.md`.
- D0_declared verdict BASELINE (drift witness): founder median 3.0
  takeoff-conditional (2.5 all cells), ignition median 13.5 on 16/16
  ignited — reproducing the committed drawn-draw profile, including its
  heavy tail (record-timed cells 20200212/19/22, all drawn Windjammer
  indices with day-0 bursts).
- Committed-cells drift witness: **CLEAN** — 0/20 seed-paired
  recorded_onsets deltas vs committed `dp_theta_8p50`. NULL-PLACEMENT
  is physics, not image drift.
- Campaign closed: ledger entry `docs/ledger/COVID-SEED-RING-01.md`
  (status measured), registration in `docs/ledger/README.md`, COVID
  open ledger and Θ/DP handoff updated in the same change.
