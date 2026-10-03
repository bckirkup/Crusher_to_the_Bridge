# PROPENSITY-V1 readout — the DP-replay clause canary at the Θ1e9 anchor: measured dead, and the anchor's recorded pass is void on drift

> **Status:** Findings (2026-10-03). Canary measured at `e0d43979`
> (image `picard-campaign@sha256:d6e27cd9…` / tag `campaign-e0d43979`,
> jobdef `picard-covid-boarding-screen:47`, queue `picard-analysis-queue`,
> prefix `campaign/covid_propensity_v1/e0d43979/cells/`).

PROPENSITY-V1 (PR #860, ledger `docs/ledger/PROPENSITY-V1.md`, spec
`docs/propensity_v1_spec.md`) is the fourth early-COVID failure mode —
persistent per-party contact-propensity heterogeneity, the
Britton/Ball–Trapman term the i.i.d. participation deal erases. This
canary asks the clause question only: does party-mode propensity move the
Diamond Princess replay onto the record at the one Θ that has ever
passed the clause?

Design `picard_framework/runs/covid_propensity_v1_design.json` (PR #865):
`{D0_declared (shipped party mode), PROP_OFF} × Θ1e9 × 20 seeds` at the
`diamond_princess_2020` replay contract — takeoff-seed conditioning,
index_onset_day −1.0, departure_epoch 120, seed base 20200205, identical
rows to v15 stage 2. The clause is frozen verbatim in the design's
`admissibility` block before any cell ran: takeoff-seed q05–q95 of
recorded_onsets ∋ 197 AND takeoff-seed median before_share within 0.10
of 0.173, scored only at ≥5 takeoff seeds. `PROP_OFF` writes
`config_overrides.rhythm.participation_propensity.mode = off` through the
new `participation_propensity` arm key — the bit-identical baseline under
the merged tree.

Campaign gate executed: design PR merged `e0d43979` → image built at the
merged SHA → digest-pinned jobdef (`:47`) → 2-cell canary array
(`0f8e5d3d`, D0 seeds 20200205+20200206) inspected → 38-cell array
(`83109e6f`, INDEX_OFFSET 2). All 40/40 cells SUCCEEDED, zero retries,
zero audit failures; ~65 min wall on On-Demand.

## Clause scorecard (per arm, takeoff-conditional)

| arm | takeoff | rec q05/med/q95 | before_share med [q05,q95] | clause |
|-----|--------:|------------------|---------------------------|--------|
| D0_declared (party on) | 19/20 | 1,518 / 2,321 / 2,445 | 0.452 [0.234, 0.900] | FAIL both legs |
| PROP_OFF | 20/20 | 1,190 / 2,343 / 2,443 | 0.397 [0.213, 0.649] | FAIL both legs |

`mass_near_t1` = 0 on both arms — no takeoff seed lands within
[98.5, 394] of the record. No report-immediately trigger fired
(`telemetry_buffer/covid_propensity_v1_readout.json`,
`tools/covid_propensity_v1_readout.py`).

## The mechanism exercised, and its footprint is seed noise

| witness | D0_declared | PROP_OFF |
|---------|-------------|----------|
| `participation_propensity.mode` resolved | `party` (40/40 echo) | `off` (20/20 echo) |
| `propensity_draw.units_drawn` med | 2,089 (per-party units) | **0 on all 20 cells** |
| multiplier q05/med/q95 med | 0.25 / 0.78 / 2.47 | — (never dealt) |

The off arm's zero units on every cell is the bit-identity witness; the
on arm dealt ~2,089 party multipliers per voyage spanning a 10×
q05–q95 range — heterogeneity genuinely in play.

Seed-paired deltas (PROP_OFF − D0, n = 19 takeoff pairs): recorded
onsets med **+12** [−923, +657]; infections_total med −23 [−1164, +857];
before_share med −0.047 [−0.49, +0.17]. Symmetric around zero — removing
propensity does not systematically move the burn in either direction.
(All-seed D0 − OFF deltas: −14 median onsets, [−1420, +1010].)

## The anchor itself drifted: the v15 pass is void at `e0d43979`

Seed-paired against the v15 stage-2 anchor row (`6efec855`,
`campaign/covid_theta_screen_v15_stage2/6efec855/cells/`, arm
`once_per_course`):

| pairing | Δ recorded med [range] | takeoff |
|---------|------------------------|---------|
| PROP_OFF − v15 | **+1,634** [−1206, +2443] | 20/20 vs 10/20 |
| D0 − v15 | +1,785 [−878, +2445] | 19/20 vs 10/20 |

v15's clause pass at anchor ran on its q05 = 153 — the low tail of a
half-fizzled row. Under the merged tree that tail is gone: PROP_OFF
(propensity never dealt) takes off 20/20 with q05 = 1,190, so the drift
is **not** propensity — it is engine movement between `6efec855` and
`e0d43979` (the caregiver-role block default-ON since
NORO-CAREGIVER-01's merge is the largest intervening mechanism change;
per-seed, the takeoff seeds that v15 fizzled now run full burns).
v15's recorded anchor PASS is therefore historical at its own
`Measured at` SHA; the clause's only ever-passing cell does not exist
on the current engine.

## Per-seed evidence (recorded onsets / before_share)

| seed | v15 `6efec855` (once_per_course) | D0_declared (party) | PROP_OFF |
|------|------|------|------|
| 20200205 | 2,223 / 0.910 | 2,365 / 0.574 | 2,360 / 0.428 |
| 20200206 | 0 | 1,963 / 0.234 | 2,443 / 0.425 |
| 20200207 | 153 / 0.013 | 2,488 / 0.900 | 2,340 / 0.406 |
| 20200208 | 2,438 / 0.916 | 2,395 / 0.934 | 2,401 / 0.935 |
| 20200209 | 0 | 2,133 / 0.316 | 2,295 / 0.380 |
| 20200210 | 0 | 2,251 / 0.291 | 1,241 / 0.225 |
| 20200211 | 575 / 0.016 | 2,256 / 0.406 | 2,320 / 0.386 |
| 20200212 | 502 / 0.012 | 2,391 / 0.562 | 1,777 / 0.272 |
| 20200213 | 2,396 / 0.310 | 1,518 / 0.216 | 1,190 / 0.241 |
| 20200214 | 1 | 1,961 / 0.286 | 2,349 / 0.450 |
| 20200215 | 0 | 2,445 / 0.715 | 1,522 / 0.213 |
| 20200216 | 2,413 / 0.466 | 2,112 / 0.298 | 1,326 / 0.236 |
| 20200217 | 0 | 0 (fizzle) | 661 / 0.005 |
| 20200218 | 0 | 946 / 0.265 | 2,366 / 0.352 |
| 20200219 | 2,417 / 0.454 | 2,406 / 0.788 | 2,446 / 0.649 |
| 20200220 | 0 | 2,398 / 0.600 | 2,410 / 0.527 |
| 20200221 | 0 | 2,401 / 0.618 | 2,418 / 0.572 |
| 20200222 | 449 / 0.004 | 1,682 / 0.273 | 2,339 / 0.330 |
| 20200223 | 0 | 2,416 / 0.616 | 2,343 / 0.397 |
| 20200224 | 1,882 / 0.090 | 2,321 / 0.452 | 2,411 / 0.624 |

The takeoff floor that carried the v15 pass (its q05 = 153 and the ten
fizzled seeds) is the quantity the merged tree no longer produces.

## Verdict

Measured: at the Θ1e9 anchor, `mode: party` fails the clause on both
legs by ~10× mass and ~0.28 share, and its seed-paired footprint against
the bit-identical off arm is statistically indistinguishable from zero.
The fourth early-COVID failure mode — persistent participation
heterogeneity — is dead at anchor under the current engine, joining
RING-CAP-V1, SUSCPOOL-V1, the frailties, and suppression.

Inferred (not measured): at the admissible band the clause fails by the
same ~10× with share medians 0.73–0.96, and propensity shows no
systematic move even where it had its best case — a band array is very
unlikely to rescue the clause, but that is the user's call on whether
the measurement is worth the wall clock.

Open decision for the user: run PROPENSITY-V1 across the admissible band
(5 Θ × 2 arms × 20 seeds), or accept the anchor canary as the
measurement of record and retire the hypothesis.
