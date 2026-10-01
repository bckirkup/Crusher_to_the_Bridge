# FRAILTY-V1
**Date:** 2026-10-01
**Commit:** c950e57
**Pathogens:** sars_cov2_resp
**Status:** declared

The last named class of the SUSCEPT-V1 surviving set: continuous
susceptibility heterogeneity — a declared per-host frailty multiplier on
the infection hazard, where SUSCEPT-V1's retired axes were a binary
immune fraction (measured incapable: IMM75 reaches the band only at the
0.75 corner and fails the count and timing legs) and a beta-shape retune
of the shipped mixing variable. CONSENSUS-50 declined partial-protection
immunity as unsourced, so no protection fraction exists to fit — every
parameter here is a declared corner, swept, never fitted.

Mechanism: hazard `1 - exp(-s_i · f_i · d)` with `s_i` the shipped beta
susceptibility draw and `f_i` a second, orthogonal mixing variable drawn
per challenged host on a dedicated stream, mean pinned exactly 1.0 —
gamma `shape = 1/cv², scale = cv²`; lognormal `σ² = ln(1+cv²),
μ = -σ²/2`. `E[challenge]` is untouched; only dispersion is declared.
The hyper-frail burn early and the surviving susceptible pool thins over
the voyage — the one mechanism in the surviving set that can move count
and timing in opposite directions.

Engine surface (this change): `dose_response.frailty
{enabled, distribution: gamma|lognormal, cv ≥ 0}` resolved at init
(spec-lands), drawn lazily on first challenge into
`agent.frailty_multiplier`, applied at both hazard sites
(`_dose_response_hazard`, `_cooperative_hazard`), echoed as
`payload.frailty_draw` quantiles. Draws run on
`SeedSequence(entropy, spawn_key=(0x5F1A17,))` — the run seed's own
material at a fixed spawn-tree address; no shared-stream draw and no
order-indexed `.spawn()` slot is touched, so the frailty-off arm is
bit-identical by construction and the cv-0 inert corner is an exact
binding audit. Arm grammar: `hazard_frailty {distribution, cv}` →
`pathogen_overrides.dose_response.frailty`. Absent or disabled is the
shipped behaviour.

Canary (the whole design — no array beyond it): anchor Θ 2.37e11,
declared replay, age 6.8, 1 import, 7 arms × 20 seeds @20200205 = 140
cells. Arms: `D0_declared` (shipped baseline, paired control and
cross-image drift check vs SUSCEPT-V1's measured D0), `FRAIL_INERT`
(cv 0 → multiplier identically 1.0; per-seed bit-identity vs D0),
`FRAIL_G05/G10/G20` (gamma cv 0.5/1.0/2.0 ladder), `FRAIL_L10/L20`
(lognormal at matched cv — the family contrast). Design
`picard_framework/runs/covid_frailty_v1_design.json`; readout
`tools/covid_frailty_v1_readout.py` (frozen audit incl. the inert
bit-identity block, both-legs test, day-16 kink discriminator,
seed-paired deltas vs D0).

Frozen criteria (committed before any cell ran): T1 197 recorded
onsets in q05–q95 AND takeoff-median before_share within 0.173±0.10;
H5 infections_total band [712, 960] median-in-band; ≥5 takeoff seeds
per row; frailty echo/quantile audit per cell; FRAIL_INERT per-seed
exact identity vs D0.
