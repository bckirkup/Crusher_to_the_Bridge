# COVID-VULN-01
**Date:** 2026-09-28
**Commit:** 6669b11e
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 6669b11e

VULN-01 maps the susceptibility-law shape axis α of the shipped
`dose_response: {beta_poisson, α 0.18, β 58.0}` on `sars_cov2_resp`.
Register-locked structure: **β⁻¹ is a scale factor degenerate with the
emission scale Θ to within 0.7% on the 5th–95th quantiles — α alone
carries the shape**; Θ is fixed at the v12 admissible-band midpoint
2.37e11 via `susceptibility_scale = Θ·(α+β)/α`, so E[s] = Θ on every arm
and α moves only the distribution's shape (β = 58: CV = √(β/(α(α+β+1))):
α 0.05 → 4.4; shipped 0.18 → 2.33; α 0.5 → 1.40; α 2.0 → 0.69; the
α→∞ exponential limit is homogeneous, CV → 1/√(α+β+1) → ~0.13 at the
point mass). Two parts: a sourced bound on α's tail mass from the
literature (no attack-rate fitting), and an endpoint A/B on the takeoff
cell family to measure whether the residual moves with α.

## Mechanism under test

Lazy per-host draw `s ~ rng.beta(α, β) × susceptibility_scale` on
`agent.dose_response_susceptibility[pathogen_id]`, hazard
`−expm1(−s·D)` (`engines/transmission_core.py` ~3720–3773 — the same
machinery NORO-FRAIL-01 verified). Under the shipped pair:
P(s<1e−7) = 0.12, P(s<1e−5) = 0.28, median 2.4e−4 — ~12% of hosts are
effectively unchallengeable at achievable doses. The burn is the
compounded tail of the joint (s-draw, D-arrival) lottery; whether the
takeoff residual is vulnerability-shaped is the question.

## Part 1 — Sourced shape bound on α (literature)

**Declared widest interval: α ∈ [0.05, 2.0], β held 58.0 (scale).**
**Graded interior: α ∈ [0.5, 1.5].**

No challenge-fitted beta-Poisson pair exists for SARS-CoV-2 (register row,
Class C, attribution withdrawn twice): Killingley 2022 is a single-dose
point (18/34 seroconverted at 10 TCID50) that cannot identify two
parameters; Jackson 2024 is seropositive-only; every fitted candidate is
attack-rate-fitted and rejected under the sourcing policy. The bound
therefore rests on indirect shape evidence:

- **Family challenge fits (the only dose–response pairs measured under
  controlled dosing for a coronavirus):** Aganovic & Widdowson 2023
  (Risk Analysis 10.1111/risa.14178) refit the HCoV-229E human challenge
  data — the **exponential law is the best fit** (homogeneous
  susceptibility, ID50 12.83 TCID50); the fitted beta-Poisson arms are
  α = 0.7269–0.7858, i.e. the near-homogeneous direction. The same
  paper's HRV-16 refit gives α = 0.152 (much heavier tail — rhinovirus,
  not coronavirus). Coronavirus challenge evidence thus points to
  α ≳ 0.7, never below ~0.15.
- **Direct susceptibility heterogeneity:** Gomes et al. 2022 estimated
  individual susceptibility CV ν = 1.314 and connectivity CV 0.83 for
  SARS-CoV-2. Mapped through CV² = β/(α(α+β+1)) at β = 58: ν 1.314 →
  α ≈ 0.56; connectivity 0.83 → α ≈ 1.4. These are population-structured
  estimates, not challenge fits — used as a graded interior anchor only.
- **Bimodality evidence:** Miura et al. 2023 (Epidemiology) fit
  individual-level susceptibility distributions on Danish register data —
  a **bimodal mixture is strongly supported**; both the homogeneous model
  and the continuous gamma family are rejected. Beta(α,β) is unimodal
  for α,β > 1 and U-shaped for α,β < 1 — a beta law cannot express the
  measured bimodality at all, so bimodality evidence neither selects an
  α nor licenses the shipped shape; it warns the whole beta family is a
  stand-in. (Recorded as evidence, not a bound.)
- **Offspring overdispersion (k ≈ 0.1–0.5, Du et al. 2022 pooled
  k = 0.55, CI 0.30–0.79):** bounds the *combined* individual-level
  heterogeneity (infectiousness + contact + susceptibility), not the
  susceptibility share. As an envelope it permits tails far heavier than
  any fitted coronavirus α; it cannot tighten the interior and is
  recorded as context only.
- **Escape fractions:** challenge-study non-converters (Killingley:
  16/34 unconverted after direct nasal challenge) are consistent with a
  resistant tail but confound inoculum escape with true
  invulnerability — the HCoV-229E series had zero escapees at the fitted
  ID50 range. Not a bound.

**Honest reading:** no defensible *sharp* bound exists — the offspring
envelope admits arbitrarily sharp tails and the challenge fits come from
other viruses (229E: α ~0.7–0.8; HRV-16: α 0.15). The declared interval
is therefore the **widest defensible envelope**: α_lo = 0.05 (heavier
tail than any measured virus-family value — a stress arm; CV ≈ 4.4),
α_hi = 2.0 (near-homogeneous direction the coronavirus challenge fits
favor, finite stand-in for the exponential limit; CV ≈ 0.69). The graded
interior [0.5, 1.5] brackets every direct susceptibility-heterogeneity
estimate and the 229E fitted values. Shipped 0.18 sits just below the
interior — between the challenge-fit direction and the offspring
envelope; the register row keeps Class C (attribution withdrawn): the
pair is *declared*, not *measured*.

## Part 2 — Endpoint A/B measurement (simulation)

### Conditions

Identical takeoff conditioning to TAKEOFF-ATTR-01 / RHYTHM-01: declared
replay on the record hulls, 1 import, infection_age 6.8 d, onset_day
−1.0, departure_day 5.0, dwell-weighted sanitary visits, SOP-017 days
16–30 (expedition 8–27), 768 epochs (expedition 672/28 d), syndromic
onset observation, boarding disabled, immune_fraction 0. Every cell pins
`rhythm.enabled` and `transmission.exposure_cap.enabled` — the axis is
read on the capped-reach exposure context. Four classes × 2 arms × 20
seeds = 160 cells, paired seeds 20200205–20200214 (mega, contemporary,
classic) and 20200315–20200334 (expedition).

| arm | α | CV | susceptibility_scale |
|---|---|---|---|
| alpha_lo | 0.05 | 4.4 | 2.751e14 |
| alpha_hi | 2.0 | 0.69 | 7.11e12 |

Instrument additions on the measurement SHA: `summary.dose_response`
echoes the resolved consumed profile (override-landing audit),
`mechanism.susceptibility.challenged_pairs` emits per-host
`{susceptibility, accrued_hazard, accrued_dose}` for challenged-uninfected
hosts (accrued_dose accrues susceptibility-free — no underflow).

### Canary (axis-liveness gate)

Two takeoff-conditioned mega cells at seed 20200205, submitted via
`--index` against digest-pinned jobdef `picard-covid-vuln-ab-fargate:1`:

| arm | α consumed (resolved echo) | recorded onsets | infections |
|---|---|---|---|
| alpha_lo | 0.05 | 1,636 | 2,348 |
| alpha_hi | 2.0 | 1,910 | 3,710 |

The resolved-α echo in `summary.dose_response` matched the declared arm
on both cells (override consumed — the axis was exercised), and the
burn moved in the direction the closed form predicts (+274 onsets,
+1,362 infections toward the sharper law). Axis live → array proceeded.

### Array readout

160 cells (4 classes × 2 arms × 20 paired seeds), 20 seeds per arm:
seeds 20200205–20200224 on mega/contemporary/classic, 20200315–20200334
on expedition. `landing_audit.landed` = true on all 160 (declared α
equals resolved α in every cell's `summary.dose_response` echo).
All counts are recorded onsets among takeoff seeds (recorded ≥ 10).

| class | arm | takeoff seeds | onsets q05 / med / q95 | takeoff share [Wilson] | clause | clause_ratio | before_share med |
|---|---|---|---|---|---|---|---|
| mega | α 0.05 | 17/20 | 712 / 1925 / 2342 | 0.85 [0.64, 0.95] | fail | 9.77 | 0.42 |
| mega | α 2.0 | 20/20 | 1910 / 3606 / 3702 | 1.00 [0.84, 1.00] | fail | 18.30 | 0.92 |
| contemporary | α 0.05 | 16/20 | 294 / 1708 / 1942 | 0.80 [0.58, 0.92] | fail | 8.67 | 0.76 |
| contemporary | α 2.0 | 20/20 | 1688 / 2927 / 2993 | 1.00 [0.84, 1.00] | fail | 14.86 | 0.93 |
| classic | α 0.05 | 19/20 | 254 / 1090 / 1195 | 0.95 [0.76, 0.99] | fail | 5.53 | 0.81 |
| classic | α 2.0 | 20/20 | 925 / 1306 / 1890 | 1.00 [0.84, 1.00] | fail | 6.63 | 0.97 |
| expedition | α 0.05 | 17/20 | 30 / 39 / 48 | 0.85 [0.64, 0.95] | fail | 0.198 | 0.93 |
| expedition | α 2.0 | 20/20 | 88 / 111 / 123 | 1.00 [0.84, 1.00] | fail | 0.563 | 0.98 |

Paired-seed deltas (hi − lo, same seed) against each arm's own
neighbouring-seed spread — the null band from the
stochastic-attribution convention:

| class | Δ onsets med (q05–q95) | within-arm spread med / q95 | effect > spread? |
|---|---|---|---|
| mega | +1668 (+123 … +3702) | 53 / 712 | yes |
| contemporary | +1222 | 27 / 358 | yes |
| classic | +130 (−31 … +1636) | 29 / 263 | yes |
| expedition | +76 (+57 … +109) | 1 / 10 | yes |

`identical_burns` = false on every class — the α axis is live and large.
Sharpening the law converts the challenged-uninfected residual pool:
the hi arms end with essentially zero survivor mass (challenged share
≈ 1.0 both arms; challenged-uninfected Λ median ~4e−7 lo vs ~0 hi —
nobody left unconverted at high α), and ~1.5–1.9% of lo-arm survivors
sit at marginal P ≥ 0.5.

Clause read: **no (α endpoint × Θ = 2.37e11) cell is clause-compatible
anywhere** — all eight fail. The record hull misses on both clause
halves even at α = 0.05 (beyond every measured virus-family value):
onset mass 1925 median vs 197 (~10×), and before_share 0.42 vs
0.173 ± 0.10 — the heavy tail delays the burn past departure day 5.
The expedition class brackets *below* the record on both arms
(q95 48 → 123), so no endpoint ordering inverts the miss direction.

## Part 3 — Analytic check (Λ convolution, no sims)

For the shipped law, the marginal infection probability of a host that
stood in an accrued dose field D̃ has the closed form
P(inf|D̃; α) = 1 − ₁F₁(α, α+β, −scale·D̃) with scale = Θ(α+β)/α
(E[s] = Θ on every arm); the α→∞ limit is the exponential law
1 − exp(−Θ·D̃). Convolving each curve over the per-cell emitted
`accrued_dose` field predicts the counterfactual infection mass under
each α — checked against the measured A/B per paired (class, seed);
>2× disagreement is the instrument-defect trigger.

Marginal curves on the measured dose field (accrued dose median ~1e−4
on challenged-uninfected hosts) sit in the **saturated regime**:
at D̃ = 3.2e−4, P(inf|D̃) ≈ 0.65 at α 0.05, ~0.97 at shipped 0.18, and
≈ 1.00 for every α ≥ 0.5 — the challenge field saturates all but the
deepest tail, so α sensitivity concentrates below ~0.18, exactly where
the shipped value sits.

Pooled predicted conversion mass over each lo-arm cell's measured
survivor field (median per cell):

| class | own α 0.05 | α 0.18 | α ≥ 0.5 | exp limit |
|---|---|---|---|---|
| mega | 842 | 1327 | ~1382 | 1383 |
| contemporary | 685 | 1051 | ~1097 | 1097 |
| classic | 438 | 676 | ~704 | 705 |
| expedition | 52 | 91 | ~106 | 108 |

Per-pair cross-check (predicted survivor-conversions under the
counterfactual α vs the measured hi − lo secondaries delta — the
tail-move, not total burn): **55 of 80 pairs applicable, ratio median
0.9997, range [0.982, 1.020]; 0 pairs outside [0.5, 2.0].** The 25
non-applicable pairs are extinct or weak basis fields (the lo arm never
ignited or burned < half the mate's mass — the survivor field there
cannot stand in for a trajectory the basis arm never took). The
measured α tail-move is *exactly* the marginal survivor-conversion
move — no unexplained residual, no instrument-defect trigger.

Check-semantics note: the cross-check as first merged divided the
predicted counterfactual mass by the mate's *total* secondaries,
spuriously flagging >2× on every pair; this PR corrects the denominator
to the measured tail-move (mate − own secondaries) and adds the
applicability gate. Recorded so the earlier artifact isn't reread as
evidence.

## Verdict

**The takeoff residual is not vulnerability-shaped.** Across the whole
declared envelope the burn moves hard with α — +130 to +1668 median
onsets per seed, takeoff-seed share 0.80–0.95 → 1.00 — and the analytic
check shows the move is fully accounted for by marginal
survivor-conversion. But no α in [0.05, 2.0] at Θ = 2.37e11 lands a
clause-compatible cell on any class: the record hull overshoots ~10×
even at the heaviest defensible tail, and the timing half of the clause
fails identically (before_share 0.42–0.98 vs 0.173). **α is therefore
not an admissible handle on the ~197 residual — the clause remains
mechanism-shaped** (cohorting / persistent-partner / exposure
structure), and the takeoff record gives no purchase on α's value.

On dimensionality: because α moves burn mass ~×1.2–3 (and ignition
share) at fixed Θ, the admissible Θ band *does* shift with α — a 2-D
(Θ, α) sweep is strictly required only if α's envelope is propagated
as declared uncertainty. The takeoff clause itself cannot select α
(every α fails it equally at fixed Θ), so no fitted 2-D readout is
licensed; carrying α's declared width through the next Θ sweep's
bands is the honest treatment.

Report-immediately triggers: **none fired.** (a) a sourced bound exists
(declared widest, graded interior); (b) no α endpoint flips any scored
output — all cells fail the clause identically, cov_theta stays the
sole L2; (c) analytic and measured A/B agree to ~2% on every applicable
pair after the check-denominator correction — no instrument defect.

## Caveats

- **Family stand-in:** beta(α,β) cannot express Miura 2023's measured
  bimodality — the [0.05, 2.0] envelope maps shape within the
  beta-Poisson family only; a mixture law could admit tails outside it.
- **Non-applicable pairs (25/80):** where the lo arm stayed extinct or
  weak its survivor field cannot represent the shared trajectory —
  ignition differences dominate there, so the analytic check is
  structurally silent on those pairs rather than negative.
- **Check-denominator fix on this PR:** the merged `_cross_check`
  compared predicted survivor-conversions to the mate's total burn and
  flagged >2× everywhere; the corrected check (predicted vs measured
  tail-move, applicability-gated) agrees ~1.00. The earlier flag was an
  artifact of check design, not the instrument.
- **Extinct draws are data:** the lo arms' 3–4 extinct seeds per class
  are genuine ignition failures of the heavy-tailed draw (P(ignite)
  falls with α), included as zeros in the takeoff distributions.
- **Compute path:** the array ran on `picard-analysis-fargate-queue`
  (Fargate jobdef `picard-covid-vuln-ab-fargate:1`, digest-pinned image
  at 6669b11e) after EC2 Spot (>9 h, 0 vCPU) and EC2 on-demand (~30 min,
  0 instances) both starved — same image/digest throughout; compute
  substrate does not enter the draws.
