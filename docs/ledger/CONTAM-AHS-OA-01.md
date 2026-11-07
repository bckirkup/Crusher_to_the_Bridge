# CONTAM-AHS-OA-01
**Date:** 2026-11-07
**Commit:** bfe3fd3b
**Pathogens:** all
**Status:** closed

## Defect

`engines/contamx_ahs_bridge.py::synthesize_ahs_recirculation_paths`
collapsed every simple-AHS group's outdoor-air intent to one scalar
`oa_fraction`. When ContamX reported Rec≈0, the fallback
`Rec = (1 − oa) · min(ΣR, ΣS)` therefore lost per-group/per-room declared
OA intent. When ContamX reported a nonzero Rec, that measured value
silently superseded the declared OA intent with no surfaced divergence.

## Change

- AHS terminal path-map entries may now carry `declared_oa_fraction`.
  The Rec≈0 fallback uses the supply-weighted mean of those per-room
  declared values for the AHS group; entries without the field keep the
  scalar `oa_fraction` fallback as the labelled baseline.
- When measured Rec is nonzero and the path map carries declared per-entry
  OA, that measured value still supersedes the fallback (the ContamX
  solution remains authoritative), but a `UserWarning` is emitted if it
  diverges from the declared-OA recirculation by more than a relative
  tolerance, naming the AHS group and both flow values. Scalar-fallback
  path maps keep the previous silent measured-Rec behaviour.

The scalar `oa_fraction` argument is unchanged for callers that do not
supply declared per-entry OA; this keeps existing path-map consumers
bit-identical until producers annotate entries.

## Affected prior measurements

- `CONTAM-FLEET-01` already recorded "bridge `oa_fraction` is one global
  scalar" as an expressibility gap. This entry closes the bridge-side
  half of that gap for path maps that carry `declared_oa_fraction`;
  fleet-compare OA/filter arm cells remain governed by the companion
  fleet arm-integrity ledger entries.
- `CONTAM-DIVERGENCE-01` / `CONTAM-COMMISSION-01` are not invalidated:
  the destroyer 42%-vs-98% hook is a solver/airflow-field divergence
  measurement. This change only alters the Rec≈0 synthesis fallback when
  declared per-entry OA metadata is present, and only adds a warning
  when measured Rec disagrees with that metadata.
- No merged numeric result is void solely from this bridge change:
  without `declared_oa_fraction` on path-map entries the synthesized
  flows are identical to before, and nonzero measured Rec still wins.

## Tests

`tests/test_contamx_ahs_bridge.py` covers per-group declared OA beating
the scalar fallback, the scalar fallback remaining graduated, a
`UserWarning` when nonzero measured Rec diverges from declared OA, and
no warning when measured Rec matches declared OA.
