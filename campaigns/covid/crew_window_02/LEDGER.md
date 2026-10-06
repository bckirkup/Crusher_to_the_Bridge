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

## 2026-10-06 — preflight

- Implementation + design freeze merged at `2df542ff` (PR #927):
  `exempt_work_zones` / `exempt_fraction` confinement gates, `work_zone`
  on the dict projection, `crew_window` payload block, 5 SOP-017
  variants (`-NARROW`/`-WIDE`/`-QUARTER`/`-HALF`/`-THREEQ`).
- Local smoke (410-epoch capped voyages, seed 20200205 @7.9e6):
  ZONE_NARROW → 762 confined crew in quarantined_ids, 283 working all
  inside the 11-zone essential list, realized share 0.271 (lottery
  expectation is conditioned on posted crew — the share denominates all
  1045); FRAC_25 → drawn exactly 261 = int(0.25·1045+0.5), 213 working
  (drawn agents confined via isolation/other paths), zone-blind
  spread. `service_deliveries` > 12k on both.
- Worker image `picard-campaign@sha256:2b481866d4f5` (tag
  `covid-crew-window-02`), built at merged SHA `2df542ff` via
  `Dockerfile.campaign` over a fresh `picard-campaign` base; design
  JSON + gate code verified inside the image pre-push.
- Jobdef `picard-covid-crew-window-02` registered rev 1; manifest +
  design at `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_window_02/`
  (campaign.json, design.json, design.md).
- Chain-check child submitted: job `7713fbcd-5973-4bc0-9185-26789713b55a`
  (t7p9e6_zone_wide index 0, seed 20200205), registering jobdef rev 2.

## 2026-10-06 — canary (t7p9e6_zone_wide, 20 seeds)

- Chain-check cell SUCCEEDED (~20 min), payload contract verified:
  `crew_window` block echoes the 19-zone list verbatim,
  `service_deliveries` = 166k, all working crew inside the essential
  list.
- Canary array `c91492d8-9dcd-4197-9eb1-6e35b9a0b526` — 20/20 children
  SUCCEEDED, zero failures. Readout (carried into the full report):
  during-window median **504** vs band [150,350] → **UNDER-ATTENUATED**;
  crew share 0.986; realized exempt share 0.540 vs 19/34≈0.559 lottery
  conditioned on posted crew — consistent; min `service_deliveries`
  149,343; takeoff 19/20. Cliff structure persists at the widest
  interior point.
- Readout-tool defect found + fixed during the canary: falsy-zero on
  `settled_share=0.0` spuriously flagged all cells; `_CW1_PREFIX`
  default lacked the `s3://` bucket. Lands with the final readout
  commit.
- User approved the remaining 220 cells after the canary report.

## 2026-10-06 — full array (220 cells submitted)

| block | array job id |
|---|---|
| t1e6_d0 | 4bf7ba3b-f435-4094-b4ad-e93e5dd248e9 |
| t7p9e6_d0 | 8992462d-0984-4fcf-b504-cbfa88d0e353 |
| t1e6_zone_narrow | f10e59d2-169b-4f95-bf94-2a2cee0bee43 |
| t7p9e6_zone_narrow | 9a397eb0-b165-4ad8-8b9c-a5979bf54d08 |
| t1e6_zone_wide | b6d79db2-1337-4962-84ab-df17cd90aded |
| t1e6_frac_25 | f733b623-945c-4de7-bd77-5ae644de6580 |
| t7p9e6_frac_25 | 73f1eea9-2c02-4eaa-8059-eca33f5fa66d |
| t1e6_frac_50 | f9d52960-7455-47ef-bc6b-3d916c5defda |
| t7p9e6_frac_50 | 8dcc2f6b-0aef-402c-82e3-e64f5b1c39c1 |
| t1e6_frac_75 | 8df6bd5e-1dc6-4c1e-98ac-4c94d17da01f |
| t7p9e6_frac_75 | 75372b7e-2a55-4ea5-a096-f72f4f88ec23 |
