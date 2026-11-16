# CONTAM-AMBIENT-OPENING-SCHEMA-01
**Date:** 2026-11-16
**Commit:** 852d22a0
**Pathogens:** all
**Status:** measured
**Measured at:** a632cabf

## Scope

Stage 1 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6: the `ambient_openings` representation in the schema and in both transport
lanes, with **no platform declaring a record**. Base `origin/main` `852d22a0`;
measurements at code commit `a632cabf` with local ContamX
`third_party/contamx/contamx3`. Audit base:
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

Owner rulings applied (Benjamin, 2026-11-16, "Proceed on the recommendations",
relayed in the session prompt): D1(a) top-level `ambient_openings` list;
D4(a) native magnitude from a declared per-type axis; D8 decided here. D2, D3,
D5, D7 belong to later stages and are untouched.

## Change

- `schemas/air_flow_paths.schema.json`: optional top-level `ambient_openings`
  list of `AmbientOpening` records — `zone`, `type`, `area_m2` required;
  `exchange_m3h` and `azimuth_deg` nullable; `schedule` optional;
  no other properties. `type` is one of `open_deck`, `balcony_door`,
  `weather_hatch`, `weather_door`, `hangar_door`, `makeup_louvre`.
- `engines/py_contam_bridge.py` (native lane): each record becomes one path
  `zone -> ambient`, `sink=True`, `path_type` `ambient_exchange_<type>`, and
  the new path attribute `exchange=True`. The rate is the record's
  `exchange_m3h`, else the per-type axis `hvac.ambient_exchange_m3h`
  (`parse_ambient_exchange_axis`); with neither, the build raises. The axis has
  no default and no config sets it. `area_m2`, `azimuth_deg` and `schedule` are
  not read by the native lane.
- `tools/contamw34_prj.py` (export lane): `_add_ambient_opening_paths` emits
  each record as `zone -> ambient (-1)` paths of `kind: "ambient_opening"`,
  sized by `orifice_params_for_area`, with the hobbyist wind profile and the
  record's `azimuth_deg` (else the zone's derived wall azimuth), and a week
  schedule from the record's `schedule` (else from the type: doors
  `DoorTrafficW`, hatches/hangar door `HatchOccasionalW`, open deck and louvre
  always open). `path_map_from_prj` recovers the kind from the reserved
  `AmbOp_` element-name prefix. The `PathFields.rel_ht` field carries the leg
  height into the `relHt` column, which was a constant `0.000` before.
- `engines/contamx_runner.py`: `SimFrame.path_flow1_kg_s` exposes the `.sim`
  `Flow1` column for the D8 witness. No transport consumer reads it.
- `schemas/contam_path_map.schema.json`: description of `kind` only.

Not changed: `engines/contamx_transport.py` — an `ambient_opening` path is
neither `crusher_transfer` nor `envelope_leak`, so the field lane skips it
today. The `cross_zone_links` rejection of `from: "ambient"` and the one-way
`to: "ambient"` sink are as they were. No `data/platforms/**` file, no
`flow_rate_m3h`, no transmission constant, no campaign directory, cache,
readout or existing ledger entry.

## The native equivalence, and where it stops

The native operator has no ambient concentration state. Two-way exchange at
rate Q with ambient air at zero concentration is `-(Q/V)·C` on the zone and
nothing else, which is the existing sink path at flow Q
(`tests/test_contam_ambient_opening.py::TestNativeBuilder::test_exchange_is_the_sink_operator_at_rate_q`
asserts the two operators are equal element-for-element). It is not net
extraction — Q of ambient air also enters — which is what `exchange=True`
states for air-balance audits. The equivalence holds only while ambient is
clean; a nonzero ambient contaminant would need a source term this stage does
not add.

## D8 — ContamX two-way element (measured)

Decision: **`paired_orifices`** — the declared area split into two `plr_orfc`
of half the area at 1/4 and 3/4 of the zone height. It is the exporter default;
the other two models stay selectable by the export override
`ambient_opening_model` for the witness only.

Witness: one scratch `open_deck` record, 40 m², on `Pool_Deck` of
`expedition_cruise_300`, declared in memory (nothing written under `data/`),
hobbyist design export, one ContamX solve per model and per deck temperature
offset from ambient. Deterministic, no seeds. Steady-state frame, m³/h;
"outward"/"inward" are the sums of positive/negative `Flow0` over the
opening's paths, which is everything the field lane reads.

```
.venv/bin/python tools/diag/ambient_opening_d8_witness.py \
  --offset-k 0 --offset-k 1 --offset-k 5 --offset-k -5
```

| ΔT (K) | Model | Paths | `Flow0` outward | `Flow0` inward | `Flow0` net | `Flow1` (unread) |
|---|---|---|---|---|---|---|
| 0 | `paired_orifices` | 2 | 0.00 | 0.51 | -0.51 | 0.00 |
| 0 | `single_orifice` | 1 | 0.00 | 0.51 | -0.51 | 0.00 |
| 0 | `two_way_door` | 1 | 0.00 | 0.51 | -0.51 | 0.00 |
| 1 | `paired_orifices` | 2 | 9654.24 | 9652.90 | 1.34 | 0.00 |
| 1 | `single_orifice` | 1 | 0.00 | 0.95 | -0.95 | 0.00 |
| 1 | `two_way_door` | 1 | 11829.16 | 0.00 | 11829.16 | 11830.12 |
| 5 | `paired_orifices` | 2 | 21392.23 | 21388.93 | 3.29 | 0.00 |
| 5 | `single_orifice` | 1 | 0.00 | 1.68 | -1.68 | 0.00 |
| 5 | `two_way_door` | 1 | 26211.85 | 0.00 | 26211.85 | 26213.55 |
| -5 | `paired_orifices` | 2 | 21884.28 | 21887.97 | -3.69 | 0.00 |
| -5 | `single_orifice` | 1 | 0.95 | 0.00 | 0.95 | 0.00 |
| -5 | `two_way_door` | 1 | 0.00 | 26819.47 | -26819.47 | 26820.46 |

Reading:

- `single_orifice` carries only the zone's net flow (about 1 m³/h at every
  ΔT). It solves no exchange and is not a two-way element.
- `two_way_door` (`dor_door`) does solve the exchange, but splits it across
  two `.sim` columns: one direction in `Flow0`, the counter-flow in `Flow1`.
  Which direction lands in `Flow0` flips with the sign of ΔT. Reading `Flow0`
  alone, the opening looks like a 26,000 m³/h one-way flow, and at ΔT = -5 K
  it shows no outward flow at all. Using it would need the `.sim` reader's
  consumers and the field lane to carry a second flow channel per path.
- `paired_orifices` puts the outward and the inward stream on separate paths,
  each a plain signed `Flow0`, balanced to within the zone's net flow. The
  existing reader and a per-path "solved-positive is outward" rule see all of
  it. Its exchange is 18% below the door element's at every nonzero ΔT
  (21392 vs 26212 at +5 K; 9654 vs 11829 at +1 K).

Limits of this witness, for stage 2 to carry:

- One hull, one zone, one area. The 18% gap to `dor_door` and the two leg
  heights (1/4, 3/4) are a modelling choice, not a calibrated value.
- At ΔT = 0 every model exchanges nothing: both legs sit on the same wall with
  the same wind pressure, so steady wind alone drives no counter-flow through
  one opening. In the ContamX lane the exchange is buoyancy-driven and scales
  with the zone/ambient temperature difference, which the exporter sets from
  `deck_temp_offset_K`. A weather-deck zone exported at ambient temperature
  will show ~0 solved exchange where the native lane applies its declared
  axis. The two lanes will not agree on magnitude without a decision on that.

## Stage 2 hook

Every leg is authored `zone -> ambient`, like `envelope_leak`, so positive
solved `Flow0` is outward. Widening the boundary-sink predicate in
`engines/contamx_transport.py` from `kind == "envelope_leak"` to also accept
`"ambient_opening"` is the whole of the stage-2 lane change; the inward leg
then adds no path, as for an inward envelope leak.

## Byte-identity witness (measured)

`tools/diag/ambient_opening_schema_witness.py` hashes, per platform, the
in-memory PRJ text and path_map in four export lanes (skeleton/hobbyist ×
design/commissioned) and the native path list (id, endpoints, flow as hex
float, type, ducted, filtered, sink) in four topology modes
(`duty0_terminal_mode` × `passive_link_mode`).

```
# on origin/main 852d22a0 (script copied in, tree otherwise unchanged)
.venv/bin/python tools/diag/ambient_opening_schema_witness.py \
  --out telemetry_buffer/ambient_opening_schema_witness/before.json
# on a632cabf
.venv/bin/python tools/diag/ambient_opening_schema_witness.py \
  --out telemetry_buffer/ambient_opening_schema_witness/after.json
cmp telemetry_buffer/ambient_opening_schema_witness/{before,after}.json
```

| | Platforms | Export fingerprints | Native fingerprints | Declared openings | Fleet SHA-256 |
|---|---|---|---|---|---|
| Before | 82 | 328 | 328 | 0 | `a6e2e8a569aa9167d941d3fa213691279d93031eafefee2214c8637bfb066ee9` |
| After | 82 | 328 | 328 | 0 | `a6e2e8a569aa9167d941d3fa213691279d93031eafefee2214c8637bfb066ee9` |

The two reports are byte-identical (`cmp` silent). `git status data/` is
empty. No committed `platform.prj` contains an `AmbOp_` element name, so
`path_map_from_prj` on the committed bundles is unaffected. All 82 committed
`air_flow_paths.json` validate against the extended schema and none carries
the key (`TestSchema::test_no_committed_platform_declares_an_opening`).

## Tests

`tests/test_contam_ambient_opening.py` (58 cases): schema acceptance and
rejection; native path shape, sink-operator equivalence, axis fallback and
fail-loud; exporter emission, path_map kind and PRJ round trip, wind azimuth,
schedule, unchanged ambient-source rejection; and the D8 witness at ΔT = 5 K
as a live-solver test (skipped where ContamX is absent). Fast tier
`python3 -m pytest tests/ -m 'not slow' -n auto`: 8621 passed, 9 skipped.

## Open

- Stage 2: boundary-sink predicate widening, and the ΔT = 0 magnitude question
  above.
- Later stages: per-type exchange axis values (D4/D5), platform declarations,
  `exposure` field (D7). No sourced value for any exchange rate or opening
  schedule exists yet; the type-default schedules reuse the interior door and
  hatch templates as declared defaults.
