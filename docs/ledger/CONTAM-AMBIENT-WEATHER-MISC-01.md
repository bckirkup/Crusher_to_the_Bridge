# CONTAM-AMBIENT-WEATHER-MISC-01
**Date:** 2026-11-17
**Commit:** 44e6209d
**Pathogens:** all
**Status:** measured
**Measured at:** 44e6209d

## Scope

After-witnesses measured on this branch at `44e6209d`; before-witnesses were
the same solves on the pre-change `data/platforms` state. The branch is rebased
on `origin/main` `455f9ff7`, which includes auxiliary #1278; that merge touched
only auxiliary platform files and the opening-guard test, not the MISC hulls or
the Contam tools, so the `6742f1a4` before solves remain the correct before
state for this roster. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **miscellaneous remainder**: the small heterogeneous set of
platforms left after the merged stage-4 classes (cruise #1262, destroyer #1268,
carrier #1272, battleship #1274, cruiser #1277, fiction #1276, auxiliary
#1278, amphibious #1279). The roster was
enumerated from `tools/hull_audit.py` semantics (`_is_exterior` +
`_removal_ach`) over `data/platforms/`, not from the prompt's expected-member
list; exact roster and borderline calls are below.

OWNER RULING (Benjamin, 2026-11-16): the Grade C deck-face area rule and its
large solved rates are ACCEPTED as declared assumptions — record, do not tune.
Fleet default wind stays 1 m/s from ahead (#1266) unless you justify otherwise.

SCOPE RULE (status quo, owner question open): open ONLY weather zones with zero
outdoor exchange (ungrouped OR grouped with zero OA exchange). Weather zones
already exchanging via an HVAC group with OA > 0 stay untouched — recorded
below as the known grouped-zone open item.

Only zero-outdoor-exchange weather/open-deck zones are stage-4 candidates.
Each qualifying zone declares `exposure: weather` (D7(b)) and carries one
`open_deck` `ambient_openings` record (D1(a)) with the Grade C deck-face area
rule, `wind_speed_m_s` 1 m/s committed on the declared 0–10 m/s axis,
`schedule: always_open`, and `exchange_m3h` = the commissioned-lane
ContamX-solved outward flow at that point (D5). No `flow_rate_m3h`,
`envelope_leak.area_m2`, engine/exporter constant, wind override, balcony,
hatch or door changed. Naval hulls keep the fleet default weather from
`CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead).

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md)
and the sibling naval weather ledgers.
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

Dependency note: auxiliary #1278 (`CONTAM-AMBIENT-WEATHER-AUXILIARY-01`) is
merged on `origin/main` `455f9ff7`. Its nine hulls (`aeolus_arc3`, `apl_24`,
`bolster_ars38`, `cobalt_k124`, `gordon_gunter_r338`, `liberty_cargo_ec2`,
`lyon_ap71`, `passumpsic_ao106`, `savannah_ns`) are covered there and are not in
the MISC roster.

## Roster calls

Inclusion rule: remaining platform with (a) at least one `_is_exterior` zone at
zero outdoor exchange, (b) no `ambient_openings` on `origin/main`, and (c) a
committed `data/platforms/<hull>/contam/platform.prj`.

| hull | weather/open-deck zones (lexical/authored) | HVAC group / outdoor ACH | call |
|---|---|---|---|
| `castle_class_corvette` | `Foc_Deck_Open`, `Quarterdeck`; `Upper_Deck_Aft` | none for the two openings; `Upper_Deck_Aft` 2.5 | **authored** openings; `Upper_Deck_Aft` grouped OA open item |
| `eagle_pe60` | `Open_Bridge`, `Nav_Bridge`, `Gun_Platform_Fwd`, `After_Gun_Platform`, `AA_Gun_Platforms`, `Fantail`, `Gun_Deck_Fwd` | none | **authored** |
| `esteem_mso438` | `Reel_Deck`, `Boat_Deck_Aft`, `Focsle_01`, `Sweep_Deck`, `Deck_House_Main`; `Focsle_Store` | 6.0 / 3.0 for the five deck zones | no qualifying zero-exchange weather zone; `Focsle_Store` enclosed correction |
| `pce_874` | `Fantail`, `Focsle_Deck` | none | **authored** |
| `raven_am55` | `Foc_Deck_Fwd`, `Foc_Deck_Open`, `Sweep_Deck` | none | **authored** |
| `river_class_frigate` | `Quarterdeck`, `Foc_Deck_Open`; `Signal_Deck` | none for the two openings; `Signal_Deck` 2.5 | **authored** openings; `Signal_Deck` grouped OA open item |
| `rolla_pc483` | `Fantail`, `Focsle_Deck` | none | **authored** |
| `erie_pg50` | `Sup_Deck_Open`, `Fantail_Aft`, `Gun_Deck_Aft`, `Focsle_Main`, `Focsle_Stores` | 6.0 / 3.0 | skip: grouped OA > 0 open item |
| `montana_acr13` | `MD_Aft_Open`, `MD_Forecastle_Open` | 15.0 | skip: grouped OA > 0 open item |
| `expedition_cruise_300`, `messy_cruise_500` | `Pool_Deck` / `Main_Pool_Deck`, `Central_Park_Open_Atrium` | n/a | skip: no committed Contam bundle |

Borderline calls: `eagle_pe60`'s ungrouped gun/AA platforms and open navigating
bridge are authored as weather even though four ids are lexical misses
(`Nav_Bridge`, `Gun_Platform_Fwd`, `After_Gun_Platform`, `AA_Gun_Platforms`);
`esteem_mso438/Focsle_Store`
is storeroom space and is declared `exposure: enclosed`, not weather.
`erie_pg50` and `montana_acr13`, named as expected members, have no
zero-outdoor-exchange weather zone on the audit rule and are recorded/skipped.

## Exposure calls

- **Weather records: 18** (`castle_class_corvette` 2, `eagle_pe60` 7,
  `pce_874` 2, `raven_am55` 3, `river_class_frigate` 2, `rolla_pc483` 2).
  Fourteen were already lexical weather zones in
  `CONTAM-AMBIENT-EXPOSURE-01`; the authored `exposure: weather` makes the fact
  explicit for the opening guard. Four were lexical misses and are the D7(b)
  authoring: `eagle_pe60/Nav_Bridge`, `eagle_pe60/Gun_Platform_Fwd`,
  `eagle_pe60/After_Gun_Platform`, `eagle_pe60/AA_Gun_Platforms`.
- **Enclosed corrections: 1.** `esteem_mso438/Focsle_Store` carries
  `exposure: enclosed` and no opening.
- **Grouped open item:** weather zones already exchanging through an HVAC group
  with OA > 0 stay untouched by the scope rule: `castle_class_corvette/
  Upper_Deck_Aft` (2.5), `river_class_frigate/Signal_Deck` (2.5), the five
  `esteem_mso438` deck zones (6.0/3.0), `erie_pg50`'s five zones (6.0/3.0), and
  `montana_acr13`'s two zones (15.0). The auxiliary hulls covered by merged
  #1278 have the same status.
- After this PR, stage 4 is complete for ungrouped/zero-exchange weather zones
  fleet-wide; grouped OA-exchange weather zones remain the known open item.

## Bundles and design pins

Regenerated the six affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record: `castle_class_corvette`
+4, `eagle_pe60` +14, `pce_874` +4, `raven_am55` +6,
`river_class_frigate` +4, `rolla_pc483` +4. `exposure` is audit metadata, not
an exporter input, so `esteem_mso438` needed no bundle regeneration. A targeted
repository reference search found no campaign/frozen design file naming a MISC
`path_map_entries` pin that moves here, so no `_v2` succession was needed;
`_01`/`_v1` artifacts are byte-untouched. No cache was produced or uploaded.

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (design, commissioned and
authored lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the MISC
hulls are not in the tool's default `PLATFORM_SOURCES`, so the same matrix was
run programmatically with two explicit source zones per hull — the two largest
weather volumes — `pulse_t0`/`split_t0_t1`, native/commissioned/authored lanes:
12 cells per hull per run). `tools/contam_commissioned_check.py` on the
touched opening hulls: PASS, every commissioned terminal inside 5% of declared.

### Openings and D5 (commissioned U=1)

| hull | zone | volume m3 | area_m2 | wind_speed_m_s | exchange_m3h | air changes /h | commissioned U=1 out m3/h | U=1 inward m3/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `castle_class_corvette` | `Foc_Deck_Open` | 307.84 | 60.779 | 1.0 | 40,208.3 | 130.61 | 40,208.3 | 40,957.9 |
| `castle_class_corvette` | `Quarterdeck` | 575.42 | 83.097 | 1.0 | 54,865.1 | 95.35 | 54,865.1 | 56,103.0 |
| `eagle_pe60` | `Open_Bridge` | 41.27 | 22.254 | 1.0 | 14,883.4 | 360.63 | 14,883.4 | 14,894.6 |
| `eagle_pe60` | `Nav_Bridge` | 180.48 | 46.538 | 1.0 | 31,118.9 | 172.42 | 31,118.9 | 31,153.4 |
| `eagle_pe60` | `Gun_Platform_Fwd` | 60.18 | 26.873 | 1.0 | 17,977.0 | 298.72 | 17,977.0 | 17,981.6 |
| `eagle_pe60` | `After_Gun_Platform` | 128.18 | 39.219 | 1.0 | 26,649.2 | 207.90 | 26,649.2 | 25,823.0 |
| `eagle_pe60` | `AA_Gun_Platforms` | 121.61 | 38.201 | 1.0 | 25,550.6 | 210.10 | 25,550.6 | 25,566.0 |
| `eagle_pe60` | `Fantail` | 55.37 | 25.777 | 1.0 | 20,071.3 | 362.49 | 20,071.3 | 21,329.9 |
| `eagle_pe60` | `Gun_Deck_Fwd` | 114.19 | 37.017 | 1.0 | 29,721.9 | 260.28 | 29,721.9 | 29,747.4 |
| `pce_874` | `Fantail` | 195.49 | 48.434 | 1.0 | 38,280.4 | 195.82 | 38,280.4 | 38,460.1 |
| `pce_874` | `Focsle_Deck` | 116.15 | 37.334 | 1.0 | 29,435.0 | 253.42 | 29,435.0 | 29,718.7 |
| `raven_am55` | `Foc_Deck_Fwd` | 312.85 | 61.272 | 1.0 | 48,871.8 | 156.21 | 48,871.8 | 48,871.6 |
| `raven_am55` | `Foc_Deck_Open` | 198.14 | 48.761 | 1.0 | 39,030.4 | 196.98 | 39,030.4 | 38,752.7 |
| `raven_am55` | `Sweep_Deck` | 111.40 | 36.562 | 1.0 | 28,784.1 | 258.39 | 28,784.1 | 29,543.9 |
| `river_class_frigate` | `Quarterdeck` | 983.77 | 108.652 | 1.0 | 72,379.9 | 73.57 | 72,379.9 | 73,621.0 |
| `river_class_frigate` | `Foc_Deck_Open` | 526.42 | 79.480 | 1.0 | 52,548.5 | 99.82 | 52,548.5 | 54,243.1 |
| `rolla_pc483` | `Fantail` | 106.13 | 35.687 | 1.0 | 28,715.3 | 270.57 | 28,715.3 | 28,761.2 |
| `rolla_pc483` | `Focsle_Deck` | 130.01 | 39.498 | 1.0 | 31,640.7 | 243.37 | 31,640.7 | 31,974.8 |


### Pressure balance (before -> after)

| hull | lane | paths | max abs dP Pa | balance residual m3/h | envelope net in m3/h | ambient-opening net in m3/h | k field/native median |
|---|---|---:|---:|---:|---:|---:|---:|
| `castle_class_corvette` | design | 153 -> 157 | 112.1 -> 112.1 | 5.455e-09 -> 0.001597 | -5.455e-09 -> 1.611 | 0 -> -1.613 | 0.7502 -> 0.8694 |
| `castle_class_corvette` | commissioned | 153 -> 157 | 141,611.8 -> 112.1 | -4.547e-13 -> 0.004559 | 1,996.0 -> 8.481 | 0 -> 1,987.5 | 1.048 -> 1.003 |
| `castle_class_corvette` | authored | 153 -> 157 | 141,611.8 -> 112.1 | -4.547e-13 -> 0.004559 | 1,996.0 -> 8.481 | 0 -> 1,987.5 | 1.048 -> 1.003 |
| `eagle_pe60` | design | 319 -> 333 | 94.41 -> 94.41 | -2.733e-08 -> 0.002861 | 2.733e-08 -> -0.01146 | 0 -> 0.008596 | 0.6344 -> 0.9996 |
| `eagle_pe60` | commissioned | 319 -> 333 | 2,102.8 -> 94.41 | 5.597e-06 -> 0.003177 | 525.7 -> 2.168 | 0 -> 523.6 | 0.92 -> 1.001 |
| `eagle_pe60` | authored | 319 -> 333 | 2,102.8 -> 94.41 | 5.597e-06 -> 0.003177 | 525.7 -> 2.168 | 0 -> 523.6 | 0.92 -> 1.001 |
| `pce_874` | design | 172 -> 176 | 100.3 -> 100.3 | 3.843e-08 -> 0.002162 | -3.843e-08 -> 1.08 | 0 -> -1.082 | 1.127 -> 1.127 |
| `pce_874` | commissioned | 172 -> 176 | 6,855.8 -> 100.3 | 1.405e-06 -> 0.0003406 | 465.2 -> 1.809 | 0 -> 463.4 | 1.005 -> 1.009 |
| `pce_874` | authored | 172 -> 176 | 6,855.8 -> 100.3 | 1.405e-06 -> 0.0003406 | 465.2 -> 1.809 | 0 -> 463.4 | 1.005 -> 1.009 |
| `raven_am55` | design | 142 -> 148 | 0.8079 -> 0.8177 | 0 -> 0.005065 | 0 -> 0.329 | 0 -> -0.3341 | 1.38 -> 1.221 |
| `raven_am55` | commissioned | 142 -> 148 | 9,384.2 -> 5.234 | -5.684e-13 -> 0.001611 | 490.2 -> 8.307 | 0 -> 481.9 | 1.012 -> 1 |
| `raven_am55` | authored | 142 -> 148 | 9,384.2 -> 5.234 | -5.684e-13 -> 0.001611 | 490.2 -> 8.307 | 0 -> 481.9 | 1.012 -> 1 |
| `river_class_frigate` | design | 458 -> 462 | 152.2 -> 152.2 | -1.098e-08 -> 0.004912 | 1.098e-08 -> 8.858 | 0 -> -8.863 | 1.108 -> 1.108 |
| `river_class_frigate` | commissioned | 458 -> 462 | 82,027.9 -> 152.2 | -5.62e-06 -> -0.0006277 | 2,975.7 -> 40.08 | 0 -> 2,935.7 | 1.113 -> 1.009 |
| `river_class_frigate` | authored | 458 -> 462 | 82,027.9 -> 152.2 | -5.62e-06 -> -0.0006277 | 2,975.7 -> 40.08 | 0 -> 2,935.7 | 1.113 -> 1.009 |
| `rolla_pc483` | design | 206 -> 210 | 82.61 -> 82.61 | -3.082e-09 -> -0.0001622 | 3.082e-09 -> 0.4914 | 0 -> -0.4912 | 0.7394 -> 0.7706 |
| `rolla_pc483` | commissioned | 206 -> 210 | 2,081.0 -> 82.61 | 7.013e-06 -> -0.001133 | 383.7 -> 3.681 | 0 -> 380 | 0.8302 -> 0.9916 |
| `rolla_pc483` | authored | 206 -> 210 | 2,081.0 -> 82.61 | 7.013e-06 -> -0.001133 | 383.7 -> 3.681 | 0 -> 380 | 0.8302 -> 0.9916 |


Design-lane after max |ΔP| stays inside the stage-1 naval design range
0.5–374 Pa on every opened hull; the largest after balance residual is
0.005065 m³/h.

### Flow compare (before -> after)

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | boundary-sink paths | boundary sink out m3/h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `castle_class_corvette` | 153 -> 157 | 188 -> 190 | 88 -> 88 | 32 -> 32 | 0 -> 4 | 0 -> 97,060.9 | 0 -> 95,073.4 | 0 -> 3 | 0 -> 95,073.5 |
| `eagle_pe60` | 319 -> 333 | 401 -> 408 | 204 -> 204 | 58 -> 58 | 0 -> 14 | 0 -> 166,495.9 | 0 -> 165,972.3 | 0 -> 25 | 0 -> 165,975.1 |
| `pce_874` | 172 -> 176 | 239 -> 241 | 106 -> 106 | 35 -> 35 | 0 -> 4 | 0 -> 68,178.8 | 0 -> 67,715.4 | 0 -> 10 | 0 -> 67,716.1 |
| `raven_am55` | 142 -> 148 | 182 -> 185 | 78 -> 78 | 31 -> 31 | 0 -> 6 | 0 -> 117,168.2 | 0 -> 116,686.3 | 0 -> 5 | 0 -> 116,686.5 |
| `river_class_frigate` | 458 -> 462 | 675 -> 677 | 336 -> 334 | 67 -> 67 | 0 -> 4 | 0 -> 127,864.0 | 0 -> 124,928.4 | 0 -> 3 | 0 -> 124,928.5 |
| `rolla_pc483` | 206 -> 210 | 213 -> 215 | 113 -> 113 | 48 -> 48 | 0 -> 4 | 0 -> 60,736.1 | 0 -> 60,356.0 | 0 -> 9 | 0 -> 60,357.1 |


### Paired diagnostic matrix (before -> after)

| hull | cells | max abs move in whole-hull material time h | largest cell |
|---|---:|---:|---|
| `castle_class_corvette` | 12 | 5.83723 | Quarterdeck/native/pulse_t0: 5.848 -> 0.01067 |
| `eagle_pe60` | 12 | 5.93763 | After_Gun_Platform/native/pulse_t0: 5.942 -> 0.004807 |
| `pce_874` | 12 | 4.63039 | Fantail/native/pulse_t0: 4.636 -> 0.005211 |
| `raven_am55` | 12 | 6.98166 | Foc_Deck_Fwd/commissioned/pulse_t0: 6.988 -> 0.006397 |
| `river_class_frigate` | 12 | 6.65096 | Quarterdeck/native/pulse_t0: 6.665 -> 0.01362 |
| `rolla_pc483` | 12 | 5.11995 | Focsle_Deck/native/pulse_t0: 5.124 -> 0.004198 |


The same run also wrote the `split_t0_t1` cells; closure errors stayed at
solver roundoff.

## Residuals and open items

- Grouped OA-exchange weather zones remain untouched by the scope rule (list in
  Exposure calls), including the auxiliary hulls covered by merged #1278.
- `olympia_c6` is **deferred out of this PR**. Its committed PRJ does not
  solve within the tools' 1800 s ContamX timeout even before this change
  (pre-existing; it is the unsolved hull recorded by
  `CONTAM-FIELD-PRESSURE-REVIEW-01` / `CONTAM-DEFAULT-WEATHER-01`), and the
  after-change 7200 s diagnostic solve was still running at handoff and was
  killed. D5 `exchange_m3h` cannot be declared without a solve, so no
  `ambient_openings` were authored for it; its weather exposure awaits a
  solver-performance resolution, which is a separate finding, not this PR.
- No engine/exporter code changed; no `flow_rate_m3h` or
  `envelope_leak.area_m2` changed; no magnitude fitting.

## Reproduction

```bash
for h in castle_class_corvette eagle_pe60 pce_874 raven_am55 river_class_frigate rolla_pc483; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform $h \
    --ahs-terminal-mode commissioned
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull castle_class_corvette --hull eagle_pe60 --hull pce_874 \
  --hull raven_am55 --hull river_class_frigate --hull rolla_pc483 \
  --lane design --lane commissioned --lane authored \
  --out telemetry_buffer/contam_pressure_balance_diagnostic/misc_after.json
for h in castle_class_corvette eagle_pe60 pce_874 raven_am55 river_class_frigate rolla_pc483; do
  .venv/bin/python tools/contam_flow_compare.py --platform $h --run-contamx
  .venv/bin/python tools/contam_commissioned_check.py --platform $h
done
```

Before-witnesses were the same solves on the pre-change `data/platforms` state
before authoring; the paired matrix was run programmatically with
the explicit sources listed in Witnesses because
`contam_paired_diagnostic.PLATFORM_SOURCES` has no MISC entries.
