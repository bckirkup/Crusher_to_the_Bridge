# Whole-hull airflow workup, 77 bundled hulls: offline package

A numerical comparison of two airflow engines on every hull that has a
committed CONTAM bundle: the repository's native prescribed-flow engine and
NIST ContamX 3.4.0.3. It reports whole-hull engineering aggregates, their
response to weather and operational settings, and run times.

It is not a validation of any ship. No measurement of a real vessel enters
it. It contains no room, deck, path or opening data, no contaminant source,
no organism, dose, infection or voyage quantity, no ranking of hulls or
settings, and no operational guidance. Hulls are listed alphabetically.

## Verify first

```
python3 verify.py
```

Standard library only; no network, account or repository is needed. It
checks the file set and every SHA-256, the column sets, each job's run-time
input-hash receipt against the frozen manifest, that the row IDs are
the frozen matrix exactly once (2,156; 1,591 executed), the repeat and
timing counts, that unresolved quantities are blank and never zero, the
phase labels, and it recomputes `results_long`, `repeat_consistency`,
`timing_summary`, `contrasts` and `reference_baselines` from the per-repeat
aggregate records. It exits 0 only if every check passes. The archive's own
SHA-256 is shipped beside it, outside the archive.

## Scope

- 82 platforms exist; 77 have a committed CONTAM bundle and are in scope
  (`design/coverage.csv`). Five have none and are excluded, with the reason
  in that file: `expedition_cruise_300`, `fletcher_class_destroyer`,
  `legend_class_nsc`, `messy_cruise_500`, `san_antonio_class_lpd`. No bundle
  was created for them.
- The matrix (`design/run_matrix.csv`) was frozen before any run: design
  commit `fb6a0bd5b7109dff288dd7fbf5d4681805016db3`, hull inputs at commit
  `d5d50d3a7bc30d50231e6f27b5083925f26c9c23`. `design/input_manifest.json`
  pins the SHA-256 of all 392 input files (five per hull, seven shared).
  That is the frozen manifest; what each job actually hashed at run time is
  a separate fact, stated per cohort under "Run-time input verification".
- Acceptance gates and tolerances are `design/canary_criteria.json`,
  unchanged since the canary. `design/fleet_selection.json` is selection
  metadata only: which 73 hulls, in which cohort, and the expected counts.

## Lanes and comparison rules

| lane | what it is | compared with |
|---|---|---|
| `native_prescribed` | native engine on the hull's airflow definition | harmonized ContamX, setting by setting |
| `contamx_commissioned_export` | ContamX on a project exported from the same airflow definition, with each supply group's outdoor-air fraction set to the one the native lane reads, at export and at import ("harmonized") | native |
| `contamx_commissioned_export_as_committed` | ContamX on the export as committed, outdoor-air inputs not matched; baseline only | reference only |
| `contamx_authored_bundle` | ContamX on the hull's committed `platform.prj`, untouched; baseline only | reference only |

The comparison is native against harmonized ContamX (`data/contrasts.csv`).
The two as-shipped lanes are separate baselines
(`data/reference_baselines.csv`), shown beside the harmonized value and never
pooled with it.

Two blocks, kept apart in every table:

- `solved_airflow`: what the engine itself resolved (terminal supply and
  return totals, ambient inward and outward totals, gross interzone flow,
  balance residuals, pressure-difference summary).
- `downstream_mixing`: one shared operator applied to that solved field
  (derived outdoor air, effective outdoor-air fraction, clean-air
  equivalents, whole-hull air change, uniform-tracer material time and its
  closure error). It is derived, not an independent ContamX output.

ContamX reports zero flow on the simple air-handler outdoor-air, exhaust and
recirculation paths in a steady solve. The ContamX lanes therefore do not
resolve `outdoor_air_total_m3h` or `exhaust_total_m3h`: those cells are
blank with status `unimplemented` and a reason. A blank is not a zero.

## Settings

Baseline plus one-at-a-time changes, each lane measured against its own
baseline (`*_minus_baseline`). Weather settings are wind speed (0, 5,
10 m/s) and relative heading (90°, 180°), alone and combined. A weather
response is one-sided: the native lane has no weather input, so its weather
rows are `structural_nonresponse` (the baseline is carried by reference, not
re-run) and the ContamX response is a change from the ContamX baseline, not
a difference between engines. The combined rows are 10 m/s at each heading.
Operational settings are supply duty (×0.5, ×1.5), outdoor-air fraction
(×0.5) and recirculated fraction (×0.5), run in both lanes where the hull's
definition has the parameter; supply air change ×1.5 is in the matrix as a
redundancy check on duty ×1.5, not as an independent setting. A row the design could not support is in the matrix with
planned status `structural_nonresponse` or `not_applicable` and its reason,
and has no values.
`observed_status` is `ok` when the block moved from the lane baseline,
`unchanged` when the setting ran and the block did not move.

## Files

| file | one row per | notes |
|---|---|---|
| `data/coverage_observed.csv` | matrix row (2,156) | planned and observed status, reason, completed cold, solver and cached counts |
| `data/results_long.csv` | row × block × metric | `value` in `unit`; blank unless status is `ok` or `unchanged` |
| `data/contrasts.csv` | hull × setting × block × metric | native, harmonized ContamX, difference, ratio, each minus its own baseline |
| `data/reference_baselines.csv` | hull × as-shipped lane × block × metric | value beside the harmonized baseline |
| `data/repeat_metrics.csv` | executed row × repeat × block × metric | the aggregate blocks of every raw record, plus the SHA-256 of the solved field; source for the recomputation |
| `data/repeat_consistency.csv` | executed row | repeats, distinct solved-field digests, largest relative metric difference |
| `data/timing_raw.csv` | timed sample | every repeat of every phase, nanoseconds, with 1-minute load average |
| `data/timing_summary.csv` | row × repeat kind × phase | median, min, max, IQR, MAD over measured or cached repeats; warm-ups excluded |
| `data/cohorts.csv` | cohort (Batch job) | job, image digest, runner commit, host, CPU, artifact and code hashes, gate and audit result |
| `data/gates_summary.csv` | cohort × gate | passed and failed counts of the in-job gates |
| `data/input_verification.csv` | cohort | which pinned input files the job hashed at run time: scope, counts, set digests before and after |
| `data/code_sha256.csv` | cohort × code file | SHA-256 of runner, cell, gates, reducer, criteria and lock file inside the image |
| `per_hull_readout.md` | hull | generated baseline, response and timing tables |
| `design/` | — | frozen design with its own `SHA256SUMS`, criteria, fleet selection |
| `EXPECTED.json` | — | expected counts, cohort rosters and receipts, pinned hashes |

Units: flows m³/h; pressures Pa; air change 1/h; material time h; fractions
and closure errors dimensionless; counts are counts; times nanoseconds.
`row_id` is `hull|lane|setting_id`.

## Run times

Each executed row was run as 1 warm-up and 5 measured cold cells, each in a
fresh interpreter process with thread counts set to 1, one cell at a time.
Inside a hull and setting the lane order alternates by repeat (native first
on even repeats). The last measured interpreter then repeated the downstream
operator 5 times with the engine already built (`cached`).

| phase | meaning |
|---|---|
| `input_read` | read the hull definition |
| `native_construct` | native lane: build the engine |
| `contamx_export` | write the ContamX project |
| `contamx_solve` | the ContamX subprocess only |
| `contamx_import` | Python decode of the result files and engine construction |
| `field_reduce` | reduce the solved field to the `solved_airflow` block |
| `downstream` | the shared mixing operator |
| `end_to_end` | one clock from just after `input_read` to the end of `downstream`: applying the setting, the engine phases above and the downstream operator. It is not a sum of the phase rows and excludes `input_read` |
| `process_total` | the cell's whole process as timed by the parent, launch to exit, so it adds interpreter start-up, imports, `input_read` and writing the record; the cached repeats' time is subtracted |

Cold and cached timings answer different questions and are never compared.
Warm-ups are in `timing_raw.csv` and excluded from summaries. A cohort is
one Batch job on one host; hosts differ, so timings are summarized per row
inside its cohort and never pooled across cohorts. The four canary hulls
come from the corrected canary run only (run 2); the earlier canary run,
whose solve and import split was mislabelled, is not in this package.

Spread of the per-row cold medians, by cohort (hull-specific values are in
`data/timing_summary.csv` and `per_hull_readout.md`):

<<TIMING>>

## Cohorts and provenance

<<COHORTS>>

### Run-time input verification

The frozen manifest pins 392 files. The table states what each job's retained
record shows it hashed, before and after its run; `verify.py` recomputes the
digest of that exact set from `design/input_manifest.json` and compares.

<<INPUTS>>

- Each fleet job hashed all 392 files in its image, whichever hulls it ran.
- The canary job hashed 27: its four hulls' 20 files and the 7 shared files.
  It did not hash the other 73 hulls' files, and nothing here says it did.
- So every hull's five inputs, and the shared inputs, were hashed against the
  manifest inside the job that measured that hull. "Unchanged" means the
  before and after sets are identical and equal to the pinned set.

`wall min` is the reporting attempt's container time, including its untimed
in-job smoke. `attempts` above 1 means a Spot host was reclaimed before the
job finished; the retry started from nothing on a new host, and every record
of that cohort comes from the last attempt (`reporting_attempt`).

Raw artifacts are private objects under
`s3://crusherbucket-994254241749-us-east-1-an/` at `raw_artifact_key`; they
are not needed to verify this package and are not included.

## Coverage

<<COVERAGE>>

## Limits

- Declared, not measured: every hull definition, flow, volume and
  leakage element is an authored model input. Measured here: what two
  engines compute from those inputs, and how long they take.
- The native lane prescribes terminal flows; it does not solve pressures
  and does not respond to weather.
- The `downstream_mixing` block applies one operator to both lanes, so
  agreement there follows from agreement of the solved field plus matched
  outdoor-air inputs.
- Run times are for these hosts, these two images (canary and fleet) and
  single-threaded cells. The fleet hosts were shared Batch instances; the
  recorded 1-minute load average is the only evidence about contention.
- This package supersedes `contam_fleet_workup_77_package_01`, whose README
  said every job hashed all 392 inputs. The data tables are the same.
- A passing gate means the configuration reached the engine and the output
  contract held. It says nothing about any real ship.
