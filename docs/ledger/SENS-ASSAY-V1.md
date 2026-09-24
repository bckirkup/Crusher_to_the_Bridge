# SENS-ASSAY-V1
**Date:** 2026-09-23
**Commit:** b88e0ad
**Pathogens:** sars_cov2_resp
**Status:** measured

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

## Measured (240/240 cells, `b88e0ad`)

All 240 cells SUCCEEDED. On the frozen paired-seed metric every arm is
**inert** (<20% conditional-median movement) except
`A5_all_shared_air_off`, which is **takeoff_collapse** (3/20 takeoff —
the suppression bound kills the outbreak rather than resizing it). No
arm's q05–q95 contains 197; near-target share 0.00 everywhere. Largest
mover: A11 arrest bound −17.4% → conditional median 2,868 vs the
record's 197 (~14.6× over) — the declared trigger fired: the ~18× gap
is unreachable inside the transmission layer.

Decomposition: A0 records ~89% of its mass before the day-17 split
(median 3,509 before vs 53 during); the burn is ~96% complete when
SOP-017 binds, so no confinement timing/strength lever can move totals.
A11 stretches the burn into the window (594 during — all cabin droplet,
the unconfineable cabin-mate addback channel). A5's surviving
contact-only outbreaks carry ~296 infections — record-order size but
epidemiologically dead; shared-air terms are the load-bearing carrier
of the over-production.

A10 first-report confinement was vacuous, not defective: bit-identical
to A0 on all 19 paired seeds because the dense VSP report stream trips
0.03 and 0.0004 on the same schedule — an instrumented probe at seed
20200205 shows the two arms' quarantined counts identical at every one
of 288 epochs (first confinement epoch 44, ~day 1.8, for both: the
first sick-call batch already crosses the 3% passenger threshold) and
3,271 ever-reported passengers / 3,250 quarantined (~87% of the ship)
by day 12, before SOP-017 activates. The
model's reactive confinement is near-saturating early and the residual
burn rides channels confinement cannot reach (cabin-mate addback,
shared-corridor air, presymptomatic shedding).

The gap's measured locus: the observational channel (~3.5×) and natural
history/mixing (~4.7×) — both assayed by `covid_sensitivity_assay_v2`
(declared, SENS-ASSAY-V2). Readout
`docs/covid/covid_sensitivity_assay_v1_readout.md`; surface
`docs/covid/covid_sensitivity_assay_v1_surface.csv`; cells
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_sensitivity_assay_v1/b88e0ad/cells/`.
