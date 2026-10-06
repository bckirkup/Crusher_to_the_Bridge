# covid_crew_window_02 — ledger

Second COVID crew-window campaign. Executes the frozen
`picard_framework/runs/covid_crew_window_02_design.json` (CREW-WINDOW-02:
which interior point between "zero crew working" and "the whole crew
working" lands the during-quarantine median in the record-informed band)
— 2 thetas x 6 arms x 20 seeds = 240 declared-replay cells on the
verbatim DP contract.

Follows `campaigns/covid/crew_window_01/` as the working template: the
boarding-screen cell map decomposes into 12 blocks (theta x arm) x 20
seeds; `entry.py` translates block args + seed into `cell.py` argv;
`run_cell`/`merge_screen` are reused unmodified. The CW-02 engine delta
(`exempt_work_zones` + `exempt_fraction` confinement gates, `work_zone`
on the dict projection, the sticky drawn-set record, the `crew_window`
payload block) lands with the design freeze in the same change.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell -> `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — verdict grammar + audit invariants (CW-01's set plus
  the realized-share witnesses) + CW-01 drift witness (pairs D0 rows vs
  `campaign/covid_crew_window_01/{t1e6,t7p9e6}_d0/` at ea9550ef).
- Block order in campaign.json is cell-order: theta, then arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-10-06 — registration

- Spec registered: `campaigns/covid/crew_window_02/`, queue
  `picard-analysis-queue`, image tag `covid-crew-window-02`, resources
  1 vCPU / 2048 MB (matching the CW-01 jobdef).
- Canary per the campaign-preflight gate: `t7p9e6_zone_wide` (20 cells)
  read out before the remaining 11 blocks submit.
