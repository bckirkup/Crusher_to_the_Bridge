# CG-FLOOR-01
**Date:** 2026-10-04
**Commit:** 3eae8a2f
**Pathogens:** sars_cov2_resp
**Status:** closed

## Question

ANCHOR-DERIVE-01 certified the v11 clause targets mechanism-independent
and named the suspect: CAREGIVER-V1's pre-quarantine delivery
(~5–13 attributed acquisitions/takeoff seed inside days 0–4 vs the
record's 34 dated pre-6-Feb onsets). Is the disjoint leg map reachable
inside the mechanism's declared R2 factor box — i.e., is the failure
factor-driven (a constants question) or structural (a
designation/discovery question)?

## Design

`covid_cg_floor_v1` (declared by `covid_anchor_derivation_v1.md` §5):
{Θ1e6, Θ7.9e6} — the two measured leg crossings — × {`D0_declared`,
`CG_LOW`} × 20 seeds = 80 cells on the verbatim v11-lineage replay
contract. `CG_LOW` pins `tending_copresence_multiplier` [1.5,1.5] and
`tending_hours_per_day` [2.0,2.0] — the bottoms of the declared
intervals (Grade C, no new constants) — while response_probability
U[0.5,0.9], report_probability U[0.3,0.7], designation grammar and
`budget_mode: reallocate` stay shipped. The D0 rows double as the
pairing base and a replication check vs the measured floor (1e6) and
bracket (7.9e6) cells. Frozen grammar: DELIVERY-BOUNDED (legs converge
at the corner) / DELIVERY-STRUCTURAL (legs disjoint at the declared
floor) / SUB-IGNITION. Run at `3eae8a2f`, image
`picard-campaign@sha256:f906128e…` (bracket overlay + design COPY),
jobdef `picard-covid-boarding-screen:55`, 80/80 SUCCEEDED on
`picard-analysis-queue`, 0 audit failures. Readout:
`docs/covid/covid_cg_floor_v1_readout.md`.

## Measured

- D0 rows bit-identical to the floor/bracket cells (20/20 per row,
  max|delta| 0) — engine identity confirmed again.
- Clause fails on all four rows. Seed-paired CG_LOW − D0: **median
  delta 0** on recorded_onsets, before_share and infections_total at
  both thetas (spreads are draw noise, e.g. rec ±[−241,+179] at
  7.9e6). At 7.9e6 the count leg moved a hair *away* (q05 496 → 502);
  at 1e6 the count leg still passes and timing still fails
  (0.051 → 0.053).
- **Caregiver aboard-window tally unmoved**: 105 → 104 (1e6),
  138 → 135 (7.9e6). The corner reached the engine (audit echo) yet
  produced no tally response — the dose factors scale dose per visit,
  and minimum declared tending still delivers threshold dose; the
  tally is produced by the designation/discovery machinery, which the
  corner did not touch.

## Verdict

**DELIVERY-STRUCTURAL** — the failing legs do not converge at the
declared factor floor. The disjointness is not reachable by detuning
the declared dose constants; the defect lives in the mechanism's
designation/discovery shape (`tending_response_probability`,
`tending_report_probability`, the existence of a designation in the
aboard window), or in where the clause is scored. The chain of record
is now: θ-shaped? no (WINDOW-EMPTY-ORDERED) → anchor-shaped? no
(mechanism-independent targets) → factor-shaped? no (this probe) →
**structure-shaped**.

## Follow-up proposed

Structural stage, not factor-sourcing. Candidate bounded reads (each a
session-sized deliverable, user picks): (a) designation-channel probe —
`response_probability` corner or an off arm, isolating whether the
days-0–4 designation itself is the surplus channel; (b)
discovery-channel probe — `report_probability` corner, whether
tended-case reporting is what inflates the dated-onset count; (c)
clause re-scoping — score a caregiver-aware onset definition. None run
here (this stage is the corner probe only).
