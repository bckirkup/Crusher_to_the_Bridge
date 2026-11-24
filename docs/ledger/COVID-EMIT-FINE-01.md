# COVID-EMIT-FINE-01
**Date:** 2026-11-23
**Commit:** 220e6401
**Pathogens:** sars_cov2_resp
**Status:** open

Adoption of the measured airborne fine share as
`airborne_emission_fraction` on `sars_cov2_resp`, the follow-on decision
`COVID-EMIT-LEVEL-01` handed off. Owner-approved (Benjamin, 2026-11-23:
"the fine share should be incorporated and not wasted"). Status is
`open`: the constant and its provenance are landed and the moved test
expectation is attributed, but no voyage has been scored under the new
value — that is the DP-UNION-01 leg
(`docs/proposals/covid_theta_unification_plan.md`), not this one.

## What changed

- `data/pathogens/active_profiles.json`, `sars_cov2_resp`:
  `airborne_emission_fraction` **5e-5 → 0.85**, and
  `airborne_emission_mode: continuous_fraction` declared with it (the
  level-fix note deferred the mode label until the factor was a share).
  No other profile constant moved; `dose_adjustment` is untouched on the
  arms that carry it; the Edison bundle
  (`edison_10pathogen_profiles.json`) keeps its deprecated
  `surface_deposition_fraction` 5e-5.
- **Source:** Coleman 2021 (*Clin Infect Dis*, DOI 10.1093/cid/ciab691),
  85.4% of detected exhaled SARS-CoV-2 RNA in the ≤5 µm fraction.
  Grade B (clinical patients, analogous setting). Origin **R** (Results
  chunk, `docs/literature/consensus_tranche_54_covid_emission_level.md`
  §1; tranche 27 had read 85% from the abstract).
- **Interval:** [0.76, 0.92], Grade B, frozen 2026-09-05 in
  `docs/literature/consensus_tranche_27_airborne_fraction_and_drying_axis.md`
  §2/§6 — floor Yan 2018 (influenza), ceiling Chow 2023 (influenza,
  implied by fine ≈ 12× coarse). 0.85 is this virus's own published
  point inside it. **Declared, not fitted:** chosen against no anchor
  (not `covid.T3`, H5, GM, VSP, Park or any attack rate). The span is the
  declared sweep axis.
- **License check (tree-verified, not re-derived):** tranche 27 §6 made
  adoption conditional on the arm's level being a measured exhaled rate;
  `COVID-EMIT-LEVEL-01` (`7b7f0ea0`) landed that level
  (`environmental_release_log10_per_day` 1.93), so numerator and
  denominator are now both exhaled RNA copies and the factor is
  dimensionless.

## Before / after (derived from the profile, not simulated)

| | 5e-5 | 0.85 |
|---|---|---|
| Peak zone-air deposit per shedder-epoch (4.9e5 copies/h × fraction) | 24.5 copies | 4.16e5 copies |
| Against the measured bracket [4.2e3, 5.8e7] copies/epoch | ~170× under the floor | inside |

Ratio 0.85 / 5e-5 = **1.7e4**. The 8-run in-sim diagnostic of
`COVID-EMIT-LEVEL-01` was not re-run under 0.85; in-sim deposit, route
shares and every epidemic outcome under the new value are **unmeasured**.

## Scope of the move — correction to the record

The hand-off text (covid open ledger §3; the unification plan) said the
adoption "moves every droplet/direct/airborne deposit ×1.7e4". The tree
does not support that. Read from code at `220e6401`:

- `airborne_emission_fraction` is read at one site,
  `orchestrator_epoch._airborne_emission_fraction` →
  `_accumulate_pathogen_zone_mass`: the per-pathogen **zone airborne
  pool** deposit `sv × fraction × confinement factor`. That pool, and
  everything it feeds (room-air inhalation, pathogen pool transport), is
  what rises ×1.7e4.
- The droplet / near-field route uses the uniform engine constant
  `DROPLET_AEROSOL_FRACTION = 0.05`
  (`TransmissionCore._droplet_emission_fraction`), which explicitly does
  not read the profile's share — a separate open item, unchanged here.
- Direct contact and fomite paths do not read it.

**Inferred (not measured):** the route mix shifts toward the room-pool
airborne route; the size of the shift depends on how much dose that
route carried at 5e-5, which this entry did not measure.

## Θ units — label, do not delete

Θ scales host susceptibility and therefore multiplies dose on every
route, while this change multiplies emission on one route. **Every Θ
measured before this change is in the old units and is not convertible
to the new ones by a single factor** (dividing by 1.7e4 would be right
only if the airborne pool were the sole route). The affected entries
keep their numbers and their own `Measured at` SHAs as the record of
what ran; they are labelled old-unit here and in
`docs/covid/covid_open_ledger.md` §1: `COVID-THETA-REFIT-01` (3.162e11),
`DP-THETA-FIT-01` (3.16e9 selected, 4.22e9 interpolated),
`DP-THETA-PILOT-01`, `COVID-H5-RESCORE-01`, `COVID-ONSET-FUNNEL-01`,
`COVID-GM-RESCORE-01/02`, `LAMBDA-CROSS-V1`, `THETA-REFIT-01`,
`COVID-THETA-V14/V15`, `THETA-V7-01`, `THETA-SCREEN-V8`–`V13`, and every
DP/GM replay run at those operating points. Committed campaign designs
that pin a Θ keep it as the record of what ran; a new cell launched from
one of them on a tree containing this change runs old-unit Θ against
new-unit emission and is not comparable to its own archive.

## Moved test expectation, attributed

Fast tier (`pytest tests/ -m 'not slow'`) on the changed tree: 9280
passed, 2 failed.

- `tests/test_multi_pathogen_model_phase_a.py::test_covid_continuous_airborne_scope_guard[active_profiles.json]`
  — asserted `== 5e-5` and no `airborne_emission_mode`. Attributed by
  reverting each key alone: value reverted → fails only on the mode
  assertion; mode reverted → fails only on `0.85 == 5e-5`; both reverted
  → passes. Updated to the new value and mode, plus the frozen-interval
  bound; the Edison-bundle half is kept unchanged as its own test.
- `tests/test_sentinel_wastewater.py::test_stan_and_numpy_agree_on_the_wastewater_channel`
  — local CmdStan compile failure of `sentinel_fleet.stan`; fails
  identically on unmodified `220e6401`. Not caused by this change.

No other test or golden moved. After the test update: 9281 passed,
1 failed (the Stan compile above).

## Not done here

No Θ refit, no campaign cells, GM untouched. The droplet route's own
share stays the uniform 0.05. `docs/parameter_provenance_register.md`
§3.2 row is updated; its summary count table was not recounted.
