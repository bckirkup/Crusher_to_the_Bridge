# MEAL-SVC-01 steward→host meal-delivery channel — CHANNEL-FOUND at the canary (ZONE_NARROW × SVC_DIR @Θ7.9e6)

> **Status:** Findings (2026-10-06). Canary measured at `32b11ccf`
> (image `picard-campaign@sha256:2f2f27c9` / tag `covid-meal-svc-01`,
> jobdef `picard-covid-meal-service-01` rev 1, queue
> `picard-analysis-queue`, S3 prefix
> `campaign/covid_meal_service_01/`). Spec and readout under
> `campaigns/covid/meal_service_01/`, design
> `picard_framework/runs/covid_meal_service_01_design.json` (frozen
> pre-run, merged #937). **The canary is the measurement: the frozen
> report-immediately rule fired (CHANNEL-FOUND → stop, report, the
> remaining 100 cells were not submitted).**

CW-02 measured the R3 cabin-meal-delivery channel hot and
under-converting: 128k–166k `service_deliveries`/cell, passengers
acquiring ~4–19 during-window vs the record-implied bound ≥52
(F13/F14), crew share ~0.97 vs the record's 0.29 — because
`_caregiver_service_epoch` credited dose to the steward only; the
steward→host direction did not exist. MEAL-SVC-01 armed that direction
(`transmission.caregiver.service.direction: "both"` — the roles-swap
`_caregiver_pair_dose(steward, host)` credited under route
`service_to_host`) and a sticky steward-section structure arm.

Canary: `zone_narrow_svc_dir`, 20 seeds, θ7.9e6 — 20/20 children
SUCCEEDED, 0 failures, 0 audit violations.

## Result (takeoff-conditional medians, 19 takeoff seeds)

| θ | arm | confined-pax med | bound | during med (band [150,350] beside) | crew share (record 0.29) | deliveries med | host dose med | stewards/host | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 7.9e6 | zone_narrow_svc_dir | **804.0** | ≥52 | 1267.0 | 0.379 | 166150 | 0.005 | 44.0 | **CHANNEL-FOUND** |

CHANNEL-FOUND threshold ≥26 (half the bound, frozen pre-run). Crew
share median 0.379 vs the record's 0.29 and CW-02's ~0.97.

## What was measured

- **The steward→host direction exists and fires at the declared
  magnitude — the signature is recovered and the interval sits high.**
  Every takeoff seed converts deliveries into confined-passenger
  acquisitions through `service_to_host`: takeoff-conditional median
  804 vs the ≥52 bound, ~15× over. During-window total median 1,267
  vs the record-informed band [150,350] (reported beside, not gating —
  but the same overcorrection signature). `service_to_host` is the
  dominant during-window route on takeoff cells (up to 1,337
  acquisitions on seed 20200205).
- **The crew-share defect moves the right direction — and overshoots
  the record the other way.** Median 0.379 vs the record's 0.29, from
  ~0.97 at CW-02. The channel is a first-order share lever, not a
  marginal one.
- **Deliveries parity holds.** Median 166,150/cell inside the CW-02
  measured band (128k–166k); cadence unchanged — the mechanism adds a
  dose direction, not deliveries.
- **Structure witness consistent with the uniform draw** — median 44
  distinct stewards per confined host (uniform floor ≥10). The section
  arm never ran; its collapse expectation (~1–2) is untested.
- **No-takeoff carve-out.** Seed 20200217 (infections_total 0) and
  20200213 (recorded onsets under the takeoff threshold) carry zero
  host-credited dose by construction — no shedding steward exists. The
  readout's iff-DIR audit is now takeoff-conditional (fixed during
  this readout; first pass flagged the no-takeoff cell spuriously).
- Per-seed spread is wide: confined-pax 84→1290 on takeoff cells,
  crew share 0.265→0.743 — the channel's conversion scales with the
  voyage's total shedder mass, not just the delivery count.

## Audit invariants

All swept on every cell, 0 violations: direction echo `both` on every
cell; host-credited tally >0 on every takeoff DIR cell, 0 on BASE
(by construction here — no BASE row ran); structure witness vs the
declared mode; deliveries parity; CW-02's window/index/propensity/
reach set unchanged. The CW-02 drift witness pairs `*_svc_base` rows —
those cells did not run (canary stop rule), so the pairing is n=0 and
carried open to the next stage.

## Verdict grammar read

CHANNEL-FOUND, on the frozen letter (confined-pax takeoff median 804
≥ 26). The reading in context: the channel was real, and the shipped
absence of the steward→host direction was the conversion defect CW-02
measured. At the declared full pair-dose magnitude the channel
overcorrects ~15× on the primary surface — the mechanism interval
sits high, which is a magnitude question, not a defect: the direction
was a structural arm, and nothing in this campaign tunes it.

## The single open decision

The next stage is the magnitude sweep on the `service_to_host`
direction — which axis carries the attenuation between 0 (shipped
responder-only) and 1 (this arm's full pair dose): candidates the
design already names are a host-direction contact/efficiency factor,
the per-delivery `contact_factor` applied asymmetrically, the episode
share, or the delivery cadence itself. Which axis to sweep is the
owner's call; the SECT structure arm is subordinate until the
direction's magnitude is bracketed.

## Not measured this stage

- `svc_dir_sect` (section binding) and both `*_svc_base` rows — the
  canary stop rule held them back.
- The CW-02 drift witness (needs the `*_svc_base` rows).
- Whether a reduced-magnitude DIR arm lands confined-pax near 52
  without dragging the during-window total — that bracket is exactly
  the open sweep.
