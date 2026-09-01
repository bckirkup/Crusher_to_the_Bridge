# SARS-CoV-2 thread

> **Status:** Living. The COVID arm exists and executes; it is not yet scoreable.

Read [`covid_parameter_provenance_audit.md`](covid_parameter_provenance_audit.md)
**before quoting any `sars_cov2_resp` constant as a literature value.** Eight of
the twenty-five scalars in `formal_spec_v2.md` Appendix A.2 are sourced; the
dose-response α/β are not, and the emission magnitude is dimensionally wrong.

| Doc | Status | Role |
|-----|--------|------|
| [covid_parameter_provenance_audit.md](covid_parameter_provenance_audit.md) | Audit (2026-09-01) | Provenance class of every profile scalar; why the emission scale is not identifiable apart from β; which quantities are scored and must not be fitted |
| [covid_arm_status.md](covid_arm_status.md) | Findings (2026-09-01) | What the `sars_cov2_resp` campaign arm actually does, and the four reasons it is not yet scoreable |
| [../proposals/covid_trajectory_fit_spec.md](../proposals/covid_trajectory_fit_spec.md) | Proposal — **nothing implemented** | The fixed train/test split: Diamond Princess trains, Greg Mortimer and the Willebrand cross-ship distribution are held out |

## How this differs from the norovirus thread

Norovirus is a distribution fit: 37,258 voyages, no per-day series, an
observation process that is a threshold on self-reported sick calls. COVID is a
trajectory fit on a handful of hulls whose observation process is a *testing
campaign* whose schedule was published. Anchors are pathogen-scoped for that
reason — a norovirus anchor is not evidence about a COVID run, and neither
arm may borrow the other's targets.
