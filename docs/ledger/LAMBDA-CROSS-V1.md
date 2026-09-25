# LAMBDA-CROSS-V1
**Date:** 2026-09-25
**Commit:** eddbf9b
**Pathogens:** sars_cov2_resp
**Status:** declared

Hazard-rate crossing assay on the AERO-SPLIT-01 droplet-partition
architecture, opened by three measured negatives and one instrument
readout. Declared in
`picard_framework/runs/covid_lambda_cross_v1_design.json` (frozen before
any assay cell ran). Nothing in this entry is a result; it moves to
measured when the canary is read out.

## Declared (before any cell runs)

The engine's hazard is single-hit Poisson — per challenged host-epoch,
`p = 1 − exp(−susceptibility × effective_dose)`. Reach (PARTNER-RATE-V1),
per-partner dose (PLUME-DOSE-V1), and every per-activity ring knockout
all measured flat while ~95% of conditional mass lands pre-quarantine;
ROUTE-ATTR-V1 measured the droplet dose to infected hosts as ~98%
ring-side but per-agent bimodal — both channels exceed the infection
threshold for nearly every host. That is the signature of per-epoch
λ ≫ 1: p_epoch ≈ 1 regardless of how a transmission knob is turned.

This assay sweeps the mean-λ scale itself: Θ multipliers
{1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001} on the declared 4.22e10
(`theta_profile_overrides` sets `susceptibility_scale = θ(α+β)/α`, so
Θ is exactly the mean-hazard axis — no arm grammar needed), same 20
seeds, same declared replay — 140 cells. Declared reads: per-Θ
conditional recorded mass vs 197, the crossing Θ whose takeoff-seed
band contains 197 (if any), the collapse point, elasticity on the
log-log slope vs the dose axis's measured 0.004, and `before_share`
vs Θ (does the burn re-centre toward quarantine or persist until
takeoff dies).

Companion instrumentation: `tools/covid_route_attribution.py` now
wraps `_dose_response_hazard` and reports the per-challenge λ
distribution (all challenged host-epochs and infecting challenges)
locally on the declared row — the quantity whose position vs 1 the
flat assays predicted.

Canary = Θ ×0.001 (cells 120–139, INDEX_OFFSET 120), then STOP and
report; the user decides the array. Payload contract unchanged.
