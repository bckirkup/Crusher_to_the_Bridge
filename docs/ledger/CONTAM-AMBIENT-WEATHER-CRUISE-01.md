# CONTAM-AMBIENT-WEATHER-CRUISE-01
**Date:** 2026-11-16
**Commit:** 34951785
**Pathogens:** all
**Status:** measured
**Measured at:** 34951785

## Scope

After-witnesses measured at `34951785`; before-witnesses at `origin/main`
`2271f2c1`. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **cruise hull class only** (`classic_cruise_1900`,
`diamond_princess`, `expedition_cruise_450`, `greg_mortimer`,
`mega_cruise_5000`, `spirit_cruise_3000`): the open weather decks stay finite
zones (D2(a)), each declares `exposure: weather` in `spatial_layout.json`
(D7(b)) and one `open_deck` record in `ambient_openings` (D1(a)) with a
declared exchange axis (D4(a)/D5). Machinery:
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md).
Method precedent:
[`CONTAM-AMBIENT-MAKEUP-CRUISE-01`](CONTAM-AMBIENT-MAKEUP-CRUISE-01.md),
[`CONTAM-AMBIENT-MAKEUP-FICTION-01`](CONTAM-AMBIENT-MAKEUP-FICTION-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

Not changed: any `flow_rate_m3h` (the diff to the six `air_flow_paths.json`
and six `spatial_layout.json` files is additions only, 0 deleted lines), any
`envelope_leak` area, any existing exporter constant value, the steady weather
header, the transmission layer (`BALCONY_AEROSOL_REDUCTION = 0.5` stays, D3
option A), any naval or fiction hull. No `balcony_door`, hatch or door opening
is authored. No cache was produced or uploaded and nothing was submitted.

What the exporter gained (new, inert unless a record declares it): an optional
`wind_speed_m_s` on an `ambient_openings` record, and the named constants that
turn it into a pressure. The literal `0.8` wind-pressure modifier already used
on envelope leaks is now the named `_WIND_PRESSURE_MODIFIER`, same value. Before
any record was authored the changed exporter reproduced the committed bundles
of the three hulls checked (`expedition_cruise_450`, `diamond_princess`,
`enterprise_galaxy_tng`) byte-for-byte, and the fast test tier's byte pins
pass for every other platform.

## The ΔT = 0 problem and its resolution

The stage-1 D8 witness and the stage-3 ledgers recorded that paired orifices
exchange only by buoyancy, about 0.5 m³/h at ΔT = 0. Measured here on
`expedition_cruise_450` with a scratch 40 m² `open_deck` record on `PoolDeck`
added in memory at `2271f2c1` (path flows are ContamX `Flow0`, positive =
outward):

- **Zone temperatures.** The export has 85 zones at 293.15 K and six at
  297.15 K (the `2_Crew` deck offset). Ambient is 293.15 K. `PoolDeck` is at
  ambient: ΔT = 0.
- **Baseline.** Both legs flow inward: design -800.2 and -802.4 m³/h,
  commissioned -1,418.8 and -1,420.0 m³/h. Outward is 0. The opening acts as
  hull make-up only, so the field lane would solve no exchange where the native
  lane applies a declared one.
- **Wind as exported is inert.** The steady weather line is `Ws=0.000 Wd=0` and
  the opening legs carry ContamX path flag 0. Setting the header wind to 5 or
  10 m/s, or putting the legs on azimuths 0°/180°, left both leg flows
  unchanged. In the committed `expedition_cruise_450` PRJ no path of any kind
  has the wind flag bit set (flags present: 0, 8, 16, 32, 64), so the attached
  `ShipHull` profile on envelope leaks is likewise unused. This is recorded as
  a finding and not changed here.
- **Wind does drive exchange once the flag is set.** Flag 1, legs on azimuths
  0°/180°, header wind direction 0°, commissioned lane:

  | header wind m/s | outward m³/h |
  |---:|---:|
  | 1 | 25,199.1 |
  | 5 | 131,785.9 |
  | 10 | 264,849.4 |

  At 10 m/s with the wind at 90° to both legs the outward flow is 2,573.9 m³/h,
  and with both legs on the same azimuth both legs flow inward (outward 0).
- **A constant pressure on the legs also drives exchange.** Flag 1, no profile
  attached, header `Ws=0`, `wPset` = +p on one leg and -p on the other,
  commissioned lane:

  | p Pa | outward m³/h |
  |---:|---:|
  | 0.1 | 16,149.7 |
  | 1 | 54,301.8 |
  | 10 | 174,837.7 |

  Design lane at 1 Pa: 54,931.9 m³/h (1.2% above commissioned). With flag 0 the
  same `wPset` values have no effect.

Candidates and the choice:

| candidate | measured | verdict |
|---|---|---|
| accept buoyancy-only, declare the limitation | outward 0 at ΔT = 0 | rejected: native axis vs field 0 breaks §2.6 parity |
| scheduled opening | a schedule scales an opening that has no driving force | rejected: still 0 |
| a different element | stage-1 D8: all three element models give about 0.5 m³/h at ΔT = 0 | rejected |
| deck temperature offset | not measured | rejected: a weather deck warmer than ambient is not physical |
| header wind speed and wind flag fleet-wide | drives exchange, but moves every hull's envelope-leak flows | rejected here: fleet-wide exporter change, out of scope |
| **imposed wind pressure on the opening's own two legs** | non-zero, monotonic in the declared speed, design and commissioned within 5.1% | **chosen** |

**Chosen representation.** A record that declares `wind_speed_m_s` = U gets
ContamX wind flag 1 on its two legs, no wind profile, and a constant `wPset`:
windward on the lower leg and leeward on the upper leg,
`wPmod · Cp · ρU²/2`, with `wPmod` 0.8 (the exporter's existing value),
`Cp` the 0° and 180° points of the hull's own wind profile (`ShipHull`: 0.7
and -0.25) and ρ = 101,325 / (287.055 · 293.15) = 1.2041 kg/m³ (dry air at the
exporter's existing ambient temperature and pressure). At U = 1 m/s that is
+0.337147 and -0.12041 Pa. It is local to the two path lines, so the steady
weather header, the envelope leaks and every hull without such a record are
byte-unchanged. The skeleton (non-hobbyist) export imposes the same pressures.
A record that declares no speed, or 0, exports exactly as before.

Limits of this representation, declared: the relative wind is a constant, not
a weather record or a ship-speed model; the two legs are always one windward
and one leeward, so the deck is always cross-ventilated; the `ShipHull` Cp
points are the fiction-grade profile the exporter already ships, not a
measurement of any of these hulls.

## Weather zones and records

A zone is tagged when its authored `description` says it is an open or
semi-open deck and it belongs to no AHU group. `exposure` is written only on
these zones; a zone with no `exposure` falls back to the lexical classifier
(`tools.hull_audit._is_exterior`), so the fleet inventory in
`CONTAM-AMBIENT-EXPOSURE-01` is unchanged outside these 23 zones.

| hull | zone | volume m³ | area_m2 | wind_speed_m_s | windward / leeward wPset Pa | exchange_m3h | air changes /h |
|---|---|---:|---:|---:|---|---:|---:|
| classic_cruise_1900 | `PoolDeck` | 2,100 | 158.745 | 1.0 | 0.337161 / -0.120415 | 101,803.4 | 48.5 |
| diamond_princess | `OceanFront` | 800 | 97.98 | 1.0 | 0.337161 / -0.120415 | 63,357.9 | 79.2 |
| diamond_princess | `TerracePool` | 1,500 | 134.164 | 1.0 | 0.337161 / -0.120415 | 83,348.9 | 55.6 |
| diamond_princess | `NeptunePool` | 2,500 | 173.205 | 1.0 | 0.337161 / -0.120415 | 113,501.0 | 45.4 |
| diamond_princess | `CalypsoPool` | 1,800 | 146.969 | 1.0 | 0.337161 / -0.120415 | 96,535.9 | 53.6 |
| diamond_princess | `HorizonTerrace` | 600 | 84.853 | 1.0 | 0.337161 / -0.120415 | 55,963.4 | 93.3 |
| diamond_princess | `OpenAirCinema` | 800 | 97.98 | 1.0 | 0.337161 / -0.120415 | 64,061.5 | 80.1 |
| diamond_princess | `SportsCourt` | 600 | 84.853 | 1.0 | 0.337161 / -0.120415 | 55,834.0 | 93.1 |
| diamond_princess | `CenterCourt` | 400 | 69.282 | 1.0 | 0.337161 / -0.120415 | 45,416.9 | 113.5 |
| expedition_cruise_450 | `PoolDeck` | 1,050 | 112.25 | 1.0 | 0.337161 / -0.120415 | 73,376.0 | 69.9 |
| greg_mortimer | `ZodiacPlatforms` | 220 | 51.381 | 1.0 | 0.337161 / -0.120415 | 34,039.3 | 154.7 |
| greg_mortimer | `ActivityPlat` | 180 | 46.476 | 1.0 | 0.337161 / -0.120415 | 30,893.5 | 171.6 |
| greg_mortimer | `ViewPlatforms` | 160 | 43.818 | 1.0 | 0.337161 / -0.120415 | 27,471.5 | 171.7 |
| greg_mortimer | `SunDeck` | 300 | 60.0 | 1.0 | 0.337161 / -0.120415 | 39,351.8 | 131.2 |
| greg_mortimer | `TopDeck` | 250 | 54.772 | 1.0 | 0.337161 / -0.120415 | 35,887.5 | 143.6 |
| mega_cruise_5000 | `Main_Pool_Deck` | 9,000 | 328.634 | 1.0 | 0.337161 / -0.120415 | 211,952.4 | 23.6 |
| mega_cruise_5000 | `Sports_Court` | 1,800 | 146.969 | 1.0 | 0.337161 / -0.120415 | 96,737.7 | 53.7 |
| mega_cruise_5000 | `Waterpark` | 3,600 | 207.846 | 1.0 | 0.337161 / -0.120415 | 137,197.9 | 38.1 |
| mega_cruise_5000 | `CentralPark` | 36,000 | 657.267 | 1.0 | 0.337161 / -0.120415 | 421,507.5 | 11.7 |
| mega_cruise_5000 | `Aqua_Theater` | 18,000 | 464.758 | 1.0 | 0.337161 / -0.120415 | 309,439.7 | 17.2 |
| spirit_cruise_3000 | `MainPool` | 2,400 | 169.706 | 1.0 | 0.337161 / -0.120415 | 111,163.1 | 46.3 |
| spirit_cruise_3000 | `AftPool` | 1,200 | 120.0 | 1.0 | 0.337161 / -0.120415 | 79,104.8 | 65.9 |
| spirit_cruise_3000 | `SportsDeck` | 1,800 | 146.969 | 1.0 | 0.337161 / -0.120415 | 96,141.5 | 53.4 |

23 records: classic 1, diamond 8, expedition 1, greg 5, mega 5, spirit 3. All
are `type: open_deck`, `schedule: always_open`.

**Area rule.** `ASSUMED-OPEN-DECK-FACE-AREA`, Grade C. No drawing in the tree
gives a deck edge, so the opening is the two opposite side faces of a
square-plan deck of the zone's authored volume at the exporter's default 3 m
zone height: `area_m2 = 2 · sqrt(V / 3) · 3`, three decimals. It was not
checked against a drawing, the literature or a standard, and was not tuned per
hull or against any target.

**Speed.** `ASSUMED-RELATIVE-WIND`, Grade C. The committed point is 1 m/s on a
declared axis of 0 to 10 m/s. 1 m/s is not a measured wind; it is the low end
of the axis, chosen before any outcome was read. A ship under way sees more.

Zones deliberately not tagged, left for an owner decision:

- `greg_mortimer` `BarsDeck5`, `BarsDeck8`, `ObsDeck7`, `ObsDeck8`: the
  lexical classifier calls them exterior, but they are served by AHU groups
  and their descriptions do not say they are open. Tagging them needs
  `exposure: enclosed` or a drawing.
- Promenades (`classic_cruise_1900` `Promenade`, `spirit_cruise_3000`
  `Promenade`, `mega_cruise_5000` `Royal_Promenade`, `diamond_princess`
  `PromGalleria`): read from their descriptions and HVAC grouping as indoor or
  AHU-served; not confirmed against a drawing.
- Balcony cabins on every hull: D3 option A, transmission factor only. No
  record here touches a cabin zone, so the balcony factor is not double
  counted.

## D5 derivation: native rate and axis from the ContamX-solved range

Method is the stage-3 precedent with one added axis: author the record, export
`design` and `commissioned`, solve, read `Flow0` on both legs, split outward
from inward, at U = 0, 1, 5 and 10 m/s on every weather record of the hull at
once. Flows in m³/h.

| hull | zone | U=0 design out / in | U=0 comm. out / in | U=1 design out | U=1 comm. out (declared) | design ÷ comm. at U=1 | U=5 comm. out | U=10 design out | U=10 comm. out (axis upper bound) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| classic_cruise_1900 | `PoolDeck` | 0 / 5,489 | 0 / 7,674 | 102,930 | 101,803 | 1.0111 | 524,684 | 1,054,293 | 1,053,194 |
| diamond_princess | `OceanFront` | 2,709 / 0 | 0 / 3,682 | 66,566 | 63,358 | 1.0506 | 324,182 | 653,290 | 649,978 |
| diamond_princess | `TerracePool` | 0 / 6,371 | 0 / 11,553 | 86,065 | 83,349 | 1.0326 | 440,490 | 888,409 | 886,206 |
| diamond_princess | `NeptunePool` | 0 / 1,688 | 0 / 4,069 | 114,636 | 113,501 | 1.0100 | 574,748 | 1,152,092 | 1,151,065 |
| diamond_princess | `CalypsoPool` | 0 / 594 | 0 / 2,107 | 97,365 | 96,536 | 1.0086 | 487,769 | 977,612 | 976,768 |
| diamond_princess | `HorizonTerrace` | 0 / 342 | 0 / 1,047 | 56,318 | 55,963 | 1.0063 | 281,905 | 564,632 | 564,294 |
| diamond_princess | `OpenAirCinema` | 0 / 195 | 0 / 2,313 | 65,131 | 64,062 | 1.0167 | 324,954 | 652,128 | 650,996 |
| diamond_princess | `SportsCourt` | 17 / 61 | 0 / 1,304 | 56,468 | 55,834 | 1.0114 | 281,780 | 564,828 | 564,174 |
| diamond_princess | `CenterCourt` | 0 / 76 | 0 / 1,402 | 46,084 | 45,417 | 1.0147 | 229,896 | 461,105 | 460,446 |
| expedition_cruise_450 | `PoolDeck` | 0 / 1,603 | 0 / 2,839 | 74,001 | 73,376 | 1.0085 | 372,554 | 746,868 | 746,378 |
| greg_mortimer | `ZodiacPlatforms` | 270 / 0 | 0 / 679 | 34,365 | 34,039 | 1.0096 | 171,195 | 342,880 | 342,605 |
| greg_mortimer | `ActivityPlat` | 11 / 0 | 0 / 27 | 31,062 | 30,894 | 1.0055 | 154,890 | 310,146 | 309,922 |
| greg_mortimer | `ViewPlatforms` | 0 / 1,379 | 0 / 3,432 | 28,542 | 27,472 | 1.0390 | 144,386 | 291,406 | 290,366 |
| greg_mortimer | `SunDeck` | 0 / 66 | 0 / 1,244 | 40,034 | 39,352 | 1.0173 | 199,499 | 400,377 | 399,689 |
| greg_mortimer | `TopDeck` | 58 / 0 | 0 / 1,408 | 36,536 | 35,888 | 1.0181 | 182,052 | 365,371 | 364,742 |
| mega_cruise_5000 | `Main_Pool_Deck` | 0 / 6,151 | 0 / 17,068 | 216,623 | 211,952 | 1.0220 | 1,087,939 | 2,185,574 | 2,181,442 |
| mega_cruise_5000 | `Sports_Court` | 0 / 156 | 0 / 438 | 97,322 | 96,738 | 1.0060 | 487,519 | 977,580 | 976,352 |
| mega_cruise_5000 | `Waterpark` | 18 / 174 | 0 / 439 | 137,794 | 137,198 | 1.0043 | 689,921 | 1,382,655 | 1,381,260 |
| mega_cruise_5000 | `CentralPark` | 0 / 4,674 | 0 / 31,701 | 435,060 | 421,508 | 1.0322 | 2,170,807 | 4,369,348 | 4,355,928 |
| mega_cruise_5000 | `Aqua_Theater` | 213 / 214 | 210 / 218 | 309,456 | 309,440 | 1.0001 | 1,547,267 | 3,094,600 | 3,094,563 |
| spirit_cruise_3000 | `MainPool` | 0 / 2,293 | 0 / 4,711 | 112,167 | 111,163 | 1.0090 | 563,423 | 1,129,367 | 1,128,537 |
| spirit_cruise_3000 | `AftPool` | 0 / 262 | 0 / 524 | 79,455 | 79,105 | 1.0044 | 398,468 | 798,360 | 797,860 |
| spirit_cruise_3000 | `SportsDeck` | 0 / 432 | 0 / 3,409 | 97,644 | 96,142 | 1.0156 | 487,594 | 978,378 | 976,890 |

- At U = 0 the measured outward flow is 0 on 22 of 23 zones in the
  commissioned lane (`mega_cruise_5000` `Aqua_Theater`: 210 m³/h) and at most
  2,709 m³/h in the design lane (`diamond_princess` `OceanFront`). This is the
  ΔT = 0 problem reproduced on all six hulls.
- Declared native `exchange_m3h` = the commissioned-lane outward flow at the
  committed U = 1 m/s. The design lane is 1.0001 to 1.0506 times that value.
- The outward flow is close to linear in U: the 10 m/s value is 10.00 to 10.63
  times the 1 m/s value.
- **Declared axis (D4(a)/D5):** per record, 0 to the commissioned outward flow
  at 10 m/s (last column). Across the 23 records the committed point is 27,472
  to 421,508 m³/h (11.7 to 171.7 air changes per hour of the deck zone) and the
  upper bound is 290,366 to 4,355,928 m³/h.

Scope of the claim: steady solves, exporter ΔT = 0, all of a hull's weather
records at the same U. The per-record value depends on the other records and
on the hull's AHS lane; a changed area, speed or lane must be re-measured. The
range is a ContamX-derived model range, not a literature value (proposal §4
remains open).

## §2.6 parity: native vs field

Per-zone, after, commissioned lane (the committed bundle):

| hull | zone | native exchange m³/h | field outward m³/h (commissioned) | field − native m³/h |
|---|---|---:|---:|---:|
| classic_cruise_1900 | `PoolDeck` | 101,803.4 | 101,803.4 | -0.0 |
| diamond_princess | `OceanFront` | 63,357.9 | 63,357.9 | +0.0 |
| diamond_princess | `TerracePool` | 83,348.9 | 83,348.9 | -0.0 |
| diamond_princess | `NeptunePool` | 113,501.0 | 113,501.0 | -0.0 |
| diamond_princess | `CalypsoPool` | 96,535.9 | 96,535.9 | -0.0 |
| diamond_princess | `HorizonTerrace` | 55,963.4 | 55,963.4 | -0.0 |
| diamond_princess | `OpenAirCinema` | 64,061.5 | 64,061.5 | +0.0 |
| diamond_princess | `SportsCourt` | 55,834.0 | 55,834.0 | -0.0 |
| diamond_princess | `CenterCourt` | 45,416.9 | 45,416.9 | +0.0 |
| expedition_cruise_450 | `PoolDeck` | 73,376.0 | 73,376.0 | -0.0 |
| greg_mortimer | `ZodiacPlatforms` | 34,039.3 | 34,039.3 | -0.0 |
| greg_mortimer | `ActivityPlat` | 30,893.5 | 30,893.5 | +0.0 |
| greg_mortimer | `ViewPlatforms` | 27,471.5 | 27,471.5 | +0.0 |
| greg_mortimer | `SunDeck` | 39,351.8 | 39,351.8 | -0.0 |
| greg_mortimer | `TopDeck` | 35,887.5 | 35,887.5 | +0.0 |
| mega_cruise_5000 | `Main_Pool_Deck` | 211,952.4 | 211,952.4 | +0.0 |
| mega_cruise_5000 | `Sports_Court` | 96,737.7 | 96,737.7 | +0.0 |
| mega_cruise_5000 | `Waterpark` | 137,197.9 | 137,197.9 | +0.0 |
| mega_cruise_5000 | `CentralPark` | 421,507.5 | 421,507.5 | +0.0 |
| mega_cruise_5000 | `Aqua_Theater` | 309,439.7 | 309,439.7 | -0.0 |
| spirit_cruise_3000 | `MainPool` | 111,163.1 | 111,163.1 | +0.0 |
| spirit_cruise_3000 | `AftPool` | 79,104.8 | 79,104.8 | -0.0 |
| spirit_cruise_3000 | `SportsDeck` | 96,141.5 | 96,141.5 | +0.0 |

The native `ambient_exchange_open_deck` rate and the field-lane outward sink
agree to 0.04 m³/h on every record, by construction (the native rate is the
solved value rounded to one decimal). Against the design lane the difference
is at most 5.1%. Both are inside the declared axis width.

`tools/contam_flow_compare.py` hull totals, before → after:

| hull | path_map entries | native links | ambient_opening legs | field opening inward m³/h | field opening outward sink m³/h | native `ambient_exchange_*` links | native exchange total m³/h | field ÷ native |
|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 838 → 840 | 737 → 738 | 2 → 4 | 20,265 → 122,413 | 0 → 101,803 | 1 → 2 | 0 → 101,803 | 1.000000 |
| diamond_princess | 1773 → 1789 | 1558 → 1566 | 2 → 18 | 43,469 → 621,776 | 0 → 578,020 | 1 → 9 | 0 → 578,020 | 1.000000 |
| expedition_cruise_450 | 345 → 347 | 273 → 274 | 2 → 4 | 12,457 → 85,849 | 0 → 73,376 | 1 → 2 | 0 → 73,376 | 1.000000 |
| greg_mortimer | 358 → 368 | 288 → 293 | 2 → 12 | 10,537 → 178,385 | 0 → 167,644 | 1 → 6 | 0 → 167,644 | 1.000000 |
| mega_cruise_5000 | 2593 → 2603 | 2301 → 2306 | 20 → 30 | 56,662 → 1,234,098 | 0 → 1,176,903 | 10 → 15 | 0 → 1,176,835 | 1.000058 |
| spirit_cruise_3000 | 1305 → 1311 | 1142 → 1145 | 2 → 8 | 27,250 → 315,158 | 0 → 286,409 | 1 → 4 | 0 → 286,409 | 1.000000 |

Native `ambient_exchange_*` links include the stage-3 louvres at 0 m³/h.

Parity of outcome, not only of rate — whole-hull material time for a pulse
released on one weather zone per hull (`contam_pressure_balance_diagnostic`,
`--source <zone>`, `pulse_t0`):

| hull | source | native before → after h | design before → after h | commissioned before → after h | after field ÷ native (design, comm.) |
|---|---|---|---|---|---|
| classic_cruise_1900 | `PoolDeck` | 2.921 → 0.02234 | 6.767 → 0.04849 | 1.973 → 0.05443 | 2.17, 2.44 |
| diamond_princess | `NeptunePool` | 2.482 → 0.02551 | 5.587 → 0.03218 | 3.471 → 0.03741 | 1.26, 1.47 |
| expedition_cruise_450 | `PoolDeck` | 2.602 → 0.01586 | 5.609 → 0.02379 | 1.838 → 0.02726 | 1.50, 1.72 |
| greg_mortimer | `SunDeck` | 1.218 → 0.00974 | 4.703 → 0.007904 | 0.8441 → 0.01587 | 0.81, 1.63 |
| mega_cruise_5000 | `Main_Pool_Deck` | 6.82 → 0.04236 | 5.211 → 0.05532 | 2.359 → 0.07384 | 1.31, 1.74 |
| spirit_cruise_3000 | `MainPool` | 2.77 → 0.02369 | 6.304 → 0.03396 | 1.421 → 0.04261 | 1.43, 1.80 |

Before, the lanes disagreed by up to a factor 3.9 (`greg_mortimer` design
4.703 h vs native 1.218 h) and a weather-deck pulse stayed aboard for hours.
After, every lane clears it in under 0.08 h and the field lanes are 0.81 to
2.44 times native. **Residual, not resolved here:** the field lanes are
slower than native on five of six hulls even though the outward rate is the
same. Hypothesis, not measured: the wind-driven inflow leg also pushes deck
air into adjacent interior zones in the field lane (net inward flow through
the opening is 58 to 31,722 m³/h per zone in the commissioned lane), which the native lane's
fixed inter-zone flows do not do.

## Acceptance: design-lane max |ΔP|

| hull | design before Pa | design after Pa | commissioned before Pa | commissioned after Pa |
|---|---:|---:|---:|---:|
| classic_cruise_1900 | 693.5 | 126.5 | 1,052 | 102.2 |
| diamond_princess | 16.79 | 13.05 | 108.8 | 12.68 |
| expedition_cruise_450 | 11.34 | 6.731 | 90.65 | 80.8 |
| greg_mortimer | 938.4 | 934.4 | 44,880 | 44,880 |
| mega_cruise_5000 | 21.7 | 14.34 | 433.3 | 289.4 |
| spirit_cruise_3000 | 1,213 | 756.9 | 4,022 | 550.3 |

No hull worsens in either lane. Of the three stage-3 residuals, classic
improves (693.5 → 126.5 Pa), spirit improves but stays outside 0.5-374 Pa
(1,213 → 756.9 Pa), and **greg does not improve** (938.4 → 934.4 Pa design,
44,880 Pa commissioned unchanged): its exhaust-sink and envelope-leak maxima
are identical before and after (928.0 / 930.9 Pa design), so the residual is
in a cluster the five weather decks do not reach. Recorded, not tuned.

Full pressure-balance witness, before → after:

| hull | lane | paths | max \|ΔP\| Pa | interior flowing max \|ΔP\| Pa | interior blocked n | exhaust-sink max \|ΔP\| Pa | envelope max \|ΔP\| Pa | envelope net in m³/h | opening in m³/h | opening out m³/h | opening max \|ΔP\| Pa | balance residual m³/h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | design | 838 → 840 | 693.5 → 126.5 | 683.6 → 123.6 | 63 → 63 | 9.699 → 5.591 | 693 → 66.31 | 305.5 → 48.01 | 11,697 → 114,885 | 0 → 102,930 | 9.933 → 3.034 | -5.86e-04 → 1.13e-03 |
| classic_cruise_1900 | commissioned | 838 → 840 | 1052 → 102.2 | 1002 → 99.48 | 0 → 12 | 70.3 → 39.6 | 1052 → 68.74 | 443.9 → 99.63 | 20,265 → 122,413 | 0 → 101,803 | 29.81 → 12.14 | -7.06e-04 → -6.36e-03 |
| classic_cruise_1900 | authored | 838 → 840 | 1052 → 102.2 | 1002 → 99.48 | 0 → 12 | 70.3 → 39.6 | 1052 → 68.74 | 443.9 → 99.63 | 20,265 → 122,413 | 0 → 101,803 | 29.81 → 12.14 | -7.06e-04 → -6.36e-03 |
| diamond_princess | design | 1773 → 1789 | 16.79 → 13.05 | 14.54 → 11.19 | 400 → 400 | 10.24 → 0.8419 | 10.66 → 9.98 | 85.03 → 20.04 | 17,915 → 606,613 | 0 → 588,633 | 10.35 → 4.134 | 1.75e-04 → -1.45e-02 |
| diamond_princess | commissioned | 1773 → 1789 | 108.8 → 12.68 | 23.36 → 9.934 | 35 → 9 | 82.84 → 9.398 | 108.8 → 12.68 | 404.7 → 116.7 | 43,469 → 621,776 | 0 → 578,020 | 60.96 → 8.502 | 1.76e-04 → -7.98e-03 |
| diamond_princess | authored | 1773 → 1789 | 108.8 → 12.68 | 23.36 → 9.934 | 35 → 9 | 82.84 → 9.398 | 108.8 → 12.68 | 404.7 → 116.7 | 43,469 → 621,776 | 0 → 578,020 | 60.96 → 8.502 | 1.76e-04 → -7.98e-03 |
| expedition_cruise_450 | design | 345 → 347 | 11.34 → 6.731 | 1.006 → 6.697 | 53 → 53 | 10.37 → 6.615 | 11.34 → 6.731 | 30.67 → 22.27 | 7,978 → 81,988 | 0 → 74,001 | 10.37 → 6.618 | -4.64e-04 → -2.92e-03 |
| expedition_cruise_450 | commissioned | 345 → 347 | 90.65 → 80.8 | 63.79 → 64.1 | 0 → 0 | 89.08 → 79.21 | 90.65 → 80.8 | 87.17 → 71.2 | 12,457 → 85,849 | 0 → 73,376 | 25.28 → 15.1 | -6.48e-04 → -4.21e-03 |
| expedition_cruise_450 | authored | 345 → 347 | 90.65 → 80.8 | 63.79 → 64.1 | 0 → 0 | 89.08 → 79.21 | 90.65 → 80.8 | 87.17 → 71.2 | 12,457 → 85,849 | 0 → 73,376 | 25.28 → 15.1 | -6.48e-04 → -4.21e-03 |
| greg_mortimer | design | 358 → 368 | 938.4 → 934.4 | 3.563 → 6.412 | 61 → 61 | 928 → 928 | 930.9 → 930.9 | -40.21 → -68.33 | 4,984 → 175,552 | 0 → 170,540 | 10.32 → 6.311 | 1.55e-04 → 4.70e-03 |
| greg_mortimer | commissioned | 358 → 368 | 4.488e+04 → 4.488e+04 | 554.2 → 6.47 | 0 → 0 | 4.488e+04 → 4.488e+04 | 4.481e+04 → 4.481e+04 | 859.8 → 654.6 | 10,537 → 178,385 | 0 → 167,644 | 46.14 → 6.463 | 3.99e-05 → 6.15e-04 |
| greg_mortimer | authored | 358 → 368 | 4.488e+04 → 4.488e+04 | 554.2 → 6.47 | 0 → 0 | 4.488e+04 → 4.488e+04 | 4.481e+04 → 4.481e+04 | 859.8 → 654.6 | 10,537 → 178,385 | 0 → 167,644 | 46.14 → 6.463 | 3.99e-05 → 6.15e-04 |
| mega_cruise_5000 | design | 2593 → 2603 | 21.7 → 14.34 | 11.47 → 11.34 | 446 → 446 | 10.71 → 3.743 | 21.5 → 13.92 | 127.6 → 48.25 | 14,875 → 1,211,613 | 0 → 1,196,658 | 10.71 → 3.738 | -7.32e-04 → -2.61e-02 |
| mega_cruise_5000 | commissioned | 2593 → 2603 | 433.3 → 289.4 | 283 → 284.9 | 23 → 25 | 150.2 → 5.016 | 433.3 → 289.4 | 676.1 → 143.2 | 56,662 → 1,234,098 | 0 → 1,176,903 | 150.1 → 5.009 | -1.22e-03 → -3.38e-02 |
| mega_cruise_5000 | authored | 2593 → 2603 | 433.3 → 289.4 | 283 → 284.9 | 23 → 25 | 150.2 → 5.016 | 433.3 → 289.4 | 676.1 → 143.2 | 56,662 → 1,234,098 | 0 → 1,176,903 | 150.1 → 5.009 | -1.22e-03 → -3.38e-02 |
| spirit_cruise_3000 | design | 1305 → 1311 | 1213 → 756.9 | 1189 → 741.8 | 153 → 153 | 8.375 → 25.65 | 1166 → 745.3 | 541.1 → -88.04 | 14,461 → 304,357 | 0 → 289,266 | 9.709 → 6.8 | 1.28e-05 → 2.03e-03 |
| spirit_cruise_3000 | commissioned | 1305 → 1311 | 4022 → 550.3 | 2105 → 539.5 | 62 → 15 | 129.7 → 20.95 | 4022 → 519.4 | 1467 → -32.28 | 27,250 → 315,158 | 0 → 286,409 | 34.47 → 18.76 | -1.74e-04 → -2.59e-04 |
| spirit_cruise_3000 | authored | 1305 → 1311 | 4022 → 550.3 | 2105 → 539.5 | 62 → 15 | 129.7 → 20.95 | 4022 → 519.4 | 1467 → -32.28 | 27,250 → 315,158 | 0 → 286,409 | 34.47 → 18.76 | -1.74e-04 → -2.59e-04 |

Things that moved the wrong way, recorded:

- `expedition_cruise_450` design interior-flowing max |ΔP| 1.006 → 6.697 Pa
  and `greg_mortimer` design 3.563 → 6.412 Pa (the hull max still falls).
- `classic_cruise_1900` commissioned interior blocked paths 0 → 12 and
  `mega_cruise_5000` 23 → 25; `diamond_princess` 35 → 9 and
  `spirit_cruise_3000` 62 → 15 improve.
- `spirit_cruise_3000` design exhaust-sink max |ΔP| 8.4 → 25.7 Pa.

## Balance residual

`balance_residual_m3h` is at most 1.2e-3 m³/h in magnitude before and at most
3.4e-2 m³/h after (`mega_cruise_5000` commissioned, on 1.23e6 m³/h of opening
inflow: 2.7e-8 relative). It grows with the opening throughflow and stays at
solver-noise level; the mass balance is not broken. ContamX converged on every
hull and lane, including the 48 sweep solves.

## Witness-source cells

Pressure-diagnostic source cells for the stage-3 witness sources (dining room
and galley), `pulse_t0`, whole-hull material time:

| hull | source / lane | before h | after h |
|---|---|---:|---:|
| classic_cruise_1900 | MainDining_L / design | 0.2073 | 0.2045 |
| classic_cruise_1900 | MainDining_L / native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainGalley / design | 0.1035 | 0.1043 |
| classic_cruise_1900 | MainGalley / native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainDining_L / commissioned | 0.2208 | 0.1874 |
| classic_cruise_1900 | MainGalley / commissioned | 0.1099 | 0.1071 |
| diamond_princess | International / design | 0.2621 | 0.2381 |
| diamond_princess | International / native | 0.2337 | 0.2223 |
| diamond_princess | MainGalley / design | 0.09058 | 0.09528 |
| diamond_princess | MainGalley / native | 0.08395 | 0.08391 |
| diamond_princess | International / commissioned | 0.3748 | 0.2255 |
| diamond_princess | MainGalley / commissioned | 0.08522 | 0.08338 |
| expedition_cruise_450 | MainDining / design | 0.1898 | 0.1879 |
| expedition_cruise_450 | MainDining / native | 0.1768 | 0.1763 |
| expedition_cruise_450 | MainGalley / design | 0.1015 | 0.1015 |
| expedition_cruise_450 | MainGalley / native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainDining / commissioned | 0.2803 | 0.2057 |
| expedition_cruise_450 | MainGalley / commissioned | 0.1073 | 0.1074 |
| greg_mortimer | DiningRoom / design | 0.159 | 0.1587 |
| greg_mortimer | DiningRoom / native | 0.1323 | 0.1323 |
| greg_mortimer | MainGalley / design | 0.08477 | 0.08477 |
| greg_mortimer | MainGalley / native | 0.05768 | 0.05768 |
| greg_mortimer | DiningRoom / commissioned | 0.2408 | 0.1329 |
| greg_mortimer | MainGalley / commissioned | 0.05932 | 0.05932 |
| mega_cruise_5000 | MainDining_L / design | 0.5665 | 0.557 |
| mega_cruise_5000 | MainDining_L / native | 0.3659 | 0.365 |
| mega_cruise_5000 | Windjammer / design | 0.5986 | 0.5571 |
| mega_cruise_5000 | Windjammer / native | 0.3681 | 0.365 |
| mega_cruise_5000 | MainDining_L / commissioned | 0.4259 | 0.3859 |
| mega_cruise_5000 | Windjammer / commissioned | 0.4337 | 0.3618 |
| spirit_cruise_3000 | MainDining_L / design | 0.2061 | 0.2053 |
| spirit_cruise_3000 | MainDining_L / native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainGalley / design | 0.1024 | 0.1039 |
| spirit_cruise_3000 | MainGalley / native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainDining_L / commissioned | 0.1995 | 0.1894 |
| spirit_cruise_3000 | MainGalley / commissioned | 0.09468 | 0.09714 |

Paired diagnostic (`tools/diag/contam_paired_diagnostic.py`), `pulse_t0`
(the `split_t0_t1` cells agree to the printed digits), before → after:

| hull | source | lane | whole-hull material time h | transport loss | max \|closure error\| |
|---|---|---|---|---|---|
| classic_cruise_1900 | MainDining_L | authored | 0.2208 → 0.1874 | 0.9779 → 0.9813 | 1.1e-16 |
| classic_cruise_1900 | MainDining_L | commissioned | 0.2208 → 0.1874 | 0.9779 → 0.9813 | 1.1e-16 |
| classic_cruise_1900 | MainDining_L | native | 0.1726 → 0.1726 | 0.9827 → 0.9827 | 4.4e-16 |
| classic_cruise_1900 | MainGalley | authored | 0.1099 → 0.1071 | 0.989 → 0.9893 | 1.1e-16 |
| classic_cruise_1900 | MainGalley | commissioned | 0.1099 → 0.1071 | 0.989 → 0.9893 | 1.1e-16 |
| classic_cruise_1900 | MainGalley | native | 0.09452 → 0.09452 | 0.9905 → 0.9905 | 2.2e-16 |
| diamond_princess | International | authored | 0.3748 → 0.2255 | 0.9625 → 0.9775 | 6.7e-16 |
| diamond_princess | International | commissioned | 0.3748 → 0.2255 | 0.9625 → 0.9775 | 6.7e-16 |
| diamond_princess | International | native | 0.2337 → 0.2223 | 0.9766 → 0.9778 | 1.4e-15 |
| diamond_princess | MainGalley | authored | 0.08522 → 0.08338 | 0.9915 → 0.9917 | 2.2e-16 |
| diamond_princess | MainGalley | commissioned | 0.08522 → 0.08338 | 0.9915 → 0.9917 | 2.2e-16 |
| diamond_princess | MainGalley | native | 0.08395 → 0.08391 | 0.9916 → 0.9916 | 8.9e-16 |
| expedition_cruise_450 | HD_5P_M | authored | 0.05176 → 0.05176 | 0.9948 → 0.9948 | 2.2e-16 |
| expedition_cruise_450 | HD_5P_M | commissioned | 0.05176 → 0.05176 | 0.9948 → 0.9948 | 2.2e-16 |
| expedition_cruise_450 | HD_5P_M | native | 0.05181 → 0.05181 | 0.9948 → 0.9948 | 1.1e-16 |
| expedition_cruise_450 | MainDining | authored | 0.2803 → 0.2057 | 0.972 → 0.9794 | 1.1e-16 |
| expedition_cruise_450 | MainDining | commissioned | 0.2803 → 0.2057 | 0.972 → 0.9794 | 1.1e-16 |
| expedition_cruise_450 | MainDining | native | 0.1768 → 0.1763 | 0.9823 → 0.9824 | 1.1e-16 |
| expedition_cruise_450 | MainGalley | authored | 0.1073 → 0.1074 | 0.9893 → 0.9893 | 3.3e-16 |
| expedition_cruise_450 | MainGalley | commissioned | 0.1073 → 0.1074 | 0.9893 → 0.9893 | 3.3e-16 |
| expedition_cruise_450 | MainGalley | native | 0.08685 → 0.08685 | 0.9913 → 0.9913 | 3.3e-16 |
| expedition_cruise_450 | PoolDeck | authored | 1.838 → 0.02726 | 0.8158 → 0.9973 | 7.8e-16 |
| expedition_cruise_450 | PoolDeck | commissioned | 1.838 → 0.02726 | 0.8158 → 0.9973 | 7.8e-16 |
| expedition_cruise_450 | PoolDeck | native | 2.602 → 0.01586 | 0.7325 → 0.9984 | 1.4e-15 |
| greg_mortimer | DiningRoom | authored | 0.2408 → 0.1329 | 0.9759 → 0.9867 | 1.1e-16 |
| greg_mortimer | DiningRoom | commissioned | 0.2408 → 0.1329 | 0.9759 → 0.9867 | 1.1e-16 |
| greg_mortimer | DiningRoom | native | 0.1323 → 0.1323 | 0.9868 → 0.9868 | 1.3e-15 |
| greg_mortimer | MainGalley | authored | 0.05932 → 0.05932 | 0.9941 → 0.9941 | 4.4e-16 |
| greg_mortimer | MainGalley | commissioned | 0.05932 → 0.05932 | 0.9941 → 0.9941 | 4.4e-16 |
| greg_mortimer | MainGalley | native | 0.05768 → 0.05768 | 0.9942 → 0.9942 | 4.4e-16 |
| mega_cruise_5000 | MainDining_L | authored | 0.4259 → 0.3859 | 0.9571 → 0.9614 | 6.7e-16 |
| mega_cruise_5000 | MainDining_L | commissioned | 0.4259 → 0.3859 | 0.9571 → 0.9614 | 6.7e-16 |
| mega_cruise_5000 | MainDining_L | native | 0.3659 → 0.365 | 0.9634 → 0.9635 | 1.1e-15 |
| mega_cruise_5000 | Windjammer | authored | 0.4337 → 0.3618 | 0.9563 → 0.9638 | 0.0e+00 |
| mega_cruise_5000 | Windjammer | commissioned | 0.4337 → 0.3618 | 0.9563 → 0.9638 | 0.0e+00 |
| mega_cruise_5000 | Windjammer | native | 0.3681 → 0.365 | 0.963 → 0.9635 | 1.1e-16 |
| spirit_cruise_3000 | MainDining_L | authored | 0.1995 → 0.1894 | 0.9801 → 0.9811 | 1.1e-16 |
| spirit_cruise_3000 | MainDining_L | commissioned | 0.1995 → 0.1894 | 0.9801 → 0.9811 | 1.1e-16 |
| spirit_cruise_3000 | MainDining_L | native | 0.1746 → 0.1746 | 0.9825 → 0.9825 | 6.7e-16 |
| spirit_cruise_3000 | MainGalley | authored | 0.09468 → 0.09714 | 0.9905 → 0.9903 | 5.6e-16 |
| spirit_cruise_3000 | MainGalley | commissioned | 0.09468 → 0.09714 | 0.9905 → 0.9903 | 5.6e-16 |
| spirit_cruise_3000 | MainGalley | native | 0.09267 → 0.09267 | 0.9907 → 0.9907 | 4.4e-16 |

84 cells per run; the largest closure error in either run is 1.4e-15. Native
cells are identical to nine decimals on `spirit_cruise_3000` and move on the
other five hulls, mostly below the printed digits; the largest printed move is
`diamond_princess` `International` 0.2337 → 0.2223 h in the pressure
diagnostic. A native move is expected: the native lane now carries the 23
exchange sinks.

Forced-exhaust exact-check, before → after:

| hull | arm | zones | sanitary n | field sanitary exact h (median) | field endpoint sum h (median) | native sanitary exact h (median) | galley exhaust solved m³/h |
|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | as_authored | 79 → 79 | 17 → 17 | 0.052083221 → 0.052083219 | 4.586992e-09 → 4.586989e-09 | 0.052083333 → 0.052083333 | 11999.999 → 11999.999 |
| classic_cruise_1900 | sanitary_makeup_oneway | 79 → 79 | 17 → 17 | 0.052083221 → 0.052083219 | 4.586992e-09 → 4.586989e-09 | 0.052083333 → 0.052083333 | 11999.999 → 11999.999 |
| diamond_princess | as_authored | 159 → 159 | 39 → 39 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 18000.000 → 18000.000 |
| diamond_princess | sanitary_makeup_oneway | 159 → 159 | 39 → 39 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 18000.000 → 18000.000 |
| expedition_cruise_450 | as_authored | 47 → 47 | 13 → 13 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 8000.000 → 8000.000 |
| expedition_cruise_450 | sanitary_makeup_oneway | 47 → 47 | 13 → 13 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 8000.000 → 8000.000 |
| greg_mortimer | as_authored | 50 → 50 | 11 → 11 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 5000.000 → 5000.000 |
| greg_mortimer | sanitary_makeup_oneway | 50 → 50 | 11 → 11 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 5000.000 → 5000.000 |
| mega_cruise_5000 | as_authored | 192 → 192 | 63 → 63 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 0.000 → 0.000 |
| mega_cruise_5000 | sanitary_makeup_oneway | 192 → 192 | 63 → 63 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 0.000 → 0.000 |
| spirit_cruise_3000 | as_authored | 115 → 115 | 28 → 28 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 14999.999 → 14999.999 |
| spirit_cruise_3000 | sanitary_makeup_oneway | 115 → 115 | 28 → 28 | 0.052083221 → 0.052083221 | 4.586992e-09 → 4.586992e-09 | 0.052083333 → 0.052083333 | 14999.999 → 14999.999 |

The median sanitary exact integrals and the solved galley exhaust are
unchanged to the printed digits except `classic_cruise_1900` (field median 0.052083221 →
0.052083219 h).

## Bundles and design pins

- The six committed `platform.prj` / `path_map.json` bundles are regenerated
  in commissioned mode. Before authoring, the changed exporter reproduced the
  committed bundles of `expedition_cruise_450`, `diamond_princess` and
  `enterprise_galaxy_tng` byte-for-byte. Path-map entries: classic 838 → 840,
  diamond 1,773 → 1,789, expedition 345 → 347, greg 358 → 368, mega 2,593 →
  2,603, spirit 1,305 → 1,311 (two legs per record).
- `tools/contam_commissioned_check.py` on the six hulls: PASS, every
  commissioned terminal inside 5% of declared.
- `campaigns/contam/phase2_cruise_contrasts_01`: the `_02` successor design
  (`design/phase2_cruise_contrasts_design_v2.json`) is rebuilt in place under
  the same design id, as in `CONTAM-AMBIENT-MAKEUP-CRUISE-01`: only the four
  hull-panel `path_map_entries` move (panel total 5,081 → 5,101);
  `source_pools_v2.json` and `campaign_v2.json` are byte-identical. No `_02`
  field cache has been produced, so no successor beyond `_02` is needed. The
  `_01` design, pools, campaign and readouts are byte-untouched.
- `campaigns/contam/phase1_hvac_tracer_01`: rebuilding the `_02` successor is
  a no-op; `_01` byte-untouched.

Moved test expectations, each attributed to the authored records:

- `tests/test_contam_ambient_opening.py`
  `test_only_makeup_louvres_are_declared` becomes
  `test_declared_makeup_louvres` (same eight hulls, same counts, rate 0, no
  declared wind) plus `test_declared_weather_openings` (exactly the 23
  `open_deck` records above, each with a declared wind and a non-zero rate)
  plus `test_weather_zones_carry_the_authored_exposure` (exactly those 23
  zones declare `exposure`). Any other opening type fails the guard.
- `tests/test_contam_ambient_opening_boundary.py`
  `test_committed_ambient_opening_legs_are_the_makeup_louvres` becomes
  `..._are_the_declared_records`: legs per hull are the louvre legs plus two
  per weather record (classic 2+2, diamond 2+16, expedition 2+2, greg 2+10,
  mega 20+10, spirit 2+6; the two fiction hulls stay at 2).
- `tests/test_contam_phase2_cruise_contrasts_campaign.py`
  `test_v2_hull_panel_tracks_current_platform_jsons`: the four counts above.

## Residuals and open items

1. The committed point (1 m/s) and the axis (0-10 m/s) are declared
   assumptions, Grade C. Even the low end gives 12 to 172 air changes per hour
   on a deck zone; the sourced magnitude of proposal §4 is still owed.
2. The area rule is an assumption about deck geometry, not a drawing.
3. Field lanes clear a weather-deck pulse 0.81 to 2.44 times as slowly as
   native at the same outward rate; cause is a hypothesis (above).
4. `greg_mortimer` pressure residual unchanged (938 Pa design, 44.9 kPa
   commissioned); `spirit_cruise_3000` design still 757 Pa.
5. Four `greg_mortimer` AHU-served bar/observation zones and the promenades
   are untagged pending an owner decision.
6. The ContamX wind flag is clear on every exported path, so the wind profile
   on envelope leaks does nothing fleet-wide. Not changed here.
7. Naval weather-zone classes are the next PRs; they can reuse
   `wind_speed_m_s`, the area rule and this D5 method unchanged.

## Reproduction

```text
for h in classic_cruise_1900 diamond_princess expedition_cruise_450 \
  greg_mortimer mega_cruise_5000 spirit_cruise_3000; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python tools/diag/ambient_makeup_witness.py --label after \
  --hull classic_cruise_1900 --hull diamond_princess \
  --hull expedition_cruise_450 --hull greg_mortimer \
  --hull mega_cruise_5000 --hull spirit_cruise_3000
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull expedition_cruise_450 --lane design --lane commissioned \
  --source PoolDeck --out <file>
.venv/bin/python tools/contam_commissioned_check.py --platform classic_cruise_1900 \
  --platform diamond_princess --platform expedition_cruise_450 \
  --platform greg_mortimer --platform mega_cruise_5000 --platform spirit_cruise_3000
.venv/bin/python campaigns/contam/phase2_cruise_contrasts_01/design/build.py
```

The D5 sweep sets `wind_speed_m_s` to 0, 1, 5 and 10 on every `open_deck`
record of a hull in memory, exports with
`tools.contamw34_prj.export_contamw34(..., hobbyist=True, overrides=<hull
overrides>, ahs_terminal_mode=<design|commissioned>)`, solves with
`engines.contamx_runner.run_contamx` and sums positive and negative `Flow0`
over the record's two `ambient_opening` path-map entries. The "before" runs
are the same commands in a worktree of `origin/main` `2271f2c1`.
