# CONTAM-FIELD-OPS-01
**Date:** 2026-11-07
**Commit:** c1e5ff03
**Pathogens:** all
**Status:** closed

## Defect

`tools/contam_fleet_compare.py` classified only `set_duty`, `scale_ach`,
and `drop_links` as airflow-field ops (`_FIELD_OPS`). `set_oa` and
`set_filter` therefore reused the baseline ContamX field in the export
lane even though both are field-declared arm parameters: `set_oa`
rewrites the supply-side `oa_fraction` declarations (and, through
`CONTAM-OA-SCOPE-01`, must leave duty-0 exhaust branches at their
declared value), and `set_filter` carries `filter_efficiency` into the
export call. Those arms silently ran on a field solved under different
arm parameters while the native lane saw the mutated declaration.

## Change

- `_FIELD_OPS` now includes `set_oa` and `set_filter`, so every arm that
  changes a field-declared quantity forces a fresh export+solve instead
  of `{"reused": "baseline"}`.
- `_timed_field` / `_contamx_field` / `_resolve_arm_field` carry an
  optional `filter_efficiency` from the arm's `engine_args`, defaulting
  to the fleet baseline filter when the arm does not set one, and pass
  it to `export_prj_with_path_map`.
- Exported AHS path-map entries are annotated with
  `declared_oa_fraction` per `ahs_nr` so the ContamX AHS bridge can
  recover per-group OA intent instead of relying only on the global
  bridge scalar.

There is no labelled legacy arm for this change: the old reuse was a
cache bug, not a mechanism. The baseline arm still reuses its own
solved field for non-field arms exactly as before.

Expressibility caveat: the non-hobbyist exporter still carries the
`CONTAM-FLEET-01` gaps (OA fraction and AHS filter NR are not expressed
in the exported PRJ). This change makes the arm plumbing honest — no
silent baseline-field reuse — but does not by itself make the PRJ
express those knobs.

## Affected prior measurements

- `CONTAM-FLEET-01` `outdoor_air`, `full_recirc`, and `filter_merv13`
  arms are void for field-sensitive interpretation: their ContamX lane
  reused the baseline export field instead of solving the arm-mutated
  declaration. The native lane and the committed-prj baseline lane are
  unaffected by this cache defect.
- `CONTAM-FLEET-01`'s overall wall-clock/parity conclusions are not
  void: they describe solver cost and baseline divergence, not the
  stale-field arm cells. Any future quote of OA/filter arm response
  parity should come from a re-run after this change.
- `CONTAM-DIVERGENCE-01` is not invalidated: its destroyer 42%-vs-98%
  hook is a baseline committed-vs-export divergence measurement, not an
  OA/filter arm-reuse artifact.

## Tests

`tests/test_contam_fleet_compare.py` asserts `set_oa`/`set_filter` are
field ops, `_contamx_field` forwards `filter_efficiency` and annotates
exported AHS entries with `declared_oa_fraction`, and a stubbed
`run_platform` shows `filter_merv13` performs a fresh export solve with
the arm filter rather than reusing the baseline field.
