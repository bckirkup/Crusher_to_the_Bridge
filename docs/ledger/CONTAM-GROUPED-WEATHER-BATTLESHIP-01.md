# CONTAM-GROUPED-WEATHER-BATTLESHIP-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** 98eb3c10

## Scope

Stage G4 battleship leg of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md) §7, following [`CONTAM-GROUPED-WEATHER-MIDWAY-01`](CONTAM-GROUPED-WEATHER-MIDWAY-01.md). Owner rulings 2026-11-17: grouped weather zones MAY receive `ambient_openings`; the opening REPLACES the group's OA leg for that zone with no double-count; G4 rollout is staged by class. Targets are the four stage-4 battleship open items (`idaho_bb42`, `missouri_bb63`, `new_jersey_bb62`, `wisconsin_bb64`) and their 16 HVAC-grouped weather zones. No Pope/Aeolus/fiction, schema, engine, exporter, epidemiological constant, or flow-rate fitting change.

## Change (exactly)

For each target zone in `spatial_layout.json`: added `exposure: "weather"` (D7(b)). `Catwalk_02L` on the Iowa-class hulls stays grouped on `VENT_Weather` and was not tagged or opened.

In `air_flow_paths.json`:

- `idaho_bb42`: `HVAC_Main.rooms` removed `Fantail`; added one `open_deck` `ambient_openings` record; split every `HVAC_Main` cross-zone link that touched `Fantail` into group + `Fantail` records preserving per-room-pair flow.
- `missouri_bb63`, `new_jersey_bb62`, `wisconsin_bb64`: `VENT_Weather.rooms` reduced to `["Catwalk_02L"]`; added five `open_deck` `ambient_openings` records per hull; split `VENT_Weather` cross-zone links (including `ladder_well_1` and `Sanitary_Makeup` legs) into group + room records preserving per-room-pair flow.
- Every opening uses `wind_speed_m_s: 1.0`, `schedule: "always_open"`, Grade C deck-face `area_m2 = 2*sqrt(V/3)*3`, and D5 `exchange_m3h` measured after the change.

## D5 openings

| hull | zone | area_m2 | exchange_m3h |
|---|---|---:|---:|
| idaho_bb42 | Fantail | 96.281 | 74,166.9 |
| missouri_bb63 | Signal_Deck | 69.220 | 45,004.6 |
| missouri_bb63 | Fantail_Open | 171.679 | 138,440.0 |
| missouri_bb63 | Boat_Waist_Open | 231.994 | 184,190.6 |
| missouri_bb63 | Forecastle_Open | 255.645 | 203,642.3 |
| missouri_bb63 | Focsle_Void_2D | 61.310 | 47,981.5 |
| new_jersey_bb62 | Signal_Deck | 69.200 | 44,990.3 |
| new_jersey_bb62 | Fantail_Open | 171.689 | 138,448.0 |
| new_jersey_bb62 | Boat_Waist_Open | 232.013 | 184,204.2 |
| new_jersey_bb62 | Forecastle_Open | 255.631 | 203,629.6 |
| new_jersey_bb62 | Focsle_Void_2D | 61.293 | 47,967.0 |
| wisconsin_bb64 | Signal_Deck | 69.214 | 45,000.6 |
| wisconsin_bb64 | Fantail_Open | 171.691 | 138,449.6 |
| wisconsin_bb64 | Boat_Waist_Open | 232.016 | 184,208.4 |
| wisconsin_bb64 | Forecastle_Open | 255.633 | 203,632.7 |
| wisconsin_bb64 | Focsle_Void_2D | 61.297 | 47,971.1 |

Totals: Idaho 74,166.9; Missouri 619,259.0; New Jersey 619,239.2; Wisconsin 619,262.4 m³/h outward solved flow.

## No-double-count and terminal preservation

Native path and `path_map.json` row counts are unchanged per hull (Idaho 2,944 native / 1,819 path-map; Iowa hulls 3,861 / 2,248). The only removed native rows are the target HVAC return legs to `_plenum_HVAC_Main`/`_plenum_VENT_Weather`; the only added rows are `ambient_exchange_open_deck` sink/exchange rows. Remaining group members (`Catwalk_02L`, Idaho `HVAC_Main`) keep commissioned terminals: `tools/contam_commissioned_check.py --ahs-terminal-mode commissioned` PASSed before and after on all four hulls.

## Pressure-balance witnesses (commissioned lane)

| hull | envelope max \|ΔP\| Pa before → after | interior max \|ΔP\| Pa before → after | make-up m³/h | opening net inward m³/h before → after | balance residual m³/h before → after |
|---|---:|---:|---:|---:|---:|
| idaho_bb42 | 61,263.184 → 2,215.918 | 888.246 → 2,210.861 | 7,902.781 | 0 → 7,016.258 | 3.94e-05 → -0.000293 |
| missouri_bb63 | 356,245.719 → 59.163 | 2,169.084 → 58.027 | 17,263.975 | 0 → 17,058.468 | -4.73e-11 → 0.000522 |
| new_jersey_bb62 | 356,635.656 → 59.230 | 2,171.458 → 58.094 | 17,273.421 | 0 → 17,067.801 | -1.12e-05 → -0.00455 |
| wisconsin_bb64 | 356,229.781 → 59.163 | 2,168.987 → 58.026 | 17,263.589 | 0 → 17,058.099 | -5.62e-05 → -0.0177 |

All pressure and paired-diagnostic ContamX rows reported 0 unsolved.

## Flow-compare and paired witnesses

`tools/contam_flow_compare.py --run-contamx --inject <zones>` after the change reports ambient opening outward `boundary_sink` totals equal to the D5 sums above (Idaho sink-out 74,166.9219 / inward 81,183.1797; Missouri 619,259.0270 / 636,317.4946; New Jersey 619,239.2441 / 636,307.0448; Wisconsin 619,262.4345 / 636,320.5337 m³/h). Inward totals are solve-dependent and were not written to `exchange_m3h`.

Paired diagnostic commissioned-lane outflow coefficients k [1/h], before → after:

| source | hull(s) | native k before → after | field k before → after | field/native after |
|---|---|---:|---:|---:|
| Catwalk_02L | three Iowa hulls | 0.5237 → 0.5237 | 0.9816–0.9822 → 0.5275 | 1.007 |
| Forecastle_Open | three Iowa hulls | 0.5070 → 37.3986–37.4006 | 0.5390 → 38.3391–38.3418 | 1.025 |
| Fantail | idaho_bb42 | 3.3531 → 96.3621 | 5.2122 → 105.0915 | 1.091 |
| Provision_Issue | idaho_bb42 | 4.9180 → 4.9180 | 4.3119 → 3.9293 | 0.799 |

`Catwalk_02L` and `Provision_Issue` are remaining HVAC-group members; their native k did not move. Max paired-cell `closure_error` was 2.11e-14.

## Contract moves attributed to this diff

- `tests/test_forced_exhaust_audit.py`: fleet `Sanitary_Makeup` count 585 → 587. The +2 are the Idaho `Fantail → AHU_HD_HD_Crew_Aft/Fwd` records needed to preserve per-room-pair flow after `Fantail` left `HVAC_Main`; direction remains one-way with zero native reverse paths.
- `campaigns/contam/phase1_hvac_tracer_01` v2 successor artifacts were regenerated by `design/build.py` because Missouri's three opened Iowa weather zones are now HVAC-unserved and enter the remote-weak source-pool candidate rule. The frozen v1 design/pools/campaign and all campaign cells are unchanged; `campaign_v2.json` regenerated byte-identical.

## Validation

- Non-target hull bundles byte-identical: `git status`/`git diff` touched only the four battleship platform dirs, the two ambient-opening census tests, the forced-exhaust census, and phase-1 v2 generated artifacts.
- `python3 -m pytest tests/test_json_schema_validation.py -q`: 220 passed.
- Ambient opening contract/boundary plus forced-exhaust and phase-1 v2 tests: 88 passed.
- `tools/contam_commissioned_check.py`: PASS before and after on all four hulls.
- ContamX pressure/flow/paired witnesses: 0 unsolved; commissioned envelopes above collapsed from 56–356 kPa to 2.2–59 Pa.
- `python3 -m pytest tests/ -m 'not slow' -n auto -q`: first run 8,763 passed / 2 failed (the two contract moves above); after repair, targeted tests pass and the full fast tier was rerun before PR.
