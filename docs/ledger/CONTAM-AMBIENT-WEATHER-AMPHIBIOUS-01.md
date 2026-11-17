# CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01
**Date:** 2026-11-17
**Commit:** eb7d72ee
**Pathogens:** all
**Status:** measured
**Measured at:** eb7d72ee

## Scope

After-witnesses measured on this branch at `2b44cf7f`; before-witnesses were the
same solves on the pre-change `data/platforms` state at `6c6c9f3b` before
authoring. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **amphibious naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: the five `lst`/`lsm`/`lsd`/`lpd`/`apd` hulls. Exact roster
and borderline calls are in the table below.

OWNER RULING (Benjamin, 2026-11-16): the Grade C deck-face area rule and its
large solved rates are ACCEPTED as declared assumptions — record, do not tune.
Fleet default wind stays 1 m/s from ahead (#1266) unless you justify otherwise.

Only ungrouped amphibious weather/open-deck zones are stage-4 candidates.
Weather zones already in an HVAC group with outdoor-air exchange stay
untouched under the scope rule and are recorded as the known grouped-zone
open item. Each qualifying zone keeps its finite zone (D2(a)), declares
`exposure: weather` (D7(b)) and carries one `open_deck` `ambient_openings`
record (D1(a)) with the Grade C deck-face area rule, `wind_speed_m_s` 1 m/s
committed on the declared 0–10 m/s axis, `schedule: always_open`, and
`exchange_m3h` = the commissioned-lane ContamX-solved outward flow at that
point (D5). No `flow_rate_m3h`, `envelope_leak.area_m2`, engine/exporter
constant, wind override, balcony, hatch or door changed. Naval hulls keep the
fleet default weather from `CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead).

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-AMBIENT-WEATHER-DESTROYER-01`](CONTAM-AMBIENT-WEATHER-DESTROYER-01.md),
[`CONTAM-AMBIENT-WEATHER-CARRIER-01`](CONTAM-AMBIENT-WEATHER-CARRIER-01.md),
[`CONTAM-AMBIENT-WEATHER-BATTLESHIP-01`](CONTAM-AMBIENT-WEATHER-BATTLESHIP-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

| hull | weather/open-deck zones (lexical/authored) | HVAC group | call |
|---|---|---|---|
| `fort_mandan_lsd21` | `Top_House_Open`, `Well_Cover_Open`, `Well_Deck` | `VENT_Machinery_Holds`, `VENT_Well_Deck` | skip: grouped (outdoor ACH 4.5 / 2.0) |
| `lsm_354` | `Forecastle_Weather`, `Bridge_Wings`, `Weather_Aft_Super`, `Weather_Fwd_Super` | none | **authored** |
| `middlesex_lst983` | `Gun_Platform_Aft_Bridge`, `Boat_Deck`, `Gun_Platforms_Fwd_Bridge`, `Fantail_Main`, `Gun_Platform_Aft_Main`, `Weather_Deck_Amids`, `Forecastle_Bow`; `Tank_Deck`, `Tank_Deck_Port` | none for the seven openings; `HVAC_TankDeck` for the tank decks | **authored** openings; tank decks skip: grouped (outdoor ACH 1.2) |
| `ruchamkin_apd89` | `Boat_Deck_Open`, `Island_Open_Aft`, `Fantail`, `Focsle_Deck`; `Signal_Deck` | none for the four openings; `HVAC_Accom` for `Signal_Deck` | **authored** openings; `Signal_Deck` enclosed correction |
| `san_antonio_class_lpd` | `Well_Deck`, `Flight_Deck`; `Vehicle_Deck` | `HVAC_Well_Deck`, `HVAC_Aviation`, `HVAC_Vehicle_Deck` | well/flight decks skip: grouped (outdoor ACH 3.0 / 3.2); `Vehicle_Deck` enclosed correction |

Borderline calls: `middlesex_lst983/Gun_Platform_Aft_Main` is authored because
it is an ungrouped Free main-deck gun platform with davits even though its
description does not say "weather"; `lsm_354/Bow_Ramp_Area` stays unopened
because it is the intermittent bow-ramp area rather than a routine open
weather deck; `fort_mandan_lsd21` and `san_antonio_class_lpd` therefore have
no qualifying zero-outdoor-exchange weather zones and are recorded/skipped.

## Exposure calls

- **Weather records: 15** (`lsm_354` 4, `middlesex_lst983` 7,
  `ruchamkin_apd89` 4). Ten were already lexical weather zones in
  `CONTAM-AMBIENT-EXPOSURE-01`; the authored `exposure: weather` makes the
  fact explicit for the opening guard. Five were lexical misses and are the
  D7(b) authoring: `lsm_354/Bridge_Wings`,
  `middlesex_lst983/Gun_Platform_Aft_Bridge`,
  `middlesex_lst983/Gun_Platforms_Fwd_Bridge`,
  `middlesex_lst983/Gun_Platform_Aft_Main`,
  `middlesex_lst983/Forecastle_Bow`.
- **Enclosed corrections: 2.** `ruchamkin_apd89/Signal_Deck` (signal
  shelter/flag-plot level on the accommodation group) and
  `san_antonio_class_lpd/Vehicle_Deck` (enclosed vehicle storage above the
  well deck) carry `exposure: enclosed` and no opening.
- **Grouped open item: 7 zones** stay untouched by the scope rule:
  `fort_mandan_lsd21/Top_House_Open` on `VENT_Machinery_Holds`,
  `fort_mandan_lsd21/Well_Cover_Open` and `Well_Deck` on `VENT_Well_Deck`,
  `middlesex_lst983/Tank_Deck` and `Tank_Deck_Port` on `HVAC_TankDeck`,
  `san_antonio_class_lpd/Well_Deck` on `HVAC_Well_Deck` and `Flight_Deck` on
  `HVAC_Aviation`. `san_antonio_class_lpd/Vehicle_Deck` is not counted here
  because the enclosed correction removes it from the weather inventory.

## Bundles and design pins

Regenerated the three affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record: `lsm_354` +8,
`middlesex_lst983` +14, `ruchamkin_apd89` +8. `exposure` is audit metadata,
not an exporter input, so `fort_mandan_lsd21` and `san_antonio_class_lpd`
needed no bundle regeneration (`san_antonio_class_lpd` has no committed
`contam/` bundle). A targeted repository reference search found no
campaign/frozen design file naming an amphibious `path_map_entries` pin that
moves here, so no `_v2` succession was needed; `_01`/`_v1` artifacts are
byte-untouched. No cache was produced or uploaded.

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (design, commissioned and
authored lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the
amphibious hulls are not in the tool's default `PLATFORM_SOURCES`, so the same
matrix was run programmatically with explicit sources, native/commissioned/
authored lanes and `pulse_t0`/`split_t0_t1`: 12 cells per hull per run).
`tools/contam_commissioned_check.py` on the three touched hulls: PASS, every
commissioned terminal inside 5% of declared.

### Openings and D5

| hull | zone | volume m³ | area_m2 | wind_speed_m_s | exchange_m3h | air changes /h | design U=1 out m³/h | commissioned U=1 out m³/h | commissioned U=10 out m³/h | U=1 inward m³/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `lsm_354` | `Forecastle_Weather` | 445.80 | 73.141 | 1.0 | 49,054.7 | 110.04 | 49,059.0 | 49,054.7 | 490,572.4 | 49,063.6 |
| `lsm_354` | `Bridge_Wings` | 99.05 | 34.476 | 1.0 | 23,124.5 | 233.46 | 23,124.5 | 23,124.5 | 231,246.3 | 23,124.4 |
| `lsm_354` | `Weather_Aft_Super` | 384.66 | 67.941 | 1.0 | 45,365.8 | 117.94 | 45,572.5 | 45,365.8 | 455,508.5 | 45,774.9 |
| `lsm_354` | `Weather_Fwd_Super` | 624.86 | 86.593 | 1.0 | 58,026.3 | 92.86 | 58,082.7 | 58,026.3 | 580,744.0 | 58,136.5 |
| `middlesex_lst983` | `Gun_Platform_Aft_Bridge` | 405.70 | 69.774 | 1.0 | 46,653.3 | 114.99 | 46,660.6 | 46,653.3 | 466,585.4 | 46,669.0 |
| `middlesex_lst983` | `Boat_Deck` | 170.06 | 45.174 | 1.0 | 30,125.5 | 177.15 | 30,209.0 | 30,125.5 | 302,004.2 | 30,294.3 |
| `middlesex_lst983` | `Gun_Platforms_Fwd_Bridge` | 333.45 | 63.257 | 1.0 | 42,221.8 | 126.62 | 42,302.2 | 42,221.8 | 422,931.9 | 42,384.0 |
| `middlesex_lst983` | `Fantail_Main` | 60.22 | 26.882 | 1.0 | 17,867.3 | 296.70 | 17,977.3 | 17,867.3 | 179,636.5 | 18,086.2 |
| `middlesex_lst983` | `Gun_Platform_Aft_Main` | 119.88 | 37.928 | 1.0 | 24,965.9 | 208.26 | 25,364.5 | 24,965.9 | 253,305.9 | 25,756.0 |
| `middlesex_lst983` | `Weather_Deck_Amids` | 1,179.95 | 118.993 | 1.0 | 79,343.1 | 67.24 | 79,577.5 | 79,343.1 | 795,529.8 | 79,807.1 |
| `middlesex_lst983` | `Forecastle_Bow` | 1,215.71 | 120.783 | 1.0 | 80,722.0 | 66.40 | 80,773.2 | 80,722.0 | 807,664.9 | 80,822.9 |
| `ruchamkin_apd89` | `Boat_Deck_Open` | 1,051.33 | 112.321 | 1.0 | 75,141.5 | 71.47 | 75,156.9 | 75,141.5 | 751,519.9 | 75,172.4 |
| `ruchamkin_apd89` | `Island_Open_Aft` | 182.66 | 46.818 | 1.0 | 30,994.9 | 169.69 | 31,327.1 | 30,994.9 | 312,968.7 | 31,656.0 |
| `ruchamkin_apd89` | `Fantail` | 213.08 | 50.566 | 1.0 | 33,620.4 | 157.78 | 33,835.9 | 33,620.4 | 338,128.4 | 34,048.2 |
| `ruchamkin_apd89` | `Focsle_Deck` | 303.64 | 60.363 | 1.0 | 40,315.7 | 132.77 | 40,391.0 | 40,315.7 | 403,821.9 | 40,464.9 |

D5 sweep, commissioned outward flow m³/h at U = 0 / 1 / 5 / 10 m/s:
`lsm_354` 76.3 / 175,571.3 / 878,913.5 / 1,758,071.3;
`middlesex_lst983` 89.9 / 321,898.9 / 1,613,347.9 / 3,227,658.7;
`ruchamkin_apd89` 68.3 / 180,072.5 / 902,901.3 / 1,806,439.0.
The declared native rate is the U = 1 m/s solved value rounded to 0.1 m³/h;
the field lane solves the same point to the same outward sink totals
(field ÷ native = 1.000000 on all three hulls). U = 0 is not zero because the
D8 `paired_orifices` export intentionally solves buoyancy-driven counter-flow
as signed outward/inward Flow0 even at calm wind; see Residuals.

### Flow compare (before -> after)

| hull | path_map entries | native links | ambient_opening legs | field opening inward m³/h | field opening outward sink m³/h | native `ambient_exchange_*` links | native exchange total m³/h | field ÷ native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `lsm_354` | 378 -> 386 | 532 -> 536 | 0 -> 8 | 0 -> 176,099.3 | 0 -> 175,571.3 | 0 -> 4 | 0 -> 175,571.3 | 1.000000 |
| `middlesex_lst983` | 291 -> 305 | 348 -> 355 | 0 -> 14 | 0 -> 323,819.4 | 0 -> 321,898.9 | 0 -> 7 | 0 -> 321,898.9 | 1.000000 |
| `ruchamkin_apd89` | 301 -> 309 | 449 -> 453 | 0 -> 8 | 0 -> 181,341.6 | 0 -> 180,072.5 | 0 -> 4 | 0 -> 180,072.5 | 1.000000 |

### Paired source cells (whole-hull material time)

Whole-hull material time h, before -> after; largest cell per hull across the
12-cell matrix (two sources × native/commissioned/authored ×
`pulse_t0`/`split_t0_t1`):

| hull | cells | max abs move h | largest cell |
|---|---:|---:|---|
| `lsm_354` | 12 | 6.91857 | `Forecastle_Weather`/native/`pulse_t0`: 6.92765 -> 0.00907994 |
| `middlesex_lst983` | 12 | 6.72300 | `Forecastle_Bow`/native/`pulse_t0`: 6.73812 -> 0.0151130 |
| `ruchamkin_apd89` | 12 | 6.89431 | `Boat_Deck_Open`/native/`pulse_t0`: 6.90828 -> 0.0139708 |

The same run also wrote the `split_t0_t1` cells; closure errors stayed at
solver roundoff (max |closure_error| 1.23e-15 after across the 72 cells).

### Pressure balance (before -> after)

| hull | lane | paths | max abs dP Pa | balance residual m³/h | envelope net in m³/h | ambient-opening net in m³/h | k field/native median |
|---|---|---:|---:|---:|---:|---:|---:|
| `lsm_354` | design | 378 -> 386 | 89.69178 -> 89.69178 | 5.479e-09 -> -2.700e-04 | -0.0000 -> 5.9022 | 0.0000 -> -5.9019 | 0.61382 -> 0.89019 |
| `lsm_354` | commissioned | 378 -> 386 | 2663.691 -> 89.69178 | -1.403e-06 -> 2.592e-03 | 564.2176 -> 36.1550 | 0.0000 -> 528.0600 | 1.00333 -> 0.99657 |
| `lsm_354` | authored | 378 -> 386 | 2663.691 -> 89.69178 | -1.403e-06 -> 2.592e-03 | 564.2176 -> 36.1550 | 0.0000 -> 528.0600 | 1.00333 -> 0.99657 |
| `middlesex_lst983` | design | 291 -> 305 | 129.79135 -> 129.79135 | -3.824e-08 -> 1.289e-03 | 0.0000 -> 2.3989 | 0.0000 -> -2.4001 | 0.59075 -> 0.87403 |
| `middlesex_lst983` | commissioned | 291 -> 305 | 29682.428 -> 129.79135 | 5.594e-06 -> 6.067e-03 | 1926.4794 -> 5.9708 | 0.0000 -> 1920.5025 | 1.04694 -> 1.00366 |
| `middlesex_lst983` | authored | 291 -> 305 | 29682.428 -> 129.79135 | 5.594e-06 -> 6.067e-03 | 1926.4794 -> 5.9708 | 0.0000 -> 1920.5025 | 1.04694 -> 1.00366 |
| `ruchamkin_apd89` | design | 301 -> 309 | 110.92294 -> 110.92294 | 1.093e-08 -> -2.080e-03 | -0.0000 -> 2.9825 | 0.0000 -> -2.9804 | 0.75888 -> 0.95588 |
| `ruchamkin_apd89` | commissioned | 301 -> 309 | 20262.357 -> 110.92294 | 8.396e-06 -> -2.133e-03 | 1273.9094 -> 4.7868 | 0.0000 -> 1269.1247 | 1.03327 -> 1.00860 |
| `ruchamkin_apd89` | authored | 301 -> 309 | 20262.357 -> 110.92294 | 8.396e-06 -> -2.133e-03 | 1273.9094 -> 4.7868 | 0.0000 -> 1269.1247 | 1.03327 -> 1.00860 |

## Findings

1. Measured: the design lane already sat inside the stage-1 naval range on all
   three hulls (89.692–129.791 Pa) and is unchanged to the printed precision;
   the worst after value is 129.791 Pa on `middlesex_lst983`.
   Commissioned/authored max |ΔP| falls to the same design-lane values on every
   hull because the openings relieve the previously unvented weather zones.
2. Measured: boundary balance residuals stay at the diagnostic's residual
   scale (largest after |residual| 6.067e-03 m³/h on `middlesex_lst983`
   commissioned/authored; before values were ~1e-8–1e-5 m³/h with no
   openings). No hull went unsolved (9/9 pressure rows solved before and
   after) and ContamX converged on every hull and lane.
3. Measured: native `ambient_exchange_open_deck` links rise by exactly one per
   record (4/7/4 links on LSM/Middlesex/Ruchamkin) and the ContamX field lane
   classifies the solved outward legs as `ambient_opening` boundary sinks;
   flow-compare outward sink totals match the D5 commissioned outward totals
   to rounding.
4. Measured: whole-hull material time from a weather source collapses once the
   opening exists (largest moves are the weather `pulse_t0` cells, e.g.
   `lsm_354/Forecastle_Weather/native/pulse_t0` 6.92765 -> 0.00907994 h).
   Interior source cells move much less, as expected for finite weather zones.

## Residuals and open items

1. The `exchange_m3h` values are Grade C solved rates, not measured ship
   ventilation: they are large (17,867.3–80,722.0 m³/h per opening) because
   the area rule is a two-face deck estimate at 1 m/s relative wind. They are
   recorded under the owner acceptance quoted in Scope, not tuned to any
   anchor.
2. The U=10 column is the axis upper bound only; the committed record keeps
   the fleet default 1 m/s point. A per-hull wind override would move the
   ContamX lane but not the native `exchange_m3h`, the same caveat as cruise.
3. Grouped-zone open item: 7 HVAC-grouped weather zones on `fort_mandan_lsd21`,
   `middlesex_lst983` and `san_antonio_class_lpd` remain without
   `ambient_openings` by the scope rule; the owner question on grouped zones
   stays open.
4. The U=0 sweep column is not zero on any hull (68.3–89.9 m³/h outward,
   with larger signed inward counter-flow) because D8 `paired_orifices`
   solves buoyancy-driven counter-flow as signed outward/inward Flow0 even at
   calm wind. This is exporter behavior, not a magnitude fit.
5. `contam_paired_diagnostic.py` CLI choices still exclude these GA hulls;
   coverage here is via the same `_run_matrix` cells with explicit sources,
   not a CLI allow-list change.
6. `fort_mandan_lsd21` and `san_antonio_class_lpd` are roster hulls with no
   qualifying zero-outdoor-exchange weather zones under the scope rule; they
   are recorded/skipped here rather than authored.

## Reproduction

```bash
for h in lsm_354 middlesex_lst983 ruchamkin_apd89; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull lsm_354 --hull middlesex_lst983 --hull ruchamkin_apd89 \
  --lane design --lane commissioned --lane authored \
  --out telemetry_buffer/contam_pressure_balance_diagnostic/amphibious_after.json
for h in lsm_354 middlesex_lst983 ruchamkin_apd89; do
  .venv/bin/python tools/contam_flow_compare.py --platform $h --run-contamx
  .venv/bin/python tools/contam_commissioned_check.py --platform $h
done
```

Before-witnesses were the same solves on the pre-change `data/platforms` state
at `6c6c9f3b` before authoring; the paired matrix was run programmatically with
the explicit sources listed in Witnesses because
`contam_paired_diagnostic.PLATFORM_SOURCES` has no amphibious entries.
