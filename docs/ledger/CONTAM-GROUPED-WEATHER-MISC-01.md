# CONTAM-GROUPED-WEATHER-MISC-01
**Date:** 2026-11-17
**Commit:** 09c50868
**Pathogens:** all
**Status:** measured
**Measured at:** 09c50868

## Scope

Stage G4 miscellaneous-class rollout of
[`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
§3/§7, following [`CONTAM-GROUPED-WEATHER-MIDWAY-01`](CONTAM-GROUPED-WEATHER-MIDWAY-01.md)
(PR #1299). Owner rulings of 2026-11-17: grouped weather zones MAY receive
`ambient_openings`; the opening REPLACES the HVAC group's outdoor-air leg for
that zone (no double-count); G4 is staged by class, not one fleet PR.

Roster enumerated from the plan fleet table ∩ `data/platforms/` on the audit
rule (`_is_exterior` + grouped OA > 0). Eight miscellaneous hulls had grouped
OA>0 weather zones; all eight are authored here. Pope/Aeolus/fiction are not
touched.

| hull | zones opened | groups touched |
|---|---:|---|
| `castle_class_corvette` | 1 | `HVAC_Accom` |
| `erie_pg50` | 5 | `VENT_Weather`, `HVAC_Accom` |
| `esteem_mso438` | 5 | `VENT_Weather` (emptied, removed), `HVAC_Accom` |
| `fort_william_j311` | 3 | `HVAC_Accom`, `VENT_Machinery` |
| `montana_acr13` | 2 | `VENT_Weather` |
| `pt_564` | 2 | `VENT_Weather` |
| `river_class_frigate` | 1 | `HVAC_Accom` |
| `winnipeg_j337` | 3 | `HVAC_Accom`, `VENT_Machinery` |

No-op miscellaneous hulls (no grouped OA>0 weather zone on the audit rule):
`eagle_pe60` (named in the stage prompt; its seven stage-4 openings are
ungrouped/zero-exchange), `pce_874`, `raven_am55`, `rolla_pc483`,
`olympia_c6`, and the no-Comam-bundle cruise stragglers
`expedition_cruise_300`/`messy_cruise_500`. `cobalt_k124` was covered by the
auxiliary stage-4 ledger and is not in this miscellaneous roster.

## Change (exactly)

For each target zone in `data/platforms/<hull>/spatial_layout.json`:

- `exposure: "weather"` added (D7(b)).

For each target hull's `data/platforms/<hull>/air_flow_paths.json`:

1. The zone id was removed from its HVAC group's `rooms`; groups that kept
   rooms have updated descriptions. `ach`, `oa_fraction`, `hvac_duty`,
   `vent_mode` and `evidence` are untouched for remaining members, so their
   commissioned terminals are unchanged (`tools/contam_commissioned_check.py`
   PASS on all eight hulls).
2. One `ambient_openings` record per zone (D1(a)): `type` `open_deck`, Grade C
   deck-face area `2 * sqrt(V / 3) * 3`, `wind_speed_m_s` 1.0,
   `schedule` `always_open`, and `exchange_m3h` measured as below.
3. `ladder_well_*` group links were split the same way as Midway: remaining
   group members keep a group-addressed record and each removed zone gets
   zone-addressed record(s), with `flow_rate_m3h` scaled so the expanded
   per-room-pair reference flow is unchanged (before/after expansion check:
   0 ladder-well pair-flow diffs). `Sanitary_Makeup` prescribed group links
   were left whole at the same `flow_rate_m3h`: their link count is unchanged
   on all eight hulls and the forced-exhaust audit count stays 585, while the
   expanded total make-up flow is unchanged because the same declared flow is
   re-spread over the group's remaining rooms.
4. `esteem_mso438/VENT_Weather` had only the four weather rooms; with all four
   removed the empty group was deleted and its `ladder_well_1` coupling was
   re-addressed from those four zones to `HVAC_Accom`/`Deck_House_Main`,
   preserving the former 50/(4×20)=0.625 m³/h per-pair reference flow.
5. `data/platforms/<hull>/contam/{platform.prj,path_map.json}` regenerated
   with `scripts/generate_platform_contam_prj.py --platform <hull>
   --ahs-terminal-mode commissioned`. Non-target hull bundles are untouched.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES` and
`tests/test_contam_ambient_opening_boundary.py` leg counts moved for the 22
new `open_deck` records (castle/river also keep their two stage-4 openings
each).

## D5 exchange

`exchange_m3h` is the commissioned-lane ContamX-solved **outward** flow through
each opening at `wind_speed_m_s` 1.0, measured after the edits with
`tools/contam_flow_compare.py --platform <hull> --run-contamx`. Values are
rounded to 0.1 m³/h; the bundle is byte-pinned to the export, not to this
native-lane value.

| hull | zone | area_m2 | exchange_m3h |
|---|---|---:|---:|
| `castle_class_corvette` | `Upper_Deck_Aft` | 68.929 | 45,692.8 |
| `erie_pg50` | `Sup_Deck_Open` | 68.629 | 45,553.3 |
| `erie_pg50` | `Fantail_Aft` | 41.961 | 28,067.4 |
| `erie_pg50` | `Gun_Deck_Aft` | 66.947 | 44,710.9 |
| `erie_pg50` | `Focsle_Main` | 57.184 | 39,103.2 |
| `erie_pg50` | `Focsle_Stores` | 54.941 | 42,905.0 |
| `esteem_mso438` | `Sweep_Deck` | 62.704 | 49,778.6 |
| `esteem_mso438` | `Reel_Deck` | 47.564 | 31,897.7 |
| `esteem_mso438` | `Boat_Deck_Aft` | 60.525 | 41,349.1 |
| `esteem_mso438` | `Focsle_01` | 60.525 | 40,595.7 |
| `esteem_mso438` | `Deck_House_Main` | 21.287 | 16,983.7 |
| `fort_william_j311` | `Signal_Deck` | 49.148 | 32,666.4 |
| `fort_william_j311` | `Quarterdeck` | 61.872 | 41,299.4 |
| `fort_william_j311` | `Foc_Deck_Open` | 54.826 | 36,670.8 |
| `montana_acr13` | `MD_Aft_Open` | 67.360 | 47,577.5 |
| `montana_acr13` | `MD_Forecastle_Open` | 116.149 | 91,942.7 |
| `pt_564` | `Torpedo_Deck` | 26.493 | 17,695.9 |
| `pt_564` | `Foredeck` | 13.665 | 9,114.4 |
| `river_class_frigate` | `Signal_Deck` | 79.077 | 52,321.9 |
| `winnipeg_j337` | `Signal_Deck` | 54.567 | 36,224.2 |
| `winnipeg_j337` | `Quarterdeck` | 84.047 | 56,104.7 |
| `winnipeg_j337` | `Foc_Deck_Open` | 64.014 | 42,825.3 |

## Pressure/balance witness rows

`tools/diag/contam_pressure_balance_diagnostic.py --hull <hull>`, authored
lane (the committed commissioned bundle), before = `4a3d7a55`, after =
`09c50868`. All rows: **0 unsolved**. `opening net inward` is the diagnostic's
ambient-opening boundary total; on `castle_class_corvette` and
`river_class_frigate` it includes the two pre-existing stage-4 openings as
well as the new grouped-weather opening. `exchange total` is the sum of the
new openings' D5 outward flows for that hull.

| hull | before envelope max \|ΔP\| | after envelope max \|ΔP\| | before interior flowing max \|ΔP\| | after interior flowing max \|ΔP\| | before make-up demand | after make-up demand | before opening net inward | after opening net inward | before balance residual | after balance residual | exchange total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `castle_class_corvette` | 4.533 | 4.262 | 2.718 | 2.518 | 1,996.004 | 1,996.004 | 1,987.519 | 1,988.368 | 0.005 | -0.003 | 45,692.8 |
| `erie_pg50` | 11,755.968 | 3.946 | 61.288 | 1.972 | 1,637.145 | 1,637.145 | 0 | 1,627.927 | 0 | 0.001 | 200,339.8 |
| `esteem_mso438` | 1,472.934 | 3.224 | 1.623 | 2.773 | 419.578 | 419.704 | 0 | 411.585 | 0 | 0.001 | 180,604.8 |
| `fort_william_j311` | 38,187.059 | 5.840 | 237.698 | 3.751 | 1,370.724 | 1,370.724 | 0 | 1,359.180 | 0 | 0.001 | 110,636.6 |
| `montana_acr13` | 131,677.438 | 422.246 | 2,603.713 | 420.906 | 14,888.309 | 14,888.309 | 0 | 14,091.839 | 0 | 0.001 | 139,520.2 |
| `pt_564` | 1,189.722 | 2.488 | 1.560 | 1.986 | 125.366 | 125.366 | 0 | 124.996 | 0 | 0.001 | 26,810.3 |
| `river_class_frigate` | 19.780 | 9.013 | 14.653 | 5.740 | 2,975.746 | 2,975.746 | 2,935.669 | 2,952.348 | -0.001 | 0 | 52,321.9 |
| `winnipeg_j337` | 49,457.527 | 4.845 | 1.440 | 3.466 | 1,936.166 | 1,936.166 | 0 | 1,921.784 | 0 | 0.001 | 135,154.2 |

The large before envelope/interior values on `erie_pg50`, `fort_william_j311`,
`montana_acr13` and `winnipeg_j337` are the pre-change grouped OA legs now
replaced by openings; after values are the solved open-deck exchange. Make-up
demand is unchanged except `esteem_mso438` (+0.126 m³/h, the emptied
`VENT_Weather` branch), and balance residuals stay at round-off level.

## Paired diagnostic rows

The standalone `tools/diag/contam_paired_diagnostic.py` accepts only the nine
bundled hulls, so the paired NATIVE-vs-field cells were produced with the
pressure diagnostic's `--source` option on one newly opened source zone per
hull (`pulse_t0` and `split_t0_t1` cells agree). Values are the source-zone
specific outflow coefficient k (1/h), authored/commissioned field over native.

| hull | source | native k before | field k before | ratio before | native k after | field k after | ratio after |
|---|---|---:|---:|---:|---:|---:|---:|
| `castle_class_corvette` | `Upper_Deck_Aft` | 3.0863 | 4.1084 | 1.331 | 115.4820 | 117.1193 | 1.014 |
| `erie_pg50` | `Sup_Deck_Open` | 6.1008 | 6.2051 | 1.017 | 116.1601 | 117.9047 | 1.015 |
| `esteem_mso438` | `Sweep_Deck` | 6.1145 | 6.0809 | 0.995 | 152.0406 | 156.4342 | 1.029 |
| `fort_william_j311` | `Signal_Deck` | 3.1630 | 3.0856 | 0.976 | 162.3575 | 165.4752 | 1.019 |
| `montana_acr13` | `MD_Aft_Open` | 15.1124 | 16.7253 | 1.107 | 125.9422 | 157.7427 | 1.253 |
| `pt_564` | `Torpedo_Deck` | 4.1984 | 4.1009 | 0.977 | 303.1441 | 303.6611 | 1.002 |
| `river_class_frigate` | `Signal_Deck` | 2.8674 | 2.9940 | 1.044 | 100.4318 | 103.4914 | 1.030 |
| `winnipeg_j337` | `Signal_Deck` | 3.0649 | 3.0089 | 0.982 | 146.0425 | 149.4523 | 1.023 |

The after ratios are the expected order for an open-deck boundary sink (large
k from the opening) and are reported, not fitted; `flow_rate_m3h` was not
changed to match solved flow.

## Validation

- `python3 -m pytest tests/test_contam_ambient_opening.py
  tests/test_contam_ambient_opening_boundary.py -q` — 84 passed.
- `python3 -m pytest tests/test_forced_exhaust_audit.py
  ::test_sanitary_makeup_links_are_oneway_with_no_native_reverse -q` — passed
  (Sanitary_Makeup link count remains 585).
- `python3 tools/contam_commissioned_check.py --platform <hull>` — PASS on all
  eight hulls (every commissioned terminal inside 5% of declared).
- `tools/diag/contam_pressure_balance_diagnostic.py --hull <hull>` before and
  after — 0 unsolved on all rows.
- `tools/contam_flow_compare.py --platform <hull> --run-contamx` — ContamX
  solved for all eight hulls; outward ambient-opening legs are the D5 values
  above.
- Non-target hull `contam/platform.prj` and `contam/path_map.json` bundles are
  byte-identical; the diff touches only the eight target hulls, the two
  opening-guard tests and this ledger registration.
- Full fast tier, pre-commit, Sonar guard and ledger-entry tests are run before
  the PR per the stage gate.

## Reproduction

```bash
source .venv/bin/activate
for h in castle_class_corvette erie_pg50 esteem_mso438 fort_william_j311 \
         montana_acr13 pt_564 river_class_frigate winnipeg_j337; do
  python3 scripts/generate_platform_contam_prj.py --platform "$h" \
    --ahs-terminal-mode commissioned
  python3 tools/contam_commissioned_check.py --platform "$h"
  python3 tools/contam_flow_compare.py --platform "$h" --run-contamx
  python3 tools/diag/contam_pressure_balance_diagnostic.py --hull "$h"
done
```

## Non-goals

No Pope/Aeolus/fiction changes, no stage-5/6, no readout annotation, no AWS/S3,
no frozen campaign dirs, no epidemiological constants, no schema changes, and
no `flow_rate_m3h` fitting. `olympia_c6` remains deferred from stage 4 and is
not a grouped OA>0 hull.
