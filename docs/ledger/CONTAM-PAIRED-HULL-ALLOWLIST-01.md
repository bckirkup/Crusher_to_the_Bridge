# CONTAM-PAIRED-HULL-ALLOWLIST-01
**Date:** 2026-11-19
**Commit:** 56d12d6d
**Pathogens:** all
**Status:** closed
**Measured at:** 56d12d6d

## Scope

`tools/diag/contam_paired_diagnostic.py` is the standalone paired native-vs-field
material-time diagnostic. Before this change its `--hull` choices were
`sorted(PLATFORM_SOURCES)`, a nine-hull curated witness-source map, so every
other committed Contam bundle was rejected at argument parsing even when the
hull had a commissioned `contam/platform.prj` beside `contam/path_map.json`.

This was first recorded as a workaround in `CONTAM-GROUPED-WEATHER-MIDWAY-01`:
the G1 Midway readout took paired rows from `contam_pressure_balance_diagnostic.py
--source` because `--hull midway_cv41` was not an accepted choice. The same
nine-hull limitation was noted for auxiliary and miscellaneous grouped-weather
hulls in `CONTAM-GROUPED-WEATHER-AUXILIARY-01` and
`CONTAM-GROUPED-WEATHER-MISC-01`.

## Audit

On the committed tree there are 82 platform directories and 77 committed Contam
bundles. Nine of those bundles are the curated `PLATFORM_SOURCES` hulls; the
other 68 bundled hulls were rejected by the standalone paired diagnostic. The
five platform directories without a committed Contam bundle remain outside
`--hull` choices: `expedition_cruise_300`, `fletcher_class_destroyer`,
`legend_class_nsc`, `messy_cruise_500`, and `san_antonio_class_lpd`.

## Fix

`--hull` choices now come from `bundled_hulls()`, the same committed-bundle
census used by the envelope-leak enumeration and the pressure diagnostic.
`PLATFORM_SOURCES` remains only the curated default-source map: the original
nine hulls still run without `--source`, while the other 68 bundled hulls
require an explicit `--source` zone because the diagnostic has no authored
default witness for them. No platform data, engine, schema, or diagnostic math
changed.

Regression coverage in `tests/test_contam_paired_diagnostic.py` checks that
every committed bundle parses as `--hull`, a platform directory without a
committed bundle is still rejected, an unmapped bundled hull requires
`--source`, and a mocked `_run_matrix` for `midway_cv41` emits native and
commissioned paired rows for the requested source and timing.

## Witnesses

Before `56d12d6d`, `--hull midway_cv41` exited 2 with `invalid choice`. After
`56d12d6d`,
`--hull midway_cv41 --source Flight_Deck --source Island_Upper --timing pulse_t0 --timing split_t0_t1`
wrote 12 cells across the native, commissioned, and authored lanes with finite
whole-hull material times; for example, native `Flight_Deck` `pulse_t0` was
0.073754 h and commissioned `Flight_Deck` `pulse_t0` was 0.111709 h.

Validation: `pytest tests/test_contam_paired_diagnostic.py -q` passed 4 tests;
`pytest tests/ -m 'not slow' -n auto` gave 8794 passed, 6 skipped, and one
failure in `tests/test_sentinel_wastewater.py::test_stan_and_numpy_agree_on_the_wastewater_channel`,
which also fails on `origin/main` because `sentinel_fleet.stan` has a CmdStan
type error in `voyage_incidence` and is untouched by this change.
`scripts/sonar_guard.py` on the changed Python files and pre-commit on the
changed files passed.
