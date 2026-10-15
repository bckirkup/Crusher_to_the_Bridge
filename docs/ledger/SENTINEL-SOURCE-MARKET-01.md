# SENTINEL-SOURCE-MARKET-01
**Date:** 2026-10-15
**Commit:** 3b2a80c6aef0037d56eed71364cce8dcf4fa46eb
**Pathogens:** all
**Status:** declared

Sentinel fleet reverse-inference revision: provisioned-source and
embarkation-market import channels plus voyage susceptibility covariates.

Frozen design: `docs/sentinel/sentinel_source_market_revision.md`.

## Declared

Fleet incidence gains two import channels on top of ashore / aboard / renewal:

- `susc[v] * kappa[s] * prov[v,g,t,s]` — provisioned servings times a
  per-serving hazard pooled per source_id (`log kappa[s] = mu_log_prov +
  sigma_source*z_source[s]`; priors reuse the port-hazard median 1e-4 / sd 2.0,
  sigma_source half-normal(0.75) — all Grade C declared).
- `susc[v] * epsilon[m] * persons_boarded[v,g]` at `embark_epoch` — boarded
  carriers as a per-capita prevalence pooled per embarkation market
  (`epsilon[m] = inv_logit(mu_logit_market + sigma_market*z_market[m])`; prior
  median 2e-3, logit sd 1.5, sigma_market half-normal(0.75) — Grade C).
- `susc[v] = exp(X[v] . beta_x)` — voyage covariates multiply only the three
  import channels, never `lambda_aboard` / `R_onboard`; `beta_x ~
  normal(0, 0.5)`, K=0 reproduces the old model bit-for-bit.

Observation schema additions (`schemas/sentinel_observations.schema.json`):
`provisioning` per source_id (`servings_per_epoch` or
`servings_total`+`service_window_epochs`), `embarkation` (`markets` per
stratum, optional `n_boarded`, `embark_epoch`), `covariates`.

Design-only separability flags in `analysis/sentinel/fleet.py`:
`source_home_confounded` (all consuming voyages share one home port and the
source starts serving inside the embark window) and
`market_home_confounded` (all boarding voyages share one home port whose calls
generate ashore exposure). New posterior quantities: `imported_cases_source`,
`imported_cases_market`, `attribution_share_{source,market}`; `import_share`
and `secondary_cases` net all import channels. New output CSVs
`source_hazards.csv` / `market_hazards.csv` only when the fleet declares the
channels.

## Synthetic recovery measured

This entry records a declared model revision. The one measurement so far is of
the *estimator*, not the world: on the synthetic recovery path (Poisson onsets
simulated from declared κ/ε truth, numpy reference posterior, 400 draws /
1600 warmup), a four-voyage crossover sharing one source and two markets
covers all three declared truths in the 5-95% intervals — κ=2e-3 per serving,
ε={3e-3, 6e-3} per capita. At κ=1e-3 with ~140 pooled onsets the κ interval
ends just below the truth, i.e. sparse fleets leave the prior pulling. Test:
`tests/test_sentinel_fleet_validation.py::
test_pooled_recovery_covers_the_new_import_channels` (slow tier). Nothing here
may be quoted as a measurement of any real source or market.
