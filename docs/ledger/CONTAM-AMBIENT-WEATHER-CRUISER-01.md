# CONTAM-AMBIENT-WEATHER-CRUISER-01
**Date:** 2026-11-17
**Commit:** d590bf11
**Pathogens:** all
**Status:** measured
**Measured at:** d590bf11

## Scope

After-witnesses measured on this branch at `d590bf11`; before-witnesses at
`origin/main` `2a7bc166` (#1267/#1268/#1272 merged; battleship sibling #1274 was
not present). Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **cruiser naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: the `ca`/`cg`/`cl` hulls plus the prompt-listed
`alexander_henry_cgs119` (`cgs` is not one of those suffixes, but the task named
the hull). Exact roster: `alexander_henry_cgs119`, `astoria_ca34`,
`chicago_cg11`, `miami_cl89`. A suffix scan of `data/platforms/` found no other
`ca`/`cg`/`cl`/`cgs` hulls.

Only one roster hull has qualifying stage-4 weather zones.
`alexander_henry_cgs119` has one audit weather zone with zero outdoor exchange
(`Boat_Stowage_Open` on `AHU_Weather`, `ach = 0.0`). The other three rooms served
by the same `AHU_Weather` (`Wheelhouse_Top`, `Bridge_Wings`,
`Forecastle_Working`) are the same open-air deck group: the group description is
"Open-air decks", `vent_mode` is `nat_supply`, and its outdoor exchange is zero.
Under the scope rule — open only ungrouped / zero-outdoor-exchange weather zones —
all four rooms are authored. This is the borderline call: the audit inventory
counts one lexical weather zone on this hull, but the HVAC group description and
natural-supply mode make all four rooms weather-side.

`astoria_ca34` (5 lexical weather zones), `chicago_cg11` (8) and `miami_cl89` (2)
have their lexical weather zones in `VENT_Weather` with `ach = 1.0`,
`hvac_duty = 0.5`, `oa_fraction = 1.0` (computed removal ACH 0.5). Those zones are
already in an HVAC group with OA exchange, so they stay untouched and are
recorded here as the known grouped-zone open item.

Each qualifying zone keeps its finite zone (D2(a)), declares `exposure:
weather` (D7(b)) and carries one `open_deck` `ambient_openings` record (D1(a))
with the Grade C deck-face area rule, `wind_speed_m_s` 1 m/s committed on the
declared 0–10 m/s axis, `schedule: always_open`, and `exchange_m3h` = the
commissioned-lane ContamX-solved outward flow at that point (D5). No
`flow_rate_m3h`, `envelope_leak.area_m2`, engine/exporter constant, wind
override, balcony, hatch or door changed. Naval hulls keep the fleet default
weather from `CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead).

Owner ruling, verbatim (Benjamin, 2026-11-16): "the Grade C deck-face area rule
and its large solved rates are ACCEPTED as declared assumptions — record, do not
tune. Fleet default wind stays 1 m/s from ahead (#1266) unless you justify
otherwise."

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-AMBIENT-WEATHER-DESTROYER-01`](CONTAM-AMBIENT-WEATHER-DESTROYER-01.md),
[`CONTAM-AMBIENT-WEATHER-CARRIER-01`](CONTAM-AMBIENT-WEATHER-CARRIER-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

| hull | audit weather zones | zero outdoor exchange | HVAC group | call |
|---|---:|---:|---|---|
| `alexander_henry_cgs119` | 1 | 1 | `AHU_Weather` (`ach=0.0`, `vent_mode=nat_supply`) | **authored 4 rooms** |
| `astoria_ca34` | 5 | 0 | `VENT_Weather` (`ach=1.0`, duty 0.5, removal ACH 0.5) | skip: grouped with OA exchange |
| `chicago_cg11` | 8 | 0 | `VENT_Weather` (`ach=1.0`, duty 0.5, removal ACH 0.5) | skip: grouped with OA exchange |
| `miami_cl89` | 2 | 0 | `VENT_Weather` (`ach=1.0`, duty 0.5, removal ACH 0.5) | skip: grouped with OA exchange |

Grouped-zone weather zones on the three skipped hulls are the known open item:
they already exchange with outdoor air through their ventilation group, so this
stage does not add a second direct ambient opening.

## Exposure calls

- **Weather records: 4**, all on `alexander_henry_cgs119`:
  `Wheelhouse_Top`, `Bridge_Wings`, `Boat_Stowage_Open`,
  `Forecastle_Working`. The lexical `_is_exterior` fallback was already right
  for `Boat_Stowage_Open`; the other three were authored because the id/type
  match missed them although they are rooms of the "Open-air decks"
  `AHU_Weather` group with zero outdoor exchange. `Boat_Stowage_Open` also
  declares `exposure: weather` so the opening guard sees the same authored
  fact on every qualifying room.
- **Enclosed corrections: 0.** No roster zone was reclassified as enclosed.
- No other roster hull changed `spatial_layout.json`.

## Bundles and design pins

Regenerated the one affected committed bundle with
`python scripts/generate_platform_contam_prj.py --platform alexander_henry_cgs119 --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record (4 records → 8 legs):
path_map entries 227 → 235 and native airflow paths 242 → 246. No frozen Phase
1/2 campaign design names this cruiser hull (the committed Contam campaign
designs are the cruise Phase-1/Phase-2 sets on other hulls), so no `_v2`
succession was needed; `_01`/`_v1` artifacts are byte-untouched. No cache was
produced or uploaded.

## Witnesses

`python -m tools.diag.contam_pressure_balance_diagnostic` (design, commissioned
and authored lanes), `python tools/contam_flow_compare.py --run-contamx`, and
`python -m tools.diag.contam_paired_diagnostic` same cells before/after. The
paired diagnostic CLI does not list this hull, so the same `_run_matrix` cells
were run programmatically with explicit sources `Wheelhouse_Top`,
`Bridge_Wings`, `Boat_Stowage_Open`, `Forecastle_Working`, timings `pulse_t0`
and `split_t0_t1`, and lanes native/commissioned/authored/design: 32 cells per
run. `python tools/contam_commissioned_check.py --platform
alexander_henry_cgs119`: PASS, every commissioned terminal inside 5% of
declared.

### Openings and D5

| zone | volume m³ | area_m2 | wind_speed_m_s | exchange_m3h | design U=1 out m³/h | commissioned U=1 out m³/h | commissioned U=10 out m³/h | commissioned U=1 in m³/h | air changes /h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `Wheelhouse_Top` | 78.55 | 30.702 | 1.0 | 20,542.1 | 20,557.2 | 20,542.1 | 205,588.1 | 20,579.5 | 261.52 |
| `Bridge_Wings` | 69.31 | 28.840 | 1.0 | 19,028.5 | 19,303.0 | 19,028.5 | 192,852.0 | 19,595.1 | 274.54 |
| `Boat_Stowage_Open` | 114.57 | 37.079 | 1.0 | 29,252.6 | 29,468.6 | 29,252.6 | 247,779.7 | 29,656.1 | 255.33 |
| `Forecastle_Working` | 433.23 | 72.102 | 1.0 | 48,267.6 | 48,282.7 | 48,267.6 | 482,841.1 | 48,304.7 | 111.41 |

D5 sweep, commissioned outward flow totals m³/h at U = 0 / 1 / 5 / 10 m/s:
15,785.2 / 117,090.8 / 565,040.3 / 1,129,060.9. The U = 0 totals are the
buoyancy/stack-driven exchange under this hull's deck temperature offsets, not
wind. The declared native rate is the U = 1 m/s solved value rounded to 0.1
m³/h; the field lane solves the same point to 117,090.8 m³/h outward sink
(field ÷ native = 1.000000).

### Flow compare (before -> after)

| path_map entries | native links | ambient_opening legs | field opening inward m³/h | field opening outward sink m³/h | native `ambient_exchange_*` links | native exchange total m³/h | field ÷ native |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 227 -> 235 | 242 -> 246 | 0 -> 8 | 0 -> 118,135.4 | 0 -> 117,090.8 | 0 -> 4 | 0 -> 117,090.8 | 1.000000 |

### Paired source cells (whole-hull material time h, before -> after)

| source | lane | timing | before h -> after h |
|---|---|---|---|
| `Wheelhouse_Top` | native | `pulse_t0` | 4.32951 -> 0.00427773 |
| `Wheelhouse_Top` | native | `split_t0_t1` | 4.29385 -> 0.00427773 |
| `Wheelhouse_Top` | commissioned | `pulse_t0` | 2.84247 -> 0.00583448 |
| `Wheelhouse_Top` | commissioned | `split_t0_t1` | 2.84047 -> 0.00583447 |
| `Wheelhouse_Top` | authored | `pulse_t0` | 2.84247 -> 0.00583448 |
| `Wheelhouse_Top` | authored | `split_t0_t1` | 2.84047 -> 0.00583447 |
| `Wheelhouse_Top` | design | `pulse_t0` | 6.89900 -> 0.00439143 |
| `Wheelhouse_Top` | design | `split_t0_t1` | 6.74647 -> 0.00439124 |
| `Bridge_Wings` | native | `pulse_t0` | 2.67385 -> 0.00454286 |
| `Bridge_Wings` | native | `split_t0_t1` | 2.66844 -> 0.00454286 |
| `Bridge_Wings` | commissioned | `pulse_t0` | 1.32573 -> 0.0181967 |
| `Bridge_Wings` | commissioned | `split_t0_t1` | 1.32572 -> 0.0181967 |
| `Bridge_Wings` | authored | `pulse_t0` | 1.32573 -> 0.0181967 |
| `Bridge_Wings` | authored | `split_t0_t1` | 1.32572 -> 0.0181967 |
| `Bridge_Wings` | design | `pulse_t0` | 6.88062 -> 0.00464633 |
| `Bridge_Wings` | design | `split_t0_t1` | 6.72907 -> 0.00464612 |
| `Boat_Stowage_Open` | native | `pulse_t0` | 3.47560 -> 0.00452431 |
| `Boat_Stowage_Open` | native | `split_t0_t1` | 3.46014 -> 0.00452431 |
| `Boat_Stowage_Open` | commissioned | `pulse_t0` | 1.85277 -> 0.0118063 |
| `Boat_Stowage_Open` | commissioned | `split_t0_t1` | 1.85258 -> 0.0118063 |
| `Boat_Stowage_Open` | authored | `pulse_t0` | 1.85277 -> 0.0118063 |
| `Boat_Stowage_Open` | authored | `split_t0_t1` | 1.85258 -> 0.0118063 |
| `Boat_Stowage_Open` | design | `pulse_t0` | 6.93951 -> 0.00388634 |
| `Boat_Stowage_Open` | design | `split_t0_t1` | 6.78409 -> 0.00388634 |
| `Forecastle_Working` | native | `pulse_t0` | 6.29193 -> 0.00915996 |
| `Forecastle_Working` | native | `split_t0_t1` | 6.17309 -> 0.00915996 |
| `Forecastle_Working` | commissioned | `pulse_t0` | 5.30859 -> 0.00982038 |
| `Forecastle_Working` | commissioned | `split_t0_t1` | 5.24227 -> 0.00982037 |
| `Forecastle_Working` | authored | `pulse_t0` | 5.30859 -> 0.00982038 |
| `Forecastle_Working` | authored | `split_t0_t1` | 5.24227 -> 0.00982037 |
| `Forecastle_Working` | design | `pulse_t0` | 6.96834 -> 0.00920745 |
| `Forecastle_Working` | design | `split_t0_t1` | 6.81126 -> 0.00920737 |

Closure errors stayed at solver roundoff (max |closure error| 5.7e-15 before,
5.6e-16 after across the 32 cells per run).

### Pressure balance (before -> after)

| lane | paths | max abs dP Pa | ambient net in m³/h | envelope net in m³/h | balance residual m³/h |
|---|---:|---:|---:|---:|---:|
| design | 227 -> 235 | 1.90668 -> 2.20250 | 0 -> 5.71771 | 2.39339e-08 -> -5.71874 | -2.39339e-08 -> 0.00103032 |
| commissioned | 227 -> 235 | 18,995.4 -> 53.9159 | 0 -> 1,044.61 | 1,079.97 -> 35.363 | -2.80096e-06 -> 0.00127068 |
| authored | 227 -> 235 | 18,995.4 -> 53.9159 | 0 -> 1,044.61 | 1,079.97 -> 35.363 | -2.80096e-06 -> 0.00127068 |

Design-lane after max |ΔP| is 2.2025 Pa, inside the stage-1 naval design range
0.5–374 Pa; the commissioned/authored lane maxima fall from 18,995.4 Pa to
53.9 Pa. Balance residuals stay at solver-noise level (largest after magnitude
0.00127 m³/h on 117,090.8 m³/h of ambient-opening throughflow, ~1.1e-8
relative); the mass balance is not broken. ContamX converged on every lane.

## Residuals / open items

- The four `alexander_henry_cgs119` openings use the accepted Grade C
  deck-face area rule and the large solved rates recorded above; they are
  declared assumptions, not measured deck free area or wind.
- The three skipped cruiser hulls keep `VENT_Weather` grouped OA exchange;
  whether any of those grouped weather zones should also get a direct ambient
  opening remains the known grouped-zone open item.

## Reproduction

```bash
python scripts/generate_platform_contam_prj.py --platform alexander_henry_cgs119 \
  --ahs-terminal-mode commissioned
python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull alexander_henry_cgs119 --lane design --lane commissioned --lane authored \
  --out telemetry_buffer/cruiser_weather_pressure_after.json
python tools/contam_flow_compare.py --platform alexander_henry_cgs119 --run-contamx
python tools/contam_commissioned_check.py --platform alexander_henry_cgs119
```
