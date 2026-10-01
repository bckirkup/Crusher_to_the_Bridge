# FRAILTY-V1
**Date:** 2026-10-01
**Commit:** c950e57
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c950e57

The last named class of the SUSCEPT-V1 surviving set — continuous
susceptibility heterogeneity as a declared per-host frailty multiplier
on the infection hazard — is **measured incapable at every declared
corner**: `frailty_structure_incapable`.

Mechanism (engine surface, default OFF): `dose_response.frailty
{enabled, distribution: gamma|lognormal, cv ≥ 0}` resolved at init,
drawn lazily per challenged host into `agent.frailty_multiplier` on a
dedicated `SeedSequence` spawn-key stream, applied at both hazard sites
as `1 - exp(-s_i · f_i · d)`. Both families are mean pinned exactly
1.0 — E[challenge] untouched, only dispersion declared. Arm grammar:
`hazard_frailty {distribution, cv}` → `pathogen_overrides`
`.dose_response.frailty`; payloads echo `frailty_draw` quantiles.

Canary (the whole design — no array beyond it): anchor Θ 2.37e11,
declared replay, 7 arms × 20 seeds @20200205 = **140/140 cells, zero
child failures** (Batch array `6865fef9-4991-488d-afaa-123aae8bac67`,
job-def `picard-covid-boarding-screen` rev 40, image digest
`sha256:56536971…`, S3 `campaign/covid_frailty_v1/c950e57/cells/`).
Readout `tools/covid_frailty_v1_readout.py`, full projection at
`campaign_results/covid_frailty_v1/readout_full.json` (local; S3 is the
durable cell store).

**Structure audit: clean.** `FRAIL_INERT` is bit-identical to D0 on
all 20 seeds (max |Δ| = 0.0 on recorded_onsets, infections_total,
before_share — every payload field). Armed cells echo the declared
block and draw: `frailty_draw.n` ≈ 3,710 challenged hosts/cell, mean
0.99–1.01, spread q95−q05 rising with cv (1.6 → 4.8). One audit flag
(`FRAIL_G20` s20200217, draw-mean 1.494 vs band ±0.3): that seed is an
extinction — only 44 hosts ever challenged, and at cv 2 the gamma draw
has SE(mean) ≈ 0.30 at n = 44, so 1.49 is ~1.6σ of expected sampling
scatter, not a pinning defect; every high-n cell sits at mean ≈ 1.00.
E[F] = 1 is by construction; the band reads the finite-sample echo.

**D0 drift check.** Truth leg reproduces the 2e12ccf1 measurement
(infections med 3,567 vs 3,558; takeoff 18/20). The observation channel
drifted upward across the intervening merges (recorded med 3,413 vs
3,008; before_share 0.742 vs 0.606 — `hygiene_cycle` shipped default-ON
in PR #804 changes route mix and onset timing): reported as engine
drift, not a defect — all arm contrasts below are same-image
seed-paired.

**Legs (takeoff-seed medians, all 20-seed rows, takeoff n ≥ 15):**

| arm | rec med | inf med | bshr med | dur med | kink | paired Δinf | paired Δrec |
|-----|---------|---------|----------|---------|------|-------------|-------------|
| D0 | 3,413 | 3,567 | 0.742 | 93 | 0.120 | — | — |
| G05 (γ cv0.5) | 3,495 | 3,561 | 0.888 | 46 | 0.133 | −3 [−21,+59] | −25 [−88,+70] |
| G10 (γ cv1) | 3,378 | 3,534 | 0.774 | 86 | 0.157 | −34 [−70,+231] | −42 [−148,+319] |
| G20 (γ cv2) | 3,193 | 3,373 | 0.824 | 154 | 0.169 | −197 [−420,+849] | −178 [−456,+716] |
| L10 (ln cv1) | 3,462 | 3,555 | 0.771 | 83 | 0.117 | −9 [−33,+430] | −11 [−117,+533] |
| L20 (ln cv2) | 3,392 | 3,525 | 0.712 | 129 | 0.163 | −39 [−253,+277] | −38 [−281,+247] |

Truth leg: no arm lands the [712, 960] band — every median sits
3,373–3,561, ≥ 3.5× the band ceiling. Timing leg: no arm approaches
0.173 (bshr 0.71–0.89 vs D0 0.742 — overlapping noise). Count leg: no
arm approaches 197. Shape: kink 0.117–0.169 vs baseline 0.120 —
smooth curves everywhere, no kinked landing.

The mechanism's signature *is* visible at cv 2 — count leans negative
(Δinf med −197) and acquisitions push later (dur 154 vs 93) — the
frail tail burns early and the surviving pool is hardened, exactly as
designed. But the magnitude is ~5% of the needed suppression and sits
inside the 20-seed spread (Δinf q95 +849). Structural reason: at Θ
2.37e11 every host's delivered dose sits decades above the hazard
kink, so a mean-pinned multiplier f ∈ [0.06, 3.7] reshuffles hazard
*within* the saturating regime — it cannot put any host below the
kink. Only removal (SUSCEPT-V1's sterile fraction — measured
incapable) can thin that pool.

**Verdict: `frailty_structure_incapable`.** No declared
continuous-frailty corner moves the truth and timing legs together;
no follow-on corner is named. With COMBINED-V1 declined and every
grammar-expressible class now measured-retired (dose law, Θ,
ascertainment, seed geometry, susceptibility structure, delivery
machinery, scheduled suppression, frailty dispersion), the residual
needs a mechanism the grammar has not yet named.

Design `picard_framework/runs/covid_frailty_v1_design.json`; PR #809
(arm + grammar + frozen criteria) merged at `8b20aea2`.
