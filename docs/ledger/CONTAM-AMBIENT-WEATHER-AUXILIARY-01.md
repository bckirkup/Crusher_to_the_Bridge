# CONTAM-AMBIENT-WEATHER-AUXILIARY-01
**Date:** 2026-11-17
**Commit:** 07a1ac4c
**Pathogens:** all
**Status:** measured
**Measured at:** 07a1ac4c

## Scope

After-witnesses measured on this branch at `07a1ac4c`; before-witnesses at the
pre-change auxiliary state `6c6c9f3b` in a detached `origin/main` worktree.
Steady ContamX solves with the local binary `third_party/contamx/contamx3`;
no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **auxiliary naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: 19 auxiliary-type hulls. Exact roster, type-suffix rule and
borderline calls are below.

OWNER RULING (Benjamin, 2026-11-16): the Grade C deck-face area rule and its
large solved rates are ACCEPTED as declared assumptions — record, do not tune.
Fleet default wind stays 1 m/s from ahead (#1266) unless you justify otherwise.

SCOPE RULE (status quo, owner question open): open ONLY weather zones with zero
outdoor exchange (ungrouped OR grouped with zero OA exchange). Weather zones
already exchanging via an HVAC group with OA > 0 stay untouched — recorded
below as the known grouped-zone open item.

Only qualifying auxiliary weather/open-deck zones are stage-4 candidates. Each
keeps its finite zone (D2(a)), declares `exposure: weather` (D7(b)) and carries
one `open_deck` `ambient_openings` record (D1(a)) with the Grade C deck-face
area rule, `wind_speed_m_s` 1 m/s committed on the declared 0–10 m/s axis,
`schedule: always_open`, and `exchange_m3h` = the commissioned-lane
ContamX-solved outward flow at that point (D5). No `flow_rate_m3h`,
`envelope_leak.area_m2`, engine/exporter constant, wind override, balcony,
hatch or door changed. Auxiliary hulls keep the fleet default weather from
`CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead).

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-AMBIENT-WEATHER-DESTROYER-01`](CONTAM-AMBIENT-WEATHER-DESTROYER-01.md),
[`CONTAM-AMBIENT-WEATHER-CARRIER-01`](CONTAM-AMBIENT-WEATHER-CARRIER-01.md),
[`CONTAM-AMBIENT-WEATHER-BATTLESHIP-01`](CONTAM-AMBIENT-WEATHER-BATTLESHIP-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

Type-suffix rule: auxiliary-type naval hulls — `ao`, `ap`, `aoe`, `ar`, `arg`,
`aks`, `apa`, `ak`, `nsc`, `arc`, `ars`, `apl`, cargo-type suffixes and tenders.
Borderline calls: `alexander_henry_cgs119` was included as a CGS buoy tender
but is excluded here because `CONTAM-AMBIENT-WEATHER-CRUISER-01` owns it;
`legend_class_nsc` included by the stated `nsc` suffix although it is a cutter;
`luzon_arg2` included as an ARG repair ship; `cobalt_k124`, `savannah_ns` and
`gordon_gunter_r338` included because the prompt named them despite borderline
type. The exact roster is the 19 hulls below; other naval classes are untouched.

| hull | call | note |
|---|---|---|
| `aeolus_arc3` | authored | ARC cable repair ship; 3 openings |
| `alexander_henry_cgs119` | skip | CGS buoy tender borderline; owned by CONTAM-AMBIENT-WEATHER-CRUISER-01 |
| `apl_24` | authored | APL barracks craft; 4 openings |
| `assistance_ar17` | skip | AR repair ship; weather zones grouped on `HVAC_Accom` OA 3.0 |
| `bolster_ars38` | authored | ARS salvage ship; 4 openings |
| `cobalt_k124` | authored | prompt-named borderline corvette; 3 openings |
| `gordon_gunter_r338` | authored | prompt-named borderline AGOR; 4 openings |
| `gosper_apa170` | partial | APA attack transport; grouped weather skipped, 2 stores zones enclosed |
| `jupiter_ac3` | partial | AC collier; `Passage_Deckhouse` enclosed, grouped decks skipped |
| `legend_class_nsc` | skip | NSC suffix borderline cutter; only OA>0 grouped weather zones |
| `liberty_cargo_ec2` | authored | cargo-type Liberty ship; 6 openings |
| `luzon_arg2` | skip | ARG repair ship; only OA>0 grouped weather zones |
| `lyon_ap71` | authored | AP transport; 11 openings |
| `mercury_aks20` | skip | AKS stores ship; only OA>0 grouped weather zones |
| `passumpsic_ao106` | authored | AO oiler; 4 openings, `Signal_Deck` enclosed |
| `pope_ap110` | partial | APA attack transport; `Sup_Deck_Mech` enclosed, grouped decks skipped |
| `savannah_ns` | authored | prompt-named merchant/nuclear boundary; 14 openings |
| `squier_ap130` | skip | AP transport; only OA>0 grouped weather zone |

## Exposure calls

- **Weather records: 53** `open_deck` records on 9 hulls (`aeolus_arc3` 3,
  `apl_24` 4, `bolster_ars38` 4, `cobalt_k124` 3, `gordon_gunter_r338` 4,
  `liberty_cargo_ec2` 6, `lyon_ap71` 11, `passumpsic_ao106` 4,
  `savannah_ns` 14). 34 were already lexical weather zones in
  `CONTAM-AMBIENT-EXPOSURE-01`; 19 were lexical misses and are the
  D7(b) authoring (open weather/platform zones found by description/deck, not
  by id). The authored `exposure: weather` makes the fact explicit for the
  opening guard on every record.
- **Enclosed corrections: 5.** `gosper_apa170/Focsle_Stores`,
  `gosper_apa170/Focsle_Stores_2D`, `jupiter_ac3/Passage_Deckhouse`,
  `passumpsic_ao106/Signal_Deck` and `pope_ap110/Sup_Deck_Mech` declare
  `exposure: enclosed` with no opening; 5 of them were
  lexical exterior misses. They carry no airflow change.
- **Grouped open item:** HVAC-grouped weather zones with OA > 0 remain
  untouched by the scope rule; owner question on grouped zones stays open.
  `assistance_ar17` `HVAC_Accom` OA 3.0 (4 zones); `gosper_apa170`
  `VENT_Machinery_Holds` OA 4.5 (4 open weather zones — the two stores zones
  are enclosed corrections above); `jupiter_ac3` `VENT_Cargo` OA 2.0
  (`Poop_Deck_Open`, `Focsle_Deck_Open`); `legend_class_nsc` `HVAC_Aviation`
  OA 3.2 (`Flight_Deck`, `Boat_Deck`); `luzon_arg2` `HVAC_Accom` OA 3.0
  (`Gun_Weather_Sup`, `Boat_Deck_Aft`, `Stern_Weather`, `Chain_Locker_Focsle`);
  `mercury_aks20` `HVAC_Accom` OA 3.0 (`Fantail`, `Foredeck`);
  `pope_ap110` `VENT_Stores_Holds` OA 0.8 (`Boat_Deck_Open`, `Stern_Gun_Deck`,
  `Focsle_Deck`); `squier_ap130` `VENT_Stores_Open` OA 2.0 (`Stern_Deck_Up`).

## Bundles and design pins

Regenerated the nine affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record (106 legs total). The five
enclosed-correction hulls needed no bundle regeneration: `exposure` is audit
metadata, not an exporter input. No frozen Phase 1/2 design, source-pool or
campaign pin for this roster moved; `_01`/`_v1` artifacts and caches are
untouched and no cache was produced or uploaded.

| hull | records | path legs | paths before -> after |
|---|---:|---:|---:|
| `aeolus_arc3` | 3 | 6 | 357 -> 363 |
| `apl_24` | 4 | 8 | 306 -> 314 |
| `bolster_ars38` | 4 | 8 | 175 -> 183 |
| `cobalt_k124` | 3 | 6 | 284 -> 290 |
| `gordon_gunter_r338` | 4 | 8 | 268 -> 276 |
| `liberty_cargo_ec2` | 6 | 12 | 551 -> 563 |
| `lyon_ap71` | 11 | 22 | 511 -> 533 |
| `passumpsic_ao106` | 4 | 8 | 202 -> 210 |
| `savannah_ns` | 14 | 28 | 822 -> 850 |

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (authored, commissioned and
design lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the auxiliary
hulls are not in the tool's default `PLATFORM_SOURCES`, so the same `_run_matrix`
cells were run programmatically with explicit sources — the two largest-area
`open_deck` zones per hull — native/commissioned/authored lanes and
`pulse_t0`/`split_t0_t1`: 12 cells per hull per run).
`tools/contam_commissioned_check.py` on the nine touched hulls: PASS, every
commissioned terminal inside 5% of declared.

### Openings and D5

| hull | zone | volume m³ | area_m2 | wind_speed_m_s | exchange_m3h | air changes /h | design U=1 out m³/h | commissioned U=1 out m³/h | commissioned U=10 out m³/h | U=1 inward m³/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `aeolus_arc3` | `Top_Of_House` | 1,063.45 | 112.966 | 1.0 | 75,567.4 | 71.06 | 75,697.6 | 75,567.4 | 756,862.7 | 75,831.6 |
| `aeolus_arc3` | `Cable_Working_Deck` | 2,326.53 | 167.088 | 1.0 | 111,826.0 | 48.07 | 111,963.9 | 111,826.0 | 1,119,516.1 | 112,106.6 |
| `aeolus_arc3` | `Bow_Sheave_Area` | 162.86 | 44.208 | 1.0 | 29,500.0 | 181.14 | 29,622.6 | 29,500.0 | 296,133.1 | 29,747.5 |
| `apl_24` | `Fantail_Main` | 128.12 | 39.210 | 1.0 | 25,287.5 | 197.37 | 26,103.9 | 25,287.5 | 260,226.7 | 26,895.5 |
| `apl_24` | `Fantail_Upper` | 195.13 | 48.390 | 1.0 | 31,477.0 | 161.31 | 32,216.1 | 31,477.0 | 321,534.3 | 32,937.6 |
| `apl_24` | `Forecastle` | 369.57 | 66.595 | 1.0 | 41,359.3 | 111.91 | 44,336.5 | 41,359.3 | 440,687.0 | 47,124.4 |
| `apl_24` | `Gun_Platforms` | 2,931.93 | 187.572 | 1.0 | 124,683.7 | 42.53 | 124,871.0 | 124,683.7 | 1,248,199.7 | 125,064.6 |
| `bolster_ars38` | `Focsle_Deck_Open` | 145.21 | 41.744 | 1.0 | 27,903.3 | 192.16 | 27,903.3 | 27,903.3 | 279,034.8 | 27,903.5 |
| `bolster_ars38` | `Gun_Tub_Fwd` | 122.18 | 38.290 | 1.0 | 25,187.3 | 206.15 | 25,594.5 | 25,187.3 | 255,571.2 | 25,995.8 |
| `bolster_ars38` | `Focsle_Open_Aft` | 531.22 | 79.841 | 1.0 | 53,337.9 | 100.41 | 53,368.4 | 53,337.9 | 533,600.1 | 53,400.5 |
| `bolster_ars38` | `Salvage_Deck` | 527.87 | 79.589 | 1.0 | 52,803.9 | 100.03 | 53,202.4 | 52,803.9 | 531,628.6 | 53,594.7 |
| `cobalt_k124` | `Foc_Deck_Open` | 390.92 | 68.491 | 1.0 | 46,005.9 | 117.69 | 46,009.8 | 46,005.9 | 459,979.8 | 45,982.3 |
| `cobalt_k124` | `Quarterdeck` | 774.96 | 96.434 | 1.0 | 65,162.4 | 84.08 | 65,462.0 | 65,162.4 | 647,988.9 | 64,352.7 |
| `cobalt_k124` | `Stern_Open` | 768.64 | 96.040 | 1.0 | 76,424.6 | 99.43 | 76,712.1 | 76,424.6 | 643,177.4 | 78,438.8 |
| `gordon_gunter_r338` | `Boat_Deck` | 663.25 | 89.213 | 1.0 | 59,789.4 | 90.15 | 60,533.4 | 59,789.4 | 598,322.5 | 59,881.4 |
| `gordon_gunter_r338` | `Shelter_Deck` | 605.22 | 85.221 | 1.0 | 67,055.9 | 110.80 | 67,505.9 | 67,055.9 | 569,369.9 | 70,173.2 |
| `gordon_gunter_r338` | `Aft_Working_Deck` | 333.07 | 63.221 | 1.0 | 49,607.6 | 148.94 | 50,067.2 | 49,607.6 | 422,267.6 | 52,195.8 |
| `gordon_gunter_r338` | `Mission_Deck` | 550.11 | 81.249 | 1.0 | 55,730.2 | 101.31 | 55,734.2 | 55,730.2 | 546,143.8 | 53,228.4 |
| `liberty_cargo_ec2` | `Gun_Platform` | 306.33 | 60.630 | 1.0 | 40,715.9 | 132.92 | 40,716.1 | 40,715.9 | 407,198.9 | 40,724.9 |
| `liberty_cargo_ec2` | `Top_Of_House` | 313.42 | 61.327 | 1.0 | 41,184.2 | 131.40 | 41,184.4 | 41,184.2 | 411,879.9 | 41,193.2 |
| `liberty_cargo_ec2` | `Bridge_Wings` | 39.75 | 21.840 | 1.0 | 17,467.2 | 439.43 | 17,602.1 | 17,467.2 | 146,362.5 | 17,754.3 |
| `liberty_cargo_ec2` | `Boat_Deck_Open` | 90.22 | 32.903 | 1.0 | 26,057.9 | 288.83 | 26,533.9 | 26,057.9 | 220,242.0 | 26,999.2 |
| `liberty_cargo_ec2` | `Aft_Deck_Open` | 156.23 | 43.298 | 1.0 | 34,911.6 | 223.46 | 34,911.9 | 34,911.6 | 290,465.2 | 34,907.5 |
| `liberty_cargo_ec2` | `Forecastle_Deck` | 71.02 | 29.193 | 1.0 | 23,540.9 | 331.47 | 23,543.3 | 23,540.9 | 195,844.7 | 23,533.4 |
| `lyon_ap71` | `Boat_Stowage_Port` | 421.08 | 71.084 | 1.0 | 47,138.0 | 111.95 | 47,699.1 | 47,138.0 | 476,092.0 | 48,167.0 |
| `lyon_ap71` | `Boat_Stowage_Stbd` | 421.08 | 71.084 | 1.0 | 47,125.8 | 111.92 | 47,701.1 | 47,125.8 | 476,072.8 | 48,179.0 |
| `lyon_ap71` | `Boat_Deck_Walkway` | 473.71 | 75.396 | 1.0 | 50,471.0 | 106.54 | 50,560.6 | 50,471.0 | 505,331.8 | 50,620.9 |
| `lyon_ap71` | `Bridge_Wings_Walkway` | 553.56 | 81.503 | 1.0 | 54,621.7 | 98.67 | 54,644.8 | 54,621.7 | 546,371.4 | 54,658.7 |
| `lyon_ap71` | `House_Top_Platform` | 1,139.50 | 116.936 | 1.0 | 78,372.6 | 68.78 | 78,399.8 | 78,372.6 | 783,886.9 | 78,420.1 |
| `lyon_ap71` | `Forecastle_Weather` | 1,894.84 | 150.792 | 1.0 | 101,468.7 | 53.55 | 101,468.7 | 101,468.7 | 1,011,358.9 | 100,715.5 |
| `lyon_ap71` | `Stern_Weather_Shelter` | 755.49 | 95.215 | 1.0 | 75,681.5 | 100.18 | 75,704.6 | 75,681.5 | 637,408.1 | 75,737.3 |
| `lyon_ap71` | `Hatch_4_Weather` | 886.55 | 103.144 | 1.0 | 79,987.8 | 90.22 | 81,956.3 | 79,987.8 | 688,603.4 | 84,017.9 |
| `lyon_ap71` | `Quarter_Weather` | 783.76 | 96.980 | 1.0 | 76,232.8 | 97.27 | 77,071.8 | 76,232.8 | 648,444.3 | 77,994.4 |
| `lyon_ap71` | `Hatch_3_Weather` | 827.44 | 99.646 | 1.0 | 78,970.0 | 95.44 | 79,210.5 | 78,970.0 | 666,839.7 | 79,497.6 |
| `lyon_ap71` | `Bow_Shelter_Weather` | 308.36 | 60.830 | 1.0 | 48,004.6 | 155.68 | 48,008.2 | 48,004.6 | 406,874.9 | 48,734.2 |
| `passumpsic_ao106` | `Island_Deck` | 2,029.15 | 156.044 | 1.0 | 105,451.7 | 51.97 | 105,607.2 | 105,451.7 | 1,047,993.7 | 103,991.0 |
| `passumpsic_ao106` | `Focsle_Deck` | 1,162.15 | 118.092 | 1.0 | 78,943.0 | 67.93 | 79,487.6 | 78,943.0 | 792,240.6 | 79,563.2 |
| `passumpsic_ao106` | `Working_Deck` | 2,953.08 | 188.247 | 1.0 | 150,252.5 | 50.88 | 150,566.9 | 150,252.5 | 1,260,437.4 | 153,099.0 |
| `passumpsic_ao106` | `Aft_Open_Deck` | 140.53 | 41.065 | 1.0 | 32,426.5 | 230.74 | 33,075.5 | 32,426.5 | 274,616.3 | 33,742.5 |
| `savannah_ns` | `Docking_Bridge_Aft` | 302.05 | 60.205 | 1.0 | 48,576.6 | 160.82 | 48,583.5 | 48,576.6 | 404,219.3 | 48,592.4 |
| `savannah_ns` | `Promenade_Aft_Open` | 642.54 | 87.809 | 1.0 | 70,848.2 | 110.26 | 70,858.9 | 70,848.2 | 589,552.1 | 70,872.8 |
| `savannah_ns` | `Swimming_Pool` | 219.67 | 51.342 | 1.0 | 41,311.5 | 188.06 | 41,426.3 | 41,311.5 | 344,598.5 | 41,554.1 |
| `savannah_ns` | `Promenade_Walkway_Port` | 845.74 | 100.742 | 1.0 | 81,183.1 | 95.99 | 81,292.6 | 81,183.1 | 676,306.3 | 81,412.6 |
| `savannah_ns` | `Promenade_Walkway_Stbd` | 845.74 | 100.742 | 1.0 | 81,287.8 | 96.11 | 81,295.9 | 81,287.8 | 676,389.9 | 81,306.6 |
| `savannah_ns` | `Fwd_Deck_Promenade` | 1,383.94 | 128.869 | 1.0 | 103,981.7 | 75.13 | 103,993.4 | 103,981.7 | 865,234.8 | 104,008.8 |
| `savannah_ns` | `Top_Of_House` | 494.48 | 77.031 | 1.0 | 51,772.2 | 104.70 | 51,778.7 | 51,772.2 | 517,790.0 | 51,787.6 |
| `savannah_ns` | `Bridge_Wings` | 172.56 | 45.505 | 1.0 | 36,701.8 | 212.69 | 36,721.1 | 36,701.8 | 305,505.6 | 36,749.6 |
| `savannah_ns` | `Boat_Deck_Fwd` | 332.82 | 63.197 | 1.0 | 50,846.2 | 152.77 | 50,993.4 | 50,846.2 | 424,158.8 | 51,158.6 |
| `savannah_ns` | `Boat_Deck_Aft` | 870.74 | 102.220 | 1.0 | 82,486.5 | 94.73 | 82,492.7 | 82,486.5 | 686,320.5 | 82,501.8 |
| `savannah_ns` | `Fantail_Aft` | 440.67 | 72.719 | 1.0 | 58,549.6 | 132.86 | 58,682.3 | 58,549.6 | 488,117.6 | 58,813.3 |
| `savannah_ns` | `Weather_Deck_Port_A` | 467.38 | 74.890 | 1.0 | 60,323.0 | 129.07 | 60,440.9 | 60,323.0 | 502,714.0 | 60,543.4 |
| `savannah_ns` | `Weather_Deck_Stbd_A` | 701.07 | 91.722 | 1.0 | 73,905.6 | 105.42 | 74,023.6 | 73,905.6 | 615,727.6 | 74,126.1 |
| `savannah_ns` | `Forecastle_A` | 157.74 | 43.507 | 1.0 | 34,991.3 | 221.83 | 35,115.2 | 34,991.3 | 291,997.5 | 35,225.9 |

D5 sweep, commissioned outward flow m³/h at U = 0 / 1 / 5 / 10 m/s:
| hull | openings | U=0 out m³/h | U=1 out m³/h | U=5 out m³/h | U=10 out m³/h |
|---|---:|---:|---:|---:|---:|
| `aeolus_arc3` | 3 | 23.0 | 216,893.4 | 1,086,058.1 | 2,172,511.9 |
| `apl_24` | 4 | 113.3 | 222,807.4 | 1,133,014.6 | 2,270,647.7 |
| `bolster_ars38` | 4 | 54.4 | 159,232.3 | 799,500.7 | 1,599,834.8 |
| `cobalt_k124` | 3 | 43,052.9 | 187,592.9 | 877,446.1 | 1,751,146.1 |
| `gordon_gunter_r338` | 4 | 66,270.2 | 232,183.2 | 1,070,569.7 | 2,136,103.8 |
| `liberty_cargo_ec2` | 6 | 56,607.8 | 183,877.8 | 838,558.6 | 1,671,993.0 |
| `lyon_ap71` | 11 | 193,908.6 | 738,074.6 | 3,430,950.5 | 6,847,284.1 |
| `passumpsic_ao106` | 4 | 102,391.5 | 367,073.6 | 1,691,977.7 | 3,375,288.0 |
| `savannah_ns` | 14 | 459,563.3 | 876,765.3 | 3,716,917.6 | 7,388,632.4 |

### Pressure/balance diagnostic

Design-lane acceptance: max |ΔP| stays in the stage-1 naval design range
(0.5–374 Pa) on every hull before and after, and boundary residuals stay at the
diagnostic's solver scale (largest after |residual| 0.02466 m³/h on
`liberty_cargo_ec2` design; before values were ~1e-7 m³/h with no openings).
Authored/commissioned max |ΔP| fall from the unvented-weather range
(6.98e3–9.55e5 Pa) to 22.21–953 Pa after the openings relieve the previously
unvented zones; the design lane remains the acceptance lane below.

| hull | lane | paths | max abs dP Pa | balance residual m³/h | envelope net in m³/h | ambient-opening net in m³/h | k field/native median |
|---|---|---:|---|---|---|---|---|
| `aeolus_arc3` | authored | 357 -> 363 | 9637 -> 953 | -2.803e-06 -> -0.002823 | 1066 -> 273.8 | 0 -> 792.3 | 1.012 -> 1.057 |
| `aeolus_arc3` | commissioned | 357 -> 363 | 9637 -> 953 | -2.803e-06 -> -0.002823 | 1066 -> 273.8 | 0 -> 792.3 | 1.012 -> 1.057 |
| `aeolus_arc3` | design | 357 -> 363 | 2.223 -> 3.122 | -3.284e-08 -> -0.0006976 | 3.284e-08 -> -11.59 | 0 -> 11.59 | 0.9318 -> 1.001 |
| `apl_24` | authored | 306 -> 314 | 9.552e+05 -> 23.61 | -2.228e-05 -> 1.591 | 9250 -> 33.5 | 0 -> 9215 | 1.623 -> 1 |
| `apl_24` | commissioned | 306 -> 314 | 9.552e+05 -> 23.61 | -2.228e-05 -> 1.591 | 9250 -> 33.5 | 0 -> 9215 | 1.623 -> 1 |
| `apl_24` | design | 306 -> 314 | 23.61 -> 23.61 | 0 -> 0.0005861 | 0 -> -3.254 | 0 -> 3.253 | 0.5 -> 0.5223 |
| `bolster_ars38` | authored | 175 -> 183 | 6.774e+04 -> 106.2 | 0 -> 0.0001407 | 1673 -> 10.49 | 0 -> 1662 | 1.121 -> 0.9955 |
| `bolster_ars38` | commissioned | 175 -> 183 | 6.774e+04 -> 106.2 | 0 -> 0.0001407 | 1673 -> 10.49 | 0 -> 1662 | 1.121 -> 0.9955 |
| `bolster_ars38` | design | 175 -> 183 | 106.2 -> 106.2 | 1.092e-08 -> -0.001643 | -1.092e-08 -> 1.132 | 0 -> -1.131 | 0.5444 -> 0.7909 |
| `cobalt_k124` | authored | 284 -> 290 | 2.183e+04 -> 151 | -5.617e-06 -> 0.001552 | 1202 -> 21.37 | 0 -> 1181 | 1.042 -> 0.9911 |
| `cobalt_k124` | commissioned | 284 -> 290 | 2.183e+04 -> 151 | -5.617e-06 -> 0.001552 | 1202 -> 21.37 | 0 -> 1181 | 1.042 -> 0.9911 |
| `cobalt_k124` | design | 284 -> 290 | 151 -> 151 | -2.194e-08 -> 0.002512 | 2.194e-08 -> 4.001 | 0 -> -4.004 | 0.6951 -> 0.9764 |
| `gordon_gunter_r338` | authored | 268 -> 276 | 1.145e+05 -> 131.3 | 3.366e-05 -> -0.003556 | 3320 -> 24.79 | 0 -> 3296 | 1.007 -> 1.019 |
| `gordon_gunter_r338` | commissioned | 268 -> 276 | 1.145e+05 -> 131.3 | 3.366e-05 -> -0.003556 | 3320 -> 24.79 | 0 -> 3296 | 1.007 -> 1.019 |
| `gordon_gunter_r338` | design | 268 -> 276 | 131.3 -> 131.3 | -4.657e-08 -> 0.008208 | 4.657e-08 -> 3.95 | 0 -> -3.958 | 0.7487 -> 1.012 |
| `liberty_cargo_ec2` | authored | 551 -> 563 | 6980 -> 22.21 | -1.405e-06 -> 0.0007215 | 1240 -> 5.446 | 0 -> 1235 | 1.01 -> 0.9891 |
| `liberty_cargo_ec2` | commissioned | 551 -> 563 | 6980 -> 22.21 | -1.405e-06 -> 0.0007215 | 1240 -> 5.446 | 0 -> 1235 | 1.01 -> 0.9891 |
| `liberty_cargo_ec2` | design | 551 -> 563 | 1.688 -> 1.432 | 5.486e-09 -> -0.001846 | -5.486e-09 -> -8.068 | 0 -> 8.07 | 0.7494 -> 0.9991 |
| `lyon_ap71` | authored | 511 -> 533 | 2.782e+05 -> 151 | 2.243e-05 -> 0.001204 | 8720 -> 52.13 | 0 -> 8668 | 1.161 -> 1.012 |
| `lyon_ap71` | commissioned | 511 -> 533 | 2.782e+05 -> 151 | 2.243e-05 -> 0.001204 | 8720 -> 52.13 | 0 -> 8668 | 1.161 -> 1.012 |
| `lyon_ap71` | design | 511 -> 533 | 151 -> 151 | 4.929e-08 -> -0.001077 | -4.929e-08 -> 4.104 | 0 -> -4.103 | 0.7188 -> 0.9999 |
| `passumpsic_ao106` | authored | 202 -> 210 | 1.934e+05 -> 165.2 | -3.368e-05 -> 0.001879 | 3330 -> 8.206 | 0 -> 3322 | 1.15 -> 1.019 |
| `passumpsic_ao106` | commissioned | 202 -> 210 | 1.934e+05 -> 165.2 | -3.368e-05 -> 0.001879 | 3330 -> 8.206 | 0 -> 3322 | 1.15 -> 1.019 |
| `passumpsic_ao106` | design | 202 -> 210 | 165.2 -> 165.2 | -1.096e-08 -> 0.003055 | 1.096e-08 -> 2.13 | 0 -> -2.133 | 0.8857 -> 1.007 |
| `savannah_ns` | authored | 822 -> 850 | 9183 -> 92.05 | -4.366e-11 -> -0.01588 | 1963 -> 74.72 | 0 -> 1888 | 1.015 -> 1.01 |
| `savannah_ns` | commissioned | 822 -> 850 | 9183 -> 92.05 | -4.366e-11 -> -0.01588 | 1963 -> 74.72 | 0 -> 1888 | 1.015 -> 1.01 |
| `savannah_ns` | design | 822 -> 850 | 92.05 -> 92.05 | -1.592e-07 -> 0.02466 | 1.592e-07 -> -11.5 | 0 -> 11.47 | 0.8406 -> 1.002 |

### Flow compare

| hull | ambient_opening paths | sink out m³/h | inward m³/h | boundary sink out m³/h |
|---|---:|---:|---:|---:|
| `aeolus_arc3` | 0 -> 6 | 0.0 -> 216,893.4 | 0.0 -> 217,685.7 | 0.0 -> 216,893.7 |
| `apl_24` | 0 -> 8 | 0.0 -> 222,807.4 | 0.0 -> 232,022.1 | 0.0 -> 222,807.9 |
| `bolster_ars38` | 0 -> 8 | 0.0 -> 159,232.3 | 0.0 -> 160,894.5 | 0.0 -> 159,233.0 |
| `cobalt_k124` | 0 -> 6 | 0.0 -> 187,592.9 | 0.0 -> 188,773.8 | 0.0 -> 187,593.2 |
| `gordon_gunter_r338` | 0 -> 8 | 0.0 -> 232,183.2 | 0.0 -> 235,478.8 | 0.0 -> 232,183.6 |
| `liberty_cargo_ec2` | 0 -> 12 | 0.0 -> 183,877.8 | 0.0 -> 185,112.5 | 0.0 -> 183,884.9 |
| `lyon_ap71` | 0 -> 22 | 0.0 -> 738,074.6 | 0.0 -> 746,742.7 | 0.0 -> 738,076.2 |
| `passumpsic_ao106` | 0 -> 8 | 0.0 -> 367,073.6 | 0.0 -> 370,395.6 | 0.0 -> 367,074.4 |
| `savannah_ns` | 0 -> 28 | 0.0 -> 876,765.3 | 0.0 -> 878,653.4 | 0.0 -> 876,766.6 |

The after `ambient_opening` sink totals match the D5 commissioned U=1 outward
totals to rounding; before rows are zero because the hulls had no opening paths.

### Paired source cells (whole-hull material time)

Whole-hull material time h, before -> after; largest cell per hull across the
12-cell matrix (two sources × native/commissioned/authored × `pulse_t0`/
`split_t0_t1`):

| hull | cells | max abs move h | largest cell |
|---|---:|---:|---|
| `aeolus_arc3` | 12 | 6.72577 | `Cable_Working_Deck`/native/pulse_t0: 6.746616 -> 0.020848 |
| `apl_24` | 12 | 6.92406 | `Gun_Platforms`/native/pulse_t0: 6.947518 -> 0.023457 |
| `bolster_ars38` | 12 | 6.79374 | `Focsle_Open_Aft`/native/pulse_t0: 6.803690 -> 0.009949 |
| `cobalt_k124` | 12 | 6.60825 | `Quarterdeck`/native/pulse_t0: 6.620171 -> 0.011918 |
| `gordon_gunter_r338` | 12 | 6.54530 | `Boat_Deck`/native/pulse_t0: 6.556462 -> 0.011166 |
| `liberty_cargo_ec2` | 12 | 6.30764 | `Top_Of_House`/native/pulse_t0: 6.315428 -> 0.007783 |
| `lyon_ap71` | 12 | 6.96899 | `Forecastle_Weather`/native/pulse_t0: 6.987626 -> 0.018638 |
| `passumpsic_ao106` | 12 | 6.76124 | `Island_Deck`/native/pulse_t0: 6.780528 -> 0.019286 |
| `savannah_ns` | 12 | 6.87936 | `Fwd_Deck_Promenade`/native/pulse_t0: 6.892665 -> 0.013307 |

## Findings and open items

1. Measured: design-lane max |ΔP| is unchanged inside the naval design range on
   every hull; the largest design move is `aeolus_arc3` 2.22 -> 3.12 Pa. No hull
   went unsolved (27/27 pressure rows solved before and after) and ContamX
   converged on every hull and lane.
2. Measured: native `ambient_exchange_open_deck` links rise by exactly one per
   record (53 links across the roster) and the ContamX field lane classifies
   the solved outward legs as `ambient_opening` boundary sinks.
3. Measured: whole-hull material time from a weather source collapses once the
   opening exists (largest moves are the weather `pulse_t0` cells, e.g.
   `lyon_ap71/Forecastle_Weather/native/pulse_t0` 6.987626 -> 0.018638 h).
   Interior source cells were not used here; the two-source matrix is the
   largest-area opening witness.
4. The `exchange_m3h` values are Grade C solved rates, not measured ship
   ventilation: they are large (17,467.2–150,252.5 m³/h per opening on the
   committed 1 m/s point; hull totals 159,232.3–876,765.3 m³/h) because the
   area rule is a two-face deck estimate at 1 m/s relative wind. They are
   recorded under the owner acceptance quoted in Scope, not tuned to any
   anchor.
5. The U=10 column is the axis upper bound only; the committed record keeps
   the fleet default 1 m/s point. A per-hull wind override would move the
   ContamX lane but not the native `exchange_m3h`, the same caveat as cruise.
6. Grouped-zone open item: the HVAC-grouped weather zones listed under Exposure
   calls remain without `ambient_openings` by the scope rule; the owner
   question on grouped zones stays open.
7. The U=0 sweep column is not zero on every hull (23.0–459,563.3 m³/h
   outward) because D8 `paired_orifices` solves buoyancy-driven counter-flow as
   signed outward/inward Flow0 even at calm wind. This is exporter behavior,
   not a magnitude fit.
8. `contam_paired_diagnostic.py` CLI choices still exclude these GA hulls;
   coverage here is via the same `_run_matrix` cells with explicit `--source`,
   not a CLI allow-list change.

## Reproduction

```bash
for h in aeolus_arc3 apl_24 bolster_ars38 cobalt_k124 \
  gordon_gunter_r338 liberty_cargo_ec2 lyon_ap71 passumpsic_ao106 savannah_ns; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull aeolus_arc3 --hull apl_24 \
  --hull bolster_ars38 --hull cobalt_k124 --hull gordon_gunter_r338 \
  --hull liberty_cargo_ec2 --hull lyon_ap71 --hull passumpsic_ao106 \
  --hull savannah_ns --lane authored --lane commissioned --lane design \
  --out telemetry_buffer/contam_pressure_balance_diagnostic/auxiliary_after.json
for h in aeolus_arc3 apl_24 bolster_ars38 cobalt_k124 \
  gordon_gunter_r338 liberty_cargo_ec2 lyon_ap71 passumpsic_ao106 savannah_ns; do
  .venv/bin/python tools/contam_flow_compare.py --platform $h --run-contamx
done
.venv/bin/python tools/contam_commissioned_check.py --platform aeolus_arc3 \
  --platform apl_24 --platform bolster_ars38 \
  --platform cobalt_k124 --platform gordon_gunter_r338 \
  --platform liberty_cargo_ec2 --platform lyon_ap71 --platform passumpsic_ao106 \
  --platform savannah_ns
```

Before-witnesses were the same solves in a detached `origin/main` worktree at
`6c6c9f3b` with `CONTAMX_BINARY` pointed at the same local binary; the paired
matrix was run programmatically with the explicit sources listed in Witnesses
because `contam_paired_diagnostic.PLATFORM_SOURCES` has no auxiliary entries.
