# covid_crew_window_01 — ledger

First COVID campaign under the `campaigns/` grammar. Executes the frozen
`picard_framework/runs/covid_crew_window_01_design.json` (CREW-WINDOW-01:
which sourceable attenuation of the working-crew channel lands the
during-quarantine median in the record-informed band) — 2 thetas x 6 arms x
20 seeds = 240 declared-replay cells on the verbatim DP contract.

Migrated onto the generic harness per the AGENTS.md frozen-legacy-layout
rule (added 1d4778f6): the boarding-screen cell map decomposes into 12
blocks (theta x arm) x 20 seeds; `entry.py` translates block args + seed
into `cell.py` argv; `run_cell`/`merge_screen` are reused unmodified. The
earlier `deploy/aws/Dockerfile.covid_crew_window` overlay predated the
decision and was removed unused.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell -> `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — verdict grammar + audit invariants + D4 drift witness
  (pairs D0 rows vs `campaign/covid_quar_suppression_v1/6ea3093d/`).
- Block order in campaign.json is cell-order: theta, then arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-10-05 — registration

- Spec registered: `campaigns/covid/crew_window_01/`, queue
  `picard-analysis-queue`, image tag `covid-crew-window-01`, resources
  1 vCPU / 2048 MB (matching the retired `picard-covid-boarding-screen`
  jobdef rev 56).
- Canary per the campaign-preflight gate: `t7p9e6_crewduty` (20 cells)
  read out before the remaining 11 blocks submit.
