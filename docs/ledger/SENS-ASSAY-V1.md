# SENS-ASSAY-V1
**Date:** 2026-09-23
**Commit:** 9ba9d5e
**Pathogens:** sars_cov2_resp
**Status:** declared

Paired-seed sensitivity assay on the declared Diamond Princess replay at
the v11 admissible-band centre, Θ 4.22e10 — one suppression channel
removed or strengthened per arm, scored against the stage-2 gap.
Declared in
`picard_framework/runs/covid_sensitivity_assay_v1_design.json`
(frozen before any assay cell ran). Nothing in this entry is a result;
it moves to measured when the canary is read out.

## Declared (before any cell runs)

THETA-SCREEN-V11-S2 measured takeoff seeds recording a median
~3,470–3,520 onsets against the record's 197 (~17.7×) with attack ~0.95
against ~712/3,711 — and showed Θ moves that conditional mass by ~1%
inside the band, so the assay holds Θ fixed and interrogates the
suppression machinery instead. The declared decomposition of the 17.7×:
~4.7× biological over-burn compounded with ~3.5× observational
bookkeeping (197 dated onsets are ~28–31% of the record's 634 confirmed
positives while the model's recorded channel reports every
specimen-confirmed symptomatic onset).

Twelve arms × 20 matched seeds (base 20200205) at Θ 4.22e10, 240 cells:

- A0 declared replay — execution witness; must reproduce the stage-2
  Θ 4.22e10 row's statistics.
- A1–A5, the QUAR-ATTR-V1 arm set verbatim (crew confined, pool
  transport off, near-field off, crew+pool, all shared air off),
  re-measured at band Θ.
- A6/A7, contact-route dose at ×0.5 / ×0.25 — a dose-side probe of how
  much conditional mass rides the contact channel.
- A8, the confinement order retimed to day 12 (1 February — the day the
  index's Hong Kong result was public; counterfactual, historically
  false).
- A9, confinement_isolation_factor 0.05 → 0.0 — the bound on what a
  stronger cabin lockdown could have done.
- A10, the symptomatic-confinement counter threshold 0.03 → ~1/2666 —
  confinement from the first reported sick call.
- A11, the combined arrest bound (A4 + contact ×0.25 + day-12 +
  perfect confinement): whether any combination of the assayed levers
  reaches the record at all.

Frozen verdict bands: closes_the_gap / load_bearing (≥50% cut) /
partial (20–50%) / inert (<20%) / takeoff_collapse — see the design's
`scoring` block for the verbatim clause. New arm grammar wired in the
same change: `scheduled_protocol_window`, `infection_counters`,
`transmission_overrides`, plus `transmission.*` cfg precedence over
platform values for `confinement_isolation_factor` /
`corridor_direct_contact_factor`.

## Report immediately if

- any arm's conditional q05–q95 contains 197;
- any arm collapses takeoff below 5/20;
- A11 still over-produces by ~4× or more — meaning the transmission
  layer cannot account for the gap and the deficit lives in the
  observational channel or natural history;
- the A0 witness row fails to reproduce the stage-2 Θ 4.22e10 row.
