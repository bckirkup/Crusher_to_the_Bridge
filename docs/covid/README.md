# SARS-CoV-2 thread

> **Status:** Living. The COVID arm exists and executes. The Θ screens
> iterated to `covid_theta_screen_v13` (2026-09-28): under capped reach
> (COVID-EXPOCAP-01) the admissible band is {1.78e11 … 5.62e11} and the
> conditional clause fails at every interior admissible Θ — it passes only
> at the boundary anchor. `covid_rebase_01` re-screened the void window on
> the post-721 base: admissible set empty, the fleet-shape window bracketed
> between 1e11 and 1e12. The current hunt is mechanism-level on the
> residual (COVID-RINGCAP-V1 + COVID-SUSCPOOL-V1 canary measured). Read
> [`covid_open_ledger.md`](covid_open_ledger.md) before quoting any figure —
> earlier Θ surfaces and route shares are withdrawn at their own entries.

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
| [covid_theta_screen_v7_readout.md](covid_theta_screen_v7_readout.md) | Findings (2026-09-19) | 3,080-cell screen on the pre-v9 engine: admissible region empty |
| [covid_theta_screen_v11_readout.md](covid_theta_screen_v11_readout.md) | Findings (2026-09-22) | Stage 1, 1,600 cells: empty admissible set on the decade lattice; H3 window bracketed (1e10, 1e11) |
| [covid_theta_screen_v11_refine_readout.md](covid_theta_screen_v11_refine_readout.md) | Findings (2026-09-22) | Refine stage 1, 1,400 cells: admissible {3.16e10, 4.22e10, 5.62e10} — interior band ~0.25 decades |
| [covid_theta_screen_v11_stage2_readout.md](covid_theta_screen_v11_stage2_readout.md) | Findings (2026-09-22) | Conditional clause fails at every admissible Θ; deficit localised to conditional outbreak size |
| [covid_theta_screen_v12_readout.md](covid_theta_screen_v12_readout.md) | Findings | Bisection over (1e11, 1e12) on the post-721 base: clause fails at every admissible Θ, passes only at the boundary anchor |
| [covid_theta_screen_v13_readout.md](covid_theta_screen_v13_readout.md) | Findings | Re-admission under capped reach: band {1.78e11 … 5.62e11}, clause still fails at every admissible Θ |
| [covid_rebase_01_readout.md](covid_rebase_01_readout.md) | Findings | COVID-REBASE-01 Θ re-screen on the post-721 base: admissible set empty; window bracketed (1e11, 1e12) |
| [covid_sensitivity_assay_v1_readout.md](covid_sensitivity_assay_v1_readout.md) | Findings (2026-09-23) | 240-cell assay: every transmission-layer arm inert on the frozen conditional metric; only the all-shared-air bound moves, and it kills takeoff |
| [covid_partner_rate_assay_v1_readout.md](covid_partner_rate_assay_v1_readout.md) | Canary readout | `R1_rate_0p25` measured end to end; the other eight arms stood down |
| [covid_plume_dose_assay_v1_readout.md](covid_plume_dose_assay_v1_readout.md) | Findings | Complete: all 10 arms × 20 seeds = 200 cells |
| [covid_route_attribution_v1_readout.md](covid_route_attribution_v1_readout.md) | Findings | ROUTE-ATTR-V1 whole-voyage route attribution + ascertainment funnel (local, structural) |
| [covid_lambda_cross_v1_readout.md](covid_lambda_cross_v1_readout.md) | Findings | LAMBDA-CROSS-V1 hazard-rate (Θ) response curve, 140/140 cells |
| [covid_mech_v1_canary_readout.md](covid_mech_v1_canary_readout.md) | Stale | COVID-RINGCAP-V1 + COVID-SUSCPOOL-V1 mechanism assays on the v13 residual (anchor row only); superseded by the v2 re-measurement |
| [covid_mech_v2_canary_readout.md](covid_mech_v2_canary_readout.md) | Canary measured | Anchor row re-measured under `once_per_course` at `def39066`: rings_first premise collapsed, f050 premise survived |
| [covid_mech_v2_band_readout.md](covid_mech_v2_band_readout.md) | Findings | Full arrays measured at `def39066`: f050 fails the clause at every admissible Θ — both assays dead; f050's fleet response lands inside the covid.H3 window at 4/5 θs |
| [covid_propensity_v1_readout.md](covid_propensity_v1_readout.md) | Canary measured | PROPENSITY-V1 clause canary at the Θ1e9 anchor (`e0d43979`): clause fails on both arms; propensity footprint is seed noise; v15 anchor pass void on engine drift |
| [covid_caregiver_off_v1_readout.md](covid_caregiver_off_v1_readout.md) | Canary measured | CAREGIVER-ATTR-01 at `b932d0e9`: caregiver-off restores the v15 clause pass at Θ1e9 (11/20 takeoff, band ∋197, share 0.200) — CAREGIVER-V1 measured as the anchor-drift mover |
| [covid_theta_refit_v1_readout.md](covid_theta_refit_v1_readout.md) | Findings (2026-10-04) | THETA-REFIT-01 at `78f52a58`: 9-row quarter-decade Θ lattice × 20 seeds under shipped defaults, 180/180 cells — verdict NO-ADMISSIBLE: every row fails the count leg on the same side (q05 ≥ 523 > 197, floor ~700 at Θ1e7); the residual is mechanism-shaped, not Θ-shaped |
| [covid_theta_refit_floor_v1_readout.md](covid_theta_refit_floor_v1_readout.md) | Findings (2026-10-04) | THETA-REFIT-01 floor falsifier at `8f49652f`: Θ1e6 × 20 seeds, 20/20 cells — count leg PASSES ([149,760] ∋ 197, `mass_near_197` 0.474) while the timing leg fails below-side (0.051 < 0.073); the projected mechanism-shaped floor is falsified and the (1e6,1e7) bracket reopens |
| [covid_theta_refit_bracket_v1_readout.md](covid_theta_refit_bracket_v1_readout.md) | Findings (2026-10-04) | THETA-REFIT-01 bracket refine at `8f926382`: 5 rows on (1e6,1e7) × 20 seeds, 100/100 cells — verdict WINDOW-EMPTY-ORDERED certified: θ_c ∈ (1e6,1.4e6) < θ_t ∈ (5.62e6,7.9e6), the legs' admissible half-planes are disjoint; the clause passes nowhere on [1e6,1e9] — the residual is clause-shaped |
| [covid_dp_ventilation_sourcing.md](covid_dp_ventilation_sourcing.md) | Sourcing note | Diamond Princess ventilation and the confinement leak; no constant adopted |
| [covid_droplet_split_options_memo.md](covid_droplet_split_options_memo.md) | Decided | Option 1 (emission partition at source) implemented as AERO-SPLIT-01 |
| [covid_theta_handoff_2026_09_19.md](covid_theta_handoff_2026_09_19.md) | Handoff record | Where the Θ calibration stood at v9 → v10 |
| [covid_theta_handoff_2026_09_21.md](covid_theta_handoff_2026_09_21.md) | Handoff record | THETA-SCREEN-V10 measured; the v11 admissibility-criterion decision |
| [covid_channel_anchor_handoff_2026_09_25.md](covid_channel_anchor_handoff_2026_09_25.md) | Handoff record | The conditional-gap hunt after PARTNER-RATE / PLUME-DOSE / ROUTE-ATTR / LAMBDA-CROSS; the SERO-CHANNEL-V1 proposal |
| [covid_arm_status.md](covid_arm_status.md) | Findings (2026-09-01) | What the `sars_cov2_resp` campaign arm actually does, and the four reasons it is not yet scoreable |
| [../proposals/covid_trajectory_fit_spec.md](../proposals/covid_trajectory_fit_spec.md) | Proposal — split and one-composite fit implemented (`picard_framework/covid_theta_fit.py`, `covid_first_look.py`); calendar/import axes not | The fixed train/test split: Diamond Princess trains, Greg Mortimer and the Willebrand cross-ship distribution are held out |

## How this differs from the norovirus thread

Norovirus is a distribution fit: 37,258 voyages, no per-day series, an
observation process that is a threshold on self-reported sick calls. COVID is a
trajectory fit on a handful of hulls whose observation process is a *testing
campaign* whose schedule was published. Anchors are pathogen-scoped for that
reason — a norovirus anchor is not evidence about a COVID run, and neither
arm may borrow the other's targets.
