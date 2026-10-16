# Systems inference notes — keppler_dd765

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_Fwd | funnel | up | exhaust | Fwd_Engine_Room | sheet_read |
| Funnel_Aft | funnel | up | exhaust | Aft_Engine_Room | sheet_read |
| Vent_Hood_01 | air_shaft | up | supply | Radio_Block | sheet_read |
| Fan_Room_01 | fan_room | unknown | supply | Radio_Block | sheet_read |
| Hangar_Door | hangar_door | aft | exhaust | Helo_Hangar | sheet_read |
| Vent_Focsle | cowl | fore | supply | Fwd_Stores_1P | sheet_read |
| Air_Intake_Mid | air_shaft | up | supply | Uptake_Mid | sheet_read |
| Mag_Vent_3P | mushroom | unknown | exhaust | Powder_Mag_3P | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Mach_Rm | mech_supply_exhaust | era_rule |
| Aft_Engine_Room | mech_supply_exhaust | sheet_read |
| Aft_Fire_Room | mech_supply_exhaust | era_rule |
| Aft_Shops | mech_ac | era_rule |
| Ammo_Handling_Aft | mech_ac | era_rule |
| Ammo_Handling_Fwd | mech_ac | era_rule |
| CIC | mech_ac | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| CPO_Pantry | mech_ac | era_rule |
| CPO_Quarters_1P | mech_ac | era_rule |
| CPO_Quarters_2P | mech_ac | era_rule |
| Capt_Sea_Cabin | mech_ac | era_rule |
| Captains_Cabin | mech_ac | era_rule |
| Chain_Locker_3P | mech_ac | era_rule |
| Chart_House | mech_ac | era_rule |
| Crew_Berthing_Aft | mech_ac | era_rule |
| Crew_Berthing_Mid_2P | mech_ac | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Dry_Provisions_Hold | mech_ac | era_rule |
| Electronics_Block | mech_ac | era_rule |
| Emerg_Diesel_Gen | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Flag_Plot | mech_ac | era_rule |
| Focsle_Fwd | nat_supply | era_rule |
| Food_Service_1P | mech_ac | era_rule |
| Forecastle_Top_01 | nat_supply | era_rule |
| Fruits_Veg_3P | mech_ac | era_rule |
| Fuel_Tanks_2P | mech_ac | era_rule |
| Fuel_Tanks_Hold | mech_ac | era_rule |
| Fwd_Engine_Room | mech_supply_exhaust | sheet_read |
| Fwd_Fire_Room | mech_supply_exhaust | era_rule |
| Fwd_Stores_1P | nat_supply | sheet_read |
| Fwd_Stores_2P | mech_ac | era_rule |
| Galley | mech_exhaust | era_rule |
| Gen_Wkshop | mech_ac | era_rule |
| Gun_Deck_Aft | nat_supply | era_rule |
| HD_CPO_1P | exhaust_only | era_rule |
| HD_Crew_1P | exhaust_only | era_rule |
| HD_Crew_Main | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| Handling_Rm_3P | mech_ac | era_rule |
| Helo_Hangar | nat_supply | sheet_read |
| Helo_Platform | nat_supply | era_rule |
| ICA_Plotting | mech_ac | era_rule |
| JP5_Pump_Rm | mech_ac | era_rule |
| Landing_Force_3P | mech_ac | era_rule |
| Machinery_Bottom_Hold | mech_supply_exhaust | era_rule |
| Magazine_2P | mech_ac | era_rule |
| Main_Issue_Rm | mech_ac | era_rule |
| Mid_Shops | mech_ac | era_rule |
| Officers_Country | mech_ac | era_rule |
| Ops_Office | mech_ac | era_rule |
| Ordnance_Stores_Hold | mech_ac | era_rule |
| Paint_Store_3P | mech_ac | era_rule |
| Peak_Hold | mech_ac | era_rule |
| Peak_Tank_2P | mech_ac | era_rule |
| Peak_Tank_3P | mech_ac | era_rule |
| Pilot_House | mech_ac | era_rule |
| Post_Office | mech_ac | era_rule |
| Powder_Mag_3P | mech_exhaust | era_plausible |
| Proj_Chg_Mag | mech_ac | era_rule |
| Provisions_3P | mech_ac | era_rule |
| Radio_Block | mech_supply_exhaust | sheet_read |
| Shaft_Alley | mech_ac | era_rule |
| Signal_Shelter | nat_supply | era_rule |
| Sonar_Equip_2 | mech_ac | era_rule |
| Sonar_Rm | mech_ac | era_rule |
| Steering_Gear | mech_ac | era_rule |
| Stores_2P | mech_ac | era_rule |
| Tanks_Machinery_2P | mech_supply_exhaust | era_rule |
| Torpedo_Shop | mech_ac | era_rule |
| Uptake_Mid | mech_supply_exhaust | sheet_read |
| Uptake_Stacks | mech_supply_exhaust | era_rule |
| Voids_Aft_2P | mech_ac | era_rule |
| WR_Staterooms_Fwd | mech_ac | era_rule |
| Wardroom_Mess | mech_exhaust | era_rule |
| Water_Fuel_Hold_Fwd | mech_ac | era_rule |
| Weather_Deck_01 | nat_supply | era_rule |
| Windlass_Room | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL OR BALLAST C-10-F | fuel | Fuel_Tanks_2P |
| RESERVE FEED WATER B-14-W | freshwater | Tanks_Machinery_2P |
| JP-5 GRAVITY TANK A-305-J | unknown | Emerg_Diesel_Gen |
| FRESH WATER B-12-W | freshwater | Water_Fuel_Hold_Fwd |
| FUEL OIL C-17-F | fuel | Fuel_Tanks_Hold |
| PEAK TANK A-1-W | unknown | Peak_Tank_3P |

## Plumbing drains

- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- HD_Crew_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Main
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess
- HD_Crew_1P (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1P
- HD_CPO_1P (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO_1P
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy DD-765 USS Keppler (Gearing FRAM II), Booklet of General Plans, 1969 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [dd765.pdf](https://maritime.org/doc/plans/dd765.pdf).
