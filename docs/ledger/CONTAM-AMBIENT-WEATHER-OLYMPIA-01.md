# CONTAM-AMBIENT-WEATHER-OLYMPIA-01
**Date:** 2026-11-17
**Commit:** e02d3480
**Pathogens:** all
**Status:** measured
**Measured at:** e02d3480

## Scope

Final stage-4 holdout for ambient weather-zone exposure on `olympia_c6`, after
the fleet-wide stage-4 rollout for ungrouped/zero-outdoor-exchange weather
zones. Branch is rebased on `origin/main` `a2166829`, which includes the
merged `olympia_c6` ContamX self-pair solver fix #1285. Steady ContamX solves
used the local binary `third_party/contamx/contamx3`; no seeds, no AWS.

Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md)
and the sibling naval weather ledgers. Inventory:
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

Only zero-outdoor-exchange weather/open-deck zones were candidates. Each
qualifying zone declares `exposure: weather` (D7(b)) and carries one `open_deck`
`ambient_openings` record (D1(a)) with the owner-accepted Grade C deck-face area
rule, `wind_speed_m_s` 1 m/s committed on the declared 0–10 m/s axis,
`schedule: always_open`, and `exchange_m3h` = the commissioned-lane
ContamX-solved outward flow at that point (D5). No `flow_rate_m3h`,
`envelope_leak.area_m2`, engine/exporter constant, wind override, balcony,
hatch, door, make-up or forecastle path changed.

## Census

`olympia_c6`: 104 zones, 11 HVAC groups, default `oa_fraction=0.2`,
`hvac_duty=0.5`, no prior `ambient_openings`. Census used
`tools/hull_audit.py` `_is_exterior` / ungrouped classification plus the
`CONTAM-AMBIENT-EXPOSURE-01` inventory.

| zone | volume m³ | HVAC group / outdoor exchange | call |
|---|---:|---|---|
| `SD_Stern_Open` | 272.48 | ungrouped, 0 | **authored** |
| `SD_Forecastle_Open` | 201.26 | ungrouped, 0 | **authored** |
| `MD_Stern_Fantail` | 326.30 | ungrouped, 0 | **authored** |
| `MD_Forecastle_Open` | 380.68 | ungrouped, 0 | **authored** |
| `SD_Boats_Aft_Port` | 74.31 | ungrouped, 0 | **authored** |
| `SD_Boats_Aft_Stb` | 74.31 | ungrouped, 0 | **authored** |
| `SD_Boats_Mid_Port` | 278.67 | ungrouped, 0 | **authored** |
| `SD_Boats_Mid_Stb` | 278.67 | ungrouped, 0 | **authored** |
| `SD_Boats_Fwd_Port` | 99.08 | ungrouped, 0 | **authored** |
| `SD_Boats_Fwd_Stb` | 99.08 | ungrouped, 0 | **authored** |

Borderline calls: the four `*_Open`/`*_Fantail` zones are the lexical
`_is_exterior` weather zones. The six `SD_Boats_*` zones are ungrouped Free
`open_other` boat/davit/stowage areas on the superstructure boat deck; they
are authored as weather under the same borderline precedent as auxiliary
`lyon_ap71/Boat_Stowage_Port|Stbd` and amphibious davit-bearing open platforms.
Their systems notes already carry `nat_supply` ventilation intent. No
HVAC-grouped OA>0 weather zone was touched; no enclosed correction was needed.

## Change

- `data/platforms/olympia_c6/spatial_layout.json`: `exposure: weather` on the
  ten zones above.
- `data/platforms/olympia_c6/air_flow_paths.json`: ten `open_deck`
  `ambient_openings` records; committed bundle regenerated with
  `scripts/generate_platform_contam_prj.py --platform olympia_c6
  --ahs-terminal-mode commissioned`.
- `tests/test_contam_ambient_opening.py`: `_WEATHER_ZONES["olympia_c6"]` added.

## D5 openings

`exchange_m3h` is the commissioned-lane ContamX-solved outward flow at
`wind_speed_m_s = 1.0`.

| zone | volume m³ | area m² | wind m/s | exchange m³/h |
|---|---:|---:|---:|---:|
| `SD_Stern_Open` | 272.48 | 57.182 | 1.0 | 46,661.4 |
| `SD_Boats_Aft_Port` | 74.31 | 29.862 | 1.0 | 24,135.0 |
| `SD_Boats_Aft_Stb` | 74.31 | 29.862 | 1.0 | 24,135.0 |
| `SD_Boats_Mid_Port` | 278.67 | 57.828 | 1.0 | 46,739.9 |
| `SD_Boats_Mid_Stb` | 278.67 | 57.828 | 1.0 | 46,740.3 |
| `SD_Boats_Fwd_Port` | 99.08 | 34.481 | 1.0 | 27,874.4 |
| `SD_Boats_Fwd_Stb` | 99.08 | 34.481 | 1.0 | 27,873.4 |
| `SD_Forecastle_Open` | 201.26 | 49.144 | 1.0 | 40,133.5 |
| `MD_Stern_Fantail` | 326.30 | 62.575 | 1.0 | 50,126.8 |
| `MD_Forecastle_Open` | 380.68 | 67.588 | 1.0 | 51,952.7 |

## Witnesses

ContamX `contam_flow_compare.py --platform olympia_c6 --run-contamx` on the
committed commissioned bundle: 20 `ambient_opening` legs, outward
386,372.6 m³/h, inward 390,762.8 m³/h; envelope leak max |dP| 23.77 Pa.

`contam_pressure_balance_diagnostic.py --hull olympia_c6` reported 0 unsolved
rows for `authored`, `commissioned`, and `design`. Max path |dP| was 92.1 Pa;
`ambient_opening` max |dP| was 0.362 Pa commissioned and 0.341 Pa design.
Commissioned boundary balance residual was -0.003375 m³/h with makeup demand
4,491.427 m³/h, envelope net inward 101.271 m³/h, and ambient-opening net
inward 4,390.160 m³/h; design residual was 0.004360 m³/h. Envelope max |dP|
was 23.766 Pa commissioned and 2.028 Pa design.

Paired diagnostic source `SD_Stern_Open` (`pulse_t0`, `split_t0_t1`) for
NATIVE plus `authored`/`commissioned`/`design` closed at machine precision
(`closure_error` ≤ 1.1e-16). Example `pulse_t0` whole-hull material time:
NATIVE 0.00730142 h, field lanes 0.00584346 h.

`contam_commissioned_check.py --platform olympia_c6` passed: every commissioned
terminal solved inside 5% of declared.

Byte-pin proof: all committed `data/platforms/*/contam/platform.prj` bundles
were regenerated with `--ahs-terminal-mode commissioned`; `git diff
--name-only origin/main -- data/platforms` shows only `olympia_c6` paths, so
the other 81 non-target hulls are byte-identical.

Known out-of-scope context: the commissioned lane's pre-existing sanitary
make-up envelope residual is unchanged by this leg; no make-up, forecastle, or
envelope path was authored or retuned to hide it.

## Reproduction

```bash
.venv/bin/python scripts/generate_platform_contam_prj.py --platform olympia_c6 \
  --ahs-terminal-mode commissioned
.venv/bin/python tools/contam_flow_compare.py --platform olympia_c6 --run-contamx
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
  --hull olympia_c6 --lane authored --lane commissioned --lane design \
  --source SD_Stern_Open --timeout-s 1800 \
  --out telemetry_buffer/olympia_pressure_source.json
.venv/bin/python tools/contam_commissioned_check.py --platform olympia_c6
```

## Non-goals observed

No engine/exporter code changed; no schema change; no `flow_rate_m3h` or
`envelope_leak.area_m2` change; no grouped-zone openings; no other hull; no
campaign work; no magnitude fitting.
