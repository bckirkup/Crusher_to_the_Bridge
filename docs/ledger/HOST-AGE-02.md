# HOST-AGE-02
**Date:** 2026-10-05
**Commit:** 3e7c1898
**Pathogens:** norwalk_gi, influenza_a
**Status:** declared

The presentation draw's age structure is extended to the norovirus and
influenza arms and shipped default-ON, continuing the HOST-AGE-01 line
(age-graded susceptibility + presentation on `sars_cov2_resp`). Design
frozen in `docs/host_age_02_design.md`; measured-state consequences
(hull readouts under the armed arm) are a later stage.

## Change

- **Mechanism** (`engines/natural_history.py`): the by-band seam
  `presentation_probability` gets a third term —
  `illness_probability.age_factor_by_age_band`, a per-band **multiplier**
  on the dose-conditional Hill output (unnamed bands ×1.0), alongside the
  existing `symptomatic_fraction_by_age_band` replacement-share map.
  `presentation_age_mode` is the labelled-baseline axis on the whole age
  term: default `"by_age_band"` applies the declared maps; `"flat"`
  ignores both and reads the pooled share — the pre-age-structure
  behaviour. `_validate_age_graded_terms` bounds the factor map and
  rejects unknown mode values as load errors.
- **norwalk_gi**: the Teunis 2008 η/γ pair is the register's class-M
  dose-conditional measurement (its `⊘ mech` state is a genogroup caveat,
  not a form defect), so age enters as a factor rather than replacing the
  Hill — `age_factor_by_age_band` declares the coarsest sourced
  partition, child-vs-adult: `child`/`5-17`/`0-4` = **0.51**, the ratio
  of the register's two unpooled never-symptomatic regimes (pediatric
  community cohorts sf ≈ 0.365 / adult challenge sf ≈ 0.71; Grade C as a
  cross-design adaptation). Every other band multiplies 1.0 — no
  admissible design measures p(symptomatic|infection) in ≥65 (the
  register's own `never_symptomatic` row states so), so no elderly split
  is invented.
- **influenza_a**: `symptomatic_fraction_by_age_band` carries the full
  label set from one commensurable design — Hoy 2022 (Clin Infect Dis,
  DOI 10.1093/cid/ciac734) household cohorts: `0-4` 0.965, `5-17`/`child`
  0.909, every ≥15 label 0.734 (the source reports no trend within ≥15).
  Grade B; Carrat's pooled 0.669 stays the unnamed-band fallback.

## Recorded, not softened

- The noro child factor reads 0–2y cohorts for a band that reads 5–17
  under the severity model's convention; the fraction rises through
  childhood, so 0.51 understates the band's older half — the measured
  child end, not an interpolation.
- On a senior-skewed hull (Pavli mean 72.6) noro's pooled draw is
  essentially unmoved — every non-child band multiplies 1.0 — while flu's
  pooled presentation rises toward the adult 0.734 (children present
  *more*, so a child-light hull reads the adult level).
- Flu's `severity_model.base_probabilities` asymptomatic 0.20 stays —
  renormalised away for presenters; the same consistency debt covid's
  ladder records, not silently aligned.
