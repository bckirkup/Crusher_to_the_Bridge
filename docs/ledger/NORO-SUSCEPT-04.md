# NORO-SUSCEPT-04
**Date:** 2026-09-26
**Commit:** f09ebb1b
**Pathogens:** norwalk_gi
**Status:** closed

Repair of the synthetic-recovery susceptibility-ceiling axis, which the
open-ledger Wave-1 note flagged as "still runs the withdrawn mechanism" and
the sister session's overestimation review re-flagged as one of four
structural issues. The campaign-facing defect was one step worse than the
ledger's wording: the axis did not merely run the withdrawn mechanism, it
ran **nothing at all**.

## Defect

`_iter_synthetic_recovery_runs` in
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py` read a
`non_susceptible` field off each parameter vector and wrote it into per-run
`pathogen_overrides` as `innate_nonsusceptible_fraction`, while recording
`non_susceptible` in `campaign_parameters`. But
`orchestrator_init.py::_resolve_secretor_status` resolves
`secretor_negative_fraction` **first**, and `active_profiles`' `norwalk_gi`
carries it — so the alias override was shadowed in every run: the engine
executed the profile's shipped 0.20 / 0.20 pair while the archive recorded a
swept `non_susceptible` axis that moved nothing. Swept values other than the
profile's would have been indistinguishable in output; the archive asserted
an axis the run never had. This is the duplicate-name defect archetype: two
spellings of one parameter, and the writer that lost resolution kept writing.

## Repair

The axis now speaks the mechanism's own vocabulary — the same keys the
profile and engine resolve, so there is no second spelling to go stale:

- Parameter vectors declare `secretor_negative_fraction` and/or
  `secretor_negative_relative_susceptibility`. Per coordinate the resolution
  precedence is the engine's own: vector declaration → arm base overrides →
  bundle profile → 0.0.
- The resolved pair is pinned into `pathogen_overrides` and recorded under
  the same two names in `campaign_parameters`. A spec therefore states the
  effective values it executed, including when no vector declares them and
  the profile truth (0.20 / 0.20) is pinned through.
- A vector that declares neither key on a profile that carries neither is
  left untouched: the axis is absent rather than written as zeros.
- The withdrawn spellings (`non_susceptible`,
  `innate_nonsusceptible_fraction`) in a parameter vector raise at load —
  the same refuse-stale-field convention `bounded_screen.py` applies to
  `contact_transfer_fraction` — instead of being silently shadowed.
- `innate_nonsusceptible_fraction` itself is **not** removed from the
  engine: it remains a deliberately-kept deprecated alias for the other
  `data/pathogens/` bundles that still use it.

## The uncertainty window is now representable

Secretor status is a sourced biological quantity, not a tuning knob, so the
axis carries its sourced window with it rather than flattening to one value:

- A scalar declaration is a grid sweep point, as before.
- `{"dist": "uniform"|"log_uniform", "interval": [lo, hi]}` draws once per
  run, derived as a sha256 hash of `f"{seed}:{field}"` — deterministic per
  run, a pure function of the label rather than an RNG stream, so the draw
  is reproducible and re-phases nothing downstream.
- `secretor_negative_relative_susceptibility`'s sourced window is
  **[0.04, 0.83]**, Kambhampati et al. 2015 pooled secretor:non-secretor
  odds ratios (GII.4 → 0.10 [0.04–0.26]; GII non-4 → 0.45 [0.24–0.83]);
  the declared GII.4/GII.17/GII.2 mixture straddles both rows, Grade B
  (`bounded_screen.py` `NOROVIRUS_FACTORS`). The adopted 0.20 stays inside
  it.
- `secretor_negative_fraction` is a demographic input — FUT2 se428
  homozygote prevalence, ≈0.20 in European/North American populations,
  Grade B — not a biological free parameter; the bounded screen keeps it
  fixed at 0.20 for that reason. A sweep of it is a population assumption,
  and the machinery permits it as such.

## Verification

`tests/test_mega_cruise_campaign.py::test_synthetic_recovery_cartesian_and_generator`
now asserts the generated spec's overrides and `campaign_parameters` carry
the secretor pair (0.20 / 0.20 from the shipped manifest vectors) and carry
no `innate_nonsusceptible_fraction`. `test_synthetic_recovery_secretor_axis_rules`
covers the refusal, the precedence, the bounded seeded draw, and the
absent-axis case. Campaign results archived under the shadowed
`non_susceptible` axis remain void under the withdrawn mechanism, as the
open ledger already required.
