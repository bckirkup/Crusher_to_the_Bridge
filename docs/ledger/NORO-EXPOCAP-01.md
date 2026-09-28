# NORO-EXPOCAP-01
**Date:** 2026-09-28
**Commit:** 27efdbd4
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 429fe0f9

EXPO-CAP-01 bounded re-rank of the NORO-GROWTH-01-RERANK (`ece42dbf`)
placement metric on `fl_spr_12d` with the per-shedder per-epoch contact
budget ON — same manifest, same ignited seed set, same census instrument
(`tools/noro_diag/growth_chain_census.py --exposure-cap on`).

## Cohort

The 11 ignited `fl_spr_12d` seeds (8105, 8114, 8124, 8129, 8132, 8135,
8137, 8148, 8156, 8158, 8159) re-run under the verbatim dose-refit spec
(spirit_cruise_3000, n=3000, 288 epochs, `syndromic_comp65`,
dose_adjustment 7.57), exposure cap default-on. Baseline column: the
rhythm-on census at `ece42dbf` — `engines/` between ece42dbf and
429fe0f9 is exactly the EXPO-CAP-01 diff.

Norovirus is `emesis_conditioned` — zero continuous droplet emission —
but a vomiting event emits aerosol to the droplet pool, so the cap does
fire for this pathogen on emesis epochs: the post-emesis aerosol reach
of an ill host is bounded to its contact-budget cohort, which is exactly
the venue-scale bound the mechanism exists to impose (an unbounded
emesis plume otherwise doses every susceptible in the unit). Where the
cohort binds, the challenged set shrinks, downstream challenge draws
reorder, and trajectory moves are real mechanism plus stream shift —
not byte-identity, and not claimed as such.

## Headline moves vs RERANK baseline

- Ignition: 10/11 ignited (8159 cold, same as RERANK).
- **Challenge-acquired hosts: 7** (vs 13 RERANK, 18 baseline) — one per
  seed on 8105, 8114, 8132, 8137, 8148, 8158, and cold-seed 8159; all
  `unresolved` generation (no fomite chain link attributed).
- **Placement onto non-immune occupancy: 40.3%** (425 of 1,055
  acquired-sourced mass-bearing unit-epochs; RERANK 44.8%, baseline
  32%) — the named metric moves back toward baseline, does not flip.
  Zero-susceptible sweeps 85.8% (RERANK 84.7%); acquired mass never
  seen by a susceptible 559M of 762M GEC (73.4%, RERANK 83.6% — smaller
  absolute deposited mass, similar structure).
- Acquired-sourced patch pickup 2.84M GEC (RERANK 7.42M); hazard
  expectation on acquired-sourced doses 0.018 with **0 observed
  acquired-sourced acquisitions** (RERANK: 4.22 expected, 3 observed).
  The L4 link goes quiet entirely under the cap.
- Total acquisitions 6 in the L4 readout (7 counting the unresolved host
  on cold seed 8159); the chain remains subcritical — no compounding
  voyages.

## Per-run named link (cap vs RERANK)

| seed | RERANK link | cap link |
|---|---|---|
| 8105 | L3 | L4 (drew, no conversion) |
| 8114 | L4 | L4 (drew, no conversion) |
| 8124 | L4 | L0 |
| 8129 | intact | L0 |
| 8132 | L4 | L3 |
| 8135 | L3 | L0 |
| 8137 | intact | L4 (drew, no conversion) |
| 8148 | L4 | L3 |
| 8156 | L4 | L0 |
| 8158 | L4 | L4 (drew, no conversion) |
| 8159 | L4 | cold (not ignited) |

## Verdict

The placement metric does not flip: acquired-sourced mass still meets a
susceptible ~40% of unit-epochs (the deposition footprint is set by where
emesis lands, which the cap does not touch — it bounds who the aerosol
reaches, not where the patch files). What the cap removes is the
conversion tail: bounded post-emesis aerosol reach plus the unchanged
fomite placement structure means the L4 challenge-draw link draws on
acquired mass but converts none (0 observed vs 3 RERANK). The census
still shows the same verdict as RERANK — a subcritical chain whose
surviving acquisitions are unresolved-route one-offs — now with fewer
total acquisitions (7 vs 13).

Measured only; no constants moved.
