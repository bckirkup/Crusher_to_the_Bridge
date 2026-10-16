# Systems inference notes — ranger_cv4

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Hangar_Door_Port | hangar_door | unknown | supply | Hangar_Fwd | sheet_read |
| Hangar_Door_Stbd | hangar_door | unknown | supply | Hangar_Fwd | sheet_read |
| Hangar_Door_Aft_S | hangar_door | unknown | supply | Hangar_Mid | sheet_read |
| Uptake_Stbd | uptake | unknown | exhaust | Uptakes_1D | sheet_read |
| Blower_Rm_1 | fan_room | unknown | supply | Hangar_Aft | sheet_read |
| Exhaust_Fan_Hangar | fan_room | unknown | exhaust | Uptakes_1D | sheet_read |
| Focsle_Cowl_1 | cowl | fore | supply | Marine_Compartment | sheet_read |
| Focsle_Cowl_2 | cowl | fore | supply | Focsle_Anchor | sheet_read |
| Poop_Cowl | cowl | aft | exhaust | Crew_Poop | sheet_read |
| Mag_Mushrooms | mushroom | unknown | exhaust | Magazines_1P | era_plausible |
| Hold_Vents | vent_trunk | unknown | exhaust | Fuel_Oil_Hold | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Shops_1D | nat_supply | era_rule |
| Aft_Stores_2D | nat_supply | era_rule |
| Aux_Machinery_1P | mech_supply_exhaust | era_rule |
| Av_Stores_4D | nat_supply | era_rule |
| Aviation_Qtrs_3D | nat_supply | era_rule |
| Boiler_Rooms | mech_supply_exhaust | era_rule |
| Bomb_Machinery_1P | mech_supply_exhaust | era_rule |
| Bomb_Storage_2D | mech_supply_exhaust | era_rule |
| Bosun_2nd_Div_1D | nat_supply | era_rule |
| Brig_3D | nat_supply | era_rule |
| CPO_Quarters_4D | nat_supply | era_rule |
| Catapult_Room_1D | mech_supply_exhaust | era_rule |
| Clipping_Rm_Aft | nat_supply | era_rule |
| Clipping_Rm_Fwd | nat_supply | era_rule |
| Control_Top | nat_supply | era_rule |
| Crew_Aft_2D | nat_supply | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_3D_Aft | nat_supply | era_rule |
| Crew_Berthing_3D_Mid | nat_supply | era_rule |
| Crew_Mess_2D | mech_exhaust | era_rule |
| Crew_Poop | mech_exhaust | sheet_read |
| Crew_Space_4D | nat_supply | era_rule |
| Flag_Bridge | nat_supply | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Focsle_4D | nat_supply | era_rule |
| Focsle_Anchor | nat_supply | sheet_read |
| Focsle_Chain_3D | nat_supply | era_rule |
| Focsle_Stores_1P | nat_supply | era_rule |
| Focsle_Work | nat_supply | era_rule |
| Fuel_Oil_Hold | mech_supply_exhaust | era_plausible |
| Fwd_Tanks_Hold | mech_supply_exhaust | era_rule |
| Gallery_Walkway | nat_supply | era_rule |
| Galley_2D | mech_exhaust | era_rule |
| Gasoline_Tank_Hold | mech_supply_exhaust | era_rule |
| Gasoline_Tanks_1P | mech_supply_exhaust | era_rule |
| Generators_4D | mech_supply_exhaust | era_rule |
| Gun_Platform_Aft | nat_supply | era_rule |
| Gun_Platform_Fwd | nat_supply | era_rule |
| HD_1D_Officers | exhaust_only | era_rule |
| HD_2D_Crew | exhaust_only | era_rule |
| HD_2D_Officers | exhaust_only | era_rule |
| HD_3D_Crew | exhaust_only | era_rule |
| HD_3D_Crew_Mid | exhaust_only | era_rule |
| Hangar_Aft | mech_supply_exhaust | sheet_read |
| Hangar_Fwd | nat_supply | sheet_read |
| Hangar_Mid | nat_supply | sheet_read |
| Issue_Stores_4D | nat_supply | era_rule |
| Laundry_3D | nat_supply | era_rule |
| Machinery_4D | mech_supply_exhaust | era_rule |
| Magazines_1P | mech_supply_exhaust | era_plausible |
| Magazines_Hold | mech_supply_exhaust | era_rule |
| Marine_Compartment | nat_supply | sheet_read |
| Nav_Bridge | nat_supply | era_rule |
| Officers_2D | nat_supply | era_rule |
| Officers_Country_1D | nat_supply | era_rule |
| Officers_Country_3D | nat_supply | era_rule |
| Officers_Galley_2D | mech_exhaust | era_rule |
| Offices_1D | nat_supply | era_rule |
| Poop_Deck | nat_supply | era_rule |
| Provisions_4D | nat_supply | era_rule |
| Ready_Room_1D | nat_supply | era_rule |
| Ready_Service_Rm | nat_supply | era_rule |
| Refrig_Stores_4D | nat_supply | era_rule |
| SO_Stores_1P | nat_supply | era_rule |
| SO_Stores_2D | nat_supply | era_rule |
| Shaft_Alley_Hold | mech_supply_exhaust | era_rule |
| Shops_3D | nat_supply | era_rule |
| Sick_Bay_2D | mech_supply_exhaust | era_rule |
| Signal_Bridge | nat_supply | era_rule |
| Steering_Gear_1P | mech_supply_exhaust | era_rule |
| Uptakes_1D | mech_supply_exhaust | sheet_read |
| Uptakes_2D | mech_supply_exhaust | era_rule |
| Wardroom_2D | mech_exhaust | era_rule |
| Windlass_Room_1D | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL A-917-F (double-bottom cells) | fuel | Fuel_Oil_Hold |
| GASOLINE TANK STORAGE A-915-G | unknown | Gasoline_Tanks_1P |
| FRESH WATER TANK A-604-W | freshwater | Fwd_Tanks_Hold |
| FRESH WATER TANK A-602-W | freshwater | Fwd_Tanks_Hold |
| PEAK TANK A-601-W | unknown | Fwd_Tanks_Hold |
| PEAK TANK D-515-W (stern) | unknown | Shaft_Alley_Hold |
| RESERVE FEED WATER (aft) | freshwater | Shaft_Alley_Hold |
| DIESEL OIL A-331-B | fuel | Fuel_Oil_Hold |
| AVIATION LUB. OIL A-614-A | fuel | SO_Stores_1P |
| VOID SPACE / COFFERDAM wing cells | unknown | Gasoline_Tank_Hold |

## Plumbing drains

- HD_1D_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_1D_Officers
- Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_2D
- Crew_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2D
- Sick_Bay_2D (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay_2D
- Officers_Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Galley_2D
- Wardroom_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_2D
- HD_2D_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Crew
- HD_2D_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Officers
- HD_3D_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3D_Crew
- HD_3D_Crew_Mid (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3D_Crew_Mid

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CV-4 USS Ranger, Booklet of General Plans, 1944 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cv4.pdf](https://maritime.org/doc/plans/cv4.pdf).
