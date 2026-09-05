# Norovirus calibration thread

> **Status:** Living. The active calibration workstream.

Read [`norovirus_open_ledger.md`](norovirus_open_ledger.md) **before quoting any
dose, route share, or anchor result.** Every dose figure in the repository is
void pending a refit.

| Doc | Status | Role |
|-----|--------|------|
| [norovirus_open_ledger.md](norovirus_open_ledger.md) | Living | What is currently withdrawn, what the anchors are, what is outstanding |
| [norovirus_model_history.md](norovirus_model_history.md) | Permanent record | Every defect found and revision made, with the numbers each one invalidated. §10 lists parameters held fixed by assumption |
| [bounded_screen_isolated_36.md](bounded_screen_isolated_36.md) | Measurement of a retired initial condition (2026-09-05) | The Morris screen on the current six-factor box, isolated: one factor resolves above the noise floor, five do not, and nothing is bounded. Superseded on arrival by #54/#440's boarding migration, which replaced its one fiat index case; §0 records what that changes and why neither the ranking nor the floor carries forward |
| [bounded_screen_results.md](bounded_screen_results.md) | Superseded measurement (2026-09-01) | The Morris screen over the old seven-factor box. Superseded by `bounded_screen_isolated_36.md`; kept as the record of what that box measured — no ranking in it describes the current one |
| [c1_reported_case_bracket_result.md](c1_reported_case_bracket_result.md) | Measurement (2026-09-05) | Why the 2,880-run C1 dose bracket is withdrawn: every rung of the 12.0-14.0 ladder produced identical output at every seed, so the sweep measured its own replication |
| [norovirus_parameter_freedom_audit.md](norovirus_parameter_freedom_audit.md) | Audit (2026-08-30) | Which parameters are still free, which are set away from a literature value, and which anchors are circular |
| [cruise_pathogen_severity_observation_priors_v2.md](cruise_pathogen_severity_observation_priors_v2.md) | Living — prior elicitation | Severity and observation priors for all ten pathogen profiles. Grades its own vectors `[A]` = assumption |
| `vsp_covid_discontinuity.png` | Figure | The VSP discontinuity plot. **The numbers read off this image are withdrawn** — see the ledger; use the measured series instead |

## Work-products live elsewhere, deliberately

The measurement harnesses, their raw output, and the per-investigation findings
notes are under `telemetry_buffer/observation_model/`, not here. That directory
is an importable Python package (`tests/test_cleaning_schedule_sweep.py` and
`tests/test_vsp_discontinuity_analysis.py` import from it), so the harnesses
cannot move without changing test imports. The findings notes were left beside
their harnesses rather than split from them.

What is over there:

| Kind | Files |
|------|-------|
| Anchor definitions | `anchor_measurement_spec.md`, `score_anchors.py` |
| Incidence and posted attack rate by class and era | `incidence_and_attack_rate_scoring_spec.md`, `vsp_class_era_scoring.py` |
| VSP series | `vsp_outbreak_series.csv`, `vsp_series_spec.md`, `vsp_outbreak_series_extraction_log.md`, `fetch_vsp_outbreaks.py` |
| COVID discontinuity | `vsp_covid_discontinuity_design.md`, `vsp_covid_discontinuity_findings.md`, `vsp_discontinuity_analysis.py`, `post_covid_configuration_sources.md` |
| Surfaces & cleaning | `park_surface_check.py`, `park_surface_findings.md`, `park_emesis_findings.md`, `cleaning_schedule_sweep.py`, `cleaning_schedule_sweep_spec.md` |
| Routes | `fomite_food_rederivation.md`, `route_clearance_efficiency.py`, `route_clearance_findings.md`, `clearance_additivity_check.py`, `clearance_additivity_findings.md`, `emesis_deposition_spec.md` |
| Observation model | `observation_model_design.md`, `observation_model_calibration.md`, `five_state_severity_spec.md`, `severity_prior_sensitivity_findings.md` |
| Diagnostics | `a5_role_asymmetry_diagnosis.md`, `dose_accumulation_defect.md` |
| Pilot runs | `PILOT_SPEC.md`, `postfix_anchor_pilot_*/`, `postmerge_anchor_pilot_*/` |

Consolidating those markdown files here, leaving the `.py` and `.csv` in place,
is a reasonable follow-up; it needs a test-import sweep and was kept out of the
reorganisation that created this directory.
