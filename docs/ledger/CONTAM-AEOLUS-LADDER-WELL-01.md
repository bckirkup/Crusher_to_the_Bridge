# CONTAM-AEOLUS-LADDER-WELL-01
**Date:** 2026-11-17
**Commit:** 0229916a
**Pathogens:** all
**Status:** measured
**Measured at:** 0229916a4750c4ce5b625d1616aad57bbffb3967

## Scope

G3 (`aeolus_arc3` only) of `docs/proposals/grouped_weather_openings_decision_plan.md`
§5.3/§7-G3, under the 2026-11-17 owner ruling approving G1–G3 staging with no fleet
rollout. This entry records scratch capacity-control witnesses for the two
group links named by the pressure-localization audit: `ladder_well_5`
(committed `air_flow_paths.json` direction `AHU_Machinery -> AHU_Cable`)
and `ladder_well_6` (`AHU_Cable -> AHU_Weather`). The plan's §5.1/§5.2
parenthetical endpoint labels for those ids appear swapped relative to the
committed tree; the tree wins for current representation, and the expanded
`path_map.json` counts match the committed ids (8 and 3 paths).

No platform data, schema, exporter, `flow_rate_m3h`, `ambient_openings`,
leak area, schedule, wind, filter or epidemiological constant was changed.
The controls are in-memory ContamW34 exports only; nothing under
`data/platforms/` was regenerated or committed. Official ContamX 3.4.0.3
(`third_party/contamx/contamx3`, SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, not
committed) solved the commissioned lane (`ahs_terminal_mode="commissioned"`,
hobbyist overrides, paired-diagnostic filter efficiency).

## Frozen acceptance

Frozen before the control solves on 2026-11-17. For the unmodified baseline
and every control, record envelope max |ΔP|, interior flowing max |ΔP|,
make-up demand, per-link net/gross/max |ΔP| for `ladder_well_5` and
`ladder_well_6`, ambient-opening inward/outward legs, envelope inward/outward
legs, and the boundary balance residual. Acceptance is evaluated against the
plan's capacity-defect classification, not against a universal pressure
cutoff: the controls test whether bounded ladder-well passage areas reduce
the `ladder_well_5`/`ladder_well_6` residuals while preserving the declared
make-up demand and boundary balance. The zero-sanitary-exhaust row remains a
diagnostic bound only and was not rerun here.

## Controls

Each control states a **total clear orifice area per group link** and splits
it uniformly across that link's expanded room-pair paths, so the summed
representation area is the stated value. The exported reference for both
links is 50 m³/h at the exporter's 1 Pa reference, i.e. total area
0.0179610835691135 m² per link (element 31 for `ladder_well_5`, element 32 for
`ladder_well_6`). The candidate areas are Grade C sensitivity assumptions
anchored to the hobbyist opening catalog, not passage evidence and not fitted
to any pressure target.

| Variant | `ladder_well_5` total area m² | `ladder_well_6` total area m² | Assumption grade / basis |
|---|---:|---:|---|
| baseline | exported reference | exported reference | committed representation |
| `hatch_0p36` | 0.36 | 0.36 | C — crew-passage/service-hatch candidate (catalog hatch 0.36 m²) |
| `ladder_well_0p8` | 0.80 | 0.80 | C — ladder-well-open candidate (catalog `ladder_well` 0.8 m²) |
| `passageway_2p0` | 2.00 | 2.00 | C — upper crew-passage candidate (catalog passageway 2.0 m²) |

The scratch export changed only the `plr_orfc` area/params for elements 31 and
32. Path-map kind counts were identical in every solve: 363 paths,
`ambient_opening` 6, `envelope_leak` 40, `ladder_well_5` 8, `ladder_well_6` 3,
and the other ladder-well/passageway counts unchanged. The shared
`_orifice_elem_for_flow` cache was checked: elements 31/32 were used only by
their target kinds, so no non-target path changed element.

## Witnesses

### Pressure and boundary balance

| Variant | PRJ SHA-256 | Envelope max abs ΔP Pa | Interior flowing max abs ΔP Pa | Make-up demand m³/h | Balance residual m³/h |
|---|---|---:|---:|---:|---:|
| baseline | `b51eb51215cba315c294405ee330a205ba3d3ea0d659c5a4c154861808be38e5` | 952.953674 | 434.797516 | 1066.040948 | -0.002823 |
| `hatch_0p36` | `3e10f74083819901bd8f41037dceae86ce31da19605f46a17fe84d13a1289427` | 210.225113 | 195.316788 | 1066.040948 | 0.003380 |
| `ladder_well_0p8` | `e59cd78e4c540660ed42c121671f152954fd5fd80368631ab87e10cd4baf241d` | 203.129959 | 195.843369 | 1066.040948 | 0.007963 |
| `passageway_2p0` | `23e8e93a3eda1308c04b6800340d1db2c09e5be7b3777c3867197cb9e977c10d` | 201.296646 | 195.997574 | 1066.040948 | 0.005726 |

The baseline PRJ SHA-256 equals the committed
`data/platforms/aeolus_arc3/contam/platform.prj` SHA-256 and the audit's
`project_sha256`, so the scratch baseline reproduces the committed bundle
byte-for-byte. Variant PRJs are scratch artifacts and are not committed.

### Boundary legs

Cells are inward / outward / net inward, m³/h. The ambient-opening gross legs
are huge and nearly cancel because the committed weather openings are
wind-driven exchange paths; the net inward leg is the make-up contribution.

| Variant | Envelope in / out / net | Ambient opening in / out / net |
|---|---|---|
| baseline | 274.067 / 0.305 / 273.762587 | 217685.671 / 216893.390 / 792.281184 |
| `hatch_0p36` | 39.984 / 4.049 / 35.935417 | 217804.262 / 216774.159 / 1030.102150 |
| `ladder_well_0p8` | 33.674 / 7.673 / 26.000701 | 217809.215 / 216769.183 / 1040.032284 |
| `passageway_2p0` | 31.800 / 8.986 / 22.814389 | 217810.808 / 216767.587 / 1043.220833 |

Make-up demand is unchanged at 1066.040948 m³/h in every variant, and the
balance residual stays at solver round-off scale (worst |residual|
0.007963 m³/h). Relieving `ladder_well_5`/`ladder_well_6` shifts more of the
boundary supply onto the existing ambient openings and reduces envelope net
inward, but it does not create or remove make-up demand.

### `ladder_well_5` / `ladder_well_6` links

Cells are expanded path count; net flow along the committed authored
direction, gross flow, and max path abs ΔP. Negative net flow means the
solved direction is opposite the committed `from -> to` label.

| Variant | `ladder_well_5` | `ladder_well_6` |
|---|---|---|
| baseline | 8; -797.267406 / 797.267406 / 434.797516 Pa | 3; -792.108088 / 792.108088 / 342.858429 Pa |
| `hatch_0p36` | 8; -1029.574899 / 1029.574899 / 9.139121 Pa | 3; -1029.936095 / 1029.936095 / 1.443586 Pa |
| `ladder_well_0p8` | 8; -1039.399185 / 1039.399185 / 2.397465 Pa | 3; -1039.873202 / 1039.873202 / 0.298572 Pa |
| `passageway_2p0` | 8; -1042.569263 / 1042.569263 / 0.565750 Pa | 3; -1043.056526 / 1043.056526 / 0.048669 Pa |

## Acceptance evaluation

- Representation guard: PASS. Only `ladder_well_5`/`ladder_well_6` element
  areas changed; path-map count, kind counts, HVAC zones, adjacency,
  ambient openings, envelope leaks and all other path kinds are unchanged.
- Capacity-defect classification: SUPPORTED for the two named links.
  `ladder_well_5` max path abs ΔP falls 434.797516 → 0.565750–9.139121 Pa and
  `ladder_well_6` falls 342.858429 → 0.048669–1.443586 Pa across the bounded
  Grade C candidates, while make-up demand and balance residual are preserved.
- Pressure closure: NOT ACHIEVED by these controls alone. Envelope max abs ΔP
  falls 952.953674 → 201.296646–210.225113 Pa and interior flowing max abs ΔP
  falls 434.797516 → 195.316788–195.997574 Pa. The next interior flowing
  maximum is `ladder_well_1` (`Superstructure_Cabins -> Crew_Messing`, path
  64), about -19.79 m³/h at -195.3 to -196.0 Pa in all three controls. Thus
  the same evidence/assumption decision likely needs to cover the remaining
  ladder-well group links, or the owner must accept a bounded residual; this
  leg does not author or fit those links.
- Transport claim: none. No native/field contaminant-transport compare was
  run because pressure closure alone does not prove transport agreement and
  the plan calls for that compare only if transport improvement is claimed.

## Byte pins

Committed Aeolus files at the measured base are unchanged by this entry:

| File | SHA-256 |
|---|---|
| `data/platforms/aeolus_arc3/air_flow_paths.json` | `1e08f8ad93c8f97d7f8edf7b7f2a2ed8322cbee313733973913b1965320c6d83` |
| `data/platforms/aeolus_arc3/spatial_layout.json` | `c9268bd88b52dc9c586c2ca1b515a12851b0b5a29304739d0c494d413ddea99a` |
| `data/platforms/aeolus_arc3/contam/platform.prj` | `b51eb51215cba315c294405ee330a205ba3d3ea0d659c5a4c154861808be38e5` |
| `data/platforms/aeolus_arc3/contam/path_map.json` | `c35904c78782fba99b0008d6c831a7379a21729d856bb249bd13ebe7e7ffccf0` |

`git diff --name-only 0229916a4750c4ce5b625d1616aad57bbffb3967 -- data/platforms`
is empty for this change; the only committed files are this ledger entry and
its README registration. No frozen Phase1/Phase2 directory, cache or readout
was touched.

## Tests

`python3 -m pytest tests/test_ledger_entries.py` — ledger header/filename
convention check for this entry.

## Open

- No passage evidence (drawing, compartment description or systems note) was
  found in this leg for the ladder-well/hatch/trunk connections between
  `AHU_Weather`, `AHU_Cable` and `AHU_Machinery`; the candidate areas remain
  Grade C operating assumptions.
- The owner still chooses the defensible basis for `ladder_well_5`/
  `ladder_well_6`: authored passage evidence, a bounded Grade C assumption,
  or a schema/semantics change that separates reference flow from opening
  area. This entry supplies witnesses only.
- The post-control residual on `ladder_well_1` is recorded as a witness, not
  as a new scope decision for this G3 leg.
