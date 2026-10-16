# Systems inference notes — miami_cl89

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| vm_fan_rm_main | fan_room | unknown | supply | Ammo_Handling_5in_7 | sheet_read |
| vm_fan_rm_2nd | fan_room | unknown | supply | HD_Crew_2nd | sheet_read |
| vm_uptake_main | uptake | up | exhaust | Misc_Services_Main | sheet_read |
| vm_funnel_pair | funnel | up | exhaust | — | sheet_read |
| vm_er_supply_1p | vent_trunk | unknown | supply | Engine_Room_Aft | sheet_read |
| vm_ac_apparatus | fan_room | unknown | supply | DC_Radio_1P | sheet_read |
| vm_cowl_focsle | cowl | fore | supply | Bow_Weather | era_plausible |
| vm_mag_vents_aft | mushroom | unknown | exhaust | Aft_6In_Magazines | era_plausible |
| vm_mag_vents_fwd | mushroom | unknown | exhaust | Fwd_6In_Magazines | era_plausible |
| vm_hangar_vent | vent_trunk | up | exhaust | Hangar | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_5In_Magazines | nat_supply | era_rule |
| Aft_6In_Magazines | mech_exhaust | era_plausible |
| Ammo_Handling_5in_1 | nat_supply | era_rule |
| Ammo_Handling_5in_2 | nat_supply | era_rule |
| Ammo_Handling_5in_7 | mech_supply_exhaust | sheet_read |
| Ammo_Handling_5in_8 | nat_supply | era_rule |
| Armory_3rd | nat_supply | era_rule |
| Aviation_Trunk_3rd | nat_supply | era_rule |
| Boat_Stowage_Port | nat_supply | era_rule |
| Boat_Stowage_Stbd | nat_supply | era_rule |
| Bow_Stores_2nd | nat_supply | era_rule |
| Bow_Stores_3rd | nat_supply | era_rule |
| Bow_Weather | nat_supply | era_plausible |
| Bridge_Wings | nat_supply | era_rule |
| CIC | nat_supply | era_rule |
| CPO_Berthing_2nd | nat_supply | era_rule |
| Catapult_Deck | nat_supply | era_rule |
| Chart_House | nat_supply | era_rule |
| Comm_Shelter_01 | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_3rd | nat_supply | era_rule |
| Crew_Mess_1P | mech_exhaust | era_rule |
| Crew_Messing_2nd | mech_exhaust | era_rule |
| DC_Radio_1P | mech_supply_exhaust | sheet_read |
| Electrical_Repair | nat_supply | era_rule |
| Elevator_Pit_3rd | nat_supply | era_rule |
| Engine_Room_Aft | mech_supply_exhaust | sheet_read |
| Engine_Room_Fwd | mech_supply_exhaust | era_rule |
| Evaporator_AC_3rd | mech_supply_exhaust | era_rule |
| FO_Service_Port_Hold | nat_supply | era_rule |
| FO_Service_Stbd_Hold | nat_supply | era_rule |
| FO_Wing_Port_2P | nat_supply | era_rule |
| FO_Wing_Stbd_2P | nat_supply | era_rule |
| Fan_Issue_2nd | nat_supply | era_rule |
| Fire_Room_Aft | mech_supply_exhaust | era_rule |
| Fire_Room_Fwd | mech_supply_exhaust | era_rule |
| Forecastle_Main | nat_supply | era_rule |
| Forepeak_3rd | nat_supply | era_rule |
| Forepeak_Hold | nat_supply | era_rule |
| Fuel_Oil_Tanks_Aft | nat_supply | era_rule |
| Fuel_Oil_Tanks_Fwd | nat_supply | era_rule |
| Fwd_6In_Magazines | mech_exhaust | era_plausible |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_2P | nat_supply | era_rule |
| Fwd_Tanks_Hold | nat_supply | era_rule |
| Galley_Main | mech_exhaust | era_rule |
| Galley_Service_3rd | mech_exhaust | era_rule |
| Gun_Tubs_01 | nat_supply | era_rule |
| HD_CPO_2nd | exhaust_only | era_rule |
| HD_Crew_2nd | exhaust_only | sheet_read |
| HD_Crew_3rd | exhaust_only | era_rule |
| HD_Crew_Main | exhaust_only | era_rule |
| Hangar | mech_exhaust | sheet_read |
| Laundry | nat_supply | era_rule |
| Marine_LF_Stores | nat_supply | era_rule |
| Medical_3rd | mech_supply_exhaust | era_rule |
| Misc_Services_Main | mech_supply_exhaust | sheet_read |
| Nav_Bridge | nat_supply | era_rule |
| Navigators_Office | nat_supply | era_rule |
| Officers_Country_2nd | nat_supply | era_rule |
| Peak_Tank_1P | nat_supply | era_rule |
| Peak_Tank_2P | nat_supply | era_rule |
| Plot_Room | nat_supply | era_rule |
| Provisions_1P | nat_supply | era_rule |
| Provisions_3rd | nat_supply | era_rule |
| RS_Clipping | nat_supply | era_rule |
| Radar_Room | nat_supply | era_rule |
| Radio_01 | nat_supply | era_rule |
| Radio_Bridge | nat_supply | era_rule |
| Repair_Shops_Main | nat_supply | era_rule |
| Shaft_Alley_Hold | mech_supply_exhaust | era_rule |
| Ships_Stores_1P | nat_supply | era_rule |
| Shops_01 | nat_supply | era_rule |
| Signal_Shelter | nat_supply | era_rule |
| Steering_Flat | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stern_Aviation | nat_supply | era_rule |
| Stores_2nd | nat_supply | era_rule |
| WO_Country | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |
| Windlass_Chain_2nd | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. SERVICE TANKS B-920F..B-924F | fuel | FO_Service_Port_Hold |
| F.O. & BALLAST CELLS (fwd of machinery) | fuel | Fuel_Oil_Tanks_Fwd |
| F.O. & BALLAST WING CELLS | fuel | FO_Wing_Port_2P |
| GASOLINE TANK C-510M / C-122 GAS | unknown | Aft_6In_Magazines |
| CONTAMINATED F.O. SETTLING | fuel | FO_Wing_Stbd_2P |
| F.W. TANKS (fwd) | freshwater | Fwd_Tanks_Hold |
| PEAK TANK A-1W | unknown | Peak_Tank_1P |
| LUBE OIL / CUT OIL | fuel | Fwd_Tanks_Hold |

## Plumbing drains

- Galley_Main (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Main
- HD_Crew_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Main
- HD_CPO_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO_2nd
- Crew_Messing_2nd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Messing_2nd
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Galley_Service_3rd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Service_3rd
- HD_Crew_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_3rd
- Medical_3rd (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Medical_3rd
- Crew_Mess_1P (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_1P

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CL-89 USS Miami (Cleveland class), Booklet of General Plans, 1946 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cl89.pdf](https://maritime.org/doc/plans/cl89.pdf).
