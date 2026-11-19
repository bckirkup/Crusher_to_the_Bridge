# Four-hull airflow canary — readout

**Status:** measured, one AWS Batch job, 2026-11-19. Canary only: four of 77
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
The offline audit (`readout/audit.json`) passed all 14 checks.

## Findings

Measured at runner commit `5f524b81`; the fields are deterministic (no
seeds).

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

One host, one job, one thread, cells strictly serial: `c7a.8xlarge` (AMD
EPYC 9R14, 32 vCPU, 61 GiB), 1-minute load average ≤ 1.17 throughout. Wall
time in ms, median (interquartile range) over 5 measured cold repeats,
baseline setting. Cold means a fresh interpreter per cell.

| Hull (zones) | Native: construct | Native: downstream | Native: end to end | ContamX: export | ContamX: solve + result read ‡ | ContamX: engine build ‡ | ContamX: downstream | ContamX: end to end |
|---|---|---|---|---|---|---|---|---|
| destroyer_baseline (9) | 0.15 (0.00) | 0.60 (0.01) | 0.98 (0.02) | 1.63 (0.00) | 13.87 (0.10) | 0.29 (0.00) | 0.53 (0.01) | 17.01 (0.09) |
| enterprise_constitution_tos (63) | 1.26 (7.81) | 14.86 (0.37) | 16.80 (8.07) | 14.49 (1.31) | 82.50 (1.02) | 1.14 (0.02) | 12.94 (0.75) | 112.39 (1.39) |
| expedition_cruise_450 (47) | 0.38 (0.00) | 15.26 (8.07) | 16.11 (8.07) | 12.19 (0.24) | 51.62 (0.92) | 0.82 (0.01) | 5.78 (0.08) | 72.04 (1.33) |
| west_virginia_bb48 (198) | 13.30 (8.29) | 480.22 (3.48) | 496.74 (2.87) | 31.40 (0.82) | 471.83 (4.13) | 5.53 (0.18) | 280.14 (2.74) | 796.63 (2.01) |

‡ **Phase-label defect in this run** (found in review, after the job). The
phase recorded as `contamx_solve` contains the ContamX subprocess *and* the
Python read and decode of its result file; `contamx_import` contains only
engine construction. The solver alone is much cheaper than that column.
Median CPU inside that phase, parent Python vs ContamX child: destroyer 11.6
vs 2.5 ms; Enterprise 73.0 vs 9.8 ms; expedition 46.1 vs 5.7 ms; West
Virginia 413.1 vs 58.4 ms. The export + solve + import total, end-to-end
times and every airflow number are unaffected. The runner is fixed in this
PR (solve is the subprocess call only; import is result read plus engine
build); a clean wall-time split needs the same four-hull job re-run.

Cached downstream only (engine already built, same interpreter), reported
apart and never compared with a cold phase, native / ContamX: destroyer 0.31
/ 0.26; Enterprise 14.06 / 12.32; expedition 6.22 / 5.35; West Virginia
480.85 / 282.66 ms.

- Native construction and ContamX export + solve + import are different
  operations; they are side by side, not a speed ratio of one step.
- End-to-end cold median across all executed settings stays within 2.3 % of
  baseline on the ContamX lane. On the native lane it stays within 2.7 % on
  the destroyer and West Virginia, and varies by up to 48 % on the Enterprise
  and expedition hulls, where an ~8 ms disturbance is half the phase (see
  below).
- A full cold cell, interpreter start to exit, is 0.83 to 1.65 s (median;
  cached repeats excluded); start-up
  and imports dominate everything except West Virginia.
- On the largest hull the downstream phase (a dense matrix exponential, 280
  to 480 ms) and the Python result-file read (about 413 ms CPU) each cost
  several times the ContamX solver itself (58 ms CPU).
- Some small phases show an ~8 ms interquartile range against a ~1 ms median
  (Enterprise native construction, expedition native downstream). With five
  repeats that is one or two slow repeats; read the median with the range.
- Repeats measure timing noise only. Every repeat of every row reproduced
  identical metrics and an identical solved-field digest, and the in-job
  fields are digest-identical to the local smoke.

## Provenance

| What | Value |
|------|-------|
| Input commit (hull files) | `d5d50d3a7bc30d50231e6f27b5083925f26c9c23`; canary and shared inputs SHA-256-checked against the manifest before and after the run |
| Design commit | `fb6a0bd5b7109dff288dd7fbf5d4681805016db3`; frozen files SHA-256-checked in the job |
| Criteria | `design/canary_criteria.json`, SHA-256 `3eb085a3208797be7990ed0a00a1be511d290dc6377ba046a13801193b16b01d` |
| Runner commit | `5f524b8104dc2ca09a36d822b257f015af1fd8f4` (image label and `ENGINE_GIT_SHA`; runner file hashes recorded in `environment.json`) |
| Image | `picard-campaign:contam-fleet-workup-canary-01@sha256:92eaa848ab686f7149beb046293968ef2fab7e7ec9821a76ad733a154ae0a121`, as reported by the container |
| Job definition | `picard-contam-fleet-workup-canary-01:2` |
| Job | `3940f345-8c40-4dcb-842b-800d44178266`, `picard-campaign-queue`, not an array, 1 attempt, exit 0 |
| Host | `i-03338f7ba9911b6ae`, `c7a.8xlarge`, us-east-1b, kernel 6.1.180 |
| Python | CPython 3.11.18, numpy 2.4.6, scipy 1.17.1 |
| ContamX | NIST 3.4.0.3 64 bit; executable SHA-256 `d14dc802…274b2b`, archive `3612798d…df4fa`, checked in the job |
| Raw artifact | `canary_raw.tar.gz`, SHA-256 `0441e19ca3db1577d08bc7225188f251181f432b7fabccd53a66e97bde8bbfb9` |
| Reducer | this commit's `tools/diag/contam_fleet_workup_reduce.py`, run offline |

Check it:

```bash
cd campaigns/contam/fleet_workup_canary_01/readout && sha256sum -c SHA256SUMS
cd ../design/frozen && sha256sum -c SHA256SUMS
python3 tools/contam_fleet_workup_design.py --verify-only
python3 tools/diag/contam_fleet_workup_reduce.py --raw campaigns/contam/fleet_workup_canary_01/readout --out out/recheck
```

The last command rebuilds every table from `cells.jsonl`. Output must be\nunder the repository or a private temporary directory.

## Limits

- Four hulls. The other 73 are not run.
- The solve and import wall-time columns of this run are mislabelled as
  described under Run time.
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
