# Pope AP110 grouped-weather evidence (G2)

**Status:** evidence record for `docs/proposals/grouped_weather_openings_decision_plan.md` §4/§7. This leg authors no openings, platform data, topology, or HVAC change.

## Scope and pins

- Hull: `pope_ap110` only. Branch base: `0229916a4750c4ce5b625d1616aad57bbffb3967`.
- Audit evidence: `docs/audits/2026-11-17_contam_pressure_localization/` at pin `c93fa32fbe05440e797de8b551a2781b236d7e43`; the plan states the relevant hull platform data were byte-identical to the proposal main used there.
- ContamX: `third_party/contamx/contamx3`, SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b` (not committed).
- Machine-readable witness: `evidence/pope_topology_control_witness.json`; compartment table: `evidence/vent_stores_holds_compartment_table.csv`.

## P0 — intended operating/closure state

**Open; not established from repo evidence.** The platform era is `usn_ww2` / "USN WW2 fleet practice" (`systems_notes.json`), and the AP-110 Booklet of General Plans is the cited source, but the repo carries no AP110 HPAC/closure schedule or watertight-door/hatch state that fixes the intended service/closure mode for `VENT_Stores_Holds`. `contam/openings_draft.json` is explicitly a draft starter list (`status: draft`, "confirm clear area in ContamW"), and `contam/hobbyist_overrides.json` handoff notes say to confirm orifice clear areas against watertight door/hatch schedules and to add hatch/trunk leakage for troop berthing in converted holds. Per the task rule, this is recorded as open rather than guessed.

## P1 — compartment evidence table

`VENT_Stores_Holds` is HVAC group 6 / AHS `ahs6` with 28 rooms. All 28 rooms carry AHS supply+return leaves; exhaust is only the group-level `ahs6(Ret) -> ambient` leaf. Current committed `contam/path_map.json` has **0** `ambient_opening` rows. Full per-room deck/elevation/volume/area/type/occupancy/exposure/description/systems-mode/AHS-flow/adjacency/cross-zone/ladder-well fields are in `evidence/vent_stores_holds_compartment_table.csv`.

| room | deck | elev m | volume m3 | area m2 | type | occupancy | exposure | systems mode/evidence | AHS supply/return m3h | candidate |
|---|---:|---:|---:|---:|---|---:|---|---|---:|---|
| `Sup_Gun_Tubs_Aft` | superstructure_deck | 13.4 | 238.74 | 99.48 | Free |  | absent | nat_supply/era_rule | 477.48/477.48 | unresolved |
| `Sup_Deck_Mech` | superstructure_deck | 13.4 | 386.77 | 161.15 | Free |  | enclosed | nat_supply/era_rule | 773.54/773.54 | enclosed_candidate |
| `Nav_Bridge` | nav_bridge_deck | 16 | 1185.25 | 493.85 | Free | 10 | absent | nat_supply/era_rule | 2370.5/2370.5 | enclosed_candidate |
| `Signal_Control_Block` | nav_bridge_deck | 16 | 466.69 | 194.45 | Room | 4 | absent | nat_supply/era_rule | 933.38/933.38 | enclosed_candidate |
| `Top_House` | top_of_house | 18.2 | 415.89 | 173.29 | Free |  | absent | nat_supply/era_rule | 831.78/831.78 | enclosed_candidate |
| `Boat_Deck_Open` | boat_deck | 10.7 | 1088.42 | 453.51 | Free |  | absent | nat_supply/era_rule | 2176.84/2176.84 | open_deck_candidate |
| `Stern_Gun_Deck` | main_deck | 8 | 537.28 | 223.87 | Free |  | absent | nat_supply/era_rule | 1074.56/1074.56 | open_deck_candidate |
| `Aft_Loading_House` | main_deck | 8 | 608.92 | 253.72 | Free |  | absent | mech_supply_exhaust/sheet_read | 1217.84/1217.84 | enclosed_candidate |
| `Resistor_House_Aft` | main_deck | 8 | 470.12 | 195.88 | Free |  | absent | nat_supply/era_rule | 940.24/940.24 | enclosed_candidate |
| `Fwd_House_Mech` | main_deck | 8 | 573.1 | 238.79 | Free |  | absent | nat_supply/era_rule | 1146.2/1146.2 | enclosed_candidate |
| `Stores_Fwd` | main_deck | 8 | 573.1 | 238.79 | Room | 6 | absent | nat_supply/era_rule | 1146.2/1146.2 | enclosed_candidate |
| `Focsle_Deck` | main_deck | 8 | 501.46 | 208.94 | Free |  | absent | nat_supply/era_rule | 1002.92/1002.92 | open_deck_candidate |
| `Stores_Aft_2D` | second_deck | 5.4 | 283.71 | 118.21 | Free |  | absent | nat_supply/era_rule | 567.42/567.42 | enclosed_candidate |
| `Stores_Aft_3D` | third_deck | 2.8 | 283.71 | 118.21 | Free |  | absent | nat_supply/era_rule | 567.42/567.42 | enclosed_candidate |
| `Provisions_3D` | third_deck | 2.8 | 162.12 | 67.55 | Free |  | absent | nat_supply/era_rule | 324.24/324.24 | enclosed_candidate |
| `Tailor_Shop_3D` | third_deck | 2.8 | 141.85 | 59.11 | Free |  | absent | nat_supply/era_rule | 283.7/283.7 | enclosed_candidate |
| `Forepeak_3D` | third_deck | 2.8 | 141.85 | 59.11 | Free |  | absent | nat_supply/era_rule | 283.7/283.7 | enclosed_candidate |
| `Laundry` | first_platform | 0.2 | 273.58 | 113.99 | Free |  | absent | nat_supply/era_rule | 547.16/547.16 | enclosed_candidate |
| `Provision_Stores_1P` | first_platform | 0.2 | 136.79 | 57 | Free |  | absent | nat_supply/era_rule | 273.58/273.58 | enclosed_candidate |
| `Forepeak_Tank` | first_platform | 0.2 | 106.39 | 44.33 | Free |  | absent | nat_supply/era_rule | 212.78/212.78 | enclosed_candidate |
| `Hold5_Dry_Cargo` | machinery_flats | -2.8 | 658.55 | 274.4 | Free |  | absent | nat_supply/era_rule | 1317.1/1317.1 | enclosed_candidate |
| `Refrig_Stores` | machinery_flats | -2.8 | 838.16 | 349.23 | Free |  | absent | nat_supply/era_rule | 1676.32/1676.32 | enclosed_candidate |
| `Dry_Stores_Flat` | machinery_flats | -2.8 | 359.21 | 149.67 | Free |  | absent | nat_supply/era_rule | 718.42/718.42 | enclosed_candidate |
| `Fwd_Hold_Cargo` | machinery_flats | -2.8 | 349.23 | 145.51 | Free |  | absent | nat_supply/era_rule | 698.46/698.46 | enclosed_candidate |
| `Tanks_Aft` | tank_top | -5 | 1353.76 | 564.07 | Free |  | absent | nat_supply/era_rule | 2707.52/2707.52 | enclosed_candidate |
| `Machinery_Tankage` | tank_top | -5 | 1863.88 | 776.62 | Free |  | absent | nat_supply/era_rule | 3727.76/3727.76 | enclosed_candidate |
| `Tanks_Fwd` | tank_top | -5 | 1579.39 | 658.08 | Free |  | absent | nat_supply/era_rule | 3158.78/3158.78 | enclosed_candidate |
| `Fwd_Peak_Tank` | tank_top | -5 | 266.83 | 111.18 | Free |  | absent | nat_supply/era_rule | 533.66/533.66 | enclosed_candidate |

Open-deck candidates (plan-named): `Boat_Deck_Open`, `Stern_Gun_Deck`, `Focsle_Deck`. Only `Sup_Deck_Mech` currently declares `exposure: enclosed`; the other rows have `exposure: absent`, which is a schema absence, not proof of weather exposure.

## P2 — drawing/HVAC edge adjudication

**Open; candidate edges are not adjudicated to weather/passage/hatch/trunk/absent.** The adjacency and Contam draft-opening evidence are starter/GA-derived, not closure-schedule evidence. The three open-deck candidates appear in draft adjacency/orifice records (for example `Focsle_Deck -> Stores_Fwd`, `Stern_Gun_Deck -> Aft_Loading_House`), but `openings_draft.json` statuses are `draft` and the hobbyist overrides require watertight-door/hatch confirmation. No in-repo AP110 ventilation/HPAC closure schedule was found that would let this leg decide each candidate edge without guessing.

## P3 — `VENT_Stores_Holds` grouping question

The measured defect is concentrated in the group boundary `VENT_Machinery -> VENT_Stores_Holds` (`ladder_well_5`): commissioned baseline net −5,576.084 m³/h, gross 7,268.713 m³/h, max path |ΔP| 58,552.332 Pa; the committed all-open diagnostic moves the same boundary to net −10,527.138 m³/h, gross 12,618.746 m³/h, max path |ΔP| 804,135.812 Pa. The group mixes three open-deck candidates with enclosed stores/holds/tankage and superstructure spaces under one mechanical supply/exhaust group (`ach` 4.0, `oa_fraction` 0.4, `vent_mode` `mech_supply_exhaust`). The evidence supports adjudicating the single-group representation, but the split-vs-openings decision remains an owner/G-later platform-data change; this leg authors neither.

## Topology-control witness (before any opening control)

Fresh native ContamX diagnostic on the committed tree (`tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths`) plus committed audit controls. Balance residuals are m³/h.

| control | envelope max abs ΔP Pa | flowing interior max abs ΔP Pa | makeup demand m3/h | opening net inward m3/h | balance residual m3/h |
|---|---:|---:|---:|---:|---:|
| fresh commissioned baseline | 1355146.75 | 58552.332 | 28574.922724 | 0.000000 | 0.000157229 |
| fresh design lane | 214.66 | 0.081486 | 0.000000 | 0.000000 | 1.20642e-07 |
| audit `baseline` (commissioned) | 1355146.75 | 58552.332 | 28574.922724 | 0.000000 | 0.000157229 |
| audit `all_explicit_weather_open` (commissioned) | 806283.75 | 804135.812 | 28574.922724 | 8085.661858 | -0.00436097 |

Ladder-well link witnesses (m³/h; ΔP in Pa):

| variant | link | n | net | gross | max abs ΔP |
|---|---|---:|---:|---:|---:|
| fresh commissioned | `ladder_well_1` | 56 | 2144.859 | 2144.859 | 3116.001 |
| fresh commissioned | `ladder_well_2` | 77 | 730.195 | 744.433 | 541.789 |
| fresh commissioned | `ladder_well_3` | 121 | -899.936 | 899.936 | 524.242 |
| fresh commissioned | `ladder_well_4` | 187 | -2856.658 | 3030.884 | 40400.844 |
| fresh commissioned | `ladder_well_5` | 476 | -5576.084 | 7268.713 | 58552.332 |
| audit baseline | `ladder_well_1` | 56 | 2144.859 | 2144.859 | 3116.001 |
| audit baseline | `ladder_well_2` | 77 | 730.195 | 744.433 | 541.789 |
| audit baseline | `ladder_well_3` | 121 | -899.936 | 899.936 | 524.242 |
| audit baseline | `ladder_well_4` | 187 | -2856.658 | 3030.884 | 40400.844 |
| audit baseline | `ladder_well_5` | 476 | -5576.084 | 7268.713 | 58552.332 |
| audit all_explicit_weather_open | `ladder_well_1` | 56 | 1487.654 | 1487.654 | 1707.450 |
| audit all_explicit_weather_open | `ladder_well_2` | 77 | 807.318 | 824.299 | 681.770 |
| audit all_explicit_weather_open | `ladder_well_3` | 121 | -1017.769 | 1017.769 | 667.557 |
| audit all_explicit_weather_open | `ladder_well_4` | 187 | -3526.076 | 3708.798 | 53951.188 |
| audit all_explicit_weather_open | `ladder_well_5` | 476 | -10527.138 | 12618.746 | 804135.812 |

Interpretation: the topology/closure control has **not** been run as a separate solve because the plan requires P0–P3 to be frozen first and control A is a topology/closure/HVAC-group change; authoring that change is G-later. The evidence table therefore freezes the question and records the open owner decisions. The already-committed all-open scenario is an opening control, not a topology control, and it is not adequate by itself: it reduces envelope max |ΔP| from 1,355,146.75 Pa to 806,283.75 Pa but raises flowing-interior max |ΔP| to 804,135.81 Pa on `ladder_well_5`.

## Validation

- Pressure/balance diagnostic: `python3 tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths` → 2 rows, 0 unsolved; output kept in gitignored `telemetry_buffer/`.
- Byte-pin: this change adds only `docs/audits/2026-11-17_pope_ap110_grouped_weather_evidence/`, `docs/ledger/CONTAM-POPE-GROUPED-WEATHER-EVIDENCE-01.md`, and the ledger README registration; `data/platforms/pope_ap110/**` is unchanged.
- Pre-commit/tests: run on changed files before PR; no `data/` JSON schema surface is added except audit evidence JSON/CSV under `docs/`.
