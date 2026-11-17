# CONTAM-AMBIENT-WEATHER-BATTLESHIP-01
**Date:** 2026-11-17
**Commit:** 6f99ad17
**Pathogens:** all
**Status:** measured
**Measured at:** 6f99ad17

## Scope

After-witnesses measured on this branch at `6f99ad17`; before-witnesses at the
pre-change battleship state `32fb0ca1` in a detached `origin/main` worktree.
`origin/main` advanced to `2a7bc166` during the session with only Enterprise
life-support plenum files (#1271) and a CE ledger (#1273); `git diff
32fb0ca1..origin/main` touches no battleship roster file and neither opening
guard test. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **battleship naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: the eight `bb` hulls. `olympia_c6` is a protected cruiser,
not a battleship, and is excluded. Exact roster and borderline calls are in
the table below.

OWNER RULING (Benjamin, 2026-11-16): the Grade C deck-face area rule and its
large solved rates (destroyers 27k–75k m3/h, carriers 318k–337k m3/h per
opening at the 1 m/s fleet default) are ACCEPTED as declared assumptions —
record, do not tune. Fleet default wind stays 1 m/s from ahead (#1266) unless
you justify otherwise.

Only ungrouped battleship weather/open-deck zones are stage-4 candidates.
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
[`CONTAM-AMBIENT-WEATHER-CARRIER-01`](CONTAM-AMBIENT-WEATHER-CARRIER-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

| hull | weather/open-deck zones (lexical/authored) | HVAC group | call |
|---|---|---|---|
| `idaho_bb42` | `Fantail` | `HVAC_Main` | skip: grouped |
| `missouri_bb63` | `Boat_Waist_Open`, `Fantail_Open`, `Focsle_Void_2D`, `Forecastle_Open`, `Signal_Deck` | `VENT_Weather` | skip: grouped |
| `new_jersey_bb62` | `Boat_Waist_Open`, `Fantail_Open`, `Focsle_Void_2D`, `Forecastle_Open`, `Signal_Deck` | `VENT_Weather` | skip: grouped |
| `new_york_bb34` | `Fantail_Weather`, `Focsle_Deck`, `Super_Deck_Open`, `Weather_Deck_Aft`, `Catapult_Mid`, `AA_Control_Top` | none | **authored** |
| `south_dakota_bb49` | `Boat_Deck`, `Fantail`, `Landing_Platform`, `Forecastle` | none | **authored** |
| `texas_bb35` | `Fantail_Weather`, `Focsle_Deck`, `Super_Deck_Open`, `Weather_Deck_Aft`, `Catapult_Mid` | none | **authored** |
| `west_virginia_bb48` | `Boat_Deck`, `Fantail`, `Signal_Bridge_Open`, `Landing_Platform`, `Forecastle` | none | **authored** |
| `wisconsin_bb64` | `Boat_Waist_Open`, `Fantail_Open`, `Focsle_Void_2D`, `Forecastle_Open`, `Signal_Deck` | `VENT_Weather` | skip: grouped |

## Exposure calls

- **Weather records: 20** (`new_york_bb34` 6, `south_dakota_bb49` 4,
  `texas_bb35` 5, `west_virginia_bb48` 5). Thirteen were already lexical
  weather zones in `CONTAM-AMBIENT-EXPOSURE-01`; the authored `exposure:
  weather` makes the fact explicit for the opening guard. Seven were lexical
  misses and are the D7(b) authoring: `new_york_bb34/Catapult_Mid`,
  `new_york_bb34/AA_Control_Top`, `south_dakota_bb49/Landing_Platform`,
  `south_dakota_bb49/Forecastle`, `texas_bb35/Catapult_Mid`,
  `west_virginia_bb48/Landing_Platform`, `west_virginia_bb48/Forecastle`.
- **Enclosed corrections: 0.** `texas_bb35/Signal_Bridge` is a Free zone whose
  description is the signal-bridge/RDF/nav office fit; the lexical fallback
  already treats it as interior, so it carries no `exposure` record and no
  opening.
- **Grouped open item: 16 zones** stay untouched by the scope rule:
  `idaho_bb42/Fantail` on `HVAC_Main`, and five `VENT_Weather` zones on each
  of `missouri_bb63`, `new_jersey_bb62` and `wisconsin_bb64`.

## Bundles and design pins

Regenerated the four affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record: `new_york_bb34` +12,
`south_dakota_bb49` +8, `texas_bb35` +10, `west_virginia_bb48` +10. `exposure`
is audit metadata, not an exporter input, so the three grouped hulls needed
no bundle regeneration. A targeted repository reference search found no
campaign/frozen design file naming a battleship `path_map_entries` pin that
moves here, so no `_v2` succession was needed; `_01`/`_v1` artifacts are
byte-untouched. No cache was produced or uploaded.

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (design, commissioned and
authored lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the
battleship hulls are not in the tool's default `PLATFORM_SOURCES`, so the same
matrix was run programmatically with explicit sources, native/commissioned/
authored lanes and `pulse_t0`/`split_t0_t1`: 12 cells per hull per run).
`tools/contam_commissioned_check.py` on the four touched hulls: PASS, every
commissioned terminal inside 5% of declared.

### Openings and D5

| hull | zone | volume m³ | area_m2 | wind_speed_m_s | exchange_m3h | air changes /h | design U=1 out m³/h | commissioned U=1 out m³/h | commissioned U=10 out m³/h | U=1 inward m³/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `new_york_bb34` | `Fantail_Weather` | 900.00 | 103.923 | 1.0 | 83625.2 | 92.92 | 83,627.5 | 83,625.2 | 695,785.0 | 83,629.9 |
| `new_york_bb34` | `Weather_Deck_Aft` | 1,600.00 | 138.564 | 1.0 | 111482.5 | 69.68 | 111,503.3 | 111,482.5 | 927,671.9 | 111,524.6 |
| `new_york_bb34` | `Catapult_Mid` | 700.00 | 91.652 | 1.0 | 72518.5 | 103.60 | 73,752.9 | 72,518.5 | 612,448.9 | 74,983.8 |
| `new_york_bb34` | `Focsle_Deck` | 1,500.00 | 134.164 | 1.0 | 107916.6 | 71.94 | 107,963.0 | 107,916.6 | 898,223.1 | 108,009.3 |
| `new_york_bb34` | `Super_Deck_Open` | 1,043.17 | 111.884 | 1.0 | 89476.1 | 85.77 | 90,034.5 | 89,476.1 | 748,539.6 | 90,586.9 |
| `new_york_bb34` | `AA_Control_Top` | 113.45 | 36.897 | 1.0 | 24731.8 | 218.00 | 24,731.8 | 24,731.8 | 247,319.9 | 24,731.9 |
| `south_dakota_bb49` | `Landing_Platform` | 179.20 | 46.372 | 1.0 | 31167.4 | 173.93 | 31,167.4 | 31,167.4 | 311,676.6 | 31,166.7 |
| `south_dakota_bb49` | `Boat_Deck` | 4,433.89 | 230.666 | 1.0 | 187417.6 | 42.27 | 188,339.7 | 187,417.6 | 1,547,911.6 | 189,260.2 |
| `south_dakota_bb49` | `Forecastle` | 2,728.62 | 180.951 | 1.0 | 147038.2 | 53.89 | 147,750.1 | 147,038.2 | 1,214,303.0 | 148,468.6 |
| `south_dakota_bb49` | `Fantail` | 1,193.77 | 119.688 | 1.0 | 97014.7 | 81.27 | 97,727.4 | 97,014.7 | 802,944.1 | 98,445.3 |
| `texas_bb35` | `Super_Deck_Open` | 531.60 | 79.870 | 1.0 | 62067.0 | 116.76 | 64,498.0 | 62,067.0 | 534,204.5 | 66,858.5 |
| `texas_bb35` | `Fantail_Weather` | 654.66 | 88.634 | 1.0 | 71568.7 | 109.32 | 71,570.8 | 71,568.7 | 595,472.2 | 71,573.0 |
| `texas_bb35` | `Weather_Deck_Aft` | 1,534.36 | 135.692 | 1.0 | 109551.9 | 71.40 | 109,569.6 | 109,551.9 | 911,591.1 | 109,587.5 |
| `texas_bb35` | `Catapult_Mid` | 654.66 | 88.634 | 1.0 | 70710.5 | 108.01 | 71,571.0 | 70,710.5 | 594,655.5 | 72,432.6 |
| `texas_bb35` | `Focsle_Deck` | 1,636.65 | 140.142 | 1.0 | 112033.8 | 68.45 | 113,163.6 | 112,033.8 | 940,407.4 | 114,296.2 |
| `west_virginia_bb48` | `Signal_Bridge_Open` | 970.67 | 107.926 | 1.0 | 88127.9 | 90.79 | 88,247.9 | 88,127.9 | 725,644.1 | 88,341.8 |
| `west_virginia_bb48` | `Landing_Platform` | 1,061.43 | 112.859 | 1.0 | 76134.8 | 71.73 | 76,319.1 | 76,134.8 | 759,839.4 | 75,801.1 |
| `west_virginia_bb48` | `Boat_Deck` | 4,607.21 | 235.131 | 1.0 | 188493.4 | 40.91 | 192,042.9 | 188,493.4 | 1,577,396.2 | 196,014.7 |
| `west_virginia_bb48` | `Forecastle` | 3,675.15 | 210.004 | 1.0 | 169451.9 | 46.11 | 171,705.4 | 169,451.9 | 1,409,921.5 | 174,004.5 |
| `west_virginia_bb48` | `Fantail` | 1,441.66 | 131.529 | 1.0 | 105768.4 | 73.37 | 107,462.6 | 105,768.4 | 882,692.1 | 109,347.8 |

D5 sweep, commissioned outward flow m³/h at U = 0 / 1 / 5 / 10 m/s:
`new_york_bb34` 258,466.5 / 489,750.7 / 2,077,109.6 / 4,129,988.4;
`south_dakota_bb49` 245,776.4 / 462,637.9 / 1,950,139.7 / 3,876,835.3;
`texas_bb35` 235,466.9 / 425,932.0 / 1,797,990.8 / 3,576,330.7;
`west_virginia_bb48` 312,445.4 / 627,976.4 / 2,690,517.9 / 5,355,493.3.
The declared native rate is the U = 1 m/s solved value rounded to 0.1 m³/h;
the field lane solves the same point to the same outward sink totals
(field ÷ native = 1.000000 on all four hulls). U = 0 is not zero because the
D8 `paired_orifices` export intentionally solves buoyancy-driven counter-flow
as signed outward/inward Flow0 even at calm wind; see Residuals.

### Flow compare (before -> after)

| hull | path_map entries | native links | ambient_opening legs | field opening inward m³/h | field opening outward sink m³/h | native `ambient_exchange_*` links | native exchange total m³/h | field ÷ native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `new_york_bb34` | 1173 -> 1185 | 1888 -> 1894 | 0 -> 12 | 0 -> 493,466.4 | 0 -> 489,750.7 | 0 -> 6 | 0 -> 489,750.7 | 1.000000 |
| `south_dakota_bb49` | 468 -> 476 | 638 -> 642 | 0 -> 8 | 0 -> 467,340.7 | 0 -> 462,637.9 | 0 -> 4 | 0 -> 462,637.9 | 1.000000 |
| `texas_bb35` | 1228 -> 1238 | 1970 -> 1975 | 0 -> 10 | 0 -> 434,747.7 | 0 -> 425,932.0 | 0 -> 5 | 0 -> 425,931.9 | 1.000000 |
| `west_virginia_bb48` | 3518 -> 3528 | 5957 -> 5962 | 0 -> 10 | 0 -> 643,509.8 | 0 -> 627,976.4 | 0 -> 5 | 0 -> 627,976.4 | 1.000000 |

### Paired source cells (whole-hull material time)

Whole-hull material time h, before -> after; largest cell per hull across the
12-cell matrix (two sources × native/commissioned/authored ×
`pulse_t0`/`split_t0_t1`):

| hull | cells | max abs move h | largest cell |
|---|---:|---:|---|
| `new_york_bb34` | 12 | 6.98347 | `AA_Control_Top`/commissioned/`pulse_t0`: 6.98806 -> 0.00458508 |
| `south_dakota_bb49` | 12 | 6.98183 | `Landing_Platform`/commissioned/`pulse_t0`: 6.98758 -> 0.00574630 |
| `texas_bb35` | 12 | 6.72020 | `Focsle_Deck`/native/`pulse_t0`: 6.73488 -> 0.0146783 |
| `west_virginia_bb48` | 12 | 6.97121 | `Fantail`/native/`pulse_t0`: 6.98542 -> 0.0142150 |

The same run also wrote the `split_t0_t1` cells; closure errors stayed at
solver roundoff (max |closure_error| 1.11e-14 before, 5.55e-16 after across
the 48 cells per tree).

### Pressure balance (before -> after)

| hull | lane | paths | max abs dP Pa | balance residual m³/h | envelope net in m³/h | ambient-opening net in m³/h | k field/native median |
|---|---|---:|---:|---:|---:|---:|---:|
| `new_york_bb34` | design | 1173 -> 1185 | 97.949 -> 97.949 | -2.1902e-08 -> -0.0059992 | 0.0000 -> 10.4241 | 0.0000 -> -10.4181 | 1.0984 -> 1.0639 |
| `new_york_bb34` | commissioned | 1173 -> 1185 | 32661 -> 645.28 | 1.1214e-05 -> 0.023929 | 4,135.6 -> 419.8352 | 0.0000 -> 3,715.7 | 1.0208 -> 1.0068 |
| `new_york_bb34` | authored | 1173 -> 1185 | 32661 -> 645.28 | 1.1214e-05 -> 0.023929 | 4,135.6 -> 419.8352 | 0.0000 -> 3,715.7 | 1.0208 -> 1.0068 |
| `south_dakota_bb49` | design | 468 -> 476 | 182.84 -> 182.84 | -5.2159e-08 -> -0.017867 | 0.0000 -> 9.6122 | 0.0000 -> -9.5943 | 0.86475 -> 0.92297 |
| `south_dakota_bb49` | commissioned | 468 -> 476 | 1.9307e+05 -> 14272 | -5.6222e-05 -> -0.0047505 | 6,047.5 -> 1,344.7 | 0.0000 -> 4,702.8 | 1.0374 -> 1.0151 |
| `south_dakota_bb49` | authored | 468 -> 476 | 1.9307e+05 -> 14272 | -5.6222e-05 -> -0.0047505 | 6,047.5 -> 1,344.7 | 0.0000 -> 4,702.8 | 1.0374 -> 1.0151 |
| `texas_bb35` | design | 1228 -> 1238 | 129.79 -> 129.79 | 3.5714e-08 -> -0.0011568 | -0.0000 -> 16.2542 | 0.0000 -> -16.2530 | 1.2566 -> 1.2567 |
| `texas_bb35` | commissioned | 1228 -> 1238 | 1.2829e+05 -> 129.79 | 3.3758e-05 -> 0.0096981 | 9,022.0 -> 206.2940 | 0.0000 -> 8,815.7 | 1.0996 -> 1.0046 |
| `texas_bb35` | authored | 1228 -> 1238 | 1.2829e+05 -> 129.79 | 3.3758e-05 -> 0.0096981 | 9,022.0 -> 206.2940 | 0.0000 -> 8,815.7 | 1.0996 -> 1.0046 |
| `west_virginia_bb48` | design | 3518 -> 3528 | 311.81 -> 311.81 | 1.1547e-07 -> -0.0093592 | -0.0000 -> 41.7243 | 0.0000 -> -41.7150 | 0.75218 -> 0.91066 |
| `west_virginia_bb48` | commissioned | 3518 -> 3528 | 84343 -> 311.81 | 7.4579e-11 -> -0.0029463 | 16,060.6 -> 527.2574 | 0.0000 -> 15,533.4 | 1.4513 -> 1.0119 |
| `west_virginia_bb48` | authored | 3518 -> 3528 | 84343 -> 311.81 | 7.4579e-11 -> -0.0029463 | 16,060.6 -> 527.2574 | 0.0000 -> 15,533.4 | 1.4513 -> 1.0119 |

## Findings

1. Measured: the design lane already sat inside the stage-1 naval range on all
   four hulls (97.949–311.808 Pa) and is unchanged to the printed precision;
   the worst after value is 311.808 Pa on `west_virginia_bb48`.
   Commissioned/authored max |ΔP| falls to the same design-lane values on every
   hull because the openings relieve the previously unvented weather zones.
2. Measured: boundary balance residuals stay at the diagnostic's residual
   scale (largest after |residual| 0.023929 m³/h on `new_york_bb34`
   commissioned; before values were ~1e-8–1e-5 m³/h with no openings). No hull
   went unsolved (12/12 pressure rows solved before and after) and ContamX
   converged on every hull and lane.
3. Measured: native `ambient_exchange_open_deck` links rise by exactly one per
   record (6/4/5/5 links on New York/South Dakota/Texas/West Virginia) and the
   ContamX field lane classifies the solved outward legs as `ambient_opening`
   boundary sinks; flow-compare outward sink totals match the D5 commissioned
   outward totals to rounding.
4. Measured: whole-hull material time from a weather source collapses once the
   opening exists (largest moves are the weather `pulse_t0` cells, e.g.
   `new_york_bb34/AA_Control_Top/commissioned/pulse_t0` 6.98806 -> 0.00458508
   h). Interior source cells move much less, as expected for finite weather
   zones.

## Residuals and open items

1. The `exchange_m3h` values are Grade C solved rates, not measured ship
   ventilation: they are large (24,731.8–188,493.4 m³/h per opening) because
   the area rule is a two-face deck estimate at 1 m/s relative wind. They are
   recorded under the owner acceptance quoted in Scope, not tuned to any
   anchor.
2. The U=10 column is the axis upper bound only; the committed record keeps
   the fleet default 1 m/s point. A per-hull wind override would move the
   ContamX lane but not the native `exchange_m3h`, the same caveat as cruise.
3. Grouped-zone open item: 16 HVAC-grouped weather zones on `idaho_bb42`,
   `missouri_bb63`, `new_jersey_bb62` and `wisconsin_bb64` remain without
   `ambient_openings` by the scope rule; the owner question on grouped zones
   stays open.
4. The U=0 sweep column is not zero on any hull (245,776.4–312,445.4 m³/h
   outward) because D8 `paired_orifices` solves buoyancy-driven counter-flow
   as signed outward/inward Flow0 even at calm wind. This is exporter
   behavior, not a magnitude fit.
5. `contam_paired_diagnostic.py` CLI choices still exclude these GA hulls;
   coverage here is via the same `_run_matrix` cells with explicit `--source`,
   not a CLI allow-list change.

## Reproduction

```bash
for h in new_york_bb34 south_dakota_bb49 texas_bb35 west_virginia_bb48; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull new_york_bb34 --hull south_dakota_bb49 --hull texas_bb35 \
  --hull west_virginia_bb48 \
  --out telemetry_buffer/contam_pressure_balance_diagnostic/battleship_after.json
for h in new_york_bb34 south_dakota_bb49 texas_bb35 west_virginia_bb48; do
  .venv/bin/python tools/contam_flow_compare.py --platform $h --run-contamx
done
.venv/bin/python tools/contam_commissioned_check.py --platform new_york_bb34 \
  --platform south_dakota_bb49 --platform texas_bb35 \
  --platform west_virginia_bb48
```

Before-witnesses were the same solves in a detached `origin/main` worktree at
`32fb0ca1` with `CONTAMX_BINARY` pointed at the same local binary; the
paired matrix was run programmatically with the explicit sources listed in
Witnesses because `contam_paired_diagnostic.PLATFORM_SOURCES` has no
battleship entries.
