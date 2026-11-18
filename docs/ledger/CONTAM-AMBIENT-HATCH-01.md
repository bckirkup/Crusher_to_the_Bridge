# CONTAM-AMBIENT-HATCH-01
**Date:** 2026-11-18
**Commit:** f50cccb19e6aae81942cc15331c02dbce9fd07c0
**Pathogens:** all
**Status:** measured
**Measured at:** f50cccb19e6aae81942cc15331c02dbce9fd07c0

Ambient-exposure stage 5, first bounded hatch/door leg. Six `weather_hatch`
`ambient_openings` records are authored on four naval hulls whose stage-4
`open_deck` weather zones sit on hatch-bearing compartments. The records
supplement the existing `open_deck` opening and the original zone-to-zone
adjacency; `service_hatch` remains a pressure opening and the three
`hangar_door` edges are ruled out. No schema, exporter, native bridge,
`flow_rate_m3h`, leak-area, or epidemiological constant changed.

## Scope

- Base: `origin/main` `b33bb52a2a8674553c0cf2c2114a846866d314ad`.
- Edges authored (adjacency `from` endpoint carries the record; all six
  endpoints already had `exposure: weather` and an `open_deck` record):

| hull | adjacency edge | `ambient_openings.zone` |
|---|---|---|
| `lsm_354` | `Weather_Aft_Super → Tank_Well` | `Weather_Aft_Super` |
| `middlesex_lst983` | `Tank_Deck → Weather_Deck_Amids` | `Tank_Deck` |
| `middlesex_lst983` | `Tank_Deck_Port → Forecastle_Bow` | `Tank_Deck_Port` |
| `lyon_ap71` | `Hatch_4_Weather → Cargo_Hold_4_Fwd` | `Hatch_4_Weather` |
| `lyon_ap71` | `Hatch_3_Weather → Cargo_Hold_3` | `Hatch_3_Weather` |
| `montana_acr13` | `MD_Forecastle_Open → GD_Windlass_Engine` | `MD_Forecastle_Open` |

- Record fields: `type: weather_hatch`, `area_m2: 0.36`, `wind_speed_m_s:
  1.0`, `schedule: HatchOccasionalW`, `exchange_m3h` = D5 commissioned-lane
  solved outward flow measured after the change. Area is Grade C, dual-
  provenanced from `data/contam_hobbyist/orifice_catalog.json` (`hatch` /
  `service_hatch`, 0.36 m²) and the MCA small-vessel analogue (0.36 m² normal /
  0.25 m² minimum). Wind is the committed 1 m/s fleet-default point.

## Per-class sections

### Amphibious (`lsm_354`, `middlesex_lst983`)

Three records. `lsm_354/Weather_Aft_Super` and the two `middlesex_lst983`
tank-deck records supplement the stage-4 `open_deck` openings on the same
zones; the tank-deck adjacencies remain zone-to-zone paths.

| hull | zone | volume m³ | outward m³/h | inward m³/h | `exchange_m3h` |
|---|---:|---:|---:|---:|---:|
| `lsm_354` | `Weather_Aft_Super` | 384.66 | 24.038 | 24.255 | 24.038 |
| `middlesex_lst983` | `Tank_Deck` | 4200.00 | 28.825 | 28.993 | 28.825 |
| `middlesex_lst983` | `Tank_Deck_Port` | 444.76 | 28.877 | 28.941 | 28.877 |

### Auxiliary (`lyon_ap71`)

Two records on the weather hatch-deck zones.

| hull | zone | volume m³ | outward m³/h | inward m³/h | `exchange_m3h` |
|---|---:|---:|---:|---:|---:|
| `lyon_ap71` | `Hatch_4_Weather` | 886.55 | 27.918 | 29.324 | 27.918 |
| `lyon_ap71` | `Hatch_3_Weather` | 827.44 | 28.530 | 28.721 | 28.530 |

### Miscellaneous (`montana_acr13`)

One record on the forecastle open-deck hatch endpoint.

| hull | zone | volume m³ | outward m³/h | inward m³/h | `exchange_m3h` |
|---|---:|---:|---:|---:|---:|
| `montana_acr13` | `MD_Forecastle_Open` | 1124.22 | 28.497 | 29.125 | 28.497 |

## Hangar-door rule-out

`hangar_door` has no generic naval magnitude and must not be assumed
`always_open`; the literature audit found ship-specific values only. The
three candidate edges remain un-authored: `astoria_ca34`
`Catapult_Deck → Hangar`, `astoria_ca34` `Boat_Deck → Hangar`, and
`miami_cl89` `Catapult_Deck → Hangar`. No `hangar_door` `ambient_openings`
record was added and no hangar bundle changed.

## No-op census

| class | hulls in scope | action |
|---|---|---|
| battleship | `new_york_bb34`, `south_dakota_bb49`, `texas_bb35`, `west_virginia_bb48`, `idaho_bb42`, `missouri_bb63`, `new_jersey_bb62`, `wisconsin_bb64` | no stage-5 hatch/door edges authored; bundles byte-identical |
| carrier | carrier roster with committed stage-4/G4 bundles | no stage-5 hatch/door edges authored; bundles byte-identical |
| destroyer | `cannon_de701`, `cushing_dd376`, `davison_dd618`, `nields_dd616`, `palmer_dms5`, `sigsbee_dd502`, `hunter_killer_dd692`, `keppler_dd765` (`destroyer_baseline`/`fletcher_dde_dd445` excluded: no stage-4 bundles) | no stage-5 hatch/door edges authored; bundles byte-identical |
| olympia | `olympia_c6` | stage-4 weather openings unchanged; no hatch/door edge authored |
| cruise | six cruise roster hulls | excluded by owner ruling; no changes |
| fiction | `enterprise_constitution_tos`, `enterprise_galaxy_tng` | excluded by owner ruling; no changes |

## Witnesses

ContamX commissioned lane, `wind_speed_m_s = 1.0`. Before is
`origin/main` `b33bb52a`; after is this branch at `f50cccb1`. Pressure values
are Pa; opening flows are m³/h from `tools/contam_flow_compare.py`; residual
is the commissioned-lane boundary balance residual in m³/h.

| hull | envelope max \|ΔP\| before → after | interior max \|ΔP\| before → after | ambient openings before → after | sink-out before → after | inward before → after | residual before → after |
|---|---:|---:|---:|---:|---:|---:|
| `lsm_354` | 19.205109 → 19.205109 | 16.194485 → 16.194483 | 8 → 10 | 175571.253 → 175595.401 | 176099.313 → 176123.465 | 0.002592 → -0.001486 |
| `middlesex_lst983` | 2.812396 → 2.812396 | 1.916502 → 1.916502 | 18 → 22 | 560897.275 → 560955.103 | 562821.248 → 562879.068 | -0.002842 → 0.005708 |
| `lyon_ap71` | 26.926928 → 26.926924 | 24.503811 → 24.503807 | 22 → 26 | 738074.587 → 738131.845 | 746742.703 → 746799.967 | 0.001204 → -0.004771 |
| `montana_acr13` | 422.246155 → 422.246155 | 420.906219 → 420.906219 | 4 → 6 | 139520.229 → 139549.038 | 153612.068 → 153640.876 | 0.000574 → 0.001471 |

Make-up demand is unchanged on all four hulls (`lsm_354` 564.2176,
`middlesex_lst983` 1926.7788, `lyon_ap71` 8720.2478, `montana_acr13`
14888.3085 m³/h). `tools/contam_commissioned_check.py` reports `PASS` with
every commissioned terminal inside 5% of declared for all four hulls. The
pressure diagnostic reports 0 unsolved rows on the commissioned lane before
and after.

Report-condition check: all six new hatch legs solve outward at the
committed point (24.038–28.877 m³/h outward versus 24.255–29.324 m³/h
inward on the paired legs), consistent with an occasional two-way hatch under
`HatchOccasionalW`; residuals stay at the pre-existing ~1e-3 m³/h round-off
scale and no residual moves to a new route class. `lyon_ap71` keeps 16 and
`montana_acr13` keeps 173 pre-existing zero-flow real candidates; neither
count changes.

## Byte pins

Only these platform files differ from `origin/main`:

- `data/platforms/lsm_354/{air_flow_paths.json,contam/path_map.json,contam/platform.prj}`
- `data/platforms/middlesex_lst983/{air_flow_paths.json,contam/path_map.json,contam/platform.prj}`
- `data/platforms/lyon_ap71/{air_flow_paths.json,contam/path_map.json,contam/platform.prj}`
- `data/platforms/montana_acr13/{air_flow_paths.json,contam/path_map.json,contam/platform.prj}`

All other committed `data/platforms/**` bundles are byte-identical.

## Tests

- `tests/test_contam_ambient_opening.py`: `weather_hatch` added to the
  committed-record type census; `_WEATHER_HATCH_ZONES` pins the six zones and
  `test_declared_weather_hatches` checks area/wind/schedule/positive D5
  exchange.
- `tests/test_contam_ambient_opening_boundary.py`: ambient-opening leg
  census moves `lsm_354` 8→10, `middlesex_lst983` 18→22, `lyon_ap71` 22→26,
  `montana_acr13` 4→6; no other committed bundle carries an opening.
- Schema validation: `check-jsonschema` passes for the four edited
  `air_flow_paths.json` files.
- Data contracts: `tests/test_data_contracts.py` passes.

## Reproduction

```bash
# before witnesses (origin/main worktree)
git worktree add --detach /tmp/ctb-main b33bb52a
cd /tmp/ctb-main
CONTAMX_BINARY=/home/ubuntu/repos/Crusher-to-the-Bridge/third_party/contamx/contamx3 \
  /home/ubuntu/repos/Crusher-to-the-Bridge/.venv/bin/python \
  tools/contam_flow_compare.py --platform <hull> --run-contamx \
  --output /tmp/ctb-main/contam_flow_<hull>_before.json
CONTAMX_BINARY=/home/ubuntu/repos/Crusher-to-the-Bridge/third_party/contamx/contamx3 \
  /home/ubuntu/repos/Crusher-to-the-Bridge/.venv/bin/python \
  -m tools.diag.contam_pressure_balance_diagnostic --hull <hull> \
  --lane design --lane commissioned --lane authored --all-paths --timeout-s 1800

# after witnesses (this branch)
.venv/bin/python scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned
.venv/bin/python tools/contam_flow_compare.py --platform <hull> --run-contamx \
  --output telemetry_buffer/contam_flow_<hull>_after.json
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic --hull <hull> \
  --lane design --lane commissioned --lane authored --all-paths --timeout-s 1800
.venv/bin/python tools/contam_commissioned_check.py --platform <hull>
```

## Open

- `hangar_door` remains un-authored pending ship-specific clear-area
  evidence; do not assume `always_open`.
- `weather_door` is in schema/exporter scope but no in-scope edge exists in
  this leg; the 1.125 m² literature value is unused here.
- `destroyer_baseline`/`fletcher` remain excluded until stage-4 bundles
  exist; cruise/fiction remain excluded by owner ruling.
