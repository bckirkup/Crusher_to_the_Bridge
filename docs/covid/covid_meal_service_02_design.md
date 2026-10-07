# MEAL-SVC-02 design — attenuating `service_to_host` on the door-drop factor

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

MEAL-SVC-01 (measured, canary 20/20 takeoff-conditional seeds at
`32b11ccf`; readout `docs/covid/covid_meal_service_01_canary_readout.md`)
proved the missing steward→host direction converts deliveries into
confined-passenger acquisitions — `zone_narrow_svc_dir` landed a
confined-pax median of **804** vs the record-implied bound ≥52
(~15× overcorrection at the shipped shared contact factor), during-total
1,267, crew share 0.379 vs record 0.29, deliveries parity 166k. The
verdict read CHANNEL-FOUND: the direction exists and carries the mass,
but at the shared (0.05, 0.3) door-drop factor the signature sits high.

The seam is the shared draw itself: `_caregiver_service_epoch` hoists
one realized `contact_factor` per delivery and applies it to BOTH dose
directions. There is no physical reason the steward→host pickup
(the guest at the door) shares the steward's door-drop discount — the
host direction may carry its own attenuation.

The question this design answers: **where on the door-drop attenuation
axis does `service_to_host` land the passenger mass — and does the same
point keep the crew share near the record?**

## Arm semantics (fixed here before cells run)

Grammar lives on `transmission.caregiver.roles.service` beside
`contact_factor`, parsed in `_init_caregiver` and echoed verbatim in the
resolved block (`delivery.caregiver.roles.service` in the cell payload)
on every cell:

- `contact_factor_to_host` — **absent** → the host direction takes the
  delivery's shared realized draw (status quo; the CF_HOST_SHIPPED
  control, which doubles as the drift witness vs the MEAL-SVC-01 canary
  row). A **scalar** or `[lo, hi]` pair resolves the host direction's
  own declared corner/interval, drawn per delivery on its own spawn of
  the dedicated stream family (`_SERVICE_HOST_CONTACT_STREAM_KEY`), so
  the shared realization — and the steward-side dose — is untouched.
  The steward side always uses the shared factor. Malformed values fail
  at spec-lands, same grammar as `contact_factor`.
- The seam is at `_credit_service_to_host`: the shared `factor` is
  passed in, and the host-side dose multiplies by the resolved host
  factor (the shared draw when undeclared, the own-draw when declared).
- Witnesses: every cell echoes the effective host factor
  (`contact_factor_to_host` + `contact_factor_to_host_mode` in both the
  resolved block and `crew_window`), and `crew_window
  .service_host_factor_draws` reports the realized-draw stats
  {n, mean, median, q05, q95, min, max} — n == service_deliveries on a
  DIR cell, 0 on a responder cell; the lottery check reads median/mean
  against the declared spec.

The arms on the single factor axis, crossed with the replay/corner
arms:

| arm_id | protocol | direction | responder mode | `contact_factor_to_host` |
|---|---|---|---|---|
| `d0_declared_svc_base` | shipped SOP-017 | responder | uniform | — (absent) |
| `zone_narrow_svc_base` | SOP-017-NARROW | responder | uniform | — (absent) |
| `zone_narrow_svc_dir_cf_shipped` | SOP-017-NARROW | both | uniform | absent (shared draw) |
| `zone_narrow_svc_dir_cf_mid` | SOP-017-NARROW | both | uniform | [0.02, 0.08] |
| `zone_narrow_svc_dir_cf_lo` | SOP-017-NARROW | both | uniform | [0.005, 0.02] |
| `zone_narrow_svc_dir_cf_floor` | SOP-017-NARROW | both | uniform | 0.01 (scalar) |
| `zone_narrow_svc_dir_cf_off` | SOP-017-NARROW | both | uniform | 0.0 (scalar) |
| `d0_svc_dir_cf_shipped` | shipped SOP-017 | both | uniform | absent (shared draw) |
| `d0_svc_dir_cf_off` | shipped SOP-017 | both | uniform | 0.0 (scalar) |
| `zone_narrow_svc_dir_sect_cf_lo` | SOP-017-NARROW | both | section | [0.005, 0.02] |

Ride-alongs per owner decision: the D0 corner pair
({SHIPPED, OFF} × D0 — the full-pool bound on the host channel), the
single SECT sub-arm at CF_HOST_LO (structure × magnitude interaction;
section remains the only structure arm), and the two `*_svc_base`
drift rows (the carried-open CW-02 pairing under today's merged tree).

## Replay contract (verbatim CW-02)

`diamond_princess_2020`, `voyage_mode: declared`, SOP-017 days 16–30,
`infection_age_days` 6.8, `imports` 1, `sanitary_visit_mode`
`dwell_weighted`, seeds 20200205–20200224 (the matched 20-seed set),
`takeoff_recorded_onsets` 10, `seed_ring_readout` true, Θ7.9e6 only.

Cells: 10 arms × 20 seeds = **200** declared-replay cells.

## Scoring surface (frozen)

- **Primary:** confined-pax during-window acquisitions
  (`confined_passenger_infections_during_quarantine`, takeoff-conditional
  medians per arm) vs the bound region (~52; the record-implied pax mass
  ~45–160 is stated as context, not threshold).
- **Direction witness:** during-window crew share vs the record's 0.29 —
  direction, never a threshold.
- **During-window total** reported beside [150,350] — not gating.
- **Crew-side co-surface:** steward share of during-window crew
  acquisitions per arm — the host factor leaves the steward side on the
  shared draw; the co-surface verifies it.
- **Cadence parity:** `service_deliveries` per cell within noise of the
  MEAL-SVC-01/CW-02 rows (~166k; CW-02 band 128k–166k @7.9e6).

## Verdict grammar (frozen)

- **MAGNITUDE-LANDED** — an arm lands the takeoff-conditional
  confined-pax median in the bound region (26–160: half the ≥52 floor up
  to the top of the record-implied context band) with crew share moving
  record-ward. The factor that lands is a magnitude to source, not a
  constant to adopt.
- **OVER-ATTENUATED** — the armed median collapses toward the
  responder-only floor (the `*_svc_base` level).
- **STILL-HIGH** — confined-pax median above ~200 even at the lowest
  declared factor.
- **NONLINEAR-BREAK** — the response departs monotone in the declared
  factor across the ZONE_NARROW ladder — a flag for attribution, not a
  failure.
- **BETWEEN** — median above the bound region but below the STILL-HIGH
  line (reported, no verdict forced).

Every arm row reports: takeoff-conditional median of
`infections_during_window`, `confined_passenger_infections_during_
quarantine`, `during_window_by_role` (crew share), steward share of crew
acquisitions, `service_deliveries`, the realized host-factor median,
per-direction dose tallies, `service_to_host` route acquisitions, and
the structure witness.

## Audit invariants (frozen — a failure halts the readout)

- CW-02's set carried unchanged: `quarantine_witness` window [16,30] +
  activated; `exempt_classes` = shipped four crew classes;
  `index_onset_day` −1.0; `index_shedding_at_day0` true;
  `propensity_draw.units_drawn` > 0; `presentation_draw_mode`
  `once_per_course`; `hand_reservoir_mode` `hygiene_cycle`; droplet
  split (0.175, 0.0); `crew_window` totals + confined/working split
  (1045); `exempt_work_zones` echo on zone arms; realized exempt share
  in (0,1).
- **Host-factor echo:** every cell echoes `contact_factor_to_host` +
  `contact_factor_to_host_mode` in BOTH `delivery.caregiver.roles
  .service` and `crew_window` — absent arms echo the shipped tuple with
  mode `shared`; declared arms echo the declared spec with mode
  `declared`. A missing or mismatched echo halts the readout.
- **Realized host-factor distribution (lottery check):**
  `service_host_factor_draws.n == service_deliveries` on DIR cells
  (0 on responder cells); realized min/max inside the declared window;
  realized mean within 10% of the declared midpoint on uniform arms;
  scalar arms realize exactly the scalar; CF_HOST_OFF realizes 0.
- **Direction echo + host credit:** `direction` echoes `both` on every
  `*_svc_dir_*` cell; `service_dose_to_host_credited > 0`
  takeoff-conditional on armed DIR cells and **== 0 by construction**
  (delivered and credited) on CF_HOST_OFF even with takeoff;
  `service_dose_credited` (steward side) stays >0 on took-off DIR
  cells — the shared draw is untouched.
- **Structure witness:** stewards/host median ~44 uniform, ~1–2 on the
  SECT sub-arm (max ≤ 6); `service_section_steward_draws` > 0 iff
  section mode.
- **Deliveries parity:** per-row `service_deliveries` median within 15%
  of the row's `*_svc_base` median.

## Diagnostics (frozen)

- `paired_vs_in_design_base`: each DIR row pairs seed-for-seed with its
  replay arm's `*_svc_base` row — Δ confined-pax acquisitions, Δ crew
  share, Δ `infections_before_quarantine` (expected ~0).
- `paired_vs_cw02`: `*_svc_base` rows pair against CW-02's `t7p9e6_d0` /
  `t7p9e6_zone_narrow` rows at `2df542ff` — deliveries parity is the
  binding comparison, not bit-identity (intervening merges moved
  realizations between measurement SHAs).
- `paired_vs_meal_svc_01`: `zone_narrow_svc_dir_cf_shipped` reported
  beside the MEAL-SVC-01 canary's confined-pax median 804 at `32b11ccf`
  — the drift witness for the control arm.
- `ladder_check`: the ZONE_NARROW × factor ladder ordered by declared
  factor mean (OFF < FLOOR < LO < MID < SHIPPED) — a falling median on a
  rising factor is the NONLINEAR-BREAK flag.
- `route_attribution`: `during_quarantine_by_route.service_to_host` per
  arm.

## Report immediately if

- The canary (`zone_narrow_svc_dir_cf_lo`, 20 seeds) lands confined pax
  near the bound with crew share ≤ ~0.5 moving record-ward — stop,
  report before the array.
- A scalar corner lands the bound exactly — the factor's floor is the
  answer; a source tranche, not more cells.
- The response departs monotone in the factor (NONLINEAR-BREAK).
- Deliveries parity fails or the host-credit witness contradicts the
  declared factor.
- Child failure rate > 5%.

## Execution (frozen)

AWS Batch via `campaigns/covid/meal_service_02/` through
`scripts/campaign`: 10 blocks (arm) × 20 seeds; jobdef
`picard-covid-meal-svc-02`, image `covid-meal-svc-02` pinned by digest
built at the merged implementation SHA, S3 prefix
`campaign/covid_meal_service_02/`, queue `picard-analysis-queue`
(On-Demand; Fargate fallback `picard-analysis-fargate-queue`),
1 vCPU / 2048 MB per cell.

Preflight per `campaign-preflight`: this file + the design JSON frozen
before any cell runs; local smoke on capped voyages proving the seam
fires (armed cell credits host dose scaled by the declared factor; OFF
zero; SHIPPED shared-draw parity; deliveries parity; echoes correct);
`--dry-run` count = 200; pinned image digest + jobdef revision recorded;
manifest in S3; canary `zone_narrow_svc_dir_cf_lo` @Θ7.9e6 (20 seeds)
read out and reported before the remaining 9 blocks submit.

## Non-goals

- No fitting: factor intervals are declared arms; whichever lands is a
  magnitude to source afterward, not a constant to adopt. Never tuned
  to the ≥52 bound or the 0.29 share.
- Episode share, delivery cadence, host-direction efficiency constants —
  rejected axes, stay parked.
- SECT stays subordinate — one sub-arm only.
- No re-run of the CW-02 ladder; no mid-campaign arms; no new Devin
  child sessions — Batch cells only.

## Rejected alternatives

- Re-declaring the shared `contact_factor` — attenuates both directions;
  the leg isolates the host direction with the steward side pinned.
- Host-direction route efficiency constants — parked per owner decision;
  the door-drop factor is the seam under test.
