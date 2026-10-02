# FLU-PRESENT-RESCORE-01
**Date:** 2026-10-02
**Commit:** 6efec85504237f7cd818b3102e24e4a6d25157bc
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 232292f238ce27140c5d1a60c6a5e717b059c46d

Post-PRESENT-SHARE-01 rescore of the influenza arm's scored surface: a
`presentation_draw_mode` paired A/B on the conditioned cabin-floor cells
(`tools/cabin_floor_probe.py:conditioned_spec` — isolated flu arm,
2-passenger index at epoch 0, declared SOP-017 confinement day 1→end) on
`classic_cruise_1900`, 288 epochs, seeds 8105–8108, both modes. Driver
`tools/flu_present_ab_driver.py`, scorer
`tools/flu_present_ab_score.py`, folded summary
`telemetry_buffer/flu_present_ab/scored_summary.json`. No engine diff
exists between the measured SHA and the commit above (intervening merges
are covid/noro design and readout files).

## Measured

- Confined cabinmate SAR identical across modes on every seed — pooled
  2/31 = 6.5%, Wilson [1.8%, 20.7%]. Cell outputs are bit-identical
  (recursive JSON diff: only run_id/wall_clock differ across the 384 KB
  timeseries payloads).
- CABIN-FLOOR-03 band on pooled `delivered_p_dose`: [4.9%, 12.2%],
  E[SAR] @ k_ship (6e-4) = 9.7%. Wilson CI overlaps the band; F1 (Lau
  2012 PCR SIR spread [0.03, 0.38]) verdict **IN** — consistent with
  FLU-RHYTHM-01 (classic on-arm 64/853 = 7.5% at `1ab8dd98`; 6.5% at
  n=4 seeds sits inside that census's noise).
- Delivered dose unchanged across modes: p50 1.20 copies, 31/31 confined
  slots dosed.
- Observation surface (new measurement — no prior baseline recorded):
  ever_ill/ever_infected passengers 14/45 = 0.31;
  reported/infected 8/45 = 0.18 vs the F5 internal check ≈0.08.

## Mechanism (measured)

The flag is inert on this surface because the conditioned cell's
infections are import-dominated. A will_present census on s8105 found
{forced-true: 11, forced-false: 7, free: 2} of 20 infected hosts, and a
call-site spy on `draw_symptom_onset` recorded draw invocations
{forced_true: 6, forced_false: 27, free: 2}: forced courses short-circuit
and consume no stream in either mode (per PRESENT-SHARE-01). The two
free-drawing courses presented on their first draw, so the streams never
diverged — a failed first draw would have split them (once_per_course
stamps and stops; daily_hazard keeps rolling), but on this sample no
course ever exercised the mode difference.

The only channel from presentation back into delivered dose —
`asymptomatic_shedding_log10` selected via `ever_presented` in
`_shedding_curve_point` — can act only on never-presenting
onboard-acquired shedders. None existed among these cells' emitters, and
the F1 endpoint is mate *infection*, not mate presentation.

## Inferred

- The scored flu surface (F1 + CABIN-FLOOR-03) is insensitive to the
  presentation-draw change by construction: index courses carry the
  import stamp and the endpoint is dose-delivered to the mate. A
  full-manifest re-census (flu_rhythm_02 manifest, 800 cells) is
  expected to reproduce the FLU-RHYTHM-01 verdict within noise; this
  rescore is evidence it is not required for the scored anchors.
- Voyage-level surfaces the anchors do not score — onboard-acquired
  incidence, silent-course counts, ascertainment — can still move under
  once_per_course (never-presenting courses shed on the asymptomatic
  curve, ~40× lower peak for flu). The 0.31 ever_ill share here is
  dominated by import stamps and onset timing (late acquisitions never
  reach their drawn onset in 288 epochs), not by the flag.

## Hypothesis

- reported/infected = 0.18 exceeding the F5 ≈0.08 internal check most
  likely reflects the conditioned surface (confined index pair,
  monitored mates, n=45) rather than an observation-model defect; flag
  for recheck on any future open-voyage census.
