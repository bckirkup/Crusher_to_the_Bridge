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
D4 quarantine-phase suppression arm at the clause thetas to split
"open-phase under-delivery" from "confinement-channel over-delivery"
(the QUAR-ATTR-V2 grammar already exists). D1+D4 is the discriminating
pair: route-tag the dated curve and suppress the quarantine channel —
the residual then reads as pure timing. **D4 measured 2026-10-04 —
CONFINEMENT-CHANNEL: the tail is ~92–96% the crew exemption; see the
addendum and `docs/covid/covid_quar_suppression_v1_readout.md`.**

Chain of record: θ-shaped? no → anchor-shaped? no → factor-shaped? no →
structure-shaped (CG-FLOOR-01) → **decomposed here as phase-inverted
delivery + flat observation-channel overshare.** The caregiver
designation is a contributor to the pre-quarantine term (5–13 attributed
acquisitions/takeoff seed inside days 0–4, settled), not the whole of
the divergence. No constants changed; no cells ran.

## Addendum — D3 measured (2026-10-04)

Scored the acquisition-date distribution (map §4-D3): the phase fix is
**not a global shift**. At the timing-leg Θ7.9e6 the event curve already
carries the record's *shape* (peaks ~day 15, declines during quarantine)
but splits mass ~25/75 instead of ~65/35 — because days 0–8 are nearly
empty (event share <day 9 = 0.011–0.019 at θ≤7.9e6 vs 0.10+ at ≥1e8)
while the day-16+ tail is fat. At Θ1e6 the curve is fully inverted
(peaks day 21, still rising through the boundary). θ stretches the same
wrong-phase curve monotonically (0.08→0.90 certified <d16) — the
residual is shape-structured, not amplitude-structured. Conforming needs
both halves: front-load days ~5–12 (open-phase under-delivery; the
window the caregiver/co-presence channels own — CG_OFF at 1e9 removes
the early hump, <d16 share 0.902→0.579, shape-level confirmation that
the designation is an early-window deliverer) AND harder quarantine
suppression (the tail; D4's measurement). Day-5–6 event dip at low θ
flagged as a scheduled-structure artifact to verify under the D4 arm.
Cells of record only; no new runs.

## Addendum — D4 measured (2026-10-04)

The quarantine-phase suppression arm ran as one bounded campaign —
`docs/covid/covid_quar_suppression_v1_readout.md`:
`picard_framework/runs/covid_quar_suppression_v1_design.json`, {Θ1e6,
Θ7.9e6} × {`D0_declared`, `SOP017_ALLHANDS`} × 20 seeds = 80 cells
(design-commit `6ea3093d`, digest-pinned image
`sha256:2c279aa2…`, jobdef `picard-covid-boarding-screen-fargate:2`
on `picard-analysis-fargate-queue` after an EC2 capacity drought;
canary 20 cells reported before the remaining 60 ran). 80/80 cells,
0 audit failures — the `scheduled_protocol_id` swap reaches the engine
on every arm cell (`quarantine_witness` echoes `SOP-017-ALLHANDS`,
`exempt_classes []`, window [16,30], activated).

**Verdict (frozen grammar): CONFINEMENT-CHANNEL over-delivery — and
stronger than the grammar pre-wrote.** At Θ1e6 the during-window mass
collapses med 678 [480,821] → 27 [5,154]; at Θ7.9e6 med 730 [398,813]
→ 105 [36,225] — seed-paired Δduring −602/−624 while
`infections_before_quarantine` is **bit-identical** (Δ 0 [0,0], pooled
day-curve identical through day 15 on both rows). The collapse
overshoots the record-informed band's low edge (150) at both thetas:
the fat day-16+ tail is ~92–96% *carried by* the crew exemption, not
merely inflated by it. Δduring-crew ≈ Δduring (−604/−623) — the crew
channel is the whole delta. The residual under all-hands confinement
is a confined-cabin channel (1,072/1,074 and 2,466/2,483 pooled events
in cabins; crew_mess/galley/corridor ~0), still crew-majority
(52%/61% vs the record's 29% dated-crew share) because crew share
cabins with crew; `confined_passenger_infections_during_window` is
unmoved (med 4→2 and 19→18) — the arm does not touch the passenger
cabin channel the record needs. D0 drift witness: 20/20 per row
bit-identical modulo bookkeeping plus one additive zero-count
`common_source_food` route key the f31de83a-generation image emits
(covid food disabled) — max|delta| 0 on every numeric leaf. D3's
flagged day-5–6 dip is arm-independent (identical pooled counts under
both arms at both thetas) — an open-phase contact-calendar artifact,
not a quarantine interaction.
