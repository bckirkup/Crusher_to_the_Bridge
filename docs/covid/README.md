# SARS-CoV-2 thread

> **Status:** Living. The COVID arm exists, executes, and has been scored at
> scale three times (`covid_first_look_v1`/`v2`/`v3`, 2026-09-14/15). v1 and
> v2 boarded an undeclared ~34-host cohort and are withdrawn; v3, seeded as
> the record declares (one index case), does not produce the Diamond Princess
> outbreak in 14-18 of 20 seeds at any Theta. The open question is the number
> of imports, before it is Theta.

Read [`covid_parameter_provenance_audit.md`](covid_parameter_provenance_audit.md)
**before quoting any `sars_cov2_resp` constant as a literature value.** Eight of
the twenty-five scalars in `formal_spec_v2.md` Appendix A.2 are sourced; the
dose-response α/β are not, and the emission magnitude is dimensionally wrong.

| Doc | Status | Role |
|-----|--------|------|
| [covid_parameter_provenance_audit.md](covid_parameter_provenance_audit.md) | Audit (2026-09-01) | Provenance class of every profile scalar; why the emission scale is not identifiable apart from β; which quantities are scored and must not be fitted |
| [covid_first_look_readout.md](covid_first_look_readout.md) | Findings (2026-09-14/16) | Replicated Theta grid on Diamond Princess (20 seeds), Greg Mortimer held-out scoring (50 seeds) and the boarding-axis screen (age x imports x Theta) on AWS Batch; the undeclared-cohort defect, the corrected v3 / screen v2 surfaces, and the v4 rerun on the corrected incubation model (Theta 3.16e7, interior) |
| [covid_arm_status.md](covid_arm_status.md) | Findings (2026-09-01) | What the `sars_cov2_resp` campaign arm actually does, and the four reasons it is not yet scoreable |
| [../proposals/covid_trajectory_fit_spec.md](../proposals/covid_trajectory_fit_spec.md) | Proposal — split and one-composite fit implemented (`picard_framework/covid_theta_fit.py`, `covid_first_look.py`); calendar/import axes not | The fixed train/test split: Diamond Princess trains, Greg Mortimer and the Willebrand cross-ship distribution are held out |

## How this differs from the norovirus thread

Norovirus is a distribution fit: 37,258 voyages, no per-day series, an
observation process that is a threshold on self-reported sick calls. COVID is a
trajectory fit on a handful of hulls whose observation process is a *testing
campaign* whose schedule was published. Anchors are pathogen-scoped for that
reason — a norovirus anchor is not evidence about a COVID run, and neither
arm may borrow the other's targets.
