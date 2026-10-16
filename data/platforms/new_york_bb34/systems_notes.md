# Systems inference notes — new_york_bb34

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_main | funnel | unknown | exhaust | Conning_Region_Super | sheet_read |
| uptake_casing | uptake | unknown | exhaust | Uptake_Mid | sheet_read |
| cowls_focsle | cowl | fore | supply | Stores_Fwd_3DF | era_plausible |
| mushroom_aft | mushroom | unknown | supply | Crew_Space_2DA | era_plausible |
| air_port_wr | air_port | unknown | supply | WR_Staterooms_2DF | era_plausible |
| vent_trunk_3d | vent_trunk | unknown | supply | Radio_Central_3DF | sheet_read |
| air_shaft_blower | air_shaft | unknown | supply | Engine_Rm_2PA | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AA_Control_Top | nat_supply | era_rule |
| Admiral_Capt_Block | nat_supply | era_rule |
| Bakery | nat_supply | era_rule |
| Boiler_Rm_2PA | mech_supply_exhaust | era_rule |
| Boiler_Rm_2PF | mech_supply_exhaust | era_rule |
| Boiler_Rms_1PF | mech_supply_exhaust | era_rule |
| Bow_Stor_Half | nat_supply | era_rule |
| Brig_3DA | nat_supply | era_rule |
| CPO_Country_Berth | nat_supply | era_rule |
| CPO_Mess_Berth | mech_exhaust | era_rule |
| Captains_Cabin_Super | nat_supply | era_rule |
| Carpenter_3DA | mech_supply_exhaust | era_rule |
| Casemate_Crew_2DA | nat_supply | era_rule |
| Casemate_Crew_2DA_N | nat_supply | era_rule |
| Catapult_Mid | nat_supply | era_rule |
| Conning_Region_Super | mech_supply_exhaust | sheet_read |
| Crew_3DA | nat_supply | era_rule |
| Crew_3DA_B | nat_supply | era_rule |
| Crew_3DA_C | nat_supply | era_rule |
| Crew_3DF_Mid | nat_supply | era_rule |
| Crew_3DF_N | nat_supply | era_rule |
| Crew_Space_2DA | nat_supply | era_plausible |
| Crew_Space_2DF_a | nat_supply | era_rule |
| Crew_Space_2DF_b | nat_supply | era_rule |
| Engine_Lower_HA | mech_supply_exhaust | era_rule |
| Engine_Rm_1PA | mech_supply_exhaust | era_rule |
| Engine_Rm_2PA | mech_supply_exhaust | era_plausible |
| Exec_Offices_2DA | nat_supply | era_rule |
| Fantail_Weather | nat_supply | era_rule |
| Flag_Bridge | nat_supply | era_rule |
| Focsle_Deck | nat_supply | era_rule |
| Galley_Mess_2DA | mech_exhaust | era_rule |
| Gunnery_Conning | mech_supply_exhaust | era_rule |
| Gyro_Dynamo_2PA | mech_supply_exhaust | era_rule |
| HD_2DF | exhaust_only | era_rule |
| HD_CPO_Berth | exhaust_only | era_rule |
| HD_Crew_2DA | exhaust_only | era_rule |
| HD_Half | exhaust_only | era_rule |
| HD_Officers_Main | exhaust_only | era_rule |
| Hold_Fwd_Tip | nat_supply | era_rule |
| Hold_Stores_HA | nat_supply | era_rule |
| Hold_Stores_HF | nat_supply | era_rule |
| IC_Rm_1PF | nat_supply | era_rule |
| Ice_Machine_3DA | mech_supply_exhaust | era_rule |
| JO_Country_Half | nat_supply | era_rule |
| JO_Mess_Half | mech_exhaust | era_rule |
| Jr_Off_2DF | nat_supply | era_rule |
| Laundry_2DA | nat_supply | era_rule |
| Machine_Shop_3DA | mech_supply_exhaust | era_rule |
| Machine_Shop_C105 | mech_supply_exhaust | era_rule |
| Machinery_Hatch_3DA | mech_supply_exhaust | era_rule |
| Magazines_1PA_R | mech_supply_exhaust | era_rule |
| Magazines_2PF | mech_supply_exhaust | era_rule |
| Marines_2DA | nat_supply | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Galley | nat_supply | era_rule |
| Offices_2DA | nat_supply | era_rule |
| Photo_Ordn_3DF | nat_supply | era_rule |
| Plotting_2PF | nat_supply | era_rule |
| Powder_1PA | mech_supply_exhaust | era_rule |
| Powder_1PF | mech_supply_exhaust | era_rule |
| Provisions_HA | nat_supply | era_rule |
| Radio_Central_3DF | nat_supply | sheet_read |
| Radio_Rm_3DA | nat_supply | era_rule |
| Refrig_3DA | nat_supply | era_rule |
| Shipfitter_Foundry | nat_supply | era_rule |
| Sick_Bay_2DA | mech_supply_exhaust | era_rule |
| Signal_Stores_3DF | nat_supply | era_rule |
| Steam_Passage_1PA | mech_supply_exhaust | era_rule |
| Stern_Crew_2DA | nat_supply | era_rule |
| Stores_2PA | nat_supply | era_rule |
| Stores_2PF | nat_supply | era_rule |
| Stores_FwdEdge_3DA | nat_supply | era_rule |
| Stores_Fwd_3DF | nat_supply | era_plausible |
| Stores_Super | nat_supply | era_rule |
| Super_Deck_Open | nat_supply | era_rule |
| Uptake_Mid | mech_supply_exhaust | sheet_read |
| WO_Country_Half | nat_supply | era_rule |
| WO_Mess_Half | mech_exhaust | era_rule |
| WR_Staterooms_2DF | nat_supply | era_plausible |
| Wardroom_Country_2DF | nat_supply | era_rule |
| Weather_Deck_Aft | nat_supply | era_rule |
| Windlass_1PF | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| fuel oil + void double bottoms | fuel | Engine_Lower_HA |
| reserve feed water | freshwater | Hold_Stores_HF |
| emergency feed water | unknown | Hold_Stores_HA |

## Plumbing drains

- HD_Officers_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers_Main
- HD_2DF (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2DF
- HD_Crew_2DA (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2DA
- Sick_Bay_2DA (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay_2DA
- Galley_Mess_2DA (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Mess_2DA
- WO_Mess_Half (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: WO_Mess_Half
- JO_Mess_Half (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: JO_Mess_Half
- HD_Half (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Half
- CPO_Mess_Berth (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess_Berth
- HD_CPO_Berth (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO_Berth

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
