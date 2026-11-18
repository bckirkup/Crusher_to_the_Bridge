# CONTAM-GROUPED-WEATHER-AMPHIBIOUS-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** 8176acf3

## Scope

Stage G4 of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
§7: grouped weather zones may receive `ambient_openings`, and the opening
replaces that zone's HVAC-group OA leg with no double-count. Owner rulings of
2026-11-17, verbatim:

- fleet rule — "Grouped zones may receive ambient_openings; the opening
  REPLACES the group's OA leg for that zone (no double-count)";
- staging — "Approve G1–G3 staging: Midway representation (after Q2), Pope
  evidence table, Aeolus capacity controls — no fleet rollout"; G4 fleet
  rollout is staged by class, not fleet-wide.

Executable precedent: [`CONTAM-GROUPED-WEATHER-MIDWAY-01`](CONTAM-GROUPED-WEATHER-MIDWAY-01.md)
(G1). Steady ContamX solves used the local official NIST binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Amphibious roster enumeration (plan fleet table ∩ `data/platforms`): five hulls.
Three have remaining grouped OA>0 weather zones and are authored here:
`fort_mandan_lsd21`, `middlesex_lst983`, `san_antonio_class_lpd`. Two are no-op
rows: `lsm_354` and `ruchamkin_apd89` already carry only the stage-4
`CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01` ungrouped openings and have no grouped
OA>0 weather zones left. No Pope/Aeolus/fiction hull is touched.

`san_antonio_class_lpd` has platform JSON but no committed `contam/` bundle. It
is authored in JSON and witnessed through the in-memory commissioned/design
lanes plus `tools/contam_commissioned_check.py`; no bundle is added in this PR.

## Change (exactly)

Common recipe, per target zone: add `exposure: "weather"` (D7(b)); add one
`ambient_openings` record (`type: "open_deck"`, `schedule: "always_open"`,
`wind_speed_m_s: 1.0`, Grade C deck-face area below); remove the zone from its
HVAC group's `rooms` so the group stops counting that zone's outdoor exchange
as HVAC OA. If a group has no remaining rooms, the empty group is removed rather
than left as dead config. Group-addressed cross-zone links that expanded over
the removed room are split/re-addressed so every room×room pair keeps its
reference flow (`flow_rate_m3h / (from_rooms × to_rooms)`); these are
re-addressings of unchanged reference flows, not magnitude fits, but they edit
`flow_rate_m3h` fields and are called out for owner review as in G1.

`data/platforms/fort_mandan_lsd21/spatial_layout.json`

- `exposure: "weather"` added to `Top_House_Open`, `Well_Cover_Open`,
  `Well_Deck`.

`data/platforms/fort_mandan_lsd21/air_flow_paths.json`

- `VENT_Well_Deck.rooms`: `["Well_Deck", "Well_Cover_Open"]` →
  `["Gallery_Port", "Gallery_Stbd"]`; `ach` 4.0, `oa_fraction` 1.0,
  `vent_mode` `mech_exhaust` unchanged.
- `VENT_Machinery_Holds.rooms`: `Top_House_Open` removed; the remaining 22
  machinery/hold rooms are unchanged (`ach` 10.0, `oa_fraction` 0.9,
  `vent_mode` `mech_supply_exhaust`).
- Three `ambient_openings` records added (D5 table below).
- `ladder_well_2` (50 m³/h, `VENT_Berthing_Messing` ×
  `{Well_Deck, Well_Cover_Open, VENT_Well_Deck}`) split into three records of
  12.5/12.5/25.0 m³/h so each room pair stays at 50/32 = 1.5625 m³/h.
- `ladder_well_3` (50 m³/h, `{Well_Deck, Well_Cover_Open,
  VENT_Well_Deck}` × `VENT_Machinery_Holds` plus the two weather rooms) split
  into six records so each of the 92 room pairs stays at 50/92 =
  0.5434782609 m³/h.

`data/platforms/middlesex_lst983/spatial_layout.json`

- `exposure: "weather"` added to `Tank_Deck`, `Tank_Deck_Port`.

`data/platforms/middlesex_lst983/air_flow_paths.json`

- `HVAC_TankDeck` removed entirely: after `Tank_Deck` and `Tank_Deck_Port`
  leave, it has no rooms. Its only former members are the two new openings.
- Two `ambient_openings` records appended to the seven stage-4 records.
- `ladder_well_5` (50 m³/h, `HVAC_Machinery` × `{Tank_Deck, Tank_Deck_Port,
  HVAC_TankDeck}`) split into `HVAC_Machinery → Tank_Deck` and
  `HVAC_Machinery → Tank_Deck_Port` at 25.0 m³/h each, preserving 50/12 per
  room pair.

`data/platforms/san_antonio_class_lpd/spatial_layout.json`

- `exposure: "weather"` added to `Flight_Deck`, `Well_Deck`.

`data/platforms/san_antonio_class_lpd/air_flow_paths.json`

- `HVAC_Well_Deck` removed entirely: after `Well_Deck` leaves, it has no rooms.
- `HVAC_Aviation.rooms`: `["Flight_Deck", "Hangar"]` → `["Hangar"]`; `Hangar`
  is not stranded (`tools/contam_commissioned_check.py` PASS).
- Two `ambient_openings` records added.
- `vehicle_ramp` re-addressed `HVAC_Vehicle_Deck → Well_Deck` at 500.0 m³/h.
- `aft_passageway` split into `HVAC_Aviation → Well_Deck` and
  `Flight_Deck → Well_Deck` at 150.0 m³/h each.
- `Sanitary_Makeup` `HVAC_Aviation → AHU_HD_01L_M/F` split so `Flight_Deck`
  keeps its two 178.4 m³/h legs to the same sanitary terminals. This raises the
  fleet `Sanitary_Makeup` link count in `tests/test_forced_exhaust_audit.py`
  by two declared links (per-destination reference flow is unchanged): 585→587
  against the pre-battleship main, and 587→589 in the merged tree after
  `CONTAM-GROUPED-WEATHER-BATTLESHIP-01` landed on main. The audit invariants
  still hold: all oneway, no native reverse, reconciled.

`data/platforms/{fort_mandan_lsd21,middlesex_lst983}/contam/{platform.prj,path_map.json}`
regenerated with `scripts/generate_platform_contam_prj.py --platform
fort_mandan_lsd21 --platform middlesex_lst983 --ahs-terminal-mode commissioned`.
`san_antonio_class_lpd` has no committed bundle to regenerate.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES` gains the seven
new zones and the amphibious comment now points at this entry;
`tests/test_contam_ambient_opening_boundary.py` committed-leg census moves
`middlesex_lst983` 14 → 18 and adds `fort_mandan_lsd21: 6` (`san_antonio_class_lpd`
has no committed path map). Both moves are exactly the new opening legs.

No engine, exporter or schema code changed.

## Area witness (Grade C)

`area_m2` = ASSUMED-OPEN-DECK-FACE-AREA, Grade C: `2 × sqrt(V / 3) × 3`, the
stage-4 square-plan deck-face rule, not a measured area and not adjusted
against any pressure result. Volumes are the zone volumes in
`spatial_layout.json`.

## D5 exchange

`exchange_m3h` is the commissioned-lane ContamX-solved **outward** flow of each
new opening at the committed 1 m/s fleet-default wind, measured after the
authoring edits (`tools/contam_flow_compare.py --run-contamx` /
`tools/diag/contam_pressure_balance_diagnostic.py --lane commissioned`). The
inward leg is the paired orifice's opposite direction; net inward is
inward − outward. The audit-style net inward figure was not used as
`exchange_m3h`.

| hull | zone | V, m³ | area_m2 | outward = `exchange_m3h`, m³/h | inward, m³/h | net inward, m³/h |
|---|---|---:|---:|---:|---:|---:|
| `fort_mandan_lsd21` | `Top_House_Open` | 1,094.47 | 114.602 | 75,973.8 | 77,419.3 | 1,445.5 |
| `fort_mandan_lsd21` | `Well_Cover_Open` | 2,162.21 | 161.079 | 108,389.4 | 107,218.0 | −1,171.3 |
| `fort_mandan_lsd21` | `Well_Deck` | 13,000.00 | 394.968 | 313,702.9 | 321,152.5 | 7,449.6 |
| `middlesex_lst983` | `Tank_Deck` | 4,200.00 | 224.499 | 179,757.2 | 180,805.3 | 1,048.0 |
| `middlesex_lst983` | `Tank_Deck_Port` | 444.76 | 73.056 | 58,601.2 | 58,731.3 | 130.0 |
| `san_antonio_class_lpd` | `Flight_Deck` | 600.00 | 84.853 | 55,865.9 | 57,108.4 | 1,242.5 |
| `san_antonio_class_lpd` | `Well_Deck` | 3,800.00 | 213.542 | 141,014.6 | 143,305.5 | 2,290.9 |

`exchange_m3h` is the native exchange-sink magnitude; the ContamW export's
paired ambient orifices are driven by `area_m2`, wind and schedule. The two
committed bundles were regenerated after the write-back and `git status` shows
no further `contam/` changes.

Middlesex note: the two new openings join seven stage-4 openings. Hull-level
ambient-opening net inward moved 1,920.502 → 1,923.974 m³/h; the new zones'
own net inward is 1,178.077 m³/h, so the pre-existing openings' net inward fell
by about 1,174.606 m³/h as the pressure field redistributed. Their committed
`exchange_m3h` values were not rewritten in this PR.

## No double-count / stranding witnesses

- `tools/contam_commissioned_check.py --platform fort_mandan_lsd21 --platform
  middlesex_lst983 --platform san_antonio_class_lpd`: PASS, every commissioned
  terminal inside 5 % of declared. Remaining group rooms are not stranded;
  `HVAC_TankDeck` and `HVAC_Well_Deck` were removed only when empty.
- `tools/contam_flow_compare.py --run-contamx` after the final data commit:
  `fort_mandan_lsd21` native 690 paths vs ContamX path_map 502 rows,
  `ambient_openings` n=6, sink-out 4.981e5 m³/h, inward 5.058e5 m³/h;
  `middlesex_lst983` native 353 paths vs path_map 302 rows,
  `ambient_openings` n=18, sink-out 5.609e5 m³/h, inward 5.628e5 m³/h.
  `san_antonio_class_lpd` has no committed path_map for the
  standalone compare; its commissioned check above is the ContamX witness.
- Pressure diagnostic `--lane design --lane commissioned --lane authored`:
  commissioned and design rows solve with 0 unsolved for all three hulls. The
  authored lane has the expected `san_antonio_class_lpd`
  `FileNotFoundError` for the absent committed `platform.prj`, not a solver
  failure.

## Pressure diagnostic rows (commissioned lane)

Before is `4a3d7a55`; after is measured on `8176acf3`. Columns are the
pressure diagnostic's envelope max |ΔP|, interior max |ΔP|, make-up demand,
opening net inward and balance residual. `exchange_m3h` is the sum of the new
records' outward flows for the hull.

| hull | when | envelope max \|ΔP\|, Pa | interior max \|ΔP\|, Pa | make-up demand, m³/h | opening net inward, m³/h | balance residual, m³/h | `exchange_m3h` sum, m³/h |
|---|---|---:|---:|---:|---:|---:|---:|
| `fort_mandan_lsd21` | before | 294,490.0 | 3.8 | 7,742.4927 | 0.0 | 2.24e-05 | 0 |
| `fort_mandan_lsd21` | after | 9.179 | 9.773 | 7,742.4927 | 7,723.826 | −0.01104 | 498,065.9 |
| `middlesex_lst983` | before | 3.310 | 1.806 | 1,926.4794 | 1,920.502 | 0.006067 | 0 new |
| `middlesex_lst983` | after | 2.812 | 1.917 | 1,926.7788 | 1,923.974 | −0.002842 | 238,358.5 |
| `san_antonio_class_lpd` | before | 198,022.969 | 14,575.515 | 3,580.8064 | 0.0 | 1.11e-05 | 0 |
| `san_antonio_class_lpd` | after | 67.574 | 45.925 | 3,580.8064 | 3,533.332 | −0.002210 | 196,880.5 |

Reading: on `fort_mandan_lsd21` and `san_antonio_class_lpd` the HVAC-group OA
legs had produced MPa-scale envelope residuals; replacing them with the seven
authorised openings collapses those residuals to tens of Pa while make-up demand
is essentially unchanged (the demand is now supplied through the openings, not
distributed envelope leaks). `middlesex_lst983` already had stage-4 openings,
so its move is small. Interior max |ΔP| rises modestly on Fort/Middlesex as the
make-up path concentrates at the new decks; this is measured, not tuned.

## Validation

- Non-target hulls byte-identical: `git status`/`git diff --name-only` show
  only the three target platform directories and the two guard tests; no
  Pope/Aeolus/fiction path moved.
- `python3 -m pytest tests/ -m 'not slow' -n auto` (fast tier).
- `python3 -m pytest tests/test_ledger_entries.py`.
- `python3 scripts/sonar_guard.py tests/test_contam_ambient_opening.py tests/test_contam_ambient_opening_boundary.py`.
- Schema/data-contract checks for edited platform JSON.
- `python3 tools/contam_commissioned_check.py --platform fort_mandan_lsd21 --platform middlesex_lst983 --platform san_antonio_class_lpd`: PASS.
- ContamX pressure witnesses: commissioned/design 0 unsolved; authored lane has
  only the expected absent-bundle `san_antonio_class_lpd` row.

## Reproduction

```bash
.venv/bin/python scripts/generate_platform_contam_prj.py \
  --platform fort_mandan_lsd21 --platform middlesex_lst983 \
  --ahs-terminal-mode commissioned
.venv/bin/python tools/contam_commissioned_check.py \
  --platform fort_mandan_lsd21 --platform middlesex_lst983 \
  --platform san_antonio_class_lpd
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull fort_mandan_lsd21 --hull middlesex_lst983 --hull san_antonio_class_lpd \
  --lane design --lane commissioned --lane authored --all-paths \
  --timeout-s 1800
.venv/bin/python tools/contam_flow_compare.py --platform fort_mandan_lsd21 --run-contamx
.venv/bin/python tools/contam_flow_compare.py --platform middlesex_lst983 --run-contamx
```
