# CREW-WINDOW-01
**Date:** 2026-10-05
**Commit:** ea9550ef
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** ea9550ef

First campaign executed through the `campaigns/` + `scripts/campaign`
harness (migrated off the frozen legacy boarding-screen layout; spec at
`campaigns/covid/crew_window_01/`, image `covid-crew-window-01`, jobdef
`picard-covid-crew-window-01` revs 1–13, prefix
`campaign/covid_crew_window_01/`). 240/240 cells, 0 audit-invariant
violations, 0 child failures. Design frozen pre-run at
`picard_framework/runs/covid_crew_window_01_design.json`; readout at
`docs/covid/covid_crew_window_01_readout.md`.

**No declared attenuation of the working-crew channel lands the
record-informed band [150, 350].** Takeoff-conditional during-window
medians (20 seeds):

| θ | CREWDUTY | EXEMPT_ENGMED | EXEMPT_ESSENTIAL | MESS_0P5 | MESS_0P25 | D0 |
|---|---:|---:|---:|---:|---:|---:|
| 1e6 | 563 | 18 | 18 | 611 | 615 | 601 |
| 7.9e6 | 758 | 70 | 70 | 729 | 734 | 739 |

Measured, not inferred:

- CREWDUTY (VSP 2018 §4.4.1.1.1 symptomatic-crew removal, sourced rule)
  fires on every cell (~660 excluded hosts/seed, 0 refused) and does not
  move the window — symptom-timed removal is too late because ~99% of
  during-window infections are crew and the dose is delivered
  pre-symptomatic.
- The exempt-set axis is a cliff carried by `crew_general` alone:
  exempt → ~740, confined → ~70 (near the ALLHANDS bound 27/105).
  EXEMPT_ENGMED and EXEMPT_ESSENTIAL are bit-identical seed-for-seed —
  `crew_galley`'s exempt status never reaches a draw. *Resolved
  2026-10-05:* it cannot reach one — the `diamond_princess_2020`
  replay instantiates only `passenger_general` + `crew_general`
  (`data/scenarios/covid_hull_scenarios.json` `role_classes`); the
  other three named classes carry no agents on this hull, so both
  arms confine the entire crew identically (ALLHANDS-equivalent) and
  SOP-017's four-class exemption exempts exactly one real class.
  The "cliff" is the hull's class vocabulary, not an attenuation
  function; the `exempt_classes` audit invariant checked the
  declared set, not realised membership.
- MESS far-field attenuation is a non-lever (729–734 vs 739 @7.9e6);
  near-field ring delivery holds the mass by construction.
- Onset-based re-read (record counts dated onsets, readout scores
  infections) does not change the verdict: EXEMPT window onsets median
  112.5 @7.9e6, still below 150.
- Before-window seed-paired unmoved at the median on every crew arm;
  MESS all-voyage arms show the declared RNG-reorder excursions.
- D4 drift witness: +12 @7.9e6, −56 @1e6 paired vs `6ea3093d` — inside
  armed-tree noise; does not bear on the 70↔739 scale.

**Verdict: CLIFF-STRUCTURE — the during-window band sits inside a binary
`crew_general` switch; no discrete sourceable attenuation lands.** The
follow-up axis is fractional general-crew attenuation (reduced-duty or
mess-access arms interpolating 70↔739); if that axis also skips the
band, suppression is not in the working-crew channel and the next
suspect is the onset-dating/ascertainment channel (the map's D1–D3
legs). Declared before running; nothing retuned. *Post-landing
refinement:* on this hull the record's "essential service" is
activity-scoped, not class-scoped — meal delivery, medical and watches
continued while cabin service stopped, all inside the single
`crew_general` class — so the follow-up should prefer an
exempt-by-duty-activity arm over a bare headcount fraction.
