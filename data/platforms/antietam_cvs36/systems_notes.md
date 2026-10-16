# Systems inference notes — antietam_cvs36

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_island | funnel | unknown | exhaust | Island_Ops | sheet_read |
| uptake_main_port | uptake | unknown | exhaust | Uptakes_Main | sheet_read |
| air_intake_boiler | air_port | unknown | supply | Boiler_Room_1 | sheet_read |
| vent_cover_foc | cowl | unknown | supply | Crew_Berthing_Foc | sheet_read |
| vent_cover_foc2 | cowl | unknown | supply | Crew_Berthing_Foc | sheet_read |
| vent_trunk_gal | vent_trunk | unknown | supply | Squadron_Offices | sheet_read |
| hangar_roller_door_aft | air_port | unknown | supply | Hangar_Aft | sheet_read |
| hangar_roller_door_mid | air_port | unknown | supply | Hangar_Mid | sheet_read |
| hangar_roller_door_fwd | air_port | unknown | supply | Hangar_Fwd | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Air_Ops_Rooms | mech_ac | era_rule |
| Armory_4D | mech_ac | era_rule |
| Aux_Machinery_Fwd | mech_supply_exhaust | era_rule |
| Avionics_Shops | mech_ac | era_rule |
| Berthing_Attd_3D | mech_ac | era_rule |
| Berthing_Gal | mech_ac | era_rule |
| Boiler_Room_1 | nat_supply | sheet_read |
| Boiler_Room_2 | mech_supply_exhaust | era_rule |
| Boiler_Room_3 | mech_supply_exhaust | era_rule |
| Comms_Foc | mech_ac | era_rule |
| Crew_Berthing_2D_Aft | mech_ac | era_rule |
| Crew_Berthing_2D_Fwd | mech_ac | era_rule |
| Crew_Berthing_2D_Mid | mech_ac | era_rule |
| Crew_Berthing_3D_Aft | mech_ac | era_rule |
| Crew_Berthing_3D_Fwd | mech_ac | era_rule |
| Crew_Berthing_Foc | nat_supply | sheet_read |
| Crew_Lounge_2D | mech_ac | era_rule |
| Crew_Mess_3D | mech_exhaust | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Forecastle_Deck | nat_supply | era_rule |
| Fuel_Tanks_1P | nat_supply | era_rule |
| Fuel_Tanks_Hold | nat_supply | era_rule |
| Funnel_Uptake | mech_supply_exhaust | era_rule |
| Gallery_Deck | nat_supply | era_rule |
| Galley_3D | mech_exhaust | era_rule |
| Gasoline_Tanks | nat_supply | era_rule |
| HD_2D | exhaust_only | era_rule |
| HD_3D | exhaust_only | era_rule |
| HD_Gallery | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | sheet_read |
| Hangar_Fwd | nat_supply | sheet_read |
| Hangar_Mid | nat_supply | sheet_read |
| Island_Ops | mech_supply_exhaust | sheet_read |
| Machinery_Aft_1P | mech_supply_exhaust | era_rule |
| Machinery_Room_1 | mech_supply_exhaust | era_rule |
| Magazine_1P | mech_ac | era_rule |
| Magazines_Hold | mech_ac | era_rule |
| Marine_Berthing_2D | mech_ac | era_rule |
| Nav_Bridge | mech_ac | era_rule |
| Officers_Country_Main | mech_ac | era_rule |
| Ordnance_2D | mech_ac | era_rule |
| Ordnance_2P | mech_ac | era_rule |
| Ordnance_4D | mech_ac | era_rule |
| Ordnance_Gal | mech_ac | era_rule |
| Provisions_4D | mech_ac | era_rule |
| Pumps_2P | mech_supply_exhaust | era_rule |
| Repair_Party_Main | mech_ac | era_rule |
| Services_4D | mech_ac | era_rule |
| Shaft_Alley_2P | mech_supply_exhaust | era_rule |
| Shops_Foc | mech_ac | era_rule |
| Sick_Bay_2D | mech_ac | era_rule |
| Side_Shops_Main | mech_ac | era_rule |
| Squad_Ready_2D | mech_ac | era_rule |
| Squadron_Offices | nat_supply | sheet_read |
| Steering_Gear_2P | mech_supply_exhaust | era_rule |
| Stern_Hold | nat_supply | era_rule |
| Stores_3D | mech_ac | era_rule |
| Stores_4D | mech_ac | era_rule |
| Tanks_1P | nat_supply | era_rule |
| Tanks_2P | nat_supply | era_rule |
| Tanks_3B | nat_supply | era_rule |
| Uptakes_Foc | mech_supply_exhaust | era_rule |
| Uptakes_Main | mech_supply_exhaust | sheet_read |
| Void_2P | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |
| Workshops_3D | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O.&B. fuel oil + overflow | fuel | Boiler_Room_2 |
| DIESEL OIL B-14F | fuel | Aux_Machinery_Fwd |
| LUB OIL + D.F. TANK | fuel | Boiler_Room_2 |
| SERVICE FUEL OIL B-30F/B-11F | fuel | Pumps_2P |
| GASOLINE + GASOLINE SURROUND C-90xF | unknown | Gasoline_Tanks |
| F.O./S.F.O./CONTAMINATED OIL cells | fuel | Fuel_Tanks_Hold |
| F.O.&B. + VOID inner bottom | fuel | Tanks_3B |

## Plumbing drains

- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- HD_Gallery (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Gallery
- HD_2D (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D
- Sick_Bay_2D (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay_2D
- Crew_Mess_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_3D
- Galley_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_3D
- HD_3D (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3D

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
