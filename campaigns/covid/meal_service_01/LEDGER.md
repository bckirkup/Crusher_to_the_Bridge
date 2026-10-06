# covid_meal_service_01 — ledger

MEAL-SVC-01 campaign. Executes the frozen
`picard_framework/runs/covid_meal_service_01_design.json` (design doc
`docs/covid/covid_meal_service_01_design.md`): what does the confinement
meal-delivery channel have to be before the passenger side of the share
defect closes — 1 theta (7.9e6) x 6 arms (2 replay x 3 channel) x 20
seeds = 120 declared-replay cells on the verbatim DP contract.

Follows `campaigns/covid/crew_window_02/` as the working template: the
boarding-screen cell map decomposes into 6 blocks (arm) x 20 seeds;
`entry.py` translates block args + seed into `cell.py` argv;
`run_cell`/`merge_screen` are reused unmodified. The MEAL-SVC-01 engine
delta (`direction`/`service_responder_mode`/`service_section_cabins` on
`transmission.caregiver.service`, the roles-swap `service_to_host`
credit, the lazy cabin-section partition + sticky steward binding, the
per-direction dose tallies and structure witness in `crew_window`) lands
with the design freeze in the same change.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell -> `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — verdict grammar CHANNEL-FOUND / DOSE-EMPTY / MASS-ONLY
  + audit invariants (CW-02's set plus the direction echo, the
  host-credited tally, the realized stewards-per-confined-host
  structure witness, and deliveries parity) + the CW-02 drift witness
  (pairs `*_svc_base` rows vs `campaign/covid_crew_window_02/{t7p9e6_d0,
  t7p9e6_zone_narrow}/` at 2df542ff).
- Block order in campaign.json is cell-order: arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-10-06 — registration

- Spec registered: `campaigns/covid/meal_service_01/`, queue
  `picard-analysis-queue`, image tag `covid-meal-svc-01`, resources
  1 vCPU / 2048 MB (matching the CW-02 jobdef).
- Canary per the campaign-preflight gate: `zone_narrow_svc_dir`
  (20 cells) read out and reported before the remaining 5 blocks submit.
