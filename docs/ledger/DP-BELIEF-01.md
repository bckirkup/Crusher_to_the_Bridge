# DP-BELIEF-01
**Date:** 2026-10-04
**Commit:** f31de83a
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 78f52a58

## Question

THETA-REFIT-01 certified the v11 clause passes nowhere on [1e6, 1e9]
under shipped defaults, and CG-FLOOR-01 narrowed the carrier to the
designation/discovery shape. Beyond the clause's two legs: which
checkable features of the Diamond Princess record does the
shipped-default replay satisfy, and which does it fail — is the
believability gap one mechanism's signature or several?

## Declaration

Divergence table only, no new cells: score every record feature the
synced payloads of record can express (420 cells at `78f52a58`,
`8f49652f`, `8f926382`, `3eae8a2f`, `b932d0e9` across the refit
lattice, floor, bracket, corner probe and attribution rows; seeds
20200205–20200224, takeoff-conditional at ≥10 recorded onsets) against
the record values in `data/observation/covid_fit_targets.json` and the
NIID field briefing; for any feature the payloads cannot express,
declare the minimal new readout leg and mark it 'needs cells'.
Deliverable: `docs/covid/covid_believability_map_v1.md`.

## Measured

**BELIEVABILITY-DIVERGENT — three orthogonal divergences, none
θ-shaped.**

1. **Mass is reachable.** `infections_total` sits inside the
   serology-informed band [712,960] at both clause-leg crossings —
   med 771 at Θ1e6, 938 at Θ7.9e6. "Too much virus" is falsified as the
   sole residual: at the timing-leg θ, infections ≈ record, lab-confirmed
   ≈ record ×1.2 (789 vs 619–634), and dated onsets ≈ record ×3.2 (634
   vs 197).
2. **Timing is inverted.** The share of infections acquired before day
   16 is 0.08–0.25 across 1e6–7.9e6 vs the record's majority
   (back-calculated: incidence declining by ~3–4 Feb): dated-onset peak
   med day 21–27 vs ~day 18; during-quarantine dated onsets are ~95%
   crew vs the record's 29% (med 302–566 crew vs 48, and 6–79 passenger
   vs 115 — a 4–19× under-production at clause θ); confined-passenger
   during-quarantine acquisitions med 4–19 vs the ≥52 record-informed
   bound; 130–292 dated onsets land after the record's curve ended.
   θ trades mass for timing — the pre-quarantine share reaches ~0.75
   only at Θ≥1e8 where totals are ~3× over.
3. **Dating is overshared ~3×, flat.** `recorded_onsets/lab_confirmed`
   = 0.79–0.87 on every measured row — invariant to θ, seeds, and the
   caregiver mechanism (0.82 on the clause-passing CG_OFF surface) — vs
   the record's 197/712 ≈ 0.277. The observation channel admits ~4 of 5
   confirmed cases to the dated curve; the record admitted ~1 in 4.

The clause-passing surface is itself unbelievable: CG_OFF (band ∋197,
share 0.200) carries 2,342 infections — 2.8× the serology band. Clause
satisfaction and believability are different objects.

Secondary divergences: campaign positives want θ ~3e6–3e7 (a third
disjoint region; T3 634 vs 213–434 at clause θ); asymptomatic share at
specimen crosses 0.505 near ~1–5e7; takeoff is 19/20 at every row
(conditioning binds nothing on the shipped tree). Expressible proxies
say during-quarantine acquisition is carried by crew venues (crew_mess
share 0.48–0.58 at clause θ) rather than the record's cabin signature.

**Needs cells (designed, not run):** D1 route-tagged dated onsets
(witness named by CG-FLOOR-01 §5); D2 cabin-cluster tallies
(with/without-prior-confirmed-case dated onsets + cabinmate-conditioned
attack rate — the 18/63/81% CID gradient); D3 readout-only scoring of
the acquisition-date histogram vs the back-calculated infection curve;
D4 quarantine-phase suppression arm at Θ7.9e6 to split "open-phase
under-delivery" from "confinement-channel over-delivery" (the
QUAR-ATTR-V2 grammar already exists). D1+D4 is the discriminating pair:
route-tag the dated curve and suppress the quarantine channel — the
residual then reads as pure timing.

Chain of record: θ-shaped? no → anchor-shaped? no → factor-shaped? no →
structure-shaped (CG-FLOOR-01) → **decomposed here as phase-inverted
delivery + flat observation-channel overshare.** The caregiver
designation is a contributor to the pre-quarantine term (5–13 attributed
acquisitions/takeoff seed inside days 0–4, settled), not the whole of
the divergence. No constants changed; no cells ran.
