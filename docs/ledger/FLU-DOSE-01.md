# FLU-DOSE-01
**Date:** 2026-09-26
**Commit:** f280e348
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** f280e348

## Measurement

Delivered-dose readout for the influenza cabinmate arm, run to test the
unit-mismatch hypothesis in `docs/literature/non_scored_arms_audit.md` §2.2
(shipped `dose_response.k = 0.18` is sourced per-TCID50 but applied per
emitted copy; the hypothesis was that confined mates receive dose deep into
the ≥99% saturation region at ~26 delivered copies).

Instrument: `tools/flu_confined_dose_probe.py` (`run_dose_arm`), reusing the
`CabinPairChallengeLedger` wired as `sim.epoch_observer` — the same tally
CABIN-FLOOR-02 read — with slot resolution replicated from
`_confined_window_counts` at member level: a confined slot is a cabinmate
(≠ earliest-infected member) of a pair that entered all-member quarantine,
uninfected at the pair's first confined epoch. Probe slot counts reproduce
the ledger's `confined_slots` exactly in all four cells.

Same instrument conditions as CABIN-FLOOR-02: platform `classic_cruise_1900`,
288 epochs, seeds 8105/8106, declared confinement (SOP-017 passengers,
day 1 → end), 19 founders per cell (`explicit_seeds` 2 + boarded 8–17).
Local runs, ~330–560 s wall each.

## Dose to confined slots (influenza_a)

Dose = cumulative emitted copies delivered to the target across all
compartment channels (pool/plume/contact/hvac/fomite/emesis/flush), before
the `base_susceptibility` scale.

| Cell | Confined slots | Slots with dose > 0 | Median dose | p90 dose | Max dose | Slots > 25.6 copies | Implied SAR median | Observed confined attack |
|---|---|---|---|---|---|---|---|---|
| active 8105 | 547 | 349 | 2.68 | 13.1 | 41.4 | 2.6% | 0.65 | 62.9% (344/547) |
| active 8106 | 160 | 109 | 2.14 | 7.7 | 44.9 | 0.6% | 0.56 | 36.3% (58/160) |
| edison 8105 | 12 | 12 | 5.19 | 16.0 | 41.0 | 8.3% | 0.61 | 50% (6/12) |
| edison 8106 | 4 | 4 | 9.21 | 35.4 | 35.4 | 25% | 0.81 | 75% (3/4) |

Pooled observed attack reproduces CABIN-FLOOR-02 exactly: active
(344+58)/(547+160) = 56.9%; edison (6+3)/16 = 56.2%.

Channel totals (copies summed over slot targets, both seeds): active —
plume 1,480; hvac 1,102; pool 690; fomite 0.63; contact ~0.001. Edison —
plume 101; pool 42; fomite 0.17; contact ~0.0003; hvac/emesis/flush nil.

## Reading

**Measured.**

- Confined-mate dose sits *at* the shipped N50 (ln2/0.18 = 3.85 copies),
  not above the ~26-copy 99%-saturation point — only 0.6–25% of slots
  exceed it. The deep-saturation picture from the audit is rejected: the
  arm does not overshoot because every mate is saturated.
- Shipped-k implied per-slot SAR medians (0.56–0.81) track observed
  confined attack (36–75%) cell by cell: conversion is what the shipped
  per-copy k says it should be at the delivered doses.
- 36% of active slots (458/707 pooled: 547−349 plus 160−109) and ~8% of
  edison slots register zero delivered copies — dose is concentrated on a
  minority of confined mates.
- Channel mix is dominated by plume + hvac + pool; contact and fomite
  deliver ~0 under both bundles' route weights. Edison's near-identical
  dose scale (median 5–9 copies) at 5× lower emission and 760× lower
  airborne share confirms — now measured, not inferred — that emission
  level is not the binding axis for confined delivery.

**Inferred (arithmetic on the measured distribution, not a run).**

- Under the unit-converted sourced bound for k (≈2e-4–1e-3 per copy,
  N50 ≈ 693–3,466 copies; audit §2.2, Alford 1966 ÷ Van Wesenbeeck 2015),
  the measured doses (median 2–9 copies, p90 ≤ ~36) yield per-slot SAR
  ≈ 0.05–1% — the arm would then read ~0% confined attack, a MISS low
  against the 15–25% floor band rather than the current MISS high.
  (The 15–25% band is since withdrawn on flu — recalibrated as the
  declared-k expected-SAR band, CABIN-FLOOR-03.)
- The flu arm therefore carries two compensating defects of roughly
  matched magnitude: `dose_response.k` ~2–3 orders above its converted
  sourced bound, and confined-mate delivered dose ~2–3 orders below the
  ~700–3,500-copy scale at which a per-TCID50-calibrated hazard would
  reach 50%. Fixing either in isolation flips the miss to the other side;
  the pair currently cancels to land at 57%.

**Hypothesis.**

- The under-delivery is consistent with, not proof of, the emission→
  delivery chain's cumulative capture (~1e-6–1e-7 of emitted copies
  reaching a cabinmate under full confinement). Which stage attenuates —
  release fraction, room-air partition, HVAC decay, breathing uptake —
  is unmeasured; a stage-resolved probe is a separate instrument.

## Diagnosis-queue consequence

Updates audit §2.2: the unit mismatch is confirmed as the operative term
(measured), but "fix k" is no longer a single-defect repair — it exposes
the under-delivery defect underneath. The flu entry in the diagnosis queue
reads: constants-level defect in `dose_response.k` (unit mismatch) *plus*
a delivery-chain magnitude defect; both must move together or the arm
overshoots → undershoots.
