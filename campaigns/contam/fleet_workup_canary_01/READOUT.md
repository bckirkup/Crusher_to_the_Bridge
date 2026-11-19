# Four-hull airflow canary — readout

**Status:** measured, 2026-11-19, in two AWS Batch jobs on two hosts. This
readout reports the second (run 2, corrected phase timers) only; run 1 is
superseded for timing and kept in `readout_run1/` (see Run time). Samples
from the two hosts are never pooled. Canary only: four of 77
hulls. Nothing here is a fleet result, and nothing was sent to Edison.

**What this is.** A numerical comparison of two models' whole-hull air
aggregates and their run times, under assumed test levels. It is not a
validation of either model against a ship. No pathogen, occupant or dose
model is involved; the tracer is inert and starts uniform.

**How to read the two blocks.**

- `solved_airflow` is each lane's own field. For ContamX it is the solver's
  output. For the native lane it is the prescribed flows, so "solved" there
  means "prescribed".
- `downstream_mixing` is one shared mass-balance model applied to each
  field. A ContamX-lane number in this block is **derived**, not an
  independent ContamX result: its recirculation comes from the declared
  outdoor-air fraction applied to solved terminal flow.

## Coverage

| | Rows |
|---|---|
| Planned | 112 |
| Executed, all repeats completed | 77 of 77 |
| Structural non-response (native lane has no weather input), blank | 21 |
| Not applicable (sealed hull, weather), blank | 14 |
| Timed cold cells | 462 of 462 |
| Timed ContamX solves | 318 of 318 |
| Cached downstream repeats | 385 of 385 |
| Untimed smoke cells (53 with a solve), reported apart | 77 |
| Timeouts, failures | 0 |

All 19 gates passed in the job before any timing (993 checks, 0 failed).
The offline audit (`readout/audit.json`) passed all 14 checks. Run 1 had
the same coverage and the same audit result.

## Findings

Measured at runner commit `d06d6850` (run 2) and before that at `5f524b81`
(run 1); the fields are deterministic (no seeds). The two runs agree on
every value and status in `results_long.csv` (3,144 entries) and on every
solved-field digest, so the findings below did not change.

1. **Outdoor-air settings do not reach the ContamX solved field.** On all
   four hulls both outdoor-air rows are `unchanged` in `solved_airflow`
   (identical field digest) and `ok` in `downstream_mixing`. ContamX reports
   zero flow on every AHS outdoor-air, exhaust and recirculation path (0
   nonzero on every executed ContamX row), so solver outdoor-air and exhaust
   totals are blank, not 0. For outdoor air, the ContamX lane and the native
   lane are the same model with different terminal flows.
2. **Realized effective outdoor-air fraction matches the declared value in
   both lanes** on every comparative row (native within 1e-9, ContamX within
   1e-3 as frozen; worst observed 1.0e-9).
3. **Duty and ACH are one parameter in both lanes.** `supply_ach_x1p5` and
   `supply_duty_x1p5` agree exactly on every metric.
4. **Harmonizing outdoor air matters on one canary hull.** On
   `west_virginia_bb48` the as-committed and authored baselines import an
   effective outdoor-air fraction of 0.20 against a declared 0.647; tracer
   material time is 1.26 h as committed and 0.91 h harmonized. On the other
   three hulls the three ContamX baselines are identical.
5. **The two airflow fields differ most in inter-zone and boundary flow.**
   Terminal supply and return agree within 1.1 %. Gross inter-zone flow is
   0.05× (destroyer) to 4.3× (West Virginia) the native value. ContamX
   closes its own zone air balance (largest zone residual ≤ 0.07 m³/h on any row); the
   native prescribed field does not, by construction (whole-hull residual
   −715 to −15,885 m³/h).
6. **Tracer material time, baseline, native vs harmonized ContamX:**
   destroyer 0.356 vs 0.497 h; Enterprise 0.492 vs 0.485 h; expedition 0.489
   vs 0.493 h; West Virginia 1.710 vs 0.909 h. Closure error ≤ 1.4e-14 on
   every row, so by the frozen rule the tracer metric is kept.
7. **Wind reaches the solver and moves boundary flow far more than whole-hull
   tracer time.** At 10 m/s, ContamX inward boundary flow rises by about
   672,500 m³/h on the expedition hull (baseline 86,035) and 4.73 million
   m³/h on West Virginia (baseline 644,040), while tracer material time
   moves by −0.002 and −0.007 h. On the destroyer, whose native lane declares no ambient
   exchange, wind moves inter-zone flow by at most 1.4 m³/h except at 10 m/s
   abeam (+16 m³/h). Heading at 1 m/s is near-inert, as the design expected.
   These are responses to an assumed test level, one-sided (ContamX against
   its own baseline); they say nothing about real wind.

Per-hull tables for every metric and setting:
[`readout/readout_tables.md`](readout/readout_tables.md).

## Run time

Run 2: one host, one job, one thread, cells strictly serial: `c7a.8xlarge`
(AMD EPYC 9R14, 32 vCPU), 1-minute load average ≤ 1.40 during timed cells
(up to 2.64 during the untimed smoke just after start-up). Wall time in ms,
median (interquartile range) over 5 measured cold repeats, baseline
setting. Cold means a fresh interpreter per cell.

| Hull (zones) | Native: construct | Native: downstream | Native: end to end | ContamX: export | ContamX: solve | ContamX: import | ContamX: downstream | ContamX: end to end |
|---|---|---|---|---|---|---|---|---|
| destroyer_baseline (9) | 0.15 (0.01) | 0.57 (0.04) | 0.96 (0.05) | 1.82 (0.01) | 2.75 (0.04) | 10.46 (0.04) | 0.51 (0.00) | 16.75 (0.04) |
| enterprise_constitution_tos (63) | 1.19 (7.39) | 14.65 (0.15) | 16.59 (7.07) | 13.82 (0.55) | 10.01 (0.09) | 72.20 (0.97) | 12.79 (0.19) | 110.15 (1.21) |
| expedition_cruise_450 (47) | 0.39 (0.01) | 14.42 (7.32) | 15.25 (7.34) | 12.32 (0.61) | 6.04 (0.06) | 44.59 (0.37) | 5.65 (0.07) | 70.63 (0.37) |
| west_virginia_bb48 (198) | 12.64 (7.58) | 466.59 (12.76) | 482.35 (12.48) | 23.48 (8.14) | 58.76 (0.23) | 414.17 (1.55) | 274.86 (0.57) | 788.70 (1.97) |

Phase definitions in run 2: **export** builds the PRJ and writes it;
**solve** is the ContamX subprocess call and nothing else; **import** reads
and decodes the solver's result file in Python and builds the engine.
End to end also includes input read and field reduction.

Solve and import, wall and CPU (median, ms; parent is the Python process,
child is ContamX):

| Hull | Solve: wall | Solve: parent CPU | Solve: child CPU | Import: wall | Import: parent CPU | Import: child CPU |
|---|---|---|---|---|---|---|
| destroyer_baseline | 2.75 | 0.59 | 2.40 | 10.46 | 10.46 | 0.00 |
| enterprise_constitution_tos | 10.01 | 0.58 | 9.65 | 72.20 | 72.21 | 0.00 |
| expedition_cruise_450 | 6.04 | 0.58 | 5.69 | 44.59 | 44.58 | 0.00 |
| west_virginia_bb48 | 58.76 | 0.66 | 58.37 | 414.17 | 414.19 | 0.00 |

Full cold process, interpreter start to exit (median, ms; cached repeats
excluded), native / ContamX: destroyer 834 / 847; Enterprise 849 / 940;
expedition 840 / 901; West Virginia 1,316 / 1,621. Across all executed
settings the median is 0.83 to 1.63 s.

Cached downstream only (engine already built, same interpreter), reported
apart and never compared with a cold phase, native / ContamX: destroyer 0.31
/ 0.24; Enterprise 13.76 / 12.21; expedition 6.17 / 5.30; West Virginia
463.62 / 274.87 ms.

- Native construction and ContamX export + solve + import are different
  operations; they are side by side, not a speed ratio of one step.
- The ContamX solver is the small part of its lane. Across every executed
  setting, solve wall time is 0.26 to 0.27 of import wall time on the
  destroyer and 0.13 to 0.15 on the other three hulls.
- On West Virginia the downstream phase (a dense matrix exponential, 275 to
  467 ms) and the import (414 ms) each cost several times the solve (59 ms).
- Start-up and imports dominate a cold process on every hull except West
  Virginia.
- End-to-end cold median across all executed settings stays within 3.0 % of
  baseline on the ContamX lane. On the native lane it stays within 1.7 % on
  the destroyer and West Virginia, and varies by up to 48 % on the Enterprise
  and expedition hulls, where a ~7 ms disturbance is half the phase.
- Some small phases show a ~7 ms interquartile range against a ~1 ms median
  (Enterprise native construction, expedition native downstream). With five
  repeats that is one or two slow repeats; read the median with the range.
- Repeats measure timing noise only. Every repeat of every row reproduced
  identical metrics and an identical solved-field digest.

**Run 1 (superseded for timing).** Job
`3940f345-8c40-4dcb-842b-800d44178266`, runner `5f524b81`, host
`i-03338f7ba9911b6ae`. Its phase recorded as `contamx_solve` contained the
ContamX subprocess *and* the Python result-file read, and its
`contamx_import` only the engine build, so its solve and import columns do
not mean what run 2's mean. Its records, tables and checksums are unchanged
in `readout_run1/`. Its airflow and mixing values are identical to run 2.
Its timings are from a different host and are not combined with run 2.

## Provenance

Run 2 (reported here). Run 1's equivalents are in `readout_run1/job.json`
and `readout_run1/environment.json`.

| What | Value |
|------|-------|
| Input commit (hull files) | `d5d50d3a7bc30d50231e6f27b5083925f26c9c23`; canary and shared inputs SHA-256-checked against the manifest before and after the run |
| Design commit | `fb6a0bd5b7109dff288dd7fbf5d4681805016db3`; frozen files SHA-256-checked in the job |
| Criteria | `design/canary_criteria.json`, SHA-256 `3eb085a3208797be7990ed0a00a1be511d290dc6377ba046a13801193b16b01d`, unchanged from run 1 |
| Runner commit | `d06d685011ebc05ebe49ed35aacc43b7f6fc2706` (image label and `ENGINE_GIT_SHA`; runner file hashes recorded in `environment.json`) |
| Image | `picard-campaign:contam-fleet-workup-canary-01-rerun1@sha256:e59acd8d426a1304387929dd9c91bb85946b28c0c2357eb7a997e7e16a28e0c3`, as reported by the container |
| Job definition | `picard-contam-fleet-workup-canary-01:3` |
| Job | `ac1b56e1-2080-40cc-be8f-b8473ceca793`, `picard-campaign-queue`, not an array, 1 attempt, exit 0 |
| Host | `i-073002017534702f0`, `c7a.8xlarge`, us-east-1b (run 1 was `i-03338f7ba9911b6ae`) |
| Python | CPython 3.11.18 |
| ContamX | NIST 3.4.0.3 64 bit; executable SHA-256 `d14dc802…274b2b`, archive `3612798d…df4fa`, checked in the job; the download also checks the bucket's owning account |
| Raw artifact | `canary_raw_rerun1.tar.gz`, SHA-256 `b99690680cd30331d4af0ad9e3afba5543d4499668e19c42205cf272f5a7ac8b` (run 1: `canary_raw.tar.gz`, `0441e19c…bbfb9`) |
| Reducer | `tools/diag/contam_fleet_workup_reduce.py` at this commit, run offline |

Check it:

```bash
cd campaigns/contam/fleet_workup_canary_01/readout && sha256sum -c SHA256SUMS
cd ../readout_run1 && sha256sum -c SHA256SUMS
cd ../design/frozen && sha256sum -c SHA256SUMS
python3 tools/contam_fleet_workup_design.py --verify-only
python3 tools/diag/contam_fleet_workup_reduce.py --raw campaigns/contam/fleet_workup_canary_01/readout --out out/recheck
```

The last command rebuilds every table from `cells.jsonl`. Its output must
be under the repository or a private temporary directory.

## Limits

- Four hulls. The other 73 are not run.
- Timing is from one host per run. Run 2's host differs from run 1's (same
  instance type), so the two are not comparable sample for sample.
- The ContamX version string is the pinned one; the executable was
  identified by SHA-256, not asked for its version.
- The 1e-3 tolerances for solved ratios and the redefinition of
  `hull_balance_residual_m3h` are amendments, written after the outdoor-air
  smoke finding and before any canary table or timing.
- Spot instance shared with nothing else at the time, but exclusivity is
  inferred from load average, not guaranteed.
- The image base was pulled through a registry mirror; its digest is in
  `readout/job.json`.

## Decision

Whether to run the remaining 73 hulls with this runner and these criteria.
