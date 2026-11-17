# CONTAM-AMBIENT-WEATHER-CARRIER-01
**Date:** 2026-11-17
**Commit:** 0efb80db
**Pathogens:** all
**Status:** measured
**Measured at:** 0efb80db

## Scope

After-witnesses measured on this branch; before-witnesses at `origin/main`
`8d4c1874` (after the destroyer sibling #1268 merged). Steady ContamX solves
with the local binary `third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **carrier naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: the `cv`/`cvl`/`cvs`/`cve`/`cc` hulls plus named carriers
the audit classifies as carrier. Exact roster and borderline calls:
`yorktown_cv5`, `wasp_cv7`, `saratoga_cv60`, `saratoga_cv3`, `ranger_cv4`,
`midway_cv41`, `lexington_cv2`, `independence_cvl26`, `antietam_cvs36`,
`wright_cc2`, `thetis_bay_cve90`, `puncher_cve53`, and borderline
`battler_acv6` (HMS Battler, Attacker/Bogue-class escort carrier by its own
description; `acv` is not a suffix in the prompt list but the hull is a named
escort carrier). `san_antonio_class_lpd` has a flight deck but is an
amphibious transport dock, not a carrier, and is excluded.

Only two roster weather zones are ungrouped stage-4 candidates; every other
lexical weather zone on the roster is already a room of `VENT_Weather` or
`VENT_Hangar` and keeps that declared ventilation-group exchange, so it is
recorded and skipped here rather than given a second direct ambient opening.
Each qualifying zone keeps its finite zone (D2(a)), declares `exposure:
weather` (D7(b)) and carries one `open_deck` `ambient_openings` record (D1(a))
with the Grade C deck-face area rule, `wind_speed_m_s` 1 m/s committed on the
declared 0–10 m/s axis, `schedule: always_open`, and `exchange_m3h` = the
commissioned-lane ContamX-solved outward flow at that point (D5). No
`flow_rate_m3h`, `envelope_leak.area_m2`, engine/exporter constant, wind
override, balcony, hatch or door changed. Naval hulls keep the fleet default
weather from `CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead).

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-AMBIENT-WEATHER-DESTROYER-01`](CONTAM-AMBIENT-WEATHER-DESTROYER-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

| hull | weather zones (lexical/authored) | HVAC group | call |
|---|---|---|---|
| `yorktown_cv5` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `wasp_cv7` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `saratoga_cv60` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `saratoga_cv3` | `Flight_Deck` | none | **authored** |
| `ranger_cv4` | `Flight_Deck`, `Poop_Deck` | `VENT_Weather` | skip: grouped |
| `midway_cv41` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `lexington_cv2` | `Flight_Deck` | none | **authored** |
| `independence_cvl26` | `Flight_Deck`, `Gallery_Deck`, `Poop_Deck`, `Forecastle_Deck` | `VENT_Weather`/`VENT_Hangar` | skip: grouped; `Focsle_Stores` enclosed correction |
| `antietam_cvs36` | `Flight_Deck`, `Gallery_Deck`, `Forecastle_Deck` | `VENT_Weather`/`VENT_Hangar` | skip: grouped |
| `wright_cc2` | `Flight_Deck_Aft`, `Flight_Deck_Mid`, `Flight_Deck_Fwd` | `VENT_Weather` | skip: grouped |
| `thetis_bay_cve90` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `puncher_cve53` | `Flight_Deck` | `VENT_Weather` | skip: grouped |
| `battler_acv6` | `Walkways_Focsle`, `Flight_Deck` | `VENT_Weather` | skip: borderline roster, grouped |

## Exposure calls

- **Weather records: 2** (`lexington_cv2/Flight_Deck`,
  `saratoga_cv3/Flight_Deck`). Both descriptions already say open flight deck;
  the authored `exposure: weather` records the fact and selects them for the
  opening guard. The other 20 roster lexical weather zones stay grouped and
  undeclared, so the fleet inventory in `CONTAM-AMBIENT-EXPOSURE-01` is
  unchanged outside these two zones.
- **Enclosed corrections: 1.** The lexical id match called
  `independence_cvl26/Focsle_Stores` weather because of `Focsle`, but its own
  description is capstan/windlass/stores, so it declares `exposure: enclosed`
  and carries no opening.

## Bundles and design pins

Regenerated the two affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record (2 records → 4 legs).
`independence_cvl26` needed no bundle regeneration: `exposure` is audit
metadata, not an exporter input. No frozen Phase 1/2 campaign design names a
carrier `path_map_entries` pin that moves here, so no `_v2` succession was
needed; `_01`/`_v1` artifacts are byte-untouched. No cache was produced or
uploaded.

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (design, commissioned and
authored lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the carrier
hulls are not in the tool's default `PLATFORM_SOURCES`, so the same matrix was
run programmatically with explicit source `Flight_Deck`, `pulse_t0` and
`split_t0_t1`, native/commissioned/authored/design lanes: 16 cells per run).
`tools/contam_commissioned_check.py` on the three touched hulls: PASS, every
commissioned terminal inside 5% of declared.

### Openings and D5

| hull | zone | volume m³ | area_m2 | wind_speed_m_s | exchange_m3h | air changes /h |
|---|---|---:|---:|---:|---:|---:|
| `lexington_cv2` | `Flight_Deck` | 14,777.49 | 421.11 | 1.0 | 337,358.9 | 22.84 |
| `saratoga_cv3` | `Flight_Deck` | 19,047.89 | 478.09 | 1.0 | 318,131.6 | 16.70 |

D5 sweep, commissioned outward flow m³/h at U = 0 / 1 / 5 / 10 m/s:
`lexington_cv2` 0 / 337,358.9 / 1,696,816.5 / 2,830,379.1;
`saratoga_cv3` 0 / 318,131.6 / 1,637,302.8 / 3,213,497.9.
The declared native rate is the U = 1 m/s solved value rounded to 0.1 m³/h;
the field lane solves the same point to 337,359 / 318,132 m³/h outward sink
(field ÷ native = 1.000000).

### Flow compare (before -> after)

| hull | path_map entries | native links | ambient_opening legs | field opening inward m³/h | field opening outward sink m³/h | native `ambient_exchange_*` links | native exchange total m³/h | field ÷ native |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `lexington_cv2` | 300 -> 302 | 331 -> 332 | 0 -> 2 | 0 -> 343,553 | 0 -> 337,359 | 0 -> 1 | 0 -> 337,358.9 | 1.000000 |
| `saratoga_cv3` | 320 -> 322 | 349 -> 350 | 0 -> 2 | 0 -> 325,258 | 0 -> 318,132 | 0 -> 1 | 0 -> 318,131.6 | 1.000000 |

### Paired source cells (`Flight_Deck`, `pulse_t0`)

Whole-hull material time h, before -> after:

| hull | lane | before h | after h |
|---|---|---:|---:|
| `lexington_cv2` | native | 6.94591 | 0.0448045 |
| `lexington_cv2` | commissioned | 3.75499 | 0.0607595 |
| `lexington_cv2` | authored | 3.75499 | 0.0607595 |
| `lexington_cv2` | design | 6.98518 | 0.0432162 |
| `saratoga_cv3` | native | 6.95523 | 0.0610789 |
| `saratoga_cv3` | commissioned | 4.89364 | 0.0782798 |
| `saratoga_cv3` | authored | 4.89364 | 0.0782798 |
| `saratoga_cv3` | design | 6.98724 | 0.0588557 |

The same run also wrote the `split_t0_t1` cells (16 cells per run); closure
errors stayed at solver roundoff (max printed 2.6e-15 before, 1.1e-16 after on
the `pulse_t0` rows shown).

### Pressure balance (before -> after)

| hull | lane | paths | max abs dP Pa | interior max abs dP Pa | blocked interior n | envelope max abs dP Pa | envelope net in m³/h | opening net in m³/h | balance residual m³/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `lexington_cv2` | design | 300 -> 302 | 314.8 -> 314.8 | 1.206 -> 1.938 | 21 -> 21 | 2.506 -> 4.533 | 4.402e-08 -> 33.09 | 0 -> -33.08 | -4.40e-08 -> -0.0161 |
| `lexington_cv2` | commissioned | 300 -> 302 | 5.211e+04 -> 314.8 | 2.231 -> 1.771 | 6 -> 6 | 5.211e+04 -> 4.61 | 6233 -> 38.58 | 0 -> 6194 | 4.51e-05 -> -0.00311 |
| `lexington_cv2` | authored | 300 -> 302 | 5.211e+04 -> 314.8 | 2.231 -> 1.771 | 6 -> 6 | 5.211e+04 -> 4.61 | 6233 -> 38.58 | 0 -> 6194 | 4.51e-05 -> -0.00311 |
| `saratoga_cv3` | design | 320 -> 322 | 317.1 -> 317.1 | 2.36 -> 1.766 | 22 -> 22 | 2.365 -> 3.758 | 4.415e-08 -> 35.41 | 0 -> -35.41 | -4.41e-08 -> 0.00223 |
| `saratoga_cv3` | commissioned | 320 -> 322 | 5.579e+04 -> 317.1 | 4.053 -> 1.746 | 7 -> 7 | 5.579e+04 -> 4.952 | 7173 -> 46.63 | 0 -> 7127 | 3.94e-05 -> -0.00573 |
| `saratoga_cv3` | authored | 320 -> 322 | 5.579e+04 -> 317.1 | 4.053 -> 1.746 | 7 -> 7 | 5.579e+04 -> 4.952 | 7173 -> 46.63 | 0 -> 7127 | 3.94e-05 -> -0.00573 |

Design-lane after max |ΔP| is 314.8 Pa on `lexington_cv2` and 317.1 Pa on
`saratoga_cv3`, both inside the stage-1 naval design range 0.5–374 Pa; the
design maxima were already 314.8 / 317.1 Pa before and are unchanged. The
commissioned/authored lane maxima fall from 5.211e4 / 5.579e4 Pa to the
design-lane values. Balance residuals stay at solver-noise level (largest
after magnitude 0.0161 m³/h on 3.37e5 m³/h of opening throughflow,
4.8e-8 relative); the mass balance is not broken. ContamX converged on every
hull and lane.

## Reproduction

```bash
for h in lexington_cv2 saratoga_cv3; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull lexington_cv2 --hull saratoga_cv3 --lane design --lane commissioned \
  --lane authored --source Flight_Deck --out telemetry_buffer/carrier_pressure_after.json
.venv/bin/python tools/contam_flow_compare.py --platform lexington_cv2 --run-contamx
.venv/bin/python tools/contam_flow_compare.py --platform saratoga_cv3 --run-contamx
.venv/bin/python tools/contam_commissioned_check.py --platform lexington_cv2 \
  --platform saratoga_cv3 --platform independence_cvl26
```
