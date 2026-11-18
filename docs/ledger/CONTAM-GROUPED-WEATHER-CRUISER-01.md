# CONTAM-GROUPED-WEATHER-CRUISER-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** 6152aeeaa325

## Scope

Stage G4 cruiser leg of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
§3/§7: the three cruiser-class `VENT_Weather` groups with grouped outdoor
exchange > 0 receive `ambient_openings`, and each opening **replaces** the
group OA leg for its zone. Owner rulings of 2026-11-17, verbatim:

- "Grouped zones may receive ambient_openings; the opening REPLACES the group's OA leg for that zone (no double-count)";
- G4 fleet rollout authorized, staged by class, no fleet-wide single PR.

Executable precedent: [`CONTAM-GROUPED-WEATHER-MIDWAY-01`](CONTAM-GROUPED-WEATHER-MIDWAY-01.md)
(G1). Stage-4 roster source: [`CONTAM-AMBIENT-WEATHER-CRUISER-01`](CONTAM-AMBIENT-WEATHER-CRUISER-01.md),
which left `astoria_ca34`, `chicago_cg11` and `miami_cl89` as the grouped/open
items. `alexander_henry_cgs119` already has zero-exchange `AHU_Weather`
openings and is a no-op here. No Pope/Aeolus/fiction hull was touched.

Steady ContamX solves used the local official NIST binary
`third_party/contamx/contamx3`; no seeds, no AWS. "Before" is `origin/main`
`4a3d7a55`; "after" is the data commit `6152aeeaa325` on this branch.

## Change (exactly)

For each of `astoria_ca34`, `chicago_cg11`, `miami_cl89`:

`data/platforms/<hull>/spatial_layout.json`

- Every targeted weather zone gained `exposure: "weather"` (D7(b)). The zone
  set is the audit-rule weather subset of the hull's `VENT_Weather` group
  (`tools/hull_audit.py` `_is_exterior`), not a new lexical guess.

`data/platforms/<hull>/air_flow_paths.json`

1. `hvac_zones[VENT_Weather].rooms` lost only the targeted weather zones; the
   remaining member rooms stayed in the group. `ach` 1.0, `oa_fraction` 1.0,
   `vent_mode`, `evidence` and the group id are untouched. Room membership is
   the declaration that makes the group count a zone's outdoor exchange, so
   removal is the minimal no-double-count edit. The removed group leg per zone
   was `ach × V × hvac_duty × oa_fraction = V × 0.5` m³/h.
2. One top-level `ambient_openings` record per removed zone (D1(a)): `type`
   `open_deck`, `schedule` `always_open`, `wind_speed_m_s` 1.0 (fleet default
   from ahead, `CONTAM-DEFAULT-WEATHER-01`), Grade C
   `ASSUMED-OPEN-DECK-FACE-AREA` `area_m2 = 2 × sqrt(V / 3) × 3`, and D5
   `exchange_m3h` below.
3. `cross_zone_links`: no `VENT_Weather`-addressed link existed on these
   hulls, so no Midway-style group-link split was required. The native and
   exported path diffs below show only the HVAC-leg → opening-leg swap.

`data/platforms/<hull>/contam/{platform.prj,path_map.json}` regenerated with
`scripts/generate_platform_contam_prj.py --platform <hull>
--ahs-terminal-mode commissioned` after the data edit and again after writing
the D5 values; the D5 write did not move the committed bundles.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES` gained the
three hulls; `tests/test_contam_ambient_opening_boundary.py` committed-leg
census gained `"astoria_ca34": 10`, `"chicago_cg11": 16`, `"miami_cl89": 4`.
Both moves are the exposure tags and two opening legs per record of this
change. No engine, exporter or schema code changed.

## Opening roster and D5 exchange

`exchange_m3h` is the commissioned-lane ContamX-solved **outward** flow of each
opening at `wind_speed_m_s` 1.0, measured after the group removal
(`tools/contam_flow_compare.py --platform <hull> --run-contamx` and the
pressure diagnostic `--all-paths` commissioned row). The audit scenario's net
inward flow was not used.

| hull | zone | V, m³ | area_m2 | exchange_m3h | removed group OA, m³/h |
|---|---|---:|---:|---:|---:|
| astoria_ca34 | Fantail | 442.70 | 72.886 | 48,709.5 | 221.350 |
| astoria_ca34 | Catapult_Deck | 885.40 | 103.077 | 68,595.0 | 442.700 |
| astoria_ca34 | Boat_Deck | 1,421.54 | 130.608 | 87,293.3 | 710.770 |
| astoria_ca34 | Focsle_Deck | 743.79 | 94.475 | 61,702.3 | 371.895 |
| astoria_ca34 | Upper_Deck_Aft | 408.49 | 70.013 | 46,799.0 | 204.245 |
| chicago_cg11 | Fantail_Weather | 288.20 | 58.808 | 39,263.7 | 144.100 |
| chicago_cg11 | Helo_Deck | 2,200.80 | 162.510 | 104,171.9 | 1,100.400 |
| chicago_cg11 | Helo_Deck_02_Aft | 432.91 | 72.076 | 47,925.5 | 216.455 |
| chicago_cg11 | Forecastle_Deck | 576.40 | 83.167 | 54,289.4 | 288.200 |
| chicago_cg11 | Bow_Weather | 377.28 | 67.286 | 44,892.2 | 188.640 |
| chicago_cg11 | Terrier_Deck_02 | 1,057.55 | 112.653 | 74,941.1 | 528.775 |
| chicago_cg11 | Launcher_Deck_01 | 430.98 | 71.915 | 47,618.1 | 215.490 |
| chicago_cg11 | Open_03 | 279.39 | 57.902 | 38,389.1 | 139.695 |
| miami_cl89 | Catapult_Deck | 410.50 | 70.185 | 44,027.9 | 205.250 |
| miami_cl89 | Bow_Weather | 431.03 | 71.919 | 46,273.9 | 215.515 |

Per-hull opening totals, commissioned lane:

| hull | openings | outward m³/h | inward m³/h | net inward m³/h |
|---|---:|---:|---:|---:|
| astoria_ca34 | 5 | 313,099.1 | 316,611.3 | 3,512.1 |
| chicago_cg11 | 8 | 451,491.0 | 465,451.4 | 13,960.4 |
| miami_cl89 | 2 | 90,301.9 | 99,660.0 | 9,358.2 |

## No double-count, both lanes

Before/after census of paths touching the targeted zones:

| hull | native HVAC legs before | native ambient legs after | path_map HVAC rows before | path_map opening rows after | path_map rows before→after |
|---|---:|---:|---:|---:|---:|
| astoria_ca34 | 5 | 5 | 10 | 10 | 323→323 |
| chicago_cg11 | 8 | 8 | 16 | 16 | 485→485 |
| miami_cl89 | 2 | 2 | 4 | 4 | 389→389 |

After the change no targeted zone has an HVAC-group leg in either lane and each
has exactly one outdoor exchange representation (one native
`ambient_exchange_open_deck` sink; one paired-orifice export). No other
platform path moved: the native paths touching targets are the same count
before/after with only the HVAC path swapped for the ambient path, and the
exported `path_map.json` row count is unchanged on every hull.

AHS group check (`contam_pressure_balance_diagnostic`, commissioned lane):
only `VENT_Weather` (AHS group 1) changed solved supply/return; every other
AHS group is identical before/after.

| hull | AHS 1 terminals before→after | AHS 1 supply before→after, m³/h | AHS 1 return before→after, m³/h |
|---|---:|---:|---:|
| astoria_ca34 | 14→4 | 2,458.807→499.962 | 2,458.807→499.962 |
| chicago_cg11 | 20→4 | 3,517.241→685.203 | 3,517.241→685.203 |
| miami_cl89 | 18→14 | 1,420.228→997.250 | 1,420.228→997.250 |

## Remaining `VENT_Weather` rooms (not stranded)

The group keeps its non-target rooms and still emits their terminals:

- `astoria_ca34`: `Gun_Gallery_01`, `Bridge_Wings` (4 terminal rows after).
- `chicago_cg11`: `Boat_Stowage_02`, `Boat_Stowage_Main` (4 terminal rows after).
- `miami_cl89`: `Stern_Aviation`, `Forecastle_Main`, `Bridge_Wings`,
  `Boat_Stowage_Port`, `Boat_Stowage_Stbd`, `Gun_Tubs_01`, `Nav_Bridge`
  (14 terminal rows after).

`tools/contam_commissioned_check.py --platform astoria_ca34 --platform
chicago_cg11 --platform miami_cl89 --tolerance 0.05` passed after the change:
every commissioned terminal solved inside 5% of declared, including the
remaining `VENT_Weather` rooms.

## Pressure diagnostic rows

`tools/diag/contam_pressure_balance_diagnostic.py --hull <hull>` before and
after, 0 unsolved on every row. Authored and commissioned lanes solve
identically before and after on these hulls.

| hull | lane | state | max \|ΔP\|, Pa | envelope max \|ΔP\|, Pa | interior max \|ΔP\|, Pa | makeup demand, m³/h | opening net inward, m³/h | balance residual, m³/h |
|---|---|---|---:|---:|---:|---:|---:|---:|
| astoria_ca34 | design | before | 11.806 | 0.843 | 1.027 | 0.0 | 0.0 | −1.1e-07 |
| astoria_ca34 | design | after | 11.806 | 0.610 | 1.027 | 0.0 | 1.308 | −0.00133 |
| astoria_ca34 | commissioned/authored | before | 94,776.672 | 94,776.672 | 227.940 | 3,611.832 | 0.0 | 5.6e-06 |
| astoria_ca34 | commissioned/authored | after | 161.788 | 161.788 | 159.382 | 3,611.832 | 3,512.102 | 0.00185 |
| chicago_cg11 | design | before | 165.160 | 2.824 | 0.605 | 0.0 | 0.0 | 1.2e-07 |
| chicago_cg11 | design | after | 165.160 | 3.056 | 0.373 | 0.0 | −2.896 | −0.00554 |
| chicago_cg11 | commissioned/authored | before | 460,482.156 | 460,482.156 | 400.373 | 14,025.823 | 0.0 | −2.2e-05 |
| chicago_cg11 | commissioned/authored | after | 165.160 | 20.799 | 13.273 | 14,025.823 | 13,960.403 | −0.00833 |
| miami_cl89 | design | before | 188.732 | 1.973 | 2.380 | 0.0 | 0.0 | −2.2e-08 |
| miami_cl89 | design | after | 188.732 | 3.359 | 2.380 | 0.0 | −10.728 | 0.00383 |
| miami_cl89 | commissioned/authored | before | 350,135.406 | 350,135.406 | 1,516.128 | 9,600.015 | 0.0 | 4.5e-05 |
| miami_cl89 | commissioned/authored | after | 285.518 | 285.518 | 165.663 | 9,600.015 | 9,358.160 | 0.000789 |

The commissioned-lane envelope maximum falls from the unphysical pre-change
make-up residual (94.8–460.5 kPa) to 161.8–285.5 Pa because the weather-deck
make-up air now enters through the authored openings instead of the distributed
envelope-leak field. Make-up demand is unchanged on every hull. Design-lane
max |ΔP| does not worsen beyond the recorded hull residuals (Astoria 11.806 Pa
AHS system path unchanged; Chicago 165.160 Pa unchanged; Miami 188.732 Pa
unchanged).

## Flow compare

`tools/contam_flow_compare.py --platform <hull> --run-contamx` after the change:
0 unsolved, native ambient-exchange links match the written D5 values, and the
ContamX field reports the opening legs as `ambient_opening` rows.

| hull | native paths | path_map rows | kept real paths | synth AHS paths | opening legs | opening sink out, m³/h | opening inward, m³/h |
|---|---:|---:|---:|---:|---:|---:|---:|
| astoria_ca34 | 263 | 323 | 71 | 114 | 10 | 313,099.245 | 316,611.348 |
| chicago_cg11 | 444 | 485 | 181 | 145 | 16 | 451,491.017 | 465,451.420 |
| miami_cl89 | 339 | 389 | 98 | 150 | 4 | 90,301.853 | 99,660.013 |

## Paired diagnostic

The standalone `tools/diag/contam_paired_diagnostic.py --hull` choices do not
include cruiser hulls, so no paired-diagnostic cell was run for this class
leg. The pressure diagnostic rows above are the lane-honest before/after
witness; no paired cell is claimed.

## Validation

- Non-target hulls: `git status` shows only `astoria_ca34`, `chicago_cg11`,
  `miami_cl89` under `data/platforms/`; no other bundle was regenerated.
- Schema: `check-jsonschema` passed for all six edited spatial/airflow JSON
  files.
- Focused guards: `tests/test_contam_ambient_opening.py` and
  `tests/test_contam_ambient_opening_boundary.py` pass (84 tests).
- `tools/contam_commissioned_check.py` for the three hulls: PASS.
- ContamX witnesses: 0 unsolved on all pressure/flow rows.
- Full fast tier, pre-commit, sonar guard, ledger-entry test and sanity
  checker results are recorded in the PR.

## Reproduction

```bash
for p in astoria_ca34 chicago_cg11 miami_cl89; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform "$p" \
    --ahs-terminal-mode commissioned
  .venv/bin/python tools/contam_flow_compare.py --platform "$p" --run-contamx \
    --output "telemetry_buffer/g4_cruiser/flow_compare_${p}.json"
  .venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
    --hull "$p" --lane design --lane commissioned --lane authored \
    --all-paths --timeout-s 1800 \
    --out "telemetry_buffer/g4_cruiser/after_${p}.json"
done
.venv/bin/python tools/contam_commissioned_check.py --platform astoria_ca34 \
  --platform chicago_cg11 --platform miami_cl89 --tolerance 0.05
```

## Non-goals observed

No Pope/Aeolus/fiction work; no `flow_rate_m3h` fitting; no stage-5/6 work; no
readout annotation; no AWS/S3; no frozen campaign dirs; no epidemiological
constants; no schema changes; no engine/exporter change; no envelope leak-area
change. The only `flow_rate_m3h`-adjacent edits are the authored
`exchange_m3h` D5 values and the removal of the replaced group OA legs.

## Open

- G4 carrier/battleship/auxiliary/amphibious/miscellaneous legs remain staged
  by class under the same owner ruling.
- Whether non-lexical open `Free` rooms left in `VENT_Weather` (for example
  `Bridge_Wings`/`Boat_Stowage` members on these hulls) should receive
  explicit `exposure` tags is a separate audit-scope question, not changed here.
