# CREW-WINDOW-01 working-crew-channel attenuation — CLIFF-STRUCTURE (no declared arm lands the band)

> **Status:** Findings (2026-10-05). Campaign measured at `ea9550ef`
> (image `picard-campaign@sha256:3ace3f2d` / tag `covid-crew-window-01`,
> jobdef `picard-covid-crew-window-01` revs 1–13, queue
> `picard-analysis-queue`, S3 prefix `campaign/covid_crew_window_01/`).
> First campaign executed on the `campaigns/` + `scripts/campaign`
> harness — spec and readout under `campaigns/covid/crew_window_01/`,
> design `picard_framework/runs/covid_crew_window_01_design.json`
> (frozen pre-run, admissibility carried verbatim from the v11 lineage).

The during-quarantine mass was bracketed by two measured corners —
`D0_declared` (all four crew classes exempt, 678/730) and
`SOP-017-ALLHANDS` (none exempt, 27/105) — against the record-informed
band [150, 350]. This design asked which *sourceable* attenuation of
the working-crew channel lands inside the band with the before-phase
seed-paired unmoved: CREWDUTY (VSP 2018 §4.4.1.1.1 symptomatic-crew
removal, sourced rule), EXEMPT_ENGMED / EXEMPT_ESSENTIAL (the narrow and
medium readings of the record's "essential service"), and MESS_0P5 /
MESS_0P25 (declared far-field attenuation of the pooled mess bath).

240/240 cells, 0 audit-invariant violations, 0 child failures across 12
20-child arrays.

## Result (takeoff-conditional medians, n≈19 takeoff seeds per row)

| θ | arm | during med | before med | Δbefore med / max | crew share | verdict |
|---|---|---:|---:|---:|---:|---|
| 1e6 | D0_declared | 601 | 37.5 | — | 1.000 | BASELINE |
| 1e6 | CREWDUTY | 563 | 38.0 | 0.0 / 8.0 | 1.000 | UNDER-ATTENUATED |
| 1e6 | EXEMPT_ENGMED | 18 | 37.5 | 0.0 / 0.0 | 1.000 | OVER-ATTENUATED |
| 1e6 | EXEMPT_ESSENTIAL | 18 | 37.5 | 0.0 / 0.0 | 1.000 | OVER-ATTENUATED |
| 1e6 | MESS_0P5 | 611 | 36.5 | 0.0 / 271 | 1.000 | UNDER-ATTENUATED |
| 1e6 | MESS_0P25 | 615 | 41.0 | 0.5 / 355 | 1.000 | UNDER-ATTENUATED |
| 7.9e6 | D0_declared | 739 | 126.0 | — | 0.992 | BASELINE |
| 7.9e6 | CREWDUTY | 758 | 130.5 | 0.0 / 126 | 0.991 | UNDER-ATTENUATED |
| 7.9e6 | EXEMPT_ENGMED | 70 | 126.0 | 0.0 / 0.0 | 0.895 | OVER-ATTENUATED |
| 7.9e6 | EXEMPT_ESSENTIAL | 70 | 126.0 | 0.0 / 0.0 | 0.895 | OVER-ATTENUATED |
| 7.9e6 | MESS_0P5 | 729 | 141.5 | −2.5 / 215 | 0.982 | UNDER-ATTENUATED |
| 7.9e6 | MESS_0P25 | 734 | 159.5 | −1.5 / 189 | 0.990 | UNDER-ATTENUATED |

D4 drift witness (D0 rows paired per seed against `6ea3093d`):
median paired delta **+12 @Θ7.9e6** (new 737.5 vs D4 726.5) and
**−56.5 @Θ1e6** (new 594.5 vs D4 674.5) — same direction as the
armed-tree drift the witness exists to catch; small relative to the
measured arm effects (700↔70), so the verdicts stand on the new engine.

## What was measured

- **CREWDUTY is a null lever at sourced strength.** The exclusion
  resolved and realized on every cell (`excluded_hosts` ~660/seed,
  `refused_events` 0, `off_duty_at_end` ~200–275), yet the during median
  moved 739→758 @7.9e6 — statistically identical. Symptom-timed removal
  is too late: crew deliver their during-window dose before the
  symptom-free-hour gate fires (the crew share of the window is ~0.99
  with or without the arm).
- **EXEMPT arms land far *below* the band** — 18 @1e6, 70 @7.9e6 —
  approaching ALLHANDS (27/105). The exempt-set reading that survives
  the record does not exist among discrete class-subsets.
- **ENGMED and ESSENTIAL are bit-identical seed-for-seed** (same 20
  values in the same order at both thetas). `crew_galley`'s exempt
  status never reaches a single draw — either galley crew's during-window
  infections flow through the pooled mess bath rather than their own
  duty presence, or the exempt machinery doesn't gate the galley path.
  (Inferred; a one-line mechanism check can separate the two.)
- **MESS_0P5/0P25 barely move the median** (739→729/734 @7.9e6,
  601→611/615 @1e6). The far-field leg of the mess bath is not the
  binding route — diverting share to `settled` keeps near-field ring
  delivery constant by construction, and that is where the mass lives.
  Per-seed before-window excursions (max |Δ| up to 355) are the
  RNG-reorder the design's diagnostics clause declared expected for
  all-voyage arms; medians sit at ~0.
- **The band sits inside a cliff.** `crew_general` circulation toggles
  the window ~70↔~740 as a near-binary: exempt → ~740, confined → ~70.
  The record-informed band [150,350] has no discrete landing in the
  declared set — only 2/80 EXEMPT cells sit in-band (252; 364 just
  above). An onset-based check (the record counts dated onsets, the
  readout scores infections) does not rescue it: EXEMPT window onsets
  median 112.5, still below 150.

## Follow-up proposal

The discriminating axis is now *fractional* general-crew attenuation —
a graded reading between "general exempt" (739) and "general confined"
(70): general-crew reduced duty, or general-class mess-access
restriction, or partial-compliance on the exempt set. A
`GENERAL_DUTY_FRACTION ∈ {…}` arm interpolates the cliff and would say
whether *any* sourceable reading of "essential service" lands the band.
If even the fractional axis skips the band (a measured cliff, not a
sampling artifact), the suppression is not in this channel at all and
the next suspect is the onset-dating/ascertainment channel again — the
map's D1–D3 legs already name it.
