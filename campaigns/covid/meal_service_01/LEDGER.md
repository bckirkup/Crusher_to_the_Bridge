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

## 2026-10-06 — preflight

- Implementation + design freeze merged at `32b11ccf` (PR #937):
  `transmission.caregiver.service.direction` + `service_responder_mode`
  + `service_section_cabins`, roles-swap `service_to_host` host credit,
  lazy cabin-section partition + sticky steward binding, per-direction
  dose tallies + structure witness in `crew_window`. Sibling #936's
  default-ON door-drop `contact_factor` merged mid-flight: one realized
  per-delivery draw now attenuates both dose directions (hoisted into
  `_caregiver_service_epoch`); the frozen `paired_vs_cw02` clause was
  amended in consequence — deliveries parity, not bit-identity, is the
  binding CW-02 invariant.
- Local smokes (capped voyages, seed 20200205 @7.9e6): all three arms
  fire — SVC_DIR credits host dose, SECT collapses realized distinct
  stewards, BASE unchanged-shape; deliveries parity holds.
- Worker image `picard-campaign@sha256:2f2f27c9cc9aa55dd8e173b56dcaaf7bfd648866444a41edd1463d9f7cc1f0ee`
  (tag `covid-meal-svc-01`), built at merged SHA `32b11ccf` via
  `Dockerfile.campaign` over a fresh `picard-campaign` base; in-image
  `--local` cell verified end-to-end (writes `cell_<seed>.json`).
- Jobdef `picard-covid-meal-service-01` registered rev 1 with the
  digest-pinned image (the rendered jobdef's bare tag was replaced
  before registration). Manifest + design at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_meal_service_01/`
  (campaign.json, design.json, design.md).
- Chain-check child `5b58924d-ee61-4d9c-b0fd-7ca4d3a9443b`
  (`zone_narrow_svc_dir` index 0, seed 20200205) SUCCEEDED ~20 min;
  payload contract verified: `crew_window.service_direction=both`,
  host-credited dose 0.027 >0, deliveries 170,576, direction echo at
  `delivery.caregiver.roles.service.direction`.

## 2026-10-06 — canary (zone_narrow_svc_dir, 20 seeds) — CHANNEL-FOUND

- Canary array `72a36039-6d83-4e1f-be6d-eea60db2b4ef` — 20/20 children
  SUCCEEDED, 0 failures. Takeoff 19/20.
- Readout: confined-passenger takeoff-conditional median **804** vs
  bound ≥52 (CW-02: ~4–19) → **CHANNEL-FOUND** (threshold ≥26 frozen
  pre-run). During-window median 1,267 (band [150,350] beside, not
  gating). Crew share median **0.379** vs record 0.29 (CW-02 ~0.97).
  Deliveries median 166,150 — parity with the CW-02 band. Host dose
  median 0.005 >0; stewards/host median 44 (uniform witness). Per-seed
  confined-pax 84→1,290; `service_to_host` carries up to 1,337
  during-window acquisitions on one cell.
- The signature is recovered and the declared interval sits high
  (~15× on the primary surface) — a magnitude to sweep, not a defect.
- **Stop rule fired: the remaining 100 cells were not submitted.** The
  open decision is the attenuation axis on `service_to_host` (see
  `docs/covid/covid_meal_service_01_readout.md` §"open decision").
- Readout-tool fix during the canary (same class as CW-02's
  falsy-zero): the iff-DIR host-credit audit flagged the no-takeoff
  cell (seed 20200217, infections_total 0 — no shedding steward exists
  by construction). The check is now takeoff-conditional.
- Committed readout: `docs/covid/covid_meal_service_01_readout.md`;
  ledger entry `docs/ledger/MEAL-SVC-01.md`; handoff
  `docs/covid/covid_meal_service_handoff_2026_10_06.md`.
