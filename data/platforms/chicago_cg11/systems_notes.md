# Systems inference notes — chicago_cg11

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| vm_stack_fwd | funnel | up | exhaust | Machinery_2P | sheet_read |
| vm_stack_aft | funnel | up | exhaust | Machinery_2P | sheet_read |
| vm_plenum | vent_trunk | unknown | supply | Mag_Machinery_2P | sheet_read |
| vm_supply_vent_3rd | vent_trunk | unknown | supply | Crew_Services_3rd | sheet_read |
| vm_ac_rooms_1p | fan_room | unknown | supply | Equipment_Mid_1P | sheet_read |
| vm_ac_rooms_2p | fan_room | unknown | supply | Sonar_AC_2P | sheet_read |
| vm_fan_rooms_main | fan_room | unknown | supply | Offices_Main_Aft | sheet_read |
| vm_ww_trunks | vent_trunk | unknown | supply | Missile_Magazine_3rd | sheet_read |
| vm_mag_vent_aft | mushroom | unknown | exhaust | Provisions_1P | era_plausible |
| vm_helo_vent | vent_trunk | up | exhaust | Helo_Deck | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Cells_Hold | mech_ac | era_rule |
| Aft_Mags_3rd | mech_ac | era_rule |
| Aft_Voids_Hold | mech_ac | era_rule |
| Amidships_Cells_3rd | mech_ac | era_rule |
| Boat_Stowage_02 | nat_supply | era_rule |
| Boat_Stowage_Main | nat_supply | era_rule |
| Bow_Cells_Hold | mech_ac | era_rule |
| Bow_Stores_1P | mech_ac | era_rule |
| Bow_Tip_2nd | mech_ac | era_rule |
| Bow_Weather | nat_supply | era_rule |
| CPO_Country_Main | mech_ac | era_rule |
| CPO_Mess_2nd | mech_exhaust | era_rule |
| Command_01 | mech_ac | era_rule |
| Crew_Berthing_1P | mech_ac | era_rule |
| Crew_Berthing_Aft_2nd | mech_ac | era_rule |
| Crew_Berthing_Aft_3rd | mech_ac | era_rule |
| Crew_Berthing_Fwd_2nd | mech_ac | era_rule |
| Crew_Berthing_Fwd_3rd | mech_ac | era_rule |
| Crew_Berthing_Main | mech_ac | era_rule |
| Crew_Messroom_2nd | mech_exhaust | era_rule |
| Crew_Services_3rd | nat_supply | sheet_read |
| Electronics_1P | mech_ac | era_rule |
| Electronics_Main | mech_ac | era_rule |
| Elevator_Trunk_3rd | mech_ac | era_rule |
| Emerg_Gen_2P | mech_supply_exhaust | era_rule |
| Equipment_Mid_1P | mech_supply_exhaust | sheet_read |
| FO_Wing_Port_2P | mech_ac | era_rule |
| FO_Wing_Port_Hold | mech_ac | era_rule |
| FO_Wing_Stbd_2P | mech_ac | era_rule |
| FO_Wing_Stbd_Hold | mech_ac | era_rule |
| Fantail_Weather | nat_supply | era_rule |
| Flag_01_Fwd | mech_ac | era_rule |
| Flag_Level_03 | mech_ac | era_rule |
| Forecastle_Deck | nat_supply | era_rule |
| Forepeak_3rd | mech_ac | era_rule |
| Fwd_Services_1P | mech_ac | era_rule |
| Fwd_Stores_2P | mech_ac | era_rule |
| Fwd_Stores_3rd | mech_ac | era_rule |
| Fwd_Tanks_Hold | mech_ac | era_rule |
| Galley_Support_2nd | mech_ac | era_rule |
| HD_CIC_3rd | exhaust_only | era_rule |
| HD_CPO_2nd | exhaust_only | era_rule |
| HD_Crew_Aft_3rd | exhaust_only | era_rule |
| HD_Crew_Fwd_2nd | exhaust_only | era_rule |
| HD_Crew_Fwd_3rd | exhaust_only | era_rule |
| HD_Crew_Mid_2nd | exhaust_only | era_rule |
| HD_Marines_3rd | exhaust_only | era_rule |
| Helo_Deck | mech_exhaust | sheet_read |
| Helo_Deck_02_Aft | nat_supply | era_rule |
| Helo_Hangar_3rd | nat_supply | era_rule |
| Helo_Service_2nd | mech_ac | era_rule |
| Landing_Force_1P | mech_ac | era_rule |
| Launcher_Deck_01 | nat_supply | era_rule |
| Machinery_2P | mech_supply_exhaust | sheet_read |
| Machinery_Port_1P | mech_supply_exhaust | era_rule |
| Machinery_Stbd_1P | mech_supply_exhaust | era_rule |
| Mag_Machinery_2P | mech_supply_exhaust | sheet_read |
| Marine_Country_3rd | mech_ac | era_rule |
| Medical_2nd | mech_ac | era_rule |
| Mess_Gear_2nd | mech_ac | era_rule |
| Missile_Mag_Deck_Fwd | mech_ac | era_rule |
| Missile_Magazine_3rd | nat_supply | sheet_read |
| Missile_Magazine_Aft | mech_ac | era_rule |
| Missile_Magazine_Fwd | mech_ac | era_rule |
| Missile_Support_1P | mech_ac | era_rule |
| Officers_Strm_2nd | mech_ac | era_rule |
| Offices_02 | mech_ac | era_rule |
| Offices_Main_Aft | mech_supply_exhaust | sheet_read |
| Open_03 | nat_supply | era_rule |
| Peak_Tank_1P | mech_ac | era_rule |
| Peak_Tank_2P | mech_ac | era_rule |
| Peak_Tank_Hold | mech_ac | era_rule |
| Provisions_1P | mech_exhaust | era_plausible |
| Radar_Control_3rd | mech_ac | era_rule |
| Recreation_2nd | mech_ac | era_rule |
| SD_Storerooms_Aft_1P | mech_ac | era_rule |
| SD_Stores_Aft_2nd | mech_ac | era_rule |
| Shaft_Alley_Hold | mech_supply_exhaust | era_rule |
| Shelters_01_Aft | mech_ac | era_rule |
| Shops_Main | mech_ac | era_rule |
| Sonar_AC_2P | mech_supply_exhaust | sheet_read |
| Sonar_Room_Hold | mech_supply_exhaust | era_rule |
| Steering_Gear_2P | mech_supply_exhaust | era_rule |
| Stern_Gear_3rd | mech_ac | era_rule |
| Superstructure_03 | mech_ac | era_rule |
| Talos_Mag_Deep_2P | mech_ac | era_rule |
| Terrier_Deck_02 | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| SERVICE FUEL / F.O. BALLAST (machinery edges) | fuel | FO_Wing_Port_Hold |
| F.O. OVERFLOW OR BALLAST / SETTLING | fuel | FO_Wing_Stbd_2P |
| FUEL OIL & BALLAST CELLS (aft) | fuel | Aft_Voids_Hold |
| FOR'VD BALLAST + AUX JP5 | unknown | Fwd_Tanks_Hold |
| WASTE WATER SUMP TANK | sewage | Shaft_Alley_Hold |
| GASOLINE TANK | unknown | Aft_Voids_Hold |
| PEAK TANK 8-1-0-W | unknown | Peak_Tank_2P |
| LOCKED F.W. BALLAST | freshwater | Fwd_Stores_2P |

## Plumbing drains

- Crew_Messroom_2nd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_Crew_Mid_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- CPO_Mess_2nd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- Medical_2nd (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_CPO_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_Crew_Fwd_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_Marines_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_Crew_Aft_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_CIC_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_Crew_Fwd_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CG-11 USS Chicago (Baltimore class), Booklet of General Plans, 1964 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cg11.pdf](https://maritime.org/doc/plans/cg11.pdf).
