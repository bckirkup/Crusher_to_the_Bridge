# Systems inference notes — wasp_cv7

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_1 | funnel | unknown | exhaust | Island_Upper | sheet_read |
| HangarDoor_1 | hangar_door | unknown | supply | Hangar_Aft | sheet_read |
| HangarDoor_2 | hangar_door | unknown | supply | Hangar_Fwd | sheet_read |
| HangarDoor_3 | hangar_door | unknown | supply | Squadron_Ops_MD | sheet_read |
| VentTrunk_3D | vent_trunk | unknown | exhaust | Crew_Berthing_3D_Mid | sheet_read |
| VentTrunk_4D | vent_trunk | unknown | exhaust | Crew_Berthing_4D | sheet_read |
| VentTrunk_1P | vent_trunk | unknown | exhaust | Provisions_1P | sheet_read |
| AirIntake_LIP | air_shaft | unknown | supply | Island_Lower | sheet_read |
| AirPorts_Island | air_port | unknown | supply | Nav_Bridge | sheet_read |
| MagVent_2P | vent_trunk | unknown | exhaust | Magazine_2P_Fwd | era_plausible |
| Cowl_FD_1 | cowl | unknown | supply | Flight_Deck | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Shops_Poop | nat_supply | era_rule |
| Aft_Stores_2P | nat_supply | era_rule |
| Ammo_1P | nat_supply | era_rule |
| Armory_Fwd | nat_supply | era_rule |
| Aux_Machinery_1P | mech_supply_exhaust | era_rule |
| Aviation_Engine_4D | nat_supply | era_rule |
| Aviation_Shops_Main | nat_supply | era_rule |
| Aviation_Stores_4D | nat_supply | era_rule |
| Bomb_Handling_3D | nat_supply | era_rule |
| CPO_3D | nat_supply | era_rule |
| Catapult_Mach_3D | mech_supply_exhaust | era_rule |
| Catapult_Mach_MD | mech_supply_exhaust | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_3D_Aft | nat_supply | era_rule |
| Crew_Berthing_3D_Fwd | nat_supply | era_rule |
| Crew_Berthing_3D_Mid | mech_exhaust | sheet_read |
| Crew_Berthing_4D | mech_exhaust | sheet_read |
| Crew_Mess_3D | mech_exhaust | era_rule |
| Diesel_Gen_2P | mech_supply_exhaust | era_rule |
| Flight_Deck | nat_supply | era_plausible |
| Focsle_Stores_FD | nat_supply | era_rule |
| Fwd_Stores_2D | nat_supply | era_rule |
| Gal_Berthing_Fwd | nat_supply | era_rule |
| Gal_Shops_Port | nat_supply | era_rule |
| Gal_Shops_Stbd | nat_supply | era_rule |
| Galley_3D | mech_exhaust | era_rule |
| Gunnery_Ops_2D | nat_supply | era_rule |
| HD_2nd | exhaust_only | era_rule |
| HD_3rd | exhaust_only | era_rule |
| HD_Gal | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | sheet_read |
| Hangar_Fwd | nat_supply | sheet_read |
| Inner_Bottom_Tanks | nat_supply | era_rule |
| Island_Lower | mech_supply_exhaust | sheet_read |
| Island_Upper | mech_supply_exhaust | sheet_read |
| Laundry_4D | nat_supply | era_rule |
| Machinery_2P | mech_supply_exhaust | era_rule |
| Machinery_4D | mech_supply_exhaust | era_rule |
| Magazine_2P_Fwd | mech_exhaust | era_plausible |
| Magazines_Hold_Fwd | nat_supply | era_rule |
| Magazines_Hold_Mid | nat_supply | era_rule |
| Nav_Bridge | nat_supply | sheet_read |
| Officers_Country_2D | nat_supply | era_rule |
| Officers_Country_MD | nat_supply | era_rule |
| PriFly_Comm | nat_supply | era_rule |
| Provisions_1P | mech_exhaust | sheet_read |
| Provisions_4D | nat_supply | era_rule |
| Pump_Rms_Hold | mech_supply_exhaust | era_rule |
| SD_Stores_4D | nat_supply | era_rule |
| Shaft_Alleys_Hold | mech_supply_exhaust | era_rule |
| Shops_3D | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Squadron_Ops_MD | nat_supply | sheet_read |
| Squadron_Ready_Rm | nat_supply | era_rule |
| Steering_Gear_1P | mech_supply_exhaust | era_rule |
| Stores_1P | nat_supply | era_rule |
| Tanks_1P | nat_supply | era_rule |
| Tanks_2P | nat_supply | era_rule |
| Tanks_Hold | nat_supply | era_rule |
| Uptake_Island | mech_supply_exhaust | era_rule |
| Wardroom_2D | mech_exhaust | era_rule |
| Work_Shops_Main | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. TANK | freshwater | Stores_1P |
| F.O. SERVICE TANK | fuel | Magazines_Hold_Mid |
| F.O. OVERFLOW TANK | fuel | Provisions_4D |
| D.O. TANK | unknown | Inner_Bottom_Tanks |
| L.O. DRAIN | unknown | Inner_Bottom_Tanks |
| GAS TANK | unknown | Magazines_Hold_Fwd |
| PEAK TANK F.W. | freshwater | Magazines_Hold_Fwd |
| RES. LUB. OIL | fuel | Inner_Bottom_Tanks |

## Plumbing drains

- HD_Gal (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Gal
- Wardroom_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_2D
- HD_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2nd
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Crew_Mess_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_3D
- Galley_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_3D
- HD_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3rd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
