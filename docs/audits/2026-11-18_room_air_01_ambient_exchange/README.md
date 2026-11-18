> **Status:** Evidence note — docs-only audit of whether ROOM-AIR-01 should see `ambient_openings.exchange_m3h`; no engine, platform, schema, or epidemiological-constant change.

# ROOM-AIR-01 and ambient-opening exchange

Date: 2026-11-18. Tree pin: `main` at `95b4974b` (after ambient stages 1–4 and grouped-weather G4 PRs #1302–#1308). Question: should the transmission layer's room-air residence factor see the exchange already declared on `ambient_openings`, given that `build_zone_air_exchange_map` reads only `hvac_zones[].rooms`?

Mechanism read: `engines/transmission_core.py::build_zone_air_exchange_map` maps room -> ACH from `hvac_zones` declarations only; a room with no entry is read as the sealed-room baseline. ROOM-AIR-01 applies the first-order residence factor \(f(x)=(1-e^{-x})/x\) with \(x=\mathrm{ACH}\cdot\mathrm{hours\_per\_epoch}\). The physical run clock is one hour per epoch (`crusher_labs/config.yaml`: `epoch_duration_hours: 1`, `natural_history_clock: hours`), so this note uses `hours_per_epoch = 1.0`; absent or zero ACH gives \(f=1.0\).

## Evidence files

- `evidence/ambient_opening_records.csv` — one row per `ambient_openings` record (302 rows).
- `evidence/ambient_opening_zones.csv` — one row per affected zone (301 zones; one zone carries two records).
- `evidence/class_summary.json` — counts and dose-factor ranges by occupancy/opening class.
- `evidence/material_zones.json` — all zones with implied ACH > 1 h⁻¹ (283 `open_deck` zones).
- `evidence/occupied_material_zones.json` — the 257-zone subset with a declared occupancy path.
- `evidence/crew_work_fallback_material_zones.json` — the 26 `open_deck` zones reachable only through the crew work fallback.

## Census

| Measure | Value |
|---|---:|
| Platforms with `ambient_openings` | 76 |
| `ambient_openings` records | 302 |
| Affected zones | 301 |
| `open_deck` records / zones | 283 records, 283 zones |
| `makeup_louvre` records | 19 |
| Zone types | 288 `Free`, 14 `Dining` |
| Origin tags | 182 stage-4 `CONTAM-AMBIENT-WEATHER-*`, 101 G4 `CONTAM-GROUPED-WEATHER-*`, 19 makeup |
| Duplicate zone | `olympia_c6/MD_Forecastle_Open` carries one `open_deck` and one `makeup_louvre` record |

`exchange_m3h` is present on every record. Nineteen `makeup_louvre` records carry `exchange_m3h = 0.0` (inward clean make-up, not a native sink); all `open_deck` records carry positive exchange.

## ACH-map status after G4

For the 283 `open_deck` zones, the current `build_zone_air_exchange_map` result is: **256 zones absent, 27 zones present with rate 0.0, 0 zones positive**. The 27 present-zero rows are `AHU_Weather`-style groups whose declared rate is already zero; absence and zero both read as the sealed-room baseline \(f=1.0\) for ROOM-AIR-01.

For the 101 G4 grouped-weather zones specifically, the pre-change HVAC-map value was present on all 101: rate 0.5–15.0 ACH (median class mix: 0.5 ×48, 3.0 ×14, 5.0 ×11, 2.0 ×9, 6.0 ×8, plus smaller counts). After G4 removed those rooms from `hvac_zones[].rooms`, every one of the 101 is absent from the ACH map. The stage-4 ambient-weather records did not leave HVAC groups: 27 were already present at rate 0.0 and the rest were already absent. Makeup-louvre dining/lounge zones mostly remain on positive HVAC groups (rates 4.0–7.5 ACH) with `exchange_m3h = 0.0`.

## Implied ACH and dose-factor magnitude

Implied ACH is `exchange_m3h / volume_m3` (h⁻¹). For the 283 `open_deck` zones:

| Quantity | Min | Median | p90 | Max |
|---|---:|---:|---:|---:|
| Implied ACH (h⁻¹) | 10.51 | 112.72 | 218.11 | 585.76 |
| ROOM-AIR-01 factor if wired | 0.001707 | 0.008871 | 0.024353 | 0.095174 |

Because current effective ACH is zero/absent for every `open_deck` zone, the "dose-factor ratio" is the wired factor itself: wiring would leave **0.17%–9.52%** of the current within-epoch air-dose factor, median **0.89%**. In dose terms that is roughly a 10×–585× reduction on those zones, median ~112×.

For the 95 strict-occupied G4 grouped-weather zones, the same wired factor is also below the pre-G4 HVAC-map factor: open-vs-before residence ratio min 0.00632, median 0.03198, max 0.18341. In other words, wiring the declared opening is more protective than both the current sealed baseline and the pre-G4 HVAC-map value, not merely a restoration of the old HVAC removal.

## Occupancy / schedule presence

`spatial_layout.json` has no per-zone schedule field; occupancy is schedule- and catalog-driven in `engines/infection_dynamics_bridge.py`. This audit therefore classifies reachability, not a realized head-count:

- `Dining` zones are meal venues (`Meal:*` tokens). All 14 `Dining` ambient zones are `makeup_louvre` records with `exchange_m3h = 0.0`, so they are occupied but not material to this question.
- A `Free` zone that passes `is_leisure_accessible` is in the leisure catalog used for `Free` tokens. 254 `open_deck` zones (253 pure `open_deck` plus `olympia_c6/MD_Forecastle_Open`, which also carries a makeup record) and 3 makeup-only `Free` zones are in this class.
- Same-platform `crew_manifest.json` `berth_zone`/`duty_zone` references add 3 more `open_deck` zones as manifest postings (the manifest is still marked as proposed in places, so this is supporting evidence, not the only occupancy path).
- Under the shipped default `ship_graph.agent_classes`, crew classes with no resolved duty pin draw `work` uniformly from all `Free` + `Dining` zones (`_resolve_class_zones`). Every ambient zone is `Free` or `Dining`, so even the 26 `open_deck` zones with no passenger-leisure or manifest posting remain crew-work reachable. Passenger-carrying hulls additionally give passenger `Free` tokens to leisure-accessible zones; crew-only hulls rely on crew work/free tokens.

Strict occupied/material count: **257 zones** have a declared occupancy path and implied ACH > 1 h⁻¹. Add the 26 crew-work-fallback-only `open_deck` zones and **all 283 `open_deck` zones are material if reached**. The "weather decks are mostly unoccupied" expectation is therefore not supported as a blanket statement: the open decks are schedule-reachable, and the only clearly unoccupied-by-exchange class is the zero-exchange makeup-louvre set.

## Materiality verdict by class

| Class | Zones | Current ACH | Implied ACH | Verdict |
|---|---:|---|---|---|
| `open_deck`, strict occupied | 257 | absent or 0.0 | 10.5–585.8, median 110.5 | Material: factor 1.0 → 0.0017–0.095 |
| `open_deck`, crew-work fallback only | 26 | absent or 0.0 | 50.1–439.4, median 161.7 | Material if reached; smaller expected occupancy |
| `makeup_louvre` dining/lounge | 17 | positive HVAC ACH 4.0–7.5 | 0.0 | Not material if additive; harmful if used as ACH=0 override |
| `makeup_louvre` no declared posting | 1 | absent | 0.0 | Not material |
| `open_deck` + `makeup_louvre` same zone | 1 (`olympia_c6/MD_Forecastle_Open`) | absent | 136.5 | Material via the `open_deck` record |

## Recommendation

**Wire — additively, not as a Phase-3 deferral and not as an override.** ROOM-AIR-01 should see ambient-opening exchange for zones that declare a positive `exchange_m3h`, because the measured occupied set is large and the dose-factor change is orders of magnitude: 257 occupied-material zones today, with a median wired factor of 0.0089 versus the current sealed 1.0. The epidemiological consequence is that the current transmission layer overstates within-epoch airborne dose on weather-exposed decks by roughly 10×–585× (median ~112×); leaving G4 openings invisible to this map also makes the native transmission layer inconsistent with the ContamX lane that already solves those openings.

Implementation shape for the later engine change: add `sum(exchange_m3h)/volume_m3` as an ACH contribution for `ambient_openings` zones, including when the HVAC-map entry is absent or zero; do **not** let `exchange_m3h = 0.0` makeup-louvre records replace positive HVAC ACH. No current zone has both a positive HVAC ACH and a positive ambient exchange, so additive wiring changes only the sealed/zero weather-deck set and leaves the dining HVAC rates intact.

## Validation

- Docs-only change: `data/platforms/**` and `engines/**` are byte-identical to `95b4974b`; the diff is confined to `docs/audits/2026-11-18_room_air_01_ambient_exchange/`.
- Pre-commit is run on the changed files before the PR.
