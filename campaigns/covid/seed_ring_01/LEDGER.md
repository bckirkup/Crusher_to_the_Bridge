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
