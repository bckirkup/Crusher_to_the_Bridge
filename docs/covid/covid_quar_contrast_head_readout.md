# QUAR-CONTRAST-01 — does the −66% pool-transport contrast survive at HEAD?

> **Status:** Findings (2026-11-01). The settled QUAR-ATTR-V2 verdict under test:
> at commit `d62f10d`, Θ 1e9, the frozen criterion called cross-zone pathogen
> pool transport load-bearing — A0_declared vs A2_pool_transport_off,
> conditional median 348.5 → 119, −66%, n = 8 shared takeoffs. QUAR-CONTAMX-01
> then measured the settled A0 cell stale at HEAD (native parity lane not
> byte-identical on any of four parity seeds). This readout re-runs BOTH arms
> of the contrast at HEAD, under both transport engines, and answers one
> question: **does the confinement-leak anchor survive the drift?**

## Cell declaration

- Cells: `A0_declared` and `A2_pool_transport_off` at Θ 1e9 on
  `diamond_princess_2020` (platform `mega_cruise_5000`), seeds
  20200205–20200224 — 20 cells per (arm, engine) lane, 80 cells total.
- Lanes: `hvac.transport_engine: native` (primary — the engine the settled
  campaign ran implicitly, since `native` is the shipped default) and
  `contamx` (parity — keeps the contrast solver-clean the way
  QUAR-CONTAMX-01 scoped it).
- Runner: `tools/covid_attribution_arm_smoke.py --theta 1e9 --num-epochs 0`
  per seed — `--num-epochs 0` resolves to the declared 35-day voyage
  (840 epochs), matching the settled campaign cells; the 432-epoch smoke
  default would truncate the day-16–30 SOP-017 window. Local only, on this
  box, at `main` = `668fe379`.
- Scorer: `tools/covid_quar_head_contrast.py`, which applies the design's
  frozen attribution criterion verbatim: takeoff is `recorded_onsets >= 10`;
  (i) is the all-20-seed median of `infections_during_quarantine`; (ii) is
  the median over seeds that took off in BOTH arms; load-bearing needs
  (ii) ≤ −50% with (i) also falling; non-load-bearing is |shift| < 20%;
  indeterminate between.

## Engine identity

Each payload carries the `transport_engine` block written at build time.
The native lane must show `ContamTransportEngine` (2258 airflow paths,
~2.94M m³/h) and the contamx lane `ContamXTransportEngine` (2182 paths,
~3.07M m³/h) in every cell — an unresolvable ContamX request falls back to
native silently, so the engine class and path counts are the honest witness,
not the config echo.

| lane | arm | engine_class | n_paths | total_flow_m3h |
|---|---|---|---|---|
| native | A0_declared | ContamTransportEngine | 2258 | 2939775.0 |
| native | A2_pool_transport_off | ContamTransportEngine | 2258 | 2939775.0 |
| contamx | A0_declared | ContamXTransportEngine | 2182 | 3066202.529 |
| contamx | A2_pool_transport_off | ContamXTransportEngine | 2182 | 3066202.529 |

All 80 payloads carry the block; `requested` and `config_transport_engine`
match the lane on every cell (verified per-payload, not per-sample).

## The contrast at HEAD vs settled

| lane | takeoff A0 | takeoff A2 | med(i) A0 | med(i) A2 | n both | med(ii) A0 | med(ii) A2 | shift | band |
|---|---|---|---|---|---|---|---|---|---|
| settled `d62f10d` | 12/20 | 9/20 | 71.5 | 1.0 | 8 | 348.5 | 119 | −66% | load-bearing |
| native @ HEAD | 19/20 | 19/20 | 567.5 | 595.0 | 19 | 573.0 | 607.0 | **+5.9%** | non_load_bearing_shift |
| contamx @ HEAD | 19/20 | 19/20 | 537.0 | 595.0 | 19 | 542.0 | 607.0 | **+12.0%** | non_load_bearing_shift |

**Answer: no — the −66% pool-transport contrast does not survive at HEAD.**
On the frozen criterion, disabling cross-zone pool transport at `668fe379`
*raises* the during-quarantine conditional median by ~6% (native) and ~12%
(contamx) instead of cutting it by two-thirds. Both frozen clauses fail —
(ii) is not ≤ −50%, and (i) rises rather than falls — so the band is
`non_load_bearing_shift` under both solvers. The collapse is solver-clean:
the parity lane shows the same dead contrast, so this is a property of the
model at HEAD, not of the airflow solver.

## Engine parity on paired seeds

Median paired delta of `infections_during_quarantine`, contamx − native,
per arm (n = 20 shared seeds each):

- A0_declared: **−3.0** (17/20 seeds differ) — engines agree within seed
  noise, matching QUAR-CONTAMX-01's −1.35% on the same arm.
- A2_pool_transport_off: **0.0** (19/20 seeds bit-identical) — expected and
  internally consistent: the arm excises exactly the cross-zone airflow
  pathway the two solvers differ on, so both engines collapse onto the same
  remaining transport model. The one differing seed (20200208: 139 vs 141)
  shows a residual hvac-mediated path survives the arm.

## Interpretation

Measured (commit `668fe379`, seeds 20200205–20200224, 80 cells):

- The contrast is dead: +5.9% (native) / +12.0% (contamx) vs the settled
  −65.9%, band `non_load_bearing_shift` on both engines.
- The whole during-quarantine surface moved with it: A0 all-seed median
  71.5 → 567.5 (native), takeoff 12/20 → 19/20 in both arms — consistent
  with the stale-surface drift QUAR-CONTAMX-01 already flagged on A0.
- At HEAD the during-quarantine infections are overwhelmingly `droplet`
  (~90%) + `caregiver` (~9%) by route attribution; the pool route
  contributes ~0 recorded infections in EITHER arm — the channel the
  −66% was carried on no longer loads the window in this regime.
- The A2 arm still expresses: outcomes move per seed and its bit-identity
  vs contamx on 19/20 seeds proves the override reaches the engine — this
  is not an expressibility no-op.

Inferred (consistent with, not proven by, this measurement):

- The outbreak regime at HEAD is larger and droplet/caregiver-dominated; in
  that regime pool transport has no load to bear. The anchor did not flip
  sign — it eroded toward ~zero.

Hypothesis (needs the drift campaign to adjudicate):

- Whether the pool mechanism itself still forms and is merely swamped by
  the larger droplet-dominated outbreak, or the mechanism broke over the
  ~573 merges, cannot be settled by this contrast. Which merge(s) moved
  the surface is the separate drift-attribution campaign.

## Caveats

- Local lanes only; the surface CSV is the committed evidence (`results/`
  payloads are gitignored).
- The arm contrast controls host frailty draws and initial conditions but
  NOT the RNG stream: per-seed differences may not be quoted as a channel
  effect; only the distributional shift over the 20 seeds may be (the
  design's own `why_not_per_seed` clause).
- This measures whether the contrast survives drift; it does not attribute
  which merge(s) moved the surface (a separate campaign, as flagged in
  QUAR-CONTAMX-01).

## Surface

Per-(engine, arm, seed) rows: `docs/covid/covid_quar_contrast_head_surface.csv`
(80 rows: the settled columns plus `engine_lane` and the engine-identity
fields). Machine summary: `results/quar_head/final_scores.json`
(not committed — `results/` is gitignored).
