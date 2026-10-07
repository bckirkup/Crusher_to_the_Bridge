# MEAL-SVC-01
**Date:** 2026-10-06
**Commit:** 32b11ccf
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 32b11ccf

The confinement meal-delivery channel on the verbatim
`diamond_princess_2020` replay (image
`picard-campaign@sha256:2f2f27c9` / tag `covid-meal-svc-01`, jobdef
`picard-covid-meal-service-01` rev 1, prefix
`campaign/covid_meal_service_01/`). CW-02 measured the R3 channel hot
and under-converting — 128k–166k deliveries/cell, passengers ~4–19
during-window vs bound ≥52 — because dose was credited to the steward
only. MEAL-SVC-01 added the missing direction:
`transmission.caregiver.service.direction: "both"` credits the host
the roles-swap `_caregiver_pair_dose(steward, host)` under route
`service_to_host`, plus a sticky steward-section arm. Declared grid
{D0_declared, ZONE_NARROW} × {SVC_BASE, SVC_DIR, SVC_DIR_SECT} × 20
seeds = 120 cells @θ7.9e6; design frozen pre-run; readout
`docs/covid/covid_meal_service_01_readout.md`.

**CHANNEL-FOUND at the canary — the steward→host direction converts
deliveries into confined-passenger infections, and the declared full
pair-dose magnitude overcorrects ~15×.** Canary `zone_narrow_svc_dir`
(20 seeds): confined-passenger takeoff-conditional median **804** vs
the ≥52 bound (CW-02: ~4–19); during-window median 1,267 (band
[150,350] reported beside); crew share median 0.379 vs the record's
0.29 (CW-02 ~0.97). The frozen stop rule fired — the remaining 100
cells were not submitted.

Measured, not inferred:

- Every takeoff cell routes acquisitions through `service_to_host`
  (up to 1,337 during-window route-attributed acquisitions on one
  seed); host-credited dose >0 on all 19 takeoff cells, exactly 0 on
  the no-takeoff cell — the tally is takeoff-conditional by
  construction.
- Deliveries parity holds: median 166,150/cell inside the CW-02 band
  (128k–166k). The mechanism adds a dose direction, not deliveries.
- Structure witness reads the uniform draw (median 44 distinct
  stewards/confined host); the section arm never ran — its collapse
  expectation is untested.
- The conversion scales with voyage shedder mass: confined-pax
  84→1,290 across takeoff seeds, crew share 0.265→0.743.

Not measured: `svc_dir_sect` and the `*_svc_base` rows (canary stop);
the CW-02 drift witness needs those base rows and stays open.

**The open decision is the attenuation axis on `service_to_host`** —
which declared magnitude between 0 (responder-only) and 1 (this arm)
brackets the record: host-direction efficiency/contact factor,
asymmetric application of the door-drop `contact_factor` (shared draw
since #936), episode share, or delivery cadence.
