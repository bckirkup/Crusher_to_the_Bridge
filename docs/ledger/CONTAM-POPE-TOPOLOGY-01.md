# CONTAM-POPE-TOPOLOGY-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** 257d9f6a

## Scope

Stage G2 Pope leg of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md) §4/§5.2/§7: author the bounded **topology/closure control A** change for `pope_ap110` only, then witness it with ContamX on the commissioned and design lanes. Owner rulings of 2026-11-17, verbatim in the tasking: P0 watertight doors/hatches CLOSED except the three explicitly open decks already authored in the platform data (no HPAC schedule evidence; closed-except-declared-open is the Grade C state); P2 keep only adjacency/opening edges corroborated by the compartment evidence and reject hobbyist draft edges implying openings through watertight boundaries; P3 SPLIT the 28-room `VENT_Stores_Holds` group because it mixes three open-deck candidates with enclosed stores/holds/tankage under one `mech_supply_exhaust` group.

This entry changes no epidemiological constant, no sanitary exhaust magnitude, no schema, and no other hull. It authors **no** `ambient_openings`; the grouped-weather evidence entry had already shown that the committed all-open-deck opening control is inadequate.

## Change (exactly)

`data/platforms/pope_ap110/air_flow_paths.json`

1. **P3 group split.** The former 28-room `VENT_Stores_Holds` group is split into three groups with the same declared `ach` 4.0 and `oa_fraction` 0.4 on each:
   - `VENT_Stores_Holds` — 17 enclosed stores/holds/tankage rooms, including `Stores_Fwd`; `vent_mode` `nat_supply`, `evidence` `era_rule`.
   - `VENT_Superstructure` — 8 enclosed superstructure/deckhouse rooms (`Sup_Gun_Tubs_Aft`, `Sup_Deck_Mech`, `Nav_Bridge`, `Signal_Control_Block`, `Top_House`, `Aft_Loading_House`, `Resistor_House_Aft`, `Fwd_House_Mech`); `vent_mode` `mech_supply_exhaust`, `evidence` `sheet_read` because `Aft_Loading_House` is the sheet-read mechanical member.
   - `VENT_Open_Decks` — the three declared open decks (`Boat_Deck_Open`, `Stern_Gun_Deck`, `Focsle_Deck`); `vent_mode` `nat_supply`, `evidence` `era_rule`.
   ACH/OA are preserved from the former aggregate pending HPAC schedule evidence; this is a membership/topology correction, not a ventilation-rate fit.
2. **P2 edge adjudication / P0 closures.** Removed the two draft adjacency/opening edges that connected declared open decks to enclosed spaces through watertight boundaries: `Focsle_Deck -> Stores_Fwd` and `Stern_Gun_Deck -> Aft_Loading_House`. The matching `contam/openings_draft.json` checklist records were removed. The other 49 adjacency edges and all 7 trunk edges are unchanged.
3. **`ladder_well_5` re-address.** `VENT_Machinery -> VENT_Stores_Holds` now terminates on the 17-room stores/holds subset only. `flow_rate_m3h` moves 50.0 → 30.357142857 so the per-room-pair reference flow stays `50/(17*28)` m³/h; this is the same re-addressing rule used for `CONTAM-GROUPED-WEATHER-MIDWAY-01`, not a fit to solved flow. No `ambient_openings` were added and no other `flow_rate_m3h` changed.

`data/platforms/pope_ap110/contam/platform.prj` and `data/platforms/pope_ap110/contam/path_map.json`

- Regenerated together with `.venv/bin/python scripts/generate_platform_contam_prj.py --platform pope_ap110 --ahs-terminal-mode commissioned`.
- `platform.prj` SHA-256 `d56dd3acca3c11b25aec4006566190094ed3a9fc0da5e6160f23d300c7a8698e`; `path_map.json` SHA-256 `284e5d2ba26b14b85d9304b08371224b801661b156f195184932192b2e9bc787`.
- `path_map.json` rows 1,343 → 1,160; `passageway` 44 → 42, `trunk` 7 → 7, `ladder_well_5` 476 → 289, AHS system legs (`ahs_oa`/`ahs_exhaust`/`ahs_recirc`) 13 → 15 because the split creates two additional AHS groups, `ahs_supply`/`ahs_return` 89 → 89, `Sanitary_Makeup` 70 → 70, `ambient_opening` 0 → 0.

## Witnesses

Fresh local ContamX 3.4.0.3 (`third_party/contamx/contamx3`, SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`) via `tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths`: 2 rows, **0 unsolved** on both lanes.

| lane | envelope max \|ΔP\| | flowing-interior max \|ΔP\| | make-up demand | balance residual |
|---|---:|---:|---:|---:|
| commissioned before (`4a3d7a55`) | 1,355,146.75 Pa | 58,552.332 Pa | 28,574.922724 m³/h | 0.000157229 m³/h |
| commissioned after (`257d9f6a`) | 1,633,363.125 Pa | 67,544.53125 Pa | 28,566.851797 m³/h | 4.490998981e-05 m³/h |
| design before (`4a3d7a55`) | 214.656 Pa | 0.081486 Pa | 0 m³/h | 1.20642e-07 m³/h |
| design after (`257d9f6a`) | 214.656 Pa | 0.090718 Pa | 0 m³/h | 1.041614e-07 m³/h |

Per-link `ladder_well_*` witness. `pope_ap110` has ladder-well links 1–5 only; there is **no `ladder_well_6`** on this hull (the `ladder_well_6` names in the wider audit belong to other hulls).

| lane / variant | link | paths | net m³/h | gross m³/h | max \|ΔP\| |
|---|---|---:|---:|---:|---:|
| commissioned before baseline | `ladder_well_5` | 476 | −5,576.084310 | 7,268.713302 | 58,552.332031 Pa |
| commissioned before all-open control | `ladder_well_5` | 476 | −10,527.137814 | 12,618.746134 | 804,135.812500 Pa |
| commissioned after control A | `ladder_well_5` | 289 | −3,572.712040 | 4,673.107376 | 67,544.531250 Pa |
| design after control A | `ladder_well_5` | 289 | 0.307869 | 3.701206 | 0.090718 Pa |

Commissioned-after `ladder_well_5` maximum is the single path `Engine_Casing_Fwd_1P -> Refrig_Stores`, ΔP −67,544.531250 Pa at −23.233602 m³/h. Design-after `ladder_well_5` maximum is `Shaft_Alley -> Machinery_Tankage`, ΔP 0.090718 Pa at 0.026926 m³/h. For completeness, commissioned-after other ladder links: `ladder_well_1` 56 paths / max 3,761.706787 Pa, `ladder_well_2` 77 / 485.834961 Pa, `ladder_well_3` 121 / 467.407104 Pa, `ladder_well_4` 187 / 43,536.257813 Pa; design-after maxima are 0.018776 / 0.004615 / 0.008877 / 0.016060 Pa respectively.

## Reading

Control A is **not** an opening control and it does **not** repair the commissioned envelope residual on this witness: envelope max |ΔP| rises 1.355 MPa → 1.633 MPa and flowing-interior max |ΔP| rises 58.55 kPa → 67.54 kPa, while make-up demand falls only 28,574.923 → 28,566.852 m³/h and the round-off balance residual improves 1.57229e-04 → 4.49100e-05 m³/h. The split removes 187 `ladder_well_5` expanded paths and reduces that link's net/gross flow, but the residual maximum moves onto `Engine_Casing_Fwd_1P -> Refrig_Stores`. This is consistent with the governing plan's sequencing: openings alone were already inadequate, and topology/closure/grouping alone is also inadequate for the commissioned sanitary make-up demand; the next bounded decision is envelope/make-up boundary work, outside this entry's non-goals.

## Validation

- Schema checks: `spatial_layout.schema.json` and `air_flow_paths.schema.json` on `pope_ap110`: 0 errors.
- Byte-pin proof: `git diff --name-only origin/main...HEAD -- data/platforms ':(exclude)data/platforms/pope_ap110/**'` is empty; non-Pope platform data are byte-identical. Changed files before this ledger are only the four `pope_ap110` files listed above.
- ContamX witnesses: pressure diagnostic 2 rows, 0 unsolved on commissioned and design lanes; `tools/contam_commissioned_check.py --platform pope_ap110` → PASS, every commissioned terminal solved inside 5% of declared.
- `ambient_openings`: no Pope record authored; regenerated `path_map.json` has 0 `ambient_opening` rows.
- Full fast tier and remaining gate commands are recorded in the PR description/checks; this ledger was committed after the measured data commit `257d9f6a`.

## Reproduction

```bash
.venv/bin/python scripts/generate_platform_contam_prj.py --platform pope_ap110 --ahs-terminal-mode commissioned
.venv/bin/python tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths
.venv/bin/python tools/contam_commissioned_check.py --platform pope_ap110
python3 -m pytest tests/test_json_schema_validation.py tests/test_ledger_entries.py -q
python3 -m pytest tests/ -m 'not slow' -n auto -q
```

## Non-goals

No `ambient_openings`, no HPAC schedule or watertight-door schedule authoring, no `flow_rate_m3h` fitting, no other hull, no stage-5/6 envelope/make-up work, no readout annotation, no AWS/S3 access, no frozen campaign directories, no epidemiological constants, and no schema change.
