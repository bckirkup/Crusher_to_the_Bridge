# covid_quar_tail_01 — ledger

Seam-probe campaign executing the frozen
`picard_framework/runs/covid_quar_tail_01_design.json`
(QUAR-TAIL-SEAM-01): does a reduced-exempt confinement declaration —
the CW-02 grammar at the right-sized truth θ=3.162e8 — land the dual
prediction declared in COVID-QUAR-TAIL-01 (during-window median into
[150,350] AND confirmed-per-infection capture ≥ 0.80)?

1 theta × 4 arms × 20 seeds = 80 declared-replay cells on the verbatim
DP contract. Follows `campaigns/covid/crew_window_02/` as the working
template: the boarding-screen cell map decomposes into 4 blocks (arm) ×
20 seeds; `entry.py` translates block args + seed into `cell.py` argv;
`run_cell`/`merge_screen` are reused unmodified. No engine delta — every
mechanism (SOP-017-NARROW / -QUARTER, crew_duty_exclusion, crew_window
witnesses) already ships from the CW-01/CW-02 legs.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell → `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — dual-prediction verdict grammar + audit invariants +
  duty-exclusion echoes + committed dp_theta_8p50 drift witness.
- Block order in campaign.json is cell-order: arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-11-21 — registration

- Spec registered: `campaigns/covid/quar_tail_01/`, queue
  `picard-analysis-queue`, image tag `covid-quar-tail-01`, resources
  1 vCPU / 4096 MB (matching the THETA-REFIT-01 DP jobdef).
- Arms: D0_declared (drift witness vs committed 8p50 cells),
  ZONE_NARROW (exempt-share lever alone), ZN_DUTY (zone + VSP duty
  exclusion — the record-warding composition; canary), F25_DUTY
  (fractional alternative composition).
- Canary per the campaign-preflight gate: `t8p50_zn_duty` (20 cells)
  read out before the remaining 60 submit.
