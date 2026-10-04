# THETA-REFIT-01 readout — quarter-decade Θ lattice under shipped defaults: NO-ADMISSIBLE (residual is mechanism-shaped)

> **Status:** Findings (2026-10-04). Campaign measured at `78f52a58`
> (image `picard-campaign@sha256:a6797429…` / tag
> `campaign-e0d43979-refit`, jobdef `picard-covid-boarding-screen:50`,
> queue `picard-analysis-queue`, prefix
> `campaign/covid_theta_refit_v1/78f52a58/cells/`).

CAREGIVER-ATTR-01 (`docs/ledger/CAREGIVER-ATTR-01.md`) settled that the
Θ1e9 anchor drift is the CAREGIVER-V1 channel: the clause passes only on
the `caregiver.mode: off` tree. The mechanism ships default-ON by
standing rule, so the anchored Θ had to be refit on the shipped-default
tree rather than read off the off-tree surface. This campaign is that
refit: the DP replay clause scored at nine quarter-decade Θ rows, all
under shipped defaults.

Design `picard_framework/runs/covid_theta_refit_v1_design.json`
(PR #876): 9 Θ rows on the quarter-decade lattice
{1e7, 1.78e7, 3.16e7, 5.62e7, 1e8, 1.78e8, 3.16e8, 5.62e8, 1e9} × 20
seeds = 180 cells, single `D0_declared` arm (empty overrides — shipped
defaults, caregiver ON) at the verbatim `diamond_princess_2020` replay
contract (`onset_day −1.0`, `departure_day 5.0`, `imports 1`,
seed_base `20200205`). The v11-lineage conditional clause and the
four-branch verdict grammar (LOCATED / STRADDLE / NO-ADMISSIBLE /
BOUNDARY-HIT) were frozen in the design's `admissibility` block before
any cell ran. The Θ1e9 row doubles as the engine-integrity witness: it
must bit-match the CAREGIVER-ATTR-01 `D0_declared` row, since
`e0d43979..78f52a58` touches no engine code.

Campaign gate executed: design merged `78f52a58` → thin overlay image on
the attribution stack (`FROM picard-campaign:campaign-e0d43979`, engine
unchanged, verified by bit-identity below) → digest-pinned jobdef rev 50
(new rev because rev 12's command silently dropped `index_offset`) →
20-cell canary (`eb4ad8bd`, indices 160–179 = the Θ1e9 row) inspected →
160-cell array (`2a40880f`, indices 0–159). 180/180 cells SUCCEEDED,
zero audit failures — `caregiver.mode` echoes `on`, propensity mode
`party`, `units_drawn` > 0, index geometry and design echoes on every
cell.

## Clause scorecard (per row, takeoff-conditional)

| Θ | takeoff | rec q05/med/q95 | before_share med [q05,q95] | count leg | timing leg | clause |
|--:|--------:|------------------|---------------------------|:---------:|:----------:|:------:|
| 1e7 | 19/20 | 523 / 704 / 2,037 | 0.097 [0.03, 0.31] | FAIL | pass | FAIL |
| 1.78e7 | 19/20 | 631 / 793 / 1,619 | 0.135 [0.05, 0.28] | FAIL | pass | FAIL |
| 3.16e7 | 19/20 | 674 / 931 / 2,181 | 0.146 [0.11, 0.70] | FAIL | pass | FAIL |
| 5.62e7 | 19/20 | 661 / 867 / 2,275 | 0.141 [0.06, 0.57] | FAIL | pass | FAIL |
| 1e8 | 19/20 | 886 / 1,842 / 2,242 | 0.219 [0.12, 0.55] | FAIL | pass | FAIL |
| 1.78e8 | 19/20 | 830 / 1,495 / 2,241 | 0.255 [0.16, 0.54] | FAIL | pass | FAIL |
| 3.16e8 | 19/20 | 1,121 / 1,688 / 2,424 | 0.287 [0.16, 0.65] | FAIL | FAIL | FAIL |
| 5.62e8 | 19/20 | 1,638 / 2,137 / 2,410 | 0.279 [0.20, 0.74] | FAIL | FAIL | FAIL |
| 1e9 | 19/20 | 1,518 / 2,321 / 2,445 | 0.452 [0.23, 0.90] | FAIL | FAIL | FAIL |

Reference rows (all takeoff-conditional): v15 anchor `once_per_course`
at `6efec855` — 10/20, q05 153, PASS (recorded); CG_OFF at `b932d0e9` —
11/20, q05 10, band ∋197, share 0.200, PASS.

Every row scored (19/20 takeoff seeds ≥ the 5-seed gate). `mass_near_t1`
= 0 on all nine rows — no takeoff seed anywhere on the lattice records
in [98.5, 394]. TIMING-IN-BAND fired on the six rows at Θ ≤ 1.78e8
(`telemetry_buffer/covid_theta_refit_v1_readout.json`,
`tools/covid_theta_refit_v1_readout.py`).

## The mechanism exercised

| witness | value |
|---------|-------|
| `delivery.caregiver.mode` resolved | `on` — 180/180 echo |
| `participation_propensity.mode` | `party` — 180/180 |
| `propensity_draw.units_drawn` med | 2,089 [2,085, 2,099] on every row |
| caregiver route, pooled aboard_window | 141 / 160 / 170 / 177 / 180 / 196 / 212 / 211 / 248 (monotone in Θ) |
| caregiver route, pooled during_quarantine | 0 on every row |

The Θ1e9 row is bit-identical to the CAREGIVER-ATTR-01 `D0_declared`
row on all 19 takeoff pairs (Δ recorded med +0 [+0, +0], Δ share +0.000)
— the overlay image runs exactly the attribution generation's engine,
so every number below is attributable to Θ alone.

## The verdict: NO-ADMISSIBLE

Per the frozen grammar, branch (c): every row — interior and boundary —
fails the count leg on the **same side**, monotone overshoot persisting
through the 1e7 floor. No straddle exists to refine: every row's takeoff
distribution sits entirely above the record (q05 ≥ 523 > 197); there is
no lower row sitting below it. The residual is mechanism-shaped, not
Θ-shaped.

The shape of the floor: recorded-onsets medians run 704 / 793 / 931 /
867 across the bottom four rows — a ~700–930 plateau that barely
responds to a full decade of Θ detuning — then rise to 2,321 at Θ1e9.
Even at the lattice floor the q05 (523) sits 2.7× above the 197 record.
The witness columns say why: the caregiver route delivers 141–248 pooled
aboard-window infections at every Θ (monotone in Θ but never zero —
caregiving contacts are attendance-bounded, not density-detuned), while
during-quarantine caregiver is 0 everywhere — the mechanism acts in the
pre-quarantine window and sets a takeoff-floor the clause's count leg
cannot undercut at any reachable Θ.

Seed-paired deltas on takeoff pairs (n / Δ recorded med [q05, q95] /
Δ before_share med):

| refit row | vs v15 anchor (n=10) | vs D0_declared @b932d0e9 (n=19) | vs CG_OFF (n=11) |
|--:|----------------------|-------------------------------|------------------|
| 1e7 | −308 [−1,921, +823] / −0.229 | −1,497 [−1,768, −265] / −0.320 | −296 [−1,918, +966] / −0.068 |
| 1.78e7 | −604 [−1,718, +690] / −0.215 | −1,359 [−1,746, −236] / −0.283 | −517 [−1,750, +824] / −0.013 |
| 3.16e7 | −1,009 [−1,597, +778] / −0.191 | −1,211 [−1,677, −214] / −0.213 | −423 [−1,618, +921] / +0.047 |
| 5.62e7 | −142 [−1,531, +1,012] / +0.031 | −1,194 [−1,730, −131] / −0.222 | −673 [−1,563, +1,155] / −0.020 |
| 1e8 | −111 [−1,547, +2,011] / +0.019 | −345 [−1,246, +190] / −0.135 | −66 [−1,544, +2,154] / +0.082 |
| 1.78e8 | −295 [−1,551, +1,989] / −0.055 | −673 [−1,492, +559] / −0.144 | −235 [−1,583, +2,132] / +0.088 |
| 3.16e8 | +212 [−933, +1,975] / +0.006 | −309 [−1,135, +742] / −0.144 | +56 [−965, +2,138] / +0.091 |
| 5.62e8 | −7 [−685, +2,308] / +0.107 | −27 [−490, +421] / −0.064 | +535 [−717, +2,451] / +0.206 |
| 1e9 | +142 [−878, +2,335] / +0.268 | **+0 [+0, +0] / +0.000** (bit-identical) | +698 [−910, +2,478] / +0.329 |

The 1e9 pairings replicate the attribution readout exactly: refit-D0 −
CG_OFF = +698 onsets / +0.329 share is precisely the CAREGIVER-V1
fill-in measured at `b932d0e9`; refit-D0 − v15 = +142 with a band
straddling zero is the same statistically-indistinguishable surface the
attribution reported. Detuning Θ does slide the surface toward the
off-tree reference (Δ vs CG_OFF runs −673 at the floor to +698 at 1e9),
but the slide flattens at the ~700-median plateau — the caregiver
channel's floor, not a Θ effect.

## What this settles

There is no Θ on the admissible range that restores the DP clause under
shipped defaults. The question the design left open — adopt a located
anchor vs refine — is moot: no located anchor exists. What is now open
is the clause itself: under CAREGIVER-V1 the replay surface carries a
mechanism-shaped floor (pre-quarantine caregiver transmission) that the
v11 count band, written against the pre-caregiver engine, cannot reach.
Whether that floor is *correct* against the record — i.e., whether the
clause's 197 figure itself needs re-derivation under the mechanism, or
the mechanism's pre-quarantine delivery is over-strong — is the named
follow-up. Per standing rule the mechanism stays default-ON either way;
this entry changes no constants.

Run note: array `2a40880f` and canary `eb4ad8bd` both ran on
`picard-analysis-queue` (On-Demand EC2, scaled 0→176 vCPU); Fargate
fallback was not needed. Job IDs, image digest and jobdef rev are in the
header.
