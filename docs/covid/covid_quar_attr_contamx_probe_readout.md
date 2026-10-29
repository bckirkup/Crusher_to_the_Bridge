# QUAR-CONTAMX-01 — ContamX engine probe of a settled QUAR-ATTR-V2 cell

> **Status:** Findings (2026-10-28). One settled transport-sensitive covid cell
> re-run under `hvac.transport_engine: contamx` with identical seeds, local only.
> Question posed: does the settled verdict move when the transport solver is
> swapped? Answer: **the settled per-seed numbers move enormously, but the move
> is HEAD drift, not the solver** — on paired seeds the two engines move
> together. See below.

## Cell declaration

- Cell: `A0_declared` at Θ 1e9 on `diamond_princess_2020` (platform
  `mega_cruise_5000`), seeds 20200205–20200224 — 20 cells.
- Criteria (from the session prompt): (a) settled — its native verdict is
  recorded in `covid_quarantine_attribution_v2_surface.csv` at commit `d62f10d`
  (QUAR-ATTR-V2, 240 cells); (b) on `mega_cruise_5000`, which ships the
  committed ContamX `platform.prj`; (c) routed through pool-transport/airborne —
  `A0_declared` ships `pathogen_pool_transport = airflow`, the channel the
  solver difference touches, and is the baseline the −66% pool-transport verdict
  is differenced against.
- Runner: `tools/covid_attribution_arm_smoke.py`, the same per-cell machinery
  the campaign uses (its A0 note requires byte-for-byte reproduction of the v9
  cells), with the only delta `hvac.transport_engine: contamx`.
  `tools/covid_quar_attr_contamx_compare.py` reads the payloads and the settled
  surface side by side.

## Engine identity

Each payload records a `transport_engine` block written at build time:
`requested`, `config_transport_engine`, `engine_class`, `n_airflow_paths`,
`total_flow_m3h`, `max_path_flow_m3h`. This is required because an
unresolvable ContamX request falls back to native silently. On this box the
contamx lane built `ContamXTransportEngine` (2182 airflow paths, ~3.07M m³/h
total) in every cell; the native parity lane built `ContamTransportEngine`
(2258 paths, ~2.94M m³/h). The config echo alone would not prove the swap —
the engine class and path counts do.

## Headline

Two questions separate cleanly once a native-HEAD parity lane is run:

1. **Do the settled cell numbers move under `contamx`?** Yes, dramatically —
   but so do they under native at HEAD. The A0_declared @ Θ 1e9 cell's
   settled surface (commit `d62f10d`) does not reproduce at HEAD on the
   same runner, seeds, and config: the native parity lane is not
   byte-identical to the settled CSV on any of the four parity seeds
   (20200205, 20200206, 20200215, 20200220). That is the design's own
   invalidation clause — A0 "must reproduce the corresponding v9 cells
   byte-for-byte … a mismatch invalidates the run rather than becoming a
   finding" — so the settled-vs-probe comparison below measures
   **drift between `d62f10d` and HEAD**, not the solver swap.
2. **Does the transport-solver swap itself move the verdict?** No. On the
   four seeds run in both local lanes (20200205, 20200206, 20200215,
   20200220), ContamX and native agree to within a handful of infections
   per seed: median paired delta −5 on
   `infections_during_quarantine`, −2.5 on `infections_total`; identical
   takeoff sets; conditional-median shift −1.35% — inside the design's
   non-load-bearing band. See the paired table below.

## Settled vs probe (measures drift, not the engine)

| Measure | Settled `d62f10d` | Probe `contamx` @ HEAD |
|---|---|---|
| takeoffs (recorded_onsets ≥ 10) | 12/20 | 19/20 |
| all-seed median during-quarantine | 71.5 | 537.0 |
| conditional median during (shared takeoffs, n=12) | 829.5 | 526.5 |
| shift on shared takeoffs | — | −36.5% (design band: indeterminate) |

The takeoff *set* also moves: seven settled non-takeoff seeds take off
under the probe lane (20200206/07/09/10/11/13/15) and no settled takeoff
is lost — the single probe non-takeoff, 20200217, is a settled
non-takeoff too.

## Probe vs HEAD-native (measures the solver)

| seed | lane | infections_total | recorded_onsets | during-quarantine |
|---|---|---|---|---|
| 20200205 | native | 2077 | 1658 | 573 |
| 20200205 | contamx | 2093 | 1676 | 562 |
| 20200206 | native | 1505 | 1168 | 721 |
| 20200206 | contamx | 1503 | 1165 | 715 |
| 20200215 | native | 1522 | 1185 | 536 |
| 20200215 | contamx | 1518 | 1188 | 532 |
| 20200220 | native | 2619 | 2127 | 513 |
| 20200220 | contamx | 2616 | 2121 | 511 |

Median paired delta: −5 during-quarantine, −2.5 total infections, −1.35%
conditional-median shift → `non_load_bearing_shift`. (An earlier ad-hoc
contamx run of 20200205 reproduced during=562 exactly — the lane is
deterministic on this box.) The ContamX airflow
operator (2182 paths, ~3.07M m³/h vs native's 2258, ~2.94M) moves the
epidemic's outcome by less than the seed noise of the same seed —
expected: CONTAM-FLEET-01 already showed most of the fleet's
native-vs-ContamX dose gap is authoring, not solver, and on
`mega_cruise_5000` the committed prj and the native network agree
closely enough that the two transport operators deliver near-identical
dose.

## What the moved verdict is

The settled QUAR-ATTR-V2 cell is **stale at HEAD, independent of
solver**. ~573 merges landed between `d62f10d` and HEAD; the covid
anchor was already recorded as drifting (CAREGIVER-V1 measured as the
anchor-drift mover; PROPENSITY-V1 notes the v15 anchor pass void on
engine drift). Naming the commit(s) that moved the A0 surface is a
separate attribution campaign — reported here, not run.

The verdict attached to this cell — during-quarantine load-bearing mass
on the declared replay — therefore moves on two counts at HEAD: the
conditional median falls ~36.5% on shared takeoffs and the takeoff
probability rises 0.6 → 0.95. Whether the −66% pool-transport arm
contrast survives that drift is not answered by a single-arm probe;
re-running A2_pool_transport_off under the same machinery is the natural
follow-on cell.

## Caveats

- The probe lane was one arm (A0) of a six-arm design. The design's
  verdicts are arm *contrasts*; this probe measures whether the baseline
  cell's numbers move, which is what the prompt asked.
- Four-seed native parity and four-seed paired engine evidence are
  sparse by design (local-only, ~60 min/cell on a 2-CPU box); the
  consistent direction across all of them is what carries the claim.
- `results/` payloads are local-only (gitignored). The committed surface
  CSV carries every column the settled CSV does plus the engine-identity
  fields.

## Surface

Per-seed probe rows: `docs/covid/covid_quar_attr_contamx_probe_surface.csv`.
Machine summary: `results/covid_quar_attr_contamx_probe/summary.json` (not
committed — `results/` is gitignored; the committed surface carries the same
rows).
