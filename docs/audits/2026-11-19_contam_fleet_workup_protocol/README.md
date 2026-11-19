# Fleet native-vs-ContamX workup: frozen protocol

**Status:** Declared — design only. No field was solved and no solver was
timed. Nothing here is a result. Ledger entry:
[CONTAM-FLEET-WORKUP-PROTOCOL-01](../../ledger/CONTAM-FLEET-WORKUP-PROTOCOL-01.md).

**Question.** For each hull with a committed Contam bundle, how do the native
prescribed-flow field and a freshly exported, commissioned ContamX field
compare in whole-hull air balance and aggregate flow, how do they respond to
relative wind and to normal ventilation settings, and what does each cost to
compute?

That is a numerical comparison of two models. It does not say which one is
closer to a real ship. The numerical reference is the two-hull
[CONTAM-PHASE3-BASELINE-01](../../ledger/CONTAM-PHASE3-BASELINE-01.md); older
fleet and Phase 1/2 comparisons are historical.

## What is frozen

| File | Content |
|------|---------|
| [`evidence/input_manifest.json`](evidence/input_manifest.json) | Input commit, root and subtree IDs, SHA-256 and git blob ID of every input file |
| [`evidence/coverage.csv`](evidence/coverage.csv) | One row per platform, the five exclusions included |
| [`evidence/run_matrix.csv`](evidence/run_matrix.csv) | One row per hull × lane × setting, with planned status and repetitions |
| [`evidence/protocol.json`](evidence/protocol.json) | Levels, lanes, metrics, runtime protocol, output contract, open items |
| [`evidence/dry_run_summary.json`](evidence/dry_run_summary.json) | Exact planned counts |
| [`evidence/SHA256SUMS`](evidence/SHA256SUMS) | Checksums of the five files above |

All six are written by `tools/contam_fleet_workup_design.py` from git objects
at input commit `d5d50d3a7bc30d50231e6f27b5083925f26c9c23`, never from the
working tree.

## Roster

82 platform directories at the pin; 77 carry all five input files
(`spatial_layout.json`, `air_flow_paths.json`, `contam/platform.prj`,
`contam/path_map.json`, `contam/hobbyist_overrides.json`) and are in scope.
Excluded, each with a row in `coverage.csv`: `expedition_cruise_300`
(legacy), `fletcher_class_destroyer`, `legend_class_nsc`, `messy_cruise_500`,
`san_antonio_class_lpd`.

## Lanes

| Lane | What it is | Settings |
|------|------------|----------|
| `native_prescribed` | Native engine from the two input documents | all 13 |
| `contamx_commissioned_export` | Fresh hobbyist export, commissioned terminals, ContamX solve, import; outdoor-air fraction harmonized (below) | all 13 |
| `contamx_commissioned_export_as_committed` | Same export with the committed overrides untouched | baseline only |
| `contamx_authored_bundle` | Committed `platform.prj` solved as authored | baseline only |

The last two are reference baselines. They are never pooled with the
comparative arms.

### Outdoor-air fraction is not matched in the committed files

Read from the inputs at the pin, without solving anything:

- the native engine takes each group's `oa_fraction` from
  `air_flow_paths.json`;
- the hobbyist export takes it from the `oa_fraction` map in
  `hobbyist_overrides.json` (7 of 77 hulls have one), otherwise the pack
  default 0.2;
- the ContamX import uses the single top-level `oa_fraction` unless a
  per-terminal declared value is present.

On groups with positive duty the first two differ for 339 of 437 groups, on
75 of 77 hulls. The comparative ContamX lane therefore passes each group's
declared fraction through the existing overrides map and the existing
per-terminal `declared_oa_fraction` field. No engine or exporter code changes.
The as-committed lane keeps the mismatch visible.

## Settings

Baseline: relative wind 1.0 m/s from ahead (0°), which is the exporter default
and an assumed level; `ach`, `hvac_duty`, `oa_fraction` as committed. Every
other level is an engineering test level chosen before any result. None is an
onboard measurement.

| Setting | Parameter | Level | Unit |
|---------|-----------|-------|------|
| `wind_speed_0`, `_5`, `_10` | relative wind speed | 0, 5, 10 | m/s |
| `wind_heading_90`, `_180` | relative wind direction from ahead | 90, 180 | deg |
| `wind_speed_10_heading_90`, `_180` | both (declared interaction) | 10 and 90 or 180 | m/s, deg |
| `supply_duty_x0p5`, `_x1p5` | `hvac_duty` of positive-duty groups | ×0.5, ×1.5 | – |
| `supply_ach_x1p5` | `ach` of positive-duty groups | ×1.5 | 1/h |
| `supply_oa_x0p5` | outdoor-air fraction of recirculating supply groups | ×0.5 | – |
| `supply_recirc_x0p5` | recirculated fraction of the same groups | ×0.5 | – |

One variable changes at a time, except the two wind interactions: heading is
expected to do little at 1 m/s, so it is also tested at 10 m/s.

Both solvers use `ach × duty` as a product on supply groups, so the two are
one physical parameter. `supply_ach_x1p5` is kept as a single redundancy check
and must equal `supply_duty_x1p5`.

Not varied: night setback, filters, openings, hatches, leakage, zone
isolation, equipment outage or any casualty state.

## How each row is classified before it runs

| Planned status | Meaning | Rows |
|----------------|---------|------|
| `planned_execute` | Run and timed | 1,591 |
| `structural_nonresponse` | The native engine has no weather input; its baseline is carried by reference, nothing is run | 525 |
| `not_applicable` | The parameter does not exist on that hull | 40 |
| **Total** | 77 hulls × 28 rows | **2,156** |

The 40 not-applicable rows: weather on the two sealed life-support hulls,
which are authored at calm (28), and the two outdoor-air settings on three
hulls whose supply groups are all once-through (12).

A wind row on the ContamX lane is a **one-sided** contrast: ContamX at the
level against ContamX at baseline, with the native lane constant by
construction. It is not solver agreement or disagreement. Ventilation rows
are **matched** perturbations in both lanes.

After a run, observed status is one of `ok`, `unchanged`,
`field_not_reached`, `failed`, `timeout`, `unimplemented`,
`structural_nonresponse`, `not_applicable`. A metric is a number only for
`ok` and `unchanged`; otherwise the cell is empty, never 0.

## What is measured

One value per hull × lane × setting: total supply, return, outdoor-air and
exhaust flow; total inward and outward boundary flow; gross inter-zone flow;
whole-hull balance residual and air-change rate; the largest zone balance
residual as a value only; median, 95th percentile and maximum absolute path
pressure drop on ContamX lanes (not defined on the native lane); and the
whole-hull material-time and closure error of an inert tracer started at the
same concentration in every zone.

No per-zone, per-path or per-opening value is written, no zone or path is
named, nothing is ranked, and there is no localized release. No biological
agent, dose or occupant model is involved.

## Runtime

Per executed row: 1 warm-up and 5 measured cold repeats, then 5 cached
repeats.

- **Cold** means a fresh interpreter, inputs read from disk, a new temporary
  directory and no reuse of any field.
- **Phases** are timed separately: native construction; ContamX export,
  solve and import; the identical downstream metric computation; and
  end-to-end.
- **Wall and CPU** are separate columns (parent CPU and solver child CPU).
- **Cached** repeats cover only the downstream phase and are reported in
  their own table. They are never compared with a cold phase.
- Native construction and ContamX export + solve + import are different
  operations. They are shown side by side and as an end-to-end total, not as
  a speed ratio of one step.
- One thread, one cell at a time, lane order alternating by repeat.
- Summaries: median, minimum, maximum, interquartile range, median absolute
  deviation. Timeouts (300 s) are counted and excluded from medians.
- Repeats measure timing noise. The fields are deterministic, so repeats are
  not independent samples of the physics.

Planned workload: 9,546 cold cell executions (1,591 warm-up, 7,955
measured), of which 6,810 call the ContamX solver and 2,736 construct the
native engine; 7,955 cached repeats; 565 rows not timed. The solver-time
ceiling if every solve hit the timeout is 567.5 h; that is a bound, not an
estimate.

## Integrity contract for the Edison package

Planned, not sent. The package keeps the four design files unchanged and
adds `results_long.csv`, `timing_raw.csv`, `timing_summary.csv`,
`coverage_observed.csv`, `environment.json`, `external_files.json` and
`SHA256SUMS`. Column definitions and units are in `protocol.json`.

Three commits are recorded separately: the **input commit** that supplies
the hull files, the **design commit** that contains this protocol, and the
**runner commit** that executes it. The manifest hashes inputs at the input
commit only, so no file contains its own hash.

A passing input check shows the inputs are the committed ones. It says
nothing about whether a solve ran or converged; that is
`coverage_observed.csv`.

Offline checks:

```bash
cd docs/audits/2026-11-19_contam_fleet_workup_protocol/evidence && sha256sum -c SHA256SUMS
python3 tools/contam_fleet_workup_design.py --check-artifacts   # no git history needed
python3 tools/contam_fleet_workup_design.py --verify-only       # rebuilds twice from the pin, byte-compares
python3 tools/contam_fleet_workup_design.py --dry-run           # prints the counts
```

## Stages

1. **This stage:** design freeze.
2. **Next, and the only next stage:** smoke and canary. Build the runner,
   show that every setting reaches the exported and native fields, run the
   four canary hulls (`destroyer_baseline`, `expedition_cruise_450`,
   `enterprise_constitution_tos`, `west_virginia_bb48`: 112 rows, 77
   executed, 318 solver calls), read out, stop.
3. The other 73 hulls run only after the canary readout is reviewed.

The canary set follows a rule fixed here: the two reference-ledger hulls, the
hulls with the fewest and most zones, and the first sealed hull by name.

## Not ready yet

- No runner exists for this matrix. `tools/contam_fleet_compare.py` exports
  without hobbyist weather or overrides and writes source-specific outputs;
  it is not reused.
- No aggregate-metric reducer exists; the pressure diagnostic returns
  per-path data that must be reduced before anything is written.
- The ContamX executable is not in the repository. The execution stage must
  record its SHA-256.
- The timing host is not chosen. Timings from different hosts are not pooled.
- Wind levels are test levels; the repository has no onboard wind record.
- Eight hulls take wall azimuth from display coordinates rather than declared
  values, so their heading response rests on a layout heuristic.
