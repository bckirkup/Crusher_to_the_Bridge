# ANCHOR-DERIVE-01
**Date:** 2026-10-04
**Commit:** 04d6ef18
**Pathogens:** sars_cov2_resp
**Status:** closed

## Question

THETA-REFIT-01 certified the v11-lineage replay clause unreachable on all
of [1e6, 1e9] under shipped defaults — the count leg's and timing leg's
admissible half-planes are disjoint (θ_c ∈ (1e6, 1.4e6) < θ_t ∈ (5.62e6,
7.9e6), WINDOW-EMPTY-ORDERED). Before naming the residual
mechanism-shaped, re-derive the clause's targets under CAREGIVER-V1: do
the 197 count and the 0.173 before-split share implicitly assume a
transmission structure the mechanism changes, or are they
measured-direct record observations any correct model must reproduce?

## Derivation

Traced and argued in
`docs/covid/covid_anchor_derivation_v1.md`. Both targets are cuts of one
histogram — the dated-onset subset of confirmed cases on the published
MHLW/NIID epidemic curve (200223_epi_curveENG; NIID field briefing
19 Feb 2020; `covid.T1`, grade A, denominator = recorded-onset subset
per fit spec §8). 197 = total dated onsets; 0.173 = 34/197 dated before
day 17 = 6 Feb 2020, the first full day under the 5 Feb
cabin-quarantine order (SOP-017, record calendar provenance grade A).

Neither figure encodes a transmission structure: the record already
contains whatever caregiver-mediated transmission actually occurred
aboard, and the model-side channel is commensurate by construction —
`_onset_observation` dates every lab-confirmed, syndrome-eligible
presenting onset, exactly the record's "confirmed case with a recorded
onset". CAREGIVER-V1's R2 tending exposure and its attendant-channel
discovery stamp (`caregiver_report_due_epoch` → sick-call roster)
feed *into* that same channel — a path the real ship also had — so the
mechanism changes the model's prediction, never the target. The
remaining clause elements (q05–q95 band, ±0.10 tolerance, `>=10`
takeoff gate, >=5-seed floor) are scorer conventions frozen in the
design files, not record quantities; the takeoff conditioning is
already met at 19/20 on every measured row, so re-deriving the gate
cannot move the verdict. The measured surface is on/off-aligned with
the mechanism: `caregiver.mode: off` clause-passes (CAREGIVER-ATTR-01,
`b932d0e9`); all 15 shipped-default rows fail >= 1 leg.

## Verdict

**(b) — certificate of mechanism-independence.** The clause
legitimately fails under shipped defaults; the suspect moves to the
mechanism's pre-quarantine delivery strength. Witness: pooled
`aboard_window` caregiver acquisitions run 105–248 monotone in Θ across
all measured rows — the index's days-0–4 window — with
`during_quarantine` caregiver = 0 everywhere (structural: confined
responders cannot be drawn). ~5–13 caregiver-attributed acquisitions
per takeoff seed inside five days against a record whose entire
pre-6-Feb dated mass is 34 onsets.

## Follow-up proposed

CG-FLOOR-01 — bounded seed-paired probe at the two leg-crossing rows
(Θ1e6, Θ7.9e6) at the frozen R2 factor box's low corner
(`tending_copresence_multiplier` 1.5, `tending_hours` 2.0 — inside the
declared intervals, no new constants), reading leg elasticity plus a
new caregiver-route share-of-dated-onsets witness. Verdict grammar
frozen: DELIVERY-BOUNDED / DELIVERY-STRUCTURAL. Proposed in the
derivation doc §5; not run (out of scope for a derivation stage).
