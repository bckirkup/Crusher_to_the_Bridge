# COVID-THETA-REFIT-01
**Date:** 2026-11-20
**Commit:** c053e15f
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c053e15f

Re-fit of the COVID arm's fitted composite Θ (emission scale × per-copy risk;
tranche 25 refused separating them) on the DP `boxed_s1s2` replay under the
shipped post-B1-B3 stack (ambient/deck sinks live), then a held-out score on
Greg Mortimer — the `covid_first_look` fit/held-out split enforced (no held-out
quantity enters selection). 840 cells (24 blocks; DP 12 θ × 20 seeds,
GM 12 θ × 50 seeds), zero failures, audit clean — every payload carries
`design_id`, `arm_id`, the four resolved repair toggles and
`transport_engine_resolved`. Campaign `campaigns/covid/theta_refit_01`,
image `covid-theta-refit-01-v1` (sha256:48a6cd06…), jobdef
`picard-covid-theta-refit-01:1`. Canary `dp_theta_6p90` reproduced the shipped
baseline exactly (pooled lab_confirmed 1,236, all 20 seeds bit-identical on the
measured channels vs REPAIR-ISOLATION-01 baseline).

## Result — Θ refits to 3.162e11 (+4.5 decades); DP magnitude restored, GM lands near record, asym residual unmoved

**Fit (DP, merge_fit, 0.736 bootstrap selection frequency, boundary_pinned=False):**
selected θ = **3.162e11**, mean_loss 13.69 (vs 50.88 at the shipped 7.9e6;
runner-up 1e9 at 0.154 frequency). Interior minimum — the loss curve bottoms at
3.16e11/1e12. At the selected θ: takeoff 95%, campaign_positives median 443 vs
the scored covid.T3 target 634 (the record's lab-confirmed total is 712),
recorded_onsets median 2,878 vs 197 (the onset channel is the
dominant remaining residual). The ~40,000× upward move is what the composite Θ
needs to restore record-scale confirmations against the post-repair mass
budget: ~12× more emission (covid #30) is drained by the ambient/deck sinks,
and Θ makes up the difference.

**Held-out (GM, merge_held_out at fitted θ ± half-decade neighbours):**
takeoff 96%, campaign_positives median 108.5 [26.5–133.2] vs the 128/217
positive anchor — magnitude within ~15%. H1 positive share median 0.50 vs 0.5899 (hit 27/50;
θ=1e12 neighbour hits 37/50). **H2 asymptomatic share median 0.272 vs 0.8125 —
miss 49/50, invariant to Θ**: measured across all 12 GM θ points of this
sweep the per-θ medians run 0.24–0.44, and TF-01 read 0.24 at 2.37e11 under
both native and ContamX engines. A natural-history/observation-channel
defect, not a mass-budget one.
H3: 98% of seeds place GM above the cross-ship IQR.

## Consequences

- The shipped Θ constant (7.9e6) is stale for the COVID arm: under the current
  engine it leaves the DP funnel an order of magnitude under the record
  (per-voyage mean 61.8 pooled lab-confirmed vs 712, ≈11.5×).
  **Landed**: Θ is not a profile key — it is carried per-design as `thetas`
  and injected into cells by `theta_profile_overrides`. The canonical replay
  operating point moved to `thetas: [3.162e11]` on the boxed_s1s2 replay spec
  (`covid_crew_reach_01_design.json`, the spec later DP campaigns copy
  verbatim) and the frozen-operating-point replay
  (`covid_platform_fidelity_02_dp_design.json`); the provenance-register Θ row
  records the refit. Per-campaign designs that already ran (TF-01, RI-01,
  GM rescore) keep their own θ values as the record of what was measured.
- The asym-share miss is now demonstrated on two hulls across both solver
  stacks and five decades of Θ — the remaining composition defect sits in
  symptom/observation channels, not dose.
- recorded_onsets overshoot at the fitted Θ (median ~2.9k vs 197) while
  campaign positives land ~440–680: the funnel's dated-onset channel is the
  binding residual on the fit side.

Ledger: `campaigns/covid/theta_refit_01/LEDGER.md`. Designs:
`picard_framework/runs/covid_theta_refit_01_{dp,gm}_design.json`.
