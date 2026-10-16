# Systems inference notes — olympia_c6

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_Aft | funnel | up | exhaust | PF_Boiler_Port | sheet_read |
| Funnel_Fwd | funnel | up | exhaust | PF_Boiler_Stb | sheet_read |
| Cowl_MainDeck_Fwd | cowl | fore | supply | MD_Fwd_Barbette | era_plausible |
| Mushroom_BoatDeck | mushroom | up | supply | SD_Boats_Mid_Stb | era_plausible |
| Skylight_Officers | skylight | up | exhaust | MD_Officers_Cabins_Port | sheet_read |
| Torpedo_Vent | vent_trunk | up | exhaust | PD_Torpedo_Room_Fwd | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| BD_Cabins_Stb | nat_supply | era_rule |
| BD_Crews_Berthing_Port | nat_supply | era_rule |
| BD_Crews_Berthing_Stb | nat_supply | era_rule |
| BD_Crews_Lavatory | exhaust_only | era_rule |
| BD_Crews_WC | exhaust_only | era_rule |
| BD_Dining_Passage | nat_supply | era_rule |
| BD_Engine_Hatch | mech_supply_exhaust | era_rule |
| BD_JnrOfficers_Mess | mech_exhaust | era_rule |
| BD_JnrOfficers_Rooms | nat_supply | era_rule |
| BD_Officers_WC | exhaust_only | era_rule |
| BD_Sick_Bay | mech_supply_exhaust | era_rule |
| BD_State_Rooms_Port | nat_supply | era_rule |
| BD_State_Rooms_Stb | nat_supply | era_rule |
| BD_Torpedo_Office | nat_supply | era_rule |
| BD_Ward_Room | mech_exhaust | era_rule |
| BD_Wardroom_Pantry | nat_supply | era_rule |
| HD_5in_Ammo_Aft | nat_supply | era_rule |
| HD_5in_Ammo_Fwd | nat_supply | era_rule |
| HD_5in_Ammo_Mid | nat_supply | era_rule |
| HD_6pdr_Ammo_Aft | nat_supply | era_rule |
| HD_6pdr_Ammo_Fwd | nat_supply | era_rule |
| HD_8in_Magazine_Aft | nat_supply | era_rule |
| HD_8in_Magazine_Fwd | nat_supply | era_rule |
| HD_8in_Shell_Aft | nat_supply | era_rule |
| HD_Aft_Stores | nat_supply | era_rule |
| HD_Boiler_Port | mech_supply_exhaust | era_rule |
| HD_Boiler_Stb | mech_supply_exhaust | era_rule |
| HD_Coal_Port | mech_supply_exhaust | era_rule |
| HD_Coal_Stb | mech_supply_exhaust | era_rule |
| HD_Electric_Stores | nat_supply | era_rule |
| HD_Engine_Port | mech_supply_exhaust | era_rule |
| HD_Engine_Stb | mech_supply_exhaust | era_rule |
| HD_Engineers_Stores | nat_supply | era_rule |
| HD_Hold_Fwd | nat_supply | era_rule |
| HD_Marine_Stores | nat_supply | era_rule |
| HD_Trimming_Tank_Aft | mech_supply_exhaust | era_rule |
| HD_Trimming_Tank_Fwd | mech_supply_exhaust | era_rule |
| MD_Admirals_Cabin | nat_supply | era_rule |
| MD_Admirals_State_Room | nat_supply | era_rule |
| MD_Aft_Barbette | mech_supply_exhaust | era_rule |
| MD_Captains_Cabin | nat_supply | era_rule |
| MD_Casemate_Port | mech_supply_exhaust | era_rule |
| MD_Casemate_Stb | mech_supply_exhaust | era_rule |
| MD_Engine_Hatch | mech_supply_exhaust | era_rule |
| MD_Forecastle_Open | nat_supply | era_rule |
| MD_Fwd_Barbette | mech_supply_exhaust | era_plausible |
| MD_Galley | mech_exhaust | era_rule |
| MD_Issuing_Room | nat_supply | era_rule |
| MD_Officers_Cabins_Port | nat_supply | sheet_read |
| MD_Officers_Cabins_Stb | nat_supply | era_rule |
| MD_Signal_Yeoman | nat_supply | era_rule |
| MD_Stern_Fantail | nat_supply | era_rule |
| MD_Wash_Room | exhaust_only | era_rule |
| PD_Aft_Stores | nat_supply | era_rule |
| PD_Bread_Room | nat_supply | era_rule |
| PD_Broadside_Torpedo_Aft | mech_supply_exhaust | era_rule |
| PD_Broadside_Torpedo_Fwd | mech_supply_exhaust | era_rule |
| PD_Chain_Lockers | nat_supply | era_rule |
| PD_Coal_Port_Aft | mech_supply_exhaust | era_rule |
| PD_Coal_Port_Fwd | mech_supply_exhaust | era_rule |
| PD_Coal_Stb_Aft | mech_supply_exhaust | era_rule |
| PD_Coal_Stb_Fwd | mech_supply_exhaust | era_rule |
| PD_Distiller_Port | nat_supply | era_rule |
| PD_Distiller_Stb | nat_supply | era_rule |
| PD_Dry_Provisions | nat_supply | era_rule |
| PD_Engine_Hatch_Port | mech_supply_exhaust | era_rule |
| PD_Engine_Hatch_Stb | mech_supply_exhaust | era_rule |
| PD_JOWO_Lockers | nat_supply | era_rule |
| PD_Officers_Lockers | nat_supply | era_rule |
| PD_Passing_Room_Aft | nat_supply | era_rule |
| PD_Paymasters_Stores | nat_supply | era_rule |
| PD_Ships_Stores | nat_supply | era_rule |
| PD_Torpedo_Room_Aft | mech_supply_exhaust | era_rule |
| PD_Torpedo_Room_Fwd | mech_supply_exhaust | era_plausible |
| PF_Aft_Stores_Port | nat_supply | era_rule |
| PF_Aft_Stores_Stb | nat_supply | era_rule |
| PF_Boiler_Port | mech_supply_exhaust | sheet_read |
| PF_Boiler_Stb | mech_supply_exhaust | sheet_read |
| PF_Coal_Mid | mech_supply_exhaust | era_rule |
| PF_Coal_Mid_Stb | mech_supply_exhaust | era_rule |
| PF_Dynamo_Room | mech_supply_exhaust | era_rule |
| PF_Engine_Port | mech_supply_exhaust | era_rule |
| PF_Engine_Stb | mech_supply_exhaust | era_rule |
| PF_Fwd_Stores | nat_supply | era_rule |
| PF_General_Stores | nat_supply | era_rule |
| PF_Hold_Fwd | nat_supply | era_rule |
| PF_Paint_Oil | nat_supply | era_rule |
| PF_Passing_Room_Aft | nat_supply | era_rule |
| PF_Passing_Room_Mid | nat_supply | era_rule |
| PF_Steering_Gear | mech_supply_exhaust | era_rule |
| PF_Trimming_Tank_Fwd | mech_supply_exhaust | era_rule |
| SD_Aft_Barbette | mech_supply_exhaust | era_rule |
| SD_Boats_Aft_Port | nat_supply | era_rule |
| SD_Boats_Aft_Stb | nat_supply | era_rule |
| SD_Boats_Fwd_Port | nat_supply | era_rule |
| SD_Boats_Fwd_Stb | nat_supply | era_rule |
| SD_Boats_Mid_Port | nat_supply | era_rule |
| SD_Boats_Mid_Stb | nat_supply | era_plausible |
| SD_Engine_Hatch | mech_supply_exhaust | era_rule |
| SD_Forecastle_Open | nat_supply | era_rule |
| SD_Fwd_Barbette | mech_supply_exhaust | era_rule |
| SD_Pilot_House | nat_supply | era_rule |
| SD_Skylight | nat_supply | era_rule |
| SD_Stern_Open | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| TRIMMING TANK (bow) | unknown | HD_Trimming_Tank_Fwd |
| TRIMMING TANK (stern) | unknown | HD_Trimming_Tank_Aft |
| COAL bunkers | unknown | PD_Passing_Room_Aft |

## Plumbing drains

- MD_Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: MD_Galley
- MD_Wash_Room (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: MD_Wash_Room
- BD_Officers_WC (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_Officers_WC
- BD_Ward_Room (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_Ward_Room
- BD_JnrOfficers_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_JnrOfficers_Mess
- BD_Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_Sick_Bay
- BD_Crews_WC (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_Crews_WC
- BD_Crews_Lavatory (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: BD_Crews_Lavatory

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy C-6 USS Olympia, Booklet of General Plans, 1895 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [c6.pdf](https://maritime.org/doc/plans/c6.pdf).
