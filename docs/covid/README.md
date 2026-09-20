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
| [covid_open_ledger.md](covid_open_ledger.md) | Living | Current withdrawals and measurement status for the COVID arm |
| [covid_parameter_provenance_audit.md](covid_parameter_provenance_audit.md) | Audit (2026-09-01) | Provenance class of every profile scalar; why the emission scale is not identifiable apart from β; which quantities are scored and must not be fitted |
| [covid_first_look_readout.md](covid_first_look_readout.md) | Findings (2026-09-14/16) | Replicated Theta grid on Diamond Princess (20 seeds), Greg Mortimer held-out scoring (50 seeds) and the boarding-axis screen (age x imports x Theta) on AWS Batch; the undeclared-cohort defect, the corrected v3 / screen v2 surfaces, and the v4 rerun on the corrected incubation model (Theta 3.16e7, interior); the quarantine-leak / roster-drain trace and the adaptive-density imports × Theta sweep design (`covid_import_sweep_v1`, not yet run) |
| [covid_theta_screen_v9_readout.md](covid_theta_screen_v9_readout.md) | Findings (2026-09-19) | `covid_theta_screen_v9` (10 decade Θ × 20 seeds, declared index geometry) on AWS Batch: geometry invariant holds in 600/600, infection-age axis byte-identical (inert under declared `onset_day`), `covid.T1` admissible set {1e9} by interval-span with `onset_mass_near_target` 0, Θ moves takeoff probability not outbreak size; surface in `covid_theta_screen_v9_surface.csv` |
| [covid_quarantine_attribution_v1_readout.md](covid_quarantine_attribution_v1_readout.md) | Findings (2026-09-20) | `covid_quarantine_attribution_v1` (six channel-removal arms × Θ {1e5, 1e9} × 20 seeds) on AWS Batch at `861a0b9`: no single channel load-bearing on the frozen `infections_during_quarantine` criterion; that measure counts reinfections (REINFECT-01 — no post-clearance immunity without a strain registry, record overwritten; fixed at `7f105a7`, see `docs/ledger/REINFECT-01.md`); on first infections crew exemption and pool transport carry the leak, near-field none; whole-voyage attack rate arm-invariant; surface in `covid_quarantine_attribution_v1_surface.csv` |
| [covid_quarantine_attribution_v2_readout.md](covid_quarantine_attribution_v2_readout.md) | Findings (2026-09-20) | `covid_quarantine_attribution_v1` re-run at `d62f10d` post-REINFECT-01: `infections_during_quarantine == ledger_events_during` in 240/240 cells; the frozen criterion now calls crew confinement (−74%) and pool transport (−66%) load-bearing at Θ 1e9, near-field not (+19%); supersedes v1's verdicts; surface in `covid_quarantine_attribution_v2_surface.csv` |
| [covid_arm_status.md](covid_arm_status.md) | Findings (2026-09-01) | What the `sars_cov2_resp` campaign arm actually does, and the four reasons it is not yet scoreable |
| [../proposals/covid_trajectory_fit_spec.md](../proposals/covid_trajectory_fit_spec.md) | Proposal — split and one-composite fit implemented (`picard_framework/covid_theta_fit.py`, `covid_first_look.py`); calendar/import axes not | The fixed train/test split: Diamond Princess trains, Greg Mortimer and the Willebrand cross-ship distribution are held out |

## How this differs from the norovirus thread

Norovirus is a distribution fit: 37,258 voyages, no per-day series, an
observation process that is a threshold on self-reported sick calls. COVID is a
trajectory fit on a handful of hulls whose observation process is a *testing
campaign* whose schedule was published. Anchors are pathogen-scoped for that
reason — a norovirus anchor is not evidence about a COVID run, and neither
arm may borrow the other's targets.
