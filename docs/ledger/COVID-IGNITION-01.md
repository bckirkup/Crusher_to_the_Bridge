# COVID-IGNITION-01
**Date:** 2026-11-21
**Commit:** 13d653d4313605a69c353c83b4c00ab0911e9aa8
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** b45911709e277bd51bf09de8ba73a742add314d9

The residual Θ blocker after QUAR-TAIL-SEAM-01: at right-sized truth
(θ=3.162e8, `dp_theta_8p50` / D0_declared verbatim replay — the 20 campaign
cells bit-identical to the committed refit), before_share 0.059 vs the
record's 0.173 because most draws ignite ~10 d late. QUAR-TAIL-01 named two
candidate explanations — seed-ring/early-cabin structure vs intrinsic dose
timing at this θ. This entry measures which. Pure readout over the
committed payloads; `tools/covid_ignition_readout.py`, evidence at
`reports/ignition_01/dp_theta_8p50_ignition.json`.

## What is measured

Every cell seeds one index: `count` 1, `departure_day` 5.0,
`infection_age_days` 6.8, `onset_day` −1.0, role passenger — identical on
all 20 cells (SEED-GEOM-01 established the spec echoes what is applied and
that age is a null axis under declared onset). The founder window is the
index's 5 days aboard: `aboard_window_acquisitions` counts every
non-seeded infection with epoch < index departure, and the clean bound
counts only those before any secondary could shed (pure index yield).

- **The founder-pool lottery is the whole story.** Founder yields split
  cleanly on record timing with zero overlap: the 4 cells that ignite by
  day ≤9 — matching the record's day-13-15 confinement peak — drew
  10/10/13/28 founders. Every cell with ≤5 founders ignites ≥day 10
  (12 takeoff cells, days 10–28) or dies below the takeoff gate (4 cells,
  yields 0–1). Record-timed founder median 10; late median 3; dead 1.
- **It is not dose amplitude or growth rate.** Post-founder growth is
  similar across cells (cum10→cum15 fold median 3.8, range 1.0–17.5 with
  no yield-stratified shift), and the day-0 droplet bursts of 25/11/6 on
  the three fastest cells prove high yield is reachable when the draw
  gives the index a broad embarkation-day footprint — the record-implied
  ~10 founders is inside the machinery's range.
- **The founder channel is structurally narrow.** Across all 20 cells
  the aboard-window routes are droplet (63) + caregiver (34) only — no
  direct, airborne, or fomite acquisition while the index is aboard in
  any draw. The index's cabin ring is always size 1; table ring 0–5 is
  not discriminating. Founder yield is bounded by the day-0 zone crowds
  the drawn index happens to visit (boarding/muster exposure), not by
  any persistent ring.

## Verdict

Late ignition is a **seed-ring / boarding-window exposure lottery**, not
intrinsic dose timing: the single declared index's yield is a draw on a
structurally narrow channel (droplet + caregiver, bounded by which
embarkation-day crowds its drawn itinerary visits), and the median draw
(2.5 founders) under-delivers the ~10+ founders record timing needs.
Slow post-ignition growth is falsified — the epidemic grows normally
once the pool exists.

## Declared seam — COVID-SEED-RING-01 (probe design)

A θ=3.162e8, D0-base probe varying the declared boarding-window exposure
structure of the index, with the prediction frozen before running:

- **Arm A — declared index placement:** the index assigned a high-traffic
  embarkation-day footprint (the day-0 crowd pathway the burst cells
  already exercise) rather than a drawn placement. Prediction: founder
  median → ≥10 → ign ≤9 → before_share → ~0.173 → the trajectory clause
  passes with θ and every other constant unchanged.
- **Arm B — boarding-event contact structure:** if the model's day-0
  crowd/muster exposure is itself under-declared, no placement arm can
  lift the founder median — that null result names the boarding-event
  geometry as the defect rather than the placement lottery.
- **Explicitly not axes:** θ, dose-response constants, imports>1 (the
  record declares one index; a multi-seed arm is a falsification probe,
  not a fit).

Null/positive results both land the next declaration: positive → index
boarding-window exposure joins the replay's declared structure; null →
the deficit is in the embarkation-day contact structure itself, and the
seed spec is not the carrier.

## Open owner calls (unchanged from QUAR-TAIL-SEAM-01)

- `confirmed / infections_reachable` as the scored capture basis
  (declared in CAPTURE-01, vindicated in SEAM-01).
- Whether FRAQMB_DUTY (boxed + quarter-exempt + duty exclusion) becomes
  the boxed_s1s2 replay default — the only arm landing the during-band.
