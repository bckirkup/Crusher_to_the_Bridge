# CONTAM-AMBIENT-OPENING-BOUNDARY-01
**Date:** 2026-11-16
**Commit:** 5be3da32
**Pathogens:** all
**Status:** measured
**Measured at:** 1fd6c8e79b30b735aec846973cc1e82302698386

## Scope

Stage 2 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6: the ContamX field lane treats solved outward `ambient_opening` flow as a
contaminant boundary sink, exactly like #1247's outward `envelope_leak` rule.
Base `origin/main` `5be3da32`; measurements at code commit `1fd6c8e7` with
local ContamX `third_party/contamx/contamx3`. Stage 1 representation:
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md).

## Change

- `engines/contamx_transport.py`: `is_outward_ambient_opening` shares
  `_is_outward_zone_to_ambient` with `is_outward_envelope_leak`: path kind
  `ambient_opening`, `from_zone` a known hull zone, `to_zone` outside the known
  hull zones (the exporter authors `zone -> ambient`), and solved `Flow0`
  at least `_FLOW_EPSILON_M3H` (1e-9 m³/h). `_is_boundary_sink` now accepts
  outward ambient openings independently of `envelope_leak_mode`; envelope
  leaks still require `boundary_sink`, so `pressure_only` remains an
  envelope-only baseline. Inward or zero-flow openings add no contaminant path.
  No `flow_rate_m3h`, path_map schema, or committed bundle changed.
- `tools/contam_flow_compare.py`: `ambient_opening` rows classify as
  `boundary_sink` when outward and `skipped` otherwise; the report adds
  `n_ambient_opening_paths`, `ambient_opening_sink_out_m3h`, and
  `ambient_opening_inward_m3h`, and prints an ambient-opening summary when
  present.
- `tools/diag/contam_pressure_balance_diagnostic.py`: `ambient_opening` is its
  own path class, so opening ΔP rows stay out of interior passive-opening
  statistics and remain visible under `by_class` / `by_kind`.
- Tests: `tests/test_contam_ambient_opening_boundary.py` covers the outward
  sink, inward/zero skip, monotonic mass removal, inward mass conservation,
  `pressure_only` envelope-only behavior, compare fates/report fields, and a
  committed path_map fleet guard; `tests/test_contam_pressure_balance_diagnostic.py`
  adds the ambient-opening class case.

Direction semantics were checked against `engines/py_contam_bridge.py`: retained
paths add `q / volume` to the source zone's outflow rate, while skipped inward
ambient openings add no source or outflow term. With clean ambient air, the
inward leg therefore needs no contaminant term; the outward solved leg is the
boundary-sink removal. `tools/diag/contam_paired_diagnostic.py` needed no
path-kind enumeration change because it consumes the `ContamXTransportEngine`
operator; the witness closure cell below is one of its `_trajectory_cell`
outputs.

## Unit and compare witnesses (measured)

Focused suite at `1fd6c8e7`:

```text
.venv/bin/python3 -m pytest tests/test_contam_ambient_opening_boundary.py \
  tests/test_contam_envelope_boundary.py \
  tests/test_contam_pressure_balance_diagnostic.py \
  tests/test_contam_flow_compare.py -q
58 passed in 1.08s
```

The compare witness uses one outward envelope leak (36 m³/h), one inward
ambient opening (-12 m³/h), one outward ambient opening (10 m³/h), and one
kept adjacency path (5 m³/h). Fates are `boundary_sink`, `skipped`,
`boundary_sink`, `kept`; `n_boundary_sink_paths=2`,
`boundary_sink_out_m3h=46`, `n_ambient_opening_paths=2`,
`ambient_opening_sink_out_m3h=10`, and `ambient_opening_inward_m3h=12`. With
`--envelope-leak-mode pressure_only`, the envelope leak is skipped while the
ambient opening still reports `boundary_sink`, confirming the mode remains
envelope-only.

## Scratch hull witness (measured)

Uncommitted in-memory declaration on `expedition_cruise_300`: one `open_deck`
ambient opening on `Pool_Deck`, `area_m2=40`, exported with
`ambient_opening_model="paired_orifices"` and `deck_temp_offset_K={"7_Sun": 5}`.
Solved paired-orifice legs: outward `Flow0=+21392.2288144495` m³/h and inward
`Flow0=-21388.934083215012` m³/h, `Flow1=0` on both. The engine keeps exactly
one ambient sink path, `contamx_417_Pool_Deck_ambient` at `21392.2288144495`
m³/h, unfiltered.

Mass-only check (`natural_decay_rate=0`, one 1 h epoch, 1.0e6 units initially
in `Pool_Deck`, baseline engine built from the same entries with the two
`ambient_opening` rows removed):

| Quantity | With opening | Without opening |
|---|---:|---:|
| Final whole-hull mass | 603.3680606987306 | 872902.7723427525 |
| Final `Pool_Deck` mass | 0.7930254903493436 | 822433.2604645899 |

Ambient-opening-attributable whole-hull mass difference after one epoch:
`872299.4042820538` units. Zone-specific outflow for `Pool_Deck` rises from
`0.19597572811098385` /h without the opening to `20.56952697996765` /h with it.

Paired exact-integral closure cell (`filter_efficiency=0.3`,
`natural_decay_rate=0.1`, horizon 12 h, pulse_t0):

| Lane | transport_loss | natural_decay_loss | retained_12h | closure_error |
|---|---:|---:|---:|---:|
| with ambient opening | 0.9947692143256895 | 0.005230785627659554 | 4.665097718359148e-11 | -1.1102230246251565e-16 |
| without ambient opening | 0.6117744490072545 | 0.35617826437432315 | 0.032047286618424334 | -1.9984014443252818e-15 |

Mass balance closes to machine precision in both arms; the opening arm moves
the removed mass from natural decay into transport loss as intended.

## Fleet guard (measured)

No committed bundle declares an ambient opening: all 82
`data/platforms/*/air_flow_paths.json` files contain zero `ambient_openings`
records, the 77 committed `contam/path_map.json` files enumerated through
`tools.contam_flow_compare.contamx_flow_report` report zero
`ambient_opening` rows, and `git grep -n "ambient_opening\|AmbOp_" --
data/platforms` is empty. The five platform directories without a committed
`path_map.json` are export-only; their `air_flow_paths.json` files are included
in the zero-record count above. `git diff --name-only` for the code commit
contains no `data/` changes.

## Open

- Carried from stage 1: at `deck_temp_offset_K=0`, ContamX paired-orifice
  exchange is buoyancy-driven and nearly zero (D8 measured `Flow0` outward
  0.00 / inward 0.51 m³/h for this witness geometry). Stage 2 keeps the solved
  direction rule, so a ΔT=0 opening contributes no outward sink until the
  stage-4 magnitude/axis decision supplies a non-buoyant exchange. This does
  not block stage 3.
- Later stages remain untouched: per-type exchange axes (D4/D5), platform
  declarations, `exposure` field (D7), make-up authoring, campaigns, and any
  magnitude or transmission-layer change.
