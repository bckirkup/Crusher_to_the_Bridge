# Systems inference notes — yorktown_cv5

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_01 | funnel | up | exhaust | Funnel_Uptake | sheet_read |
| uptake_enc_01 | uptake | up | exhaust | Nav_Bridge | sheet_read |
| hangar_door_p1 | hangar_door | port | supply | Hangar_Mid | sheet_read |
| hangar_door_p2 | hangar_door | port | supply | Hangar_Mid | sheet_read |
| hangar_door_s1 | hangar_door | starboard | supply | Hangar_Mid | sheet_read |
| hangar_door_s2 | hangar_door | starboard | supply | Hangar_Fwd | sheet_read |
| exhaust_trunk_01 | vent_trunk | up | exhaust | Uptakes_Main | sheet_read |
| fan_room_01 | fan_room | unknown | supply | Av_Shops_Port_01 | sheet_read |
| air_shaft_01 | air_shaft | unknown | supply | HD_3rd | sheet_read |
| cowl_01 | cowl | fore | supply | Av_Shops_Port_01 | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Machinery_1P | mech_supply_exhaust | era_rule |
| Aft_Machinery_2P | mech_supply_exhaust | era_rule |
| Av_Shops_Port_01 | mech_supply_exhaust | sheet_read |
| Av_Stores_Stbd_01 | nat_supply | era_rule |
| Avgas_Tanks_2P | nat_supply | era_rule |
| Avgas_Tanks_4D | nat_supply | era_rule |
| Avgas_Tanks_Hold | nat_supply | era_rule |
| Boat_Wing_Repair_Main | nat_supply | era_rule |
| CPO_3D | nat_supply | era_rule |
| Catapult_Machinery_02 | mech_supply_exhaust | era_rule |
| Central_Station_1P | mech_supply_exhaust | era_rule |
| Crew_Berthing_2D_Aft | nat_supply | era_rule |
| Crew_Berthing_2D_Mid | nat_supply | era_rule |
| Crew_Lounge_02 | nat_supply | era_rule |
| Crew_Mess_3D | mech_exhaust | era_rule |
| Crew_Mess_3D_Fwd | mech_exhaust | era_rule |
| Crew_Space_4D | nat_supply | era_rule |
| Engine_Rm_4D | mech_supply_exhaust | era_rule |
| Fire_Rooms_1P | mech_supply_exhaust | era_rule |
| Fire_Rooms_2P | mech_supply_exhaust | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Focsle_Bow_01 | nat_supply | era_rule |
| Focsle_Bow_Main | nat_supply | era_rule |
| Focsle_Stores_2D | nat_supply | era_rule |
| Funnel_Uptake | mech_supply_exhaust | sheet_read |
| Fwd_Machinery_2P | mech_supply_exhaust | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_4D | nat_supply | era_rule |
| Galley_3D | mech_exhaust | era_rule |
| HD_2nd | exhaust_only | era_rule |
| HD_3rd | exhaust_only | sheet_read |
| Hangar_Aft | nat_supply | era_rule |
| Hangar_Fwd | nat_supply | sheet_read |
| Hangar_Mid | nat_supply | sheet_read |
| Hold_Tanks | nat_supply | era_rule |
| Island_Upper | nat_supply | era_rule |
| Laundry_3D | nat_supply | era_rule |
| Machinery_Hold | mech_supply_exhaust | era_rule |
| Magazine_2P_Aft | nat_supply | era_rule |
| Magazines_1P | nat_supply | era_rule |
| Marines_Quarters_2D | nat_supply | era_rule |
| Nav_Bridge | mech_supply_exhaust | sheet_read |
| Officers_Country_02 | nat_supply | era_rule |
| Officers_Country_2D | nat_supply | era_rule |
| Peak_1P | nat_supply | era_rule |
| Peak_Tank_4D | nat_supply | era_rule |
| Peak_Tanks_3D | nat_supply | era_rule |
| PriFly_FlagPlot | nat_supply | era_rule |
| Provisions_1P | nat_supply | era_rule |
| Ready_Issue_01 | nat_supply | era_rule |
| Shaft_Alleys_Hold | mech_supply_exhaust | era_rule |
| Shops_4D | nat_supply | era_rule |
| Shops_Main_Aft | nat_supply | era_rule |
| Shops_Main_Fwd | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Squadron_Ready_02 | nat_supply | era_rule |
| Squadron_Storerooms_02 | nat_supply | era_rule |
| Stern_Gear_2D | mech_supply_exhaust | era_rule |
| Stern_Hold | nat_supply | era_rule |
| Stern_Rooms_Main | nat_supply | era_rule |
| Stern_Stores_4D | nat_supply | era_rule |
| Stern_Voids_1P | nat_supply | era_rule |
| Stores_3D | nat_supply | era_rule |
| Stores_Fwd_3D | nat_supply | era_rule |
| Torpedo_Storage_01 | nat_supply | era_rule |
| Trunks_Pits_2D | mech_supply_exhaust | era_rule |
| Uptakes_Main | mech_supply_exhaust | sheet_read |
| Voids_2P | nat_supply | era_rule |
| Wardroom_2D | mech_exhaust | era_rule |
| Wardroom_Annex_02 | mech_exhaust | era_rule |
| Warrant_Officers_3D | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. TANK A-W | freshwater | Hold_Tanks |
| FRESH WATER A-W | freshwater | Peak_Tanks_3D |
| F.O. / EMER. FUEL OIL | fuel | Provisions_1P |
| F.O. D-F | fuel | Fwd_Machinery_2P |
| PEAK TANK F.P. | unknown | Peak_1P |

## Plumbing drains

- Wardroom_Annex_02 (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Annex_02
- HD_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2nd
- Wardroom_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_2D
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Crew_Mess_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_3D
- Galley_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_3D
- Crew_Mess_3D_Fwd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_3D_Fwd
- HD_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3rd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
