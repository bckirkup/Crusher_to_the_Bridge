# COVID-THETA-V14
**Date:** 2026-10-02
**Commit:** 02740187
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 02740187

Declared before any v14 cell ran. Re-admission of the admissible Θ band
under the rebuilt hand line: NORO-HAND-PRACTICE-01 (PR #804, merged
`d0466064`) gave the reservoir practice variability + drying, and
NORO-HAND-CARRIAGE-01 (PR #811, merged `1c94de2d`) added the
wash-resistant protected compartment + own-environment pool with
`hygiene_cycle` shipped default-ON throughout — so the THETA-SCREEN-V13
admissible set {1.78e11..5.62e11}, admitted under the pre-repair hand
line on image `covid-theta-v13-edb7fc41`, is stale. This stage re-runs
the v13 stage-1 lattice on the current default mechanism: same 9-point
eighth-decade lattice, same seeds (base 20201001, 200 generic
168-epoch voyages per Θ), same frozen selectors, same interior-only
admissibility rule.

COVID-HAND-AB-01 (`docs/ledger/COVID-HAND-AB-01.md`) measured the arm
contrast as `hand_line_replay_neutral` at Θ 2.37e11: all arms burn
~96%, fomite = 0 during-quarantine acquisitions on all 60 cells, and
wash_reuptake ≡ spike_decay byte-identically on the COVID seeds, so
the per-Θ arm pairing the design still carries sees nothing on this
scenario. Stage 1 therefore ran single-arm `hygiene_cycle` only —
1,800 cells (the hygiene_cycle half of the verbatim 3,600), executed
as nine 200-child Batch arrays at INDEX_OFFSET {0,400,…,3200} on
jobdef `picard-covid-boarding-screen:44` (digest-pinned image
`picard-campaign:covid-theta-v14-02740187`, `sha256:b5280c72…`; rev
44 also carries the `--index-offset` command arg rev 43 lacked).
Prefix `campaign/covid_theta_screen_v14/02740187/`; the 2-cell canary
(`a27e884c-2bb6-433a-9c8e-b65b5d1e109e`, θ3.16e11 hygiene_cycle seeds
20201001-2) was inspected before the arrays: drawn incubation, no
declared onset/departure day, no ascertainment gate,
`hand_reservoir_mode = hygiene_cycle`, non-degenerate onsets (110, 23).

Measured 1,800/1,800 cells, zero audit failures, zero child failures.
Verdict: **the admissible band slides one lattice notch down to
{1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11}** vs v13's
{1.78e11..5.62e11} — 1.33e11 lifts off the floor (median recorded
attack 0.00054 vs 0.00027) and 5.62e11 tips over the ceiling (0.00808
vs 0.00781). Window edges: lower ∈ (1e11, 1.33e11], upper ∈ [4.22e11,
5.62e11). The signature is mild and broad — mid-band recorded medians
rise ~1.2–1.6× (largest at 2.37e11), the top tail trims, takeoff
probability rises ~0.02–0.05 at every Θ — while seed-paired per-seed
median deltas sit at 0.0 everywhere against v13 and no row shows a
suppression-shaped delta or a design report-immediately trigger.
Consistent with COVID-HAND-AB-01's `hand_line_replay_neutral` read at
Θ 2.37e11: the repaired hand line adds dose on the fomite path it
exercises, enough to re-lattice the window by one step at each edge.

Readout `tools/covid_theta_v14_readout.py`; surface
`docs/covid/covid_theta_screen_v14_surface.csv`; seed-paired deltas vs
v13 `docs/covid/covid_theta_screen_v14_pairs.csv`; narrative
`docs/covid/covid_theta_screen_v14_readout.md`. Stage 2 (declared
replay at the admissible points + nearest failing flanks {1e11,
5.62e11} + the Θ1e9 QUAR-ATTR-V2 anchor) is eligible under the frozen
rule and stays gated on this verdict.
