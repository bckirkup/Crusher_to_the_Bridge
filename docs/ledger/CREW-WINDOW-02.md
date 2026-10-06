# CREW-WINDOW-02
**Date:** 2026-10-06
**Commit:** 2df542ff
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 2df542ff

Interior of the CW-01 crew-duty cliff: fractional and activity-scoped
crew confinement on the verbatim `diamond_princess_2020` replay (image
`picard-campaign@sha256:2b481866` / tag `covid-crew-window-02`, jobdef
`picard-covid-crew-window-02`, prefix
`campaign/covid_crew_window_02/`). Two new
confinement-order modifiers — `exempt_work_zones` (postable-zone
essential lists NARROW 11/34, WIDE 19/34) and `exempt_fraction`
(sticky exact-count draws, dedicated RNG stream) — on five new
`SOP-017-{NARROW,WIDE,QUARTER,HALF,THREEQ}` variants. Grid
{Θ1e6, Θ7.9e6} × {D0, ZONE_NARROW, ZONE_WIDE, FRAC_25/50/75} × 20 seeds
= 240 cells. Design frozen pre-run; readout
`docs/covid/covid_crew_window_02_readout.md`.

**The band has an interior: FRAC_25 (301) and ZONE_NARROW (334) land
[150,350] at Θ7.9e6 with the before phase seed-paired unmoved —
CHANNEL-LANDED.** Every other arm under-attenuated (ZONE_WIDE 504,
FRAC_50 482, FRAC_75 622.5). During medians are monotone in realized
exempt share at both thetas; a working-crew share of ~0.25–0.31
brackets the band's interior.

Measured, not inferred:

- Crew share of during-window infections moves only marginally on the
  landing arms — 0.973 (FRAC_25) / 0.978 (ZONE_NARROW) vs D0's 0.992,
  still far above the record's 0.29. Confined crew are fed by R3
  steward cabin delivery (128k–166k `service_deliveries`/cell, no
  starvation) and steward/cabin-adjacency routes keep residual
  infections crew-on-crew. The channel lands the mass without
  resolving the attribution — CHANNEL-LANDED on the grammar's letter.
- At Θ1e6, FRAC_25 (195) / FRAC_50 (315) / ZONE_NARROW (238) land the
  band but crew share never leaves 1.000 → IN-BAND-INCOMPLETE: low
  theta's passenger contribution is already negligible, so confining
  crew cannot shift attribution that was never there.
- Realized shares track declarations: FRAC drawn counts exactly
  261/523/784/cell (dedicated RNG stream — before mass Δ0.0 confirms
  no stream reordering); ZONE realized 0.31/0.54 vs posted-conditioned
  lottery 0.32/0.56 (realized denominates all 1,045 crew; ~84% carry
  postings). All working crew inside the essential lists on every ZONE
  cell.
- CW-01 drift witness: in-design D0 pairs seed-for-seed at median
  paired delta **0.0** on both thetas — bit-stable at `2df542ff`.
- Frozen-invariant departure (reported, not amended): D0's
  `realized_exempt_share ≈1` flagged on 4 seeds (0.68–0.87) —
  symptomatic crew confined through the isolation path on big
  before-phase seeds; the D0 gate itself reached (no gate echo).
- Landing magnitudes to source: ~25–31% of crew continuing essential
  work during quarantine — the candidate sourcing legs are the
  record's essential-service complement and the VSP manning fractions;
  no constant moved in this campaign.
