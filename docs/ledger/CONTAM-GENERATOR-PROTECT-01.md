# CONTAM-GENERATOR-PROTECT-01
**Date:** 2026-11-15
**Commit:** fd8a7feccbcacdcddb0ba22de3d5f075b0818f70
**Pathogens:** all
**Status:** open

Stage 1 of `docs/proposals/exhaust_sink_audit_and_fix_plan.md` §6.1,
implementing the §5.4 G-min path only. Committed platform JSON is now treated
as authoritative for the recipe and legacy generators: `write_platform` (the
cruise and Enterprise recipe writers), the mega-cruise writer, and
`scripts/build_enterprise_platforms.py` refuse to overwrite existing outputs
unless `--overwrite` is passed. The GA blueprint importer and the sanitary
provisioning deriver now emit `Sanitary_Makeup` links through one shared
helper carrying `direction: "oneway"`, `mechanism: "pressure_opening"`, and
`filtered: false`.

No hull data, engine, exporter, schema, or campaign artifact changed. This
entry records the guard behavior and its tests; it does not re-measure
platform airflow or invalidate any prior readout.
