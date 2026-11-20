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

| cohort | lane class | phase | rows | min ms | median ms | max ms |
|---|---|---|---|---|---|---|
| canary_run2 | contamx (all three lanes) | contamx_export | 53 | 0.37 | 12.68 | 31.33 |
| canary_run2 | contamx (all three lanes) | contamx_import | 53 | 10.46 | 45.18 | 418.77 |
| canary_run2 | contamx (all three lanes) | contamx_solve | 53 | 2.72 | 6.14 | 62.30 |
| canary_run2 | contamx (all three lanes) | downstream | 53 | 0.50 | 5.71 | 284.37 |
| canary_run2 | contamx (all three lanes) | downstream (cached) | 53 | 0.24 | 5.34 | 293.15 |
| canary_run2 | contamx (all three lanes) | end_to_end | 53 | 15.49 | 71.36 | 799.88 |
| canary_run2 | contamx (all three lanes) | field_reduce | 53 | 0.42 | 0.74 | 4.35 |
| canary_run2 | contamx (all three lanes) | input_read | 53 | 0.36 | 0.50 | 0.97 |
| canary_run2 | contamx (all three lanes) | process_total | 53 | 846.15 | 902.27 | 1633.30 |
| canary_run2 | native | downstream | 24 | 0.57 | 14.46 | 470.21 |
| canary_run2 | native | downstream (cached) | 24 | 0.30 | 9.98 | 471.98 |
| canary_run2 | native | end_to_end | 24 | 0.95 | 15.79 | 486.31 |
| canary_run2 | native | field_reduce | 24 | 0.12 | 0.22 | 1.93 |
| canary_run2 | native | input_read | 24 | 0.37 | 0.51 | 0.99 |
| canary_run2 | native | native_construct | 24 | 0.15 | 0.79 | 12.87 |
| canary_run2 | native | process_total | 24 | 831.42 | 844.89 | 1316.72 |
| fleet_cohort0 | contamx (all three lanes) | contamx_export | 150 | 0.37 | 13.47 | 17.76 |
| fleet_cohort0 | contamx (all three lanes) | contamx_import | 150 | 21.61 | 38.92 | 107.80 |
| fleet_cohort0 | contamx (all three lanes) | contamx_solve | 150 | 3.10 | 4.75 | 9.97 |
| fleet_cohort0 | contamx (all three lanes) | downstream | 150 | 1.62 | 4.36 | 18.40 |
| fleet_cohort0 | contamx (all three lanes) | downstream (cached) | 150 | 1.36 | 3.91 | 19.95 |
| fleet_cohort0 | contamx (all three lanes) | end_to_end | 150 | 28.32 | 58.48 | 146.58 |
| fleet_cohort0 | contamx (all three lanes) | field_reduce | 150 | 0.49 | 0.66 | 1.28 |
| fleet_cohort0 | contamx (all three lanes) | input_read | 150 | 0.34 | 0.40 | 0.53 |
| fleet_cohort0 | contamx (all three lanes) | process_total | 150 | 861.55 | 893.50 | 988.68 |
| fleet_cohort0 | native | downstream | 60 | 2.31 | 7.05 | 30.19 |
| fleet_cohort0 | native | downstream (cached) | 60 | 2.01 | 5.66 | 29.78 |
| fleet_cohort0 | native | end_to_end | 60 | 2.88 | 8.74 | 44.38 |
| fleet_cohort0 | native | field_reduce | 60 | 0.18 | 0.22 | 10.48 |
| fleet_cohort0 | native | input_read | 60 | 0.34 | 0.41 | 0.54 |
| fleet_cohort0 | native | native_construct | 60 | 0.25 | 0.38 | 13.04 |
| fleet_cohort0 | native | process_total | 60 | 832.82 | 844.60 | 884.72 |
| fleet_cohort1 | contamx (all three lanes) | contamx_export | 128 | 0.43 | 11.21 | 22.35 |
| fleet_cohort1 | contamx (all three lanes) | contamx_import | 128 | 19.86 | 48.71 | 219.91 |
| fleet_cohort1 | contamx (all three lanes) | contamx_solve | 128 | 3.39 | 6.84 | 51.21 |
| fleet_cohort1 | contamx (all three lanes) | downstream | 128 | 1.32 | 5.79 | 118.98 |
| fleet_cohort1 | contamx (all three lanes) | downstream (cached) | 128 | 1.02 | 5.41 | 117.97 |
| fleet_cohort1 | contamx (all three lanes) | end_to_end | 128 | 26.63 | 68.39 | 413.19 |
| fleet_cohort1 | contamx (all three lanes) | field_reduce | 128 | 0.53 | 0.80 | 2.38 |
| fleet_cohort1 | contamx (all three lanes) | input_read | 128 | 0.40 | 0.46 | 0.81 |
| fleet_cohort1 | contamx (all three lanes) | process_total | 128 | 858.28 | 900.04 | 1248.98 |
| fleet_cohort1 | native | downstream | 54 | 1.75 | 8.65 | 129.60 |
| fleet_cohort1 | native | downstream (cached) | 54 | 1.45 | 8.20 | 129.57 |
| fleet_cohort1 | native | end_to_end | 54 | 2.27 | 13.10 | 140.22 |
| fleet_cohort1 | native | field_reduce | 54 | 0.17 | 0.24 | 0.60 |
| fleet_cohort1 | native | input_read | 54 | 0.40 | 0.46 | 0.80 |
| fleet_cohort1 | native | native_construct | 54 | 0.24 | 1.10 | 9.30 |
| fleet_cohort1 | native | process_total | 54 | 828.23 | 842.10 | 975.61 |
| fleet_cohort2 | contamx (all three lanes) | contamx_export | 135 | 0.53 | 12.62 | 17.77 |
| fleet_cohort2 | contamx (all three lanes) | contamx_import | 135 | 32.20 | 59.93 | 162.63 |
| fleet_cohort2 | contamx (all three lanes) | contamx_solve | 135 | 4.38 | 7.15 | 16.89 |
| fleet_cohort2 | contamx (all three lanes) | downstream | 135 | 2.49 | 7.13 | 36.46 |
| fleet_cohort2 | contamx (all three lanes) | downstream (cached) | 135 | 2.17 | 6.81 | 36.45 |
| fleet_cohort2 | contamx (all three lanes) | end_to_end | 135 | 41.98 | 89.20 | 238.17 |
| fleet_cohort2 | contamx (all three lanes) | field_reduce | 135 | 0.64 | 0.91 | 1.92 |
| fleet_cohort2 | contamx (all three lanes) | input_read | 135 | 0.42 | 0.51 | 0.58 |
| fleet_cohort2 | contamx (all three lanes) | process_total | 135 | 871.95 | 918.31 | 1067.54 |
| fleet_cohort2 | native | downstream | 54 | 3.74 | 10.96 | 60.63 |
| fleet_cohort2 | native | downstream (cached) | 54 | 3.46 | 10.58 | 59.30 |
| fleet_cohort2 | native | end_to_end | 54 | 4.47 | 16.00 | 71.59 |
| fleet_cohort2 | native | field_reduce | 54 | 0.20 | 0.32 | 8.09 |
| fleet_cohort2 | native | input_read | 54 | 0.42 | 0.51 | 0.59 |
| fleet_cohort2 | native | native_construct | 54 | 0.35 | 1.25 | 10.41 |
| fleet_cohort2 | native | process_total | 54 | 828.85 | 842.67 | 898.75 |
| fleet_cohort3 | contamx (all three lanes) | contamx_export | 133 | 0.64 | 13.21 | 21.11 |
| fleet_cohort3 | contamx (all three lanes) | contamx_import | 133 | 39.90 | 66.49 | 218.10 |
| fleet_cohort3 | contamx (all three lanes) | contamx_solve | 133 | 5.95 | 8.79 | 78.49 |
| fleet_cohort3 | contamx (all three lanes) | downstream | 133 | 5.56 | 11.28 | 78.13 |
| fleet_cohort3 | contamx (all three lanes) | downstream (cached) | 133 | 5.15 | 10.79 | 77.14 |
| fleet_cohort3 | contamx (all three lanes) | end_to_end | 133 | 65.97 | 102.66 | 396.54 |
| fleet_cohort3 | contamx (all three lanes) | field_reduce | 133 | 0.70 | 0.96 | 2.45 |
| fleet_cohort3 | contamx (all three lanes) | input_read | 133 | 0.46 | 0.55 | 0.72 |
| fleet_cohort3 | contamx (all three lanes) | process_total | 133 | 895.45 | 931.97 | 1226.05 |
| fleet_cohort3 | native | downstream | 52 | 8.60 | 16.92 | 132.57 |
| fleet_cohort3 | native | downstream (cached) | 52 | 8.25 | 16.28 | 149.63 |
| fleet_cohort3 | native | end_to_end | 52 | 10.25 | 23.62 | 145.01 |
| fleet_cohort3 | native | field_reduce | 52 | 0.23 | 0.34 | 1.03 |
| fleet_cohort3 | native | input_read | 52 | 0.47 | 0.55 | 0.72 |
| fleet_cohort3 | native | native_construct | 52 | 0.95 | 8.51 | 11.01 |
| fleet_cohort3 | native | process_total | 52 | 839.60 | 849.29 | 974.25 |
| fleet_cohort4 | contamx (all three lanes) | contamx_export | 133 | 0.55 | 19.59 | 31.74 |
| fleet_cohort4 | contamx (all three lanes) | contamx_import | 133 | 37.17 | 138.22 | 312.05 |
| fleet_cohort4 | contamx (all three lanes) | contamx_solve | 133 | 4.50 | 12.81 | 66.69 |
| fleet_cohort4 | contamx (all three lanes) | downstream | 133 | 4.35 | 33.40 | 185.55 |
| fleet_cohort4 | contamx (all three lanes) | downstream (cached) | 133 | 4.05 | 33.04 | 185.08 |
| fleet_cohort4 | contamx (all three lanes) | end_to_end | 133 | 52.59 | 207.78 | 595.53 |
| fleet_cohort4 | contamx (all three lanes) | field_reduce | 133 | 0.67 | 1.67 | 3.24 |
| fleet_cohort4 | contamx (all three lanes) | input_read | 133 | 0.44 | 0.58 | 12.72 |
| fleet_cohort4 | contamx (all three lanes) | process_total | 133 | 923.33 | 1077.46 | 1480.94 |
| fleet_cohort4 | native | downstream | 52 | 6.71 | 56.33 | 196.57 |
| fleet_cohort4 | native | downstream (cached) | 52 | 5.88 | 55.96 | 198.45 |
| fleet_cohort4 | native | end_to_end | 52 | 7.57 | 69.96 | 211.33 |
| fleet_cohort4 | native | field_reduce | 52 | 0.21 | 0.63 | 1.18 |
| fleet_cohort4 | native | input_read | 52 | 0.45 | 0.57 | 12.63 |
| fleet_cohort4 | native | native_construct | 52 | 0.42 | 13.16 | 15.08 |
| fleet_cohort4 | native | process_total | 52 | 880.03 | 938.55 | 1101.00 |
| fleet_cohort5 | contamx (all three lanes) | contamx_export | 135 | 0.29 | 14.33 | 20.86 |
| fleet_cohort5 | contamx (all three lanes) | contamx_import | 135 | 11.73 | 42.63 | 138.67 |
| fleet_cohort5 | contamx (all three lanes) | contamx_solve | 135 | 2.35 | 5.61 | 21.04 |
| fleet_cohort5 | contamx (all three lanes) | downstream | 135 | 0.67 | 4.53 | 34.32 |
| fleet_cohort5 | contamx (all three lanes) | downstream (cached) | 135 | 0.44 | 4.44 | 33.55 |
| fleet_cohort5 | contamx (all three lanes) | end_to_end | 135 | 16.54 | 59.82 | 214.94 |
| fleet_cohort5 | contamx (all three lanes) | field_reduce | 135 | 0.42 | 0.74 | 1.70 |
| fleet_cohort5 | contamx (all three lanes) | input_read | 135 | 0.32 | 0.41 | 0.65 |
| fleet_cohort5 | contamx (all three lanes) | process_total | 135 | 884.89 | 936.79 | 1087.34 |
| fleet_cohort5 | native | downstream | 54 | 0.84 | 12.84 | 56.05 |
| fleet_cohort5 | native | downstream (cached) | 54 | 0.58 | 6.65 | 57.41 |
| fleet_cohort5 | native | end_to_end | 54 | 1.27 | 13.65 | 70.33 |
| fleet_cohort5 | native | field_reduce | 54 | 0.15 | 0.24 | 0.61 |
| fleet_cohort5 | native | input_read | 54 | 0.32 | 0.41 | 0.66 |
| fleet_cohort5 | native | native_construct | 54 | 0.18 | 0.40 | 13.61 |
| fleet_cohort5 | native | process_total | 54 | 870.92 | 882.89 | 944.64 |
| fleet_cohort6 | contamx (all three lanes) | contamx_export | 133 | 0.37 | 15.03 | 19.61 |
| fleet_cohort6 | contamx (all three lanes) | contamx_import | 133 | 17.77 | 40.25 | 130.89 |
| fleet_cohort6 | contamx (all three lanes) | contamx_solve | 133 | 2.80 | 5.70 | 14.64 |
| fleet_cohort6 | contamx (all three lanes) | downstream | 133 | 1.26 | 5.60 | 28.86 |
| fleet_cohort6 | contamx (all three lanes) | downstream (cached) | 133 | 0.99 | 5.22 | 29.43 |
| fleet_cohort6 | contamx (all three lanes) | end_to_end | 133 | 24.30 | 80.45 | 184.53 |
| fleet_cohort6 | contamx (all three lanes) | field_reduce | 133 | 0.47 | 0.70 | 1.50 |
| fleet_cohort6 | contamx (all three lanes) | input_read | 133 | 0.34 | 0.41 | 0.60 |
| fleet_cohort6 | contamx (all three lanes) | process_total | 133 | 865.77 | 926.51 | 1028.98 |
| fleet_cohort6 | native | downstream | 52 | 1.74 | 13.75 | 46.04 |
| fleet_cohort6 | native | downstream (cached) | 52 | 1.44 | 8.25 | 45.55 |
| fleet_cohort6 | native | end_to_end | 52 | 2.22 | 17.10 | 59.90 |
| fleet_cohort6 | native | field_reduce | 52 | 0.17 | 0.25 | 0.57 |
| fleet_cohort6 | native | input_read | 52 | 0.33 | 0.42 | 0.60 |
| fleet_cohort6 | native | native_construct | 52 | 0.22 | 1.26 | 13.30 |
| fleet_cohort6 | native | process_total | 52 | 842.47 | 874.13 | 940.36 |
| fleet_cohort7 | contamx (all three lanes) | contamx_export | 135 | 0.63 | 14.73 | 23.65 |
| fleet_cohort7 | contamx (all three lanes) | contamx_import | 135 | 46.37 | 104.59 | 269.42 |
| fleet_cohort7 | contamx (all three lanes) | contamx_solve | 135 | 5.62 | 12.38 | 32.49 |
| fleet_cohort7 | contamx (all three lanes) | downstream | 135 | 4.35 | 23.16 | 86.67 |
| fleet_cohort7 | contamx (all three lanes) | downstream (cached) | 135 | 3.97 | 22.77 | 87.12 |
| fleet_cohort7 | contamx (all three lanes) | end_to_end | 135 | 60.13 | 158.29 | 413.21 |
| fleet_cohort7 | contamx (all three lanes) | field_reduce | 135 | 0.78 | 1.33 | 3.00 |
| fleet_cohort7 | contamx (all three lanes) | input_read | 135 | 0.44 | 0.58 | 0.72 |
| fleet_cohort7 | contamx (all three lanes) | process_total | 135 | 894.00 | 992.32 | 1249.45 |
| fleet_cohort7 | native | downstream | 54 | 6.95 | 38.22 | 152.39 |
| fleet_cohort7 | native | downstream (cached) | 54 | 6.56 | 37.84 | 151.34 |
| fleet_cohort7 | native | end_to_end | 54 | 8.62 | 48.80 | 165.23 |
| fleet_cohort7 | native | field_reduce | 54 | 0.21 | 0.51 | 1.32 |
| fleet_cohort7 | native | input_read | 54 | 0.44 | 0.58 | 0.72 |
| fleet_cohort7 | native | native_construct | 54 | 1.06 | 9.49 | 11.73 |
| fleet_cohort7 | native | process_total | 54 | 839.55 | 879.64 | 998.93 |

## Cohorts and provenance

| cohort | hulls | Batch job | host | CPU | runner | image digest | wall min | max load (1 m) | gates | attempts | raw artifact SHA-256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| canary_run2 | 4 | `ac1b56e1-2080-40cc-be8f-b8473ceca793` | i-073002017534702f0 (c7a.8xlarge) | AMD EPYC 9R14 | `d06d685011eb` | `e59acd8d426a…` | 10.1 | 1.40 | 993 / 0 failed | 1 | `b99690680cd30331d4af0ad9e3afba5543d4499668e19c42205cf272f5a7ac8b` |
| fleet_cohort0 | 10 | `1e44ab45-ad2e-4bcf-87ca-687ff782095b` | i-06e1e5ad169462444 (c7i.8xlarge) | Intel(R) Xeon(R) Platinum 8488C | `56b1a990f64e` | `0a25129f30ec…` | 22.0 | 1.11 | 2730 / 0 failed | 1 | `2cbde92ea0126a980c0699b4c9724c149cafe83be8c92662a9c86aec6cce2f9d` |
| fleet_cohort1 | 9 | `bf3f4891-f2db-471b-86a2-4e3b32073b5f` | i-04b0739c785945713 (c7a.4xlarge) | AMD EPYC 9R14 | `56b1a990f64e` | `0a25129f30ec…` | 20.2 | 1.21 | 2358 / 0 failed | 1 | `493997f7b7b4d290ccb3b0eeb3e366c4f796d68925019a33be371f7a8e4433cd` |
| fleet_cohort2 | 9 | `79be935e-98c5-4ab0-9a5e-cfbdfa7fd191` | i-04b0739c785945713 (c7a.4xlarge) | AMD EPYC 9R14 | `56b1a990f64e` | `0a25129f30ec…` | 20.4 | 1.00 | 2457 / 0 failed | 1 | `38e9f1c6fdb241eca6d0ae8a244f498b2358304ff6d5be94a2eea0297bf35106` |
| fleet_cohort3 | 9 | `a9941ac8-47ad-46a7-a2a4-80c3e1191a81` | i-04b0739c785945713 (c7a.4xlarge) | AMD EPYC 9R14 | `56b1a990f64e` | `0a25129f30ec…` | 21.1 | 1.29 | 2399 / 0 failed | 1 | `7a6e1edf84d67c3da0910ae11e25912ab11a370c4f90d2cff702ab91b767bae8` |
| fleet_cohort4 | 9 | `9a1564dc-06b0-44b1-81d1-ae914cd3ced0` | i-02bbd3790ef7ce816 (c7i.8xlarge) | Intel(R) Xeon(R) Platinum 8488C | `56b1a990f64e` | `0a25129f30ec…` | 24.8 | 1.16 | 2399 / 0 failed | 2 | `86c863ab8f01b663b2a417cc75869a35ce94be6443cfe8c147a1639740f19821` |
| fleet_cohort5 | 9 | `1372b774-5110-4bf1-b13d-d51cca8eaf3c` | i-02bbd3790ef7ce816 (c7i.8xlarge) | Intel(R) Xeon(R) Platinum 8488C | `56b1a990f64e` | `0a25129f30ec…` | 21.2 | 1.21 | 2457 / 0 failed | 1 | `ab0800a83fe798cf42a7f2e21ee15bdb16740ac93be28fba87a1df3f86658ecd` |
| fleet_cohort6 | 9 | `3bebb032-a5eb-44ef-aff1-843800bccff1` | i-02bbd3790ef7ce816 (c7i.8xlarge) | Intel(R) Xeon(R) Platinum 8488C | `56b1a990f64e` | `0a25129f30ec…` | 20.2 | 1.08 | 2399 / 0 failed | 1 | `462e0212d19efac5d981c5d5a3dfa77df3d99eaa61556c734325c6817a0b56f7` |
| fleet_cohort7 | 9 | `99b9d3f6-2e9f-470e-89d7-a015a4047674` | i-05d964e7ac37307aa (c7a.4xlarge) | AMD EPYC 9R14 | `56b1a990f64e` | `0a25129f30ec…` | 22.3 | 1.21 | 2457 / 0 failed | 2 | `3659a9ae07a3b0396a4ab5be72f2341c6d63f032620c18b776fa6b27e36696f5` |

### Run-time input verification

The frozen manifest pins 392 files. The table states what each job's retained
record shows it hashed, before and after its run; `verify.py` recomputes the
digest of that exact set from `design/input_manifest.json` and compares.

| cohort | scope of run-time hashing | files hashed before / after | of manifest | hulls hashed | own hulls hashed | set matches manifest, unchanged |
|---|---|---|---|---|---|---|
| canary_run2 | `own_hulls_and_shared` | 27 / 27 | 392 | 4 | 4 of 4 | yes |
| fleet_cohort0 | `all_manifest_files` | 392 / 392 | 392 | 77 | 10 of 10 | yes |
| fleet_cohort1 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort2 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort3 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort4 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort5 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort6 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |
| fleet_cohort7 | `all_manifest_files` | 392 / 392 | 392 | 77 | 9 of 9 | yes |

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

| observed status | rows | reason (non-executed rows) |
|---|---|---|
| not_applicable | 12 | every positive-duty group is declared once-through (outdoor-air fraction 1.0); there is no recirculated share to vary |
| not_applicable | 28 | sealed life-support hull authored at calm: no relative wind exists for this platform in either lane |
| ok | 1591 |  |
| structural_nonresponse | 525 | the native prescribed-flow engine has no weather input; the baseline value is carried by reference, not re-run |

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
