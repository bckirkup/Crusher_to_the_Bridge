# Norovirus calibration thread

> **Status:** Living. The active calibration workstream.

Read [`norovirus_open_ledger.md`](norovirus_open_ledger.md) **before quoting any
dose, route share, or anchor result.** Every dose figure in the repository is
void pending a refit.

| Doc | Status | Role |
|-----|--------|------|
| [norovirus_open_ledger.md](norovirus_open_ledger.md) | Living | What is currently withdrawn, what the anchors are, what is outstanding |
| [norovirus_model_history.md](norovirus_model_history.md) | Permanent record | Every defect found and revision made, with the numbers each one invalidated. §10 lists parameters held fixed by assumption |
| [admissible_region_37.md](admissible_region_37.md) | Measurement (2026-09-06) | The #37 feasibility gate over the full six-factor box: the admissible region is **empty**, 0 of 128 Sobol' points admissible. Records where it binds and, crucially, why that is not yet a structural verdict — A8 and A9 are unusable at this design's cell, A1-vs-A4 binds in the observation model, and A1-vs-A2 is the one structural tension |
| [admissible_region_37_v2.md](admissible_region_37_v2.md) | Measurement (2026-09-07) | The #37 gate re-run on the repaired structure: 256 Sobol' points × 180 seeds over the **full ten-factor box**, still **empty**, but now every anchor scored — A9 is resolvable and fails high by at least 6× everywhere, take-off is 1.0 at all 256 points, and A1-vs-A2 reproduces. Supersedes the design limitations of `admissible_region_37.md`, not its findings |
| [lowposting_region_37.md](lowposting_region_37.md) | Measurement (2026-09-05) | The quiet corner of the #37 v2 box re-run at **1,440 seeds** on 16 of its own grid indices with every voyage's row retained: the posting floor is 3.19% (exact 95% 2.35–4.24%), no interval reaches A9's 0.42–0.56%, extinction exists at 0.26%, posted voyages sit inside A4's IQR, and **51% of postings are crew-only** on a 134-crew, five-case trigger |
| [dutyexcl_matched_37.md](dutyexcl_matched_37.md) | Measurement (2026-09-05) | VSP's regulated crew duty exclusion (Operations Manual 4.4.1.1.1) implemented as `SOP-VSP-CREW-01` and measured as a matched arm over the same twelve quiet points × 1,440 common-random-number seeds: postings 793 → 780 of 17,280, crew-only 408 → 391, McNemar exact **p = 0.20**, exclusion arm still 4.514% against A9's 0.42-0.56% — **neither sufficient nor necessary** for A9, at `compliance_fraction` 1.0, the regulatory upper bound |
| [bounded_screen_isolated_36.md](bounded_screen_isolated_36.md) | Measurement of a retired initial condition (2026-09-05) | The Morris screen on the current six-factor box, isolated: one factor resolves above the noise floor, five do not, and nothing is bounded. Superseded on arrival by #54/#440's boarding migration, which replaced its one fiat index case; §0 records what that changes and why neither the ranking nor the floor carries forward |
| [bounded_screen_results.md](bounded_screen_results.md) | Superseded measurement (2026-09-01) | The Morris screen over the old seven-factor box. Superseded by `bounded_screen_isolated_36.md`; kept as the record of what that box measured — no ranking in it describes the current one |
| [c1_reported_case_bracket_result.md](c1_reported_case_bracket_result.md) | Measurement (2026-09-05) | Why the 2,880-run C1 dose bracket is withdrawn: every rung of the 12.0-14.0 ladder produced identical output at every seed, so the sweep measured its own replication |
| [adj_stratified_readout.md](adj_stratified_readout.md) | Measurement (2026-09-11) | The four expedition campaigns re-read within a dose regime, on arrays already on disk: the large contact arms were diluted ~8× by the inert part of the box rather than null, A5 is flat at 2.56–2.75 in **every** regime against ≈3.5, and the import-only stratum still posts 4.5% against A9's 0.6–1.6% — so no transmission-side change reaches the posting anchor. Nothing adopted, no stratum declared |
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
| Routes | `fomite_food_rederivation.md`, `route_clearance_efficiency.py`, `route_clearance_findings.md`, `clearance_additivity_check.py`, `clearance_additivity_findings.md`, `emesis_deposition_spec.md`, `fomite_pool_denominator_reconciliation.md` |
| Observation model | `observation_model_design.md`, `observation_model_calibration.md`, `five_state_severity_spec.md`, `severity_prior_sensitivity_findings.md` |
| Diagnostics | `a5_role_asymmetry_diagnosis.md`, `dose_accumulation_defect.md`, `adj_stratified_readout.py` |
| Pilot runs | `PILOT_SPEC.md`, `postfix_anchor_pilot_*/`, `postmerge_anchor_pilot_*/` |

Consolidating those markdown files here, leaving the `.py` and `.csv` in place,
is a reasonable follow-up; it needs a test-import sweep and was kept out of the
reorganisation that created this directory.
