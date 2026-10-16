# Systems inference notes — thetis_bay_cve90

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_island | funnel | up | exhaust | Funnel_Island | sheet_read |
| uptake_gal | uptake | up | exhaust | Island_Offices_Gal | sheet_read |
| hangar_side_port | hangar_door | port | supply | Hangar_Aft | sheet_read |
| hangar_side_stbd | hangar_door | starboard | supply | Hangar_Fwd | sheet_read |
| cowls_bow | cowl | fore | supply | Bow_Block_Upper | era_plausible |
| mag_vents_fwd | mushroom | up | exhaust | Ammo_Fwd_1P | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Engine_Rm | mech_supply_exhaust | era_rule |
| Ammo_Fwd_1P | mech_exhaust | era_plausible |
| Ammo_Fwd_TT | nat_supply | era_rule |
| Avgas_IB | nat_supply | era_rule |
| Aviation_Berthing_2D | nat_supply | era_rule |
| Battery_AC_Gal | mech_supply_exhaust | era_rule |
| Berthing_15th_1P | nat_supply | era_rule |
| Boiler_Rm | mech_supply_exhaust | era_rule |
| Bomb_Storage_TT | nat_supply | era_rule |
| Bow_Block_Upper | nat_supply | era_plausible |
| Bow_Rooms_Hangar | nat_supply | era_rule |
| CPO_Berthing_2D | nat_supply | era_rule |
| CPO_Mess_2D | mech_exhaust | era_rule |
| CPO_Quarters_Gal | nat_supply | era_rule |
| Carpenter_Shop_2D | nat_supply | era_rule |
| Crew_Berthing_Aft_1P | nat_supply | era_rule |
| Crew_Berthing_Aft_2D | nat_supply | era_rule |
| Crew_Berthing_Fwd_1P | nat_supply | era_rule |
| Crew_Berthing_Mid_2D | nat_supply | era_rule |
| Crew_Mess_2D | mech_exhaust | era_rule |
| Elec_Spare_2D | nat_supply | era_rule |
| FO_Tanks_Aft_IB | nat_supply | era_rule |
| FO_Tanks_Fwd_IB | nat_supply | era_rule |
| FO_Tanks_Mid_IB | nat_supply | era_rule |
| FW_Tanks_IB | nat_supply | era_rule |
| FW_Tanks_Mid_IB | nat_supply | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Funnel_Island | mech_supply_exhaust | sheet_read |
| Fwd_Engine_Rm | mech_supply_exhaust | era_rule |
| Galley_2D | mech_exhaust | era_rule |
| Generator_1P | mech_supply_exhaust | era_rule |
| Generator_Rm | mech_supply_exhaust | era_rule |
| Gun_5in_Sponson | nat_supply | era_rule |
| HD_2D_Aft | exhaust_only | era_rule |
| HD_2D_Fwd | exhaust_only | era_rule |
| HD_Gal_Aft | exhaust_only | era_rule |
| HD_Gal_Fwd | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | sheet_read |
| Hangar_Fwd | nat_supply | sheet_read |
| Hangar_Shops_Port | nat_supply | era_rule |
| Hangar_Shops_Stbd | nat_supply | era_rule |
| Hospital_Gal | mech_supply_exhaust | era_rule |
| Island_Offices_Gal | mech_supply_exhaust | sheet_read |
| Island_Upper | nat_supply | era_rule |
| Issue_Rm_1P | nat_supply | era_rule |
| Laundry_2D | nat_supply | era_rule |
| Machinery_Flat_Aft | mech_supply_exhaust | era_rule |
| Machinery_Flat_Fwd | mech_supply_exhaust | era_rule |
| Maintenance_2D | nat_supply | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Quarters_Gal | nat_supply | era_rule |
| Ordnance_Bow_2D | nat_supply | era_rule |
| Ordnance_Gal | nat_supply | era_rule |
| Ordnance_TT | nat_supply | era_rule |
| Paint_Alcohol_TT | nat_supply | era_rule |
| Peak_Tank_Fwd | nat_supply | era_rule |
| Provision_1P | nat_supply | era_rule |
| Radio_Radar_Gal | nat_supply | era_rule |
| SD_Stores_TT | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay_2D | mech_supply_exhaust | era_rule |
| Steering_Gear_1P | mech_supply_exhaust | era_rule |
| Stores_TT_Fwd | nat_supply | era_rule |
| Upper_Flats_Aft | nat_supply | era_rule |
| Upper_Flats_Fwd | nat_supply | era_rule |
| Upper_Mezz | nat_supply | era_rule |
| Veg_Reefer_1P | nat_supply | era_rule |
| Void_TT_Aft | nat_supply | era_rule |
| Void_Tank_Aft | nat_supply | era_rule |
| WT_Rm_Hangar | nat_supply | era_rule |
| Walkway_Gal_Port | nat_supply | era_rule |
| Walkway_Gal_Stbd | nat_supply | era_rule |
| Ward_Room_Gal | mech_exhaust | era_rule |
| Warrant_Qtrs_2D | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| VOID TANK | unknown | Void_Tank_Aft |
| F.O. TANK | fuel | FO_Tanks_Aft_IB |
| F.W. TANKS #1-4 | freshwater | FW_Tanks_IB |
| F.O. TANKS | fuel | FO_Tanks_Mid_IB |
| DIESEL OIL B-905-F | fuel | FW_Tanks_Mid_IB |
| F.W. TANKS #5-8 | freshwater | FW_Tanks_Mid_IB |
| AVIATION GAS | unknown | Avgas_IB |
| F.O. OR F.W. BALLAST | freshwater | Void_TT_Aft |
| L.O. STORAGE | unknown | Generator_Rm |

## Plumbing drains

- HD_Gal_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Gal_Aft
- Ward_Room_Gal (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Ward_Room_Gal
- Hospital_Gal (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Hospital_Gal
- HD_Gal_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Gal_Fwd
- Crew_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2D
- Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_2D
- HD_2D_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Aft
- CPO_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess_2D
- HD_2D_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Fwd
- Sick_Bay_2D (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay_2D

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
