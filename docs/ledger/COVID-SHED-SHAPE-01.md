# COVID-SHED-SHAPE-01
**Date:** 2026-11-26
**Commit:** 46160495
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 75ef817a

Implementation of the Zhou direct emitted-material source term selected after
[COVID-SHED-SHAPELIB-01](COVID-SHED-SHAPELIB-01.md). This change is literature
input implementation only: **no Diamond Princess, attack-rate, onset, testing,
Greg Mortimer, Willebrand, or H5 anchor was fitted or consulted to choose a
value.** GM remains held out; H5 remains held out forever. No campaign was run.

## What changed

1. `sars_cov2_resp` now carries `emission_shape`, a zero-inflated onset-aligned
   daily exhaled-mask RNA shape from Zhou et al. 2023 as digitized in
   `docs/covid/covid_shed_shape_library_01.json`.
2. `engines/infection_dynamics_bridge.py` consumes that shape ahead of the
   legacy nasal-indexed shedding curve. Negative onset-relative days inside the
   profile's presymptomatic gate are no longer clamped to curve entry zero for
   this representation. Daily occurrence is reproducible within an infection:
   one per-infection shape-seeded occurrence sequence decides whether each day
   emits; a positive day emits the row's conditional-positive relative mass.
   The per-infection occurrence seed is derived from the same random scalar
   already consumed for the persistent shedding multiplier, so the replacement
   does not insert an extra simulation-RNG draw at infection initialization.
3. The active arm now carries `shedding_multiplier_mixture`: high-emitter
   fraction **2/18 = 0.111111** and high/low ratio **49.142857**, the
   per-capita ratio that reproduces Zhou's three-timepoint 86%/14% emitted-RNA
   mass split. The engine normalizes the two persistent class multipliers to
   population mean one. `shedding_variance_log10: 1.2` is removed from the
   active COVID profile rather than left as a parallel heterogeneity
   representation. The Edison multi-pathogen library deliberately retains its
   frozen reference arm; mirroring there is a separate owner decision because
   that bundle scopes mixed-pathogen campaign work.
4. `emission_shape.peak_positive_log10_copies_per_day` is **7.0755**
   (**1.19e7 RNA copies/day**, 4.9e5/hour), the same independently declared
   measured exhaled-emission central level previously carried by
   `environmental_release_log10_per_day`. The old curve-normalizer key is
   removed from the COVID arm because a direct amplitude beside the shape would
   be a second scale on one quantity. Θ overrides now normalize this amplitude
   to zero log10 and put the whole scale back into the susceptibility-side
   composite.
5. No new incubation constant or distribution is adopted. The active COVID
   arm already carries the sourced ancestral lognormal incubation block. The
   remaining Edison-library fixed-onset divergence is deliberate scope, not a
   correction made here, because that bundle is shared by parallel
   mixed-pathogen campaign work.

## Evidence separation

**Measured:** Zhou's plotted mask-sample positivity and log10 E-gene RNA
magnitudes; exact digitization recovery of 109 positive mask samples; the
reported severe emission overdispersion in which two participants produced 86%
of airborne viral RNA on three timepoints; the emitted-material bracket behind
the 10^7.0755 central level; the incubation median/dispersion evidence already
recorded on the active arm.

**Inferred:** digitized numeric heights; onset alignment within approximately
±1 day; conversion of `mean_log10_positive` to linear relative positive mass;
and normalization of the high/low mixture to population mean one.

**Hypothesis / declared transfer:** treating emitted mask RNA as the upstream
source shape for viable-virus-weighted transmission; treating the
three-timepoint 86%/14% split as a persistent whole-course two-class host
mixture; treating asymptomatic hosts as following the same virtual-onset shape;
using geometric conditional-positive magnitudes as per-positive-host emission;
and transferring all of the above from a human-challenge setting to shipboard
transmission.

## Consequences and limitations

- Every COVID Θ, route-share, founder-yield, onset-control, attack-mass and
  observation-history measurement made under the smooth nasal-indexed curve is
  historical on the emission-shape channel. No numeric conversion factor is
  claimed.
- The legacy `shedding_curve_log10` and `asymptomatic_shedding_log10` arrays
  remain in the profile for non-shape consumers and provenance/history, but the
  respiratory emission path now reads `emission_shape`. They no longer define
  the respiratory emission time course.
- The implementation follows the shape library's zero-inflated contract:
  `detection_probability` controls occurrence and
  `10**mean_log10_positive`, normalized to its maximum, controls conditional
  positive relative magnitude. It deliberately does **not** reuse the
  mass-weighted high-burst arithmetic mean inside every host, because the
  persistent high/low mixture already carries cross-host overdispersion.
- Under that geometric conditional-positive representation, the onset-negative
  expected linear-mass share is **16.8%** over the tabulated support. This is
  not the paper's approximately 10% log-AUC share: the paper's share is a
  log-transformed AUC measure, while the implementation shape is exponentiated
  linear emission with geometric positive magnitudes. This discrepancy is a
  declared limitation, not hidden agreement.
- Zhou support extends to onset day −5, but the active profile's existing
  presymptomatic gate remains 2.0 days. Almost all onset-negative expected mass
  in the implementation shape is on days −2 and −1, so this does not materially
  truncate the adopted correction; widening the gate to day −5 would require a
  separate owner decision.
- The shape support ends at day +13 because the aligned observations end there;
  later emission is truncation, not measured clearance.
- Multi-strain COVID co-infection uses an explicit Grade-C default because
  the retrieved literature does not provide a general per-lineage onset or
  episodic-emission rule: the primary lineage follows the host infection's
  onset/incubation clock; each later lineage follows its own acquisition clock
  with a virtual onset at the profile median incubation plus its phenotype
  modifier; each later lineage receives an independent deterministic episodic
  occurrence sequence; each later lineage clears on its corresponding virtual
  course; and co-resident lineages partition, rather than multiply, one host's
  emission capacity in proportion to inoculum. When episodic respiratory
  emission is silent, clinical specimen genotype composition falls back to
  those inoculum weights rather than treating all lineages as equal. The dual-
  lineage evidence found in this pass is case-report-scale composition turnover
  (for example Pedro et al. 2021, DOI 10.3390/microorganisms9020300), not a
  measured general kinetic law.
- This does not implement item 4 (household/service attribution) or item 5
  (person/specimen testing history). Those are explicitly outside this change.

## Validation

Local validation at the pre-commit working tree:

- `check-jsonschema --schemafile schemas/pathogen_profiles.schema.json`
  passes for `active_profiles.json`;
  `edison_10pathogen_profiles.json` is unchanged.
- New focused tests in `tests/test_covid_emission_shape.py` cover graded
  occurrence probabilities, nonzero presymptomatic emission inside the gate,
  the gate boundary, reproducibility within a day, finite nonnegative emission,
  the two-valued mean-normalized high/low mixture, and the shipped profile's
  zero-inflated mass contract.
- `tests/test_covid_theta_fit.py`, `tests/test_multi_pathogen_model_phase_a.py`,
  and `tests/test_shedding_clock.py` pass after deliberate contract updates;
  the moved shedding-clock expectations are attributed to replacement of
  deterministic curve emission by the zero-inflated emitted-RNA shape, not to
  an unattributed baseline move.
- The full non-slow pytest tier passed at the pre-PR working tree: **9,357
  passed, 11 skipped** (`pytest tests/ -m 'not slow' -n auto -q --tb=short`).
