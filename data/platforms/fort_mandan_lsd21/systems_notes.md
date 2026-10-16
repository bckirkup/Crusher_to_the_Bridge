# Systems inference notes — fort_mandan_lsd21

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| v_turbine_1 | mushroom | up | exhaust | Well_Cover_Open | sheet_read |
| v_cowl_fwd | cowl | fore | supply | Forecastle_MD | sheet_read |
| v_well_sponson | gooseneck | up | exhaust | Well_Deck | sheet_read |
| v_uptakes | uptake | up | exhaust | Engine_Room | sheet_read |
| v_signal_mast | vent_trunk | up | exhaust | Comm_Room | era_plausible |
| v_magazines | mushroom | up | supply | Ammunition_3D | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Ammunition_3D | nat_supply | era_plausible |
| Armory_DC_Station | mech_ac | era_rule |
| Army_Officers_MD | mech_ac | era_rule |
| Army_Ranks_Qtrs_SSD | mech_ac | era_rule |
| Ballast_FW_Tanks | nat_supply | era_rule |
| Ballast_Tanks_Port | nat_supply | era_rule |
| Ballast_Tanks_Stbd | nat_supply | era_rule |
| Boatswains_Stores | nat_supply | era_rule |
| Boiler_Aux_Room | mech_supply_exhaust | era_rule |
| Chain_Locker | nat_supply | era_rule |
| Comm_Room | mech_exhaust | era_plausible |
| Crew_Berthing_SSD | mech_ac | era_rule |
| Crew_Mess_SSD | mech_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | sheet_read |
| Engine_Room_Flat | mech_supply_exhaust | era_rule |
| Fore_Peak_Hold | nat_supply | era_rule |
| Forecastle_MD | nat_supply | sheet_read |
| Fuel_Tanks | nat_supply | era_rule |
| Gallery_Port | nat_supply | era_rule |
| Gallery_Stbd | nat_supply | era_rule |
| Galley_SSD | mech_exhaust | era_rule |
| General_Stores_3D | nat_supply | era_rule |
| HD_Army_2D | exhaust_only | era_rule |
| HD_Army_MD_Port | exhaust_only | era_rule |
| HD_Army_MD_Stbd | exhaust_only | era_rule |
| HD_Crew_SSD | exhaust_only | era_rule |
| HD_Officers_MD | exhaust_only | era_rule |
| Ice_Machinery_Rm | mech_supply_exhaust | era_rule |
| Laundry_2D | mech_ac | era_rule |
| Machine_Shop | mech_ac | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Berthing_2D | mech_ac | era_rule |
| Officers_Qtrs_Bridge | mech_ac | era_rule |
| Officers_Qtrs_MD | mech_ac | era_rule |
| Officers_WR_Pantry | mech_ac | era_rule |
| Passage_2D | nat_supply | era_rule |
| Passage_Bridge | nat_supply | era_rule |
| Passage_MD | nat_supply | era_rule |
| Pump_Room_3D | mech_supply_exhaust | era_rule |
| Radar_House | mech_ac | era_rule |
| Shaft_Alley_Port | mech_supply_exhaust | era_rule |
| Shaft_Alley_Stbd | mech_supply_exhaust | era_rule |
| Shipfitters_Flat | mech_ac | era_rule |
| Ships_Office | mech_ac | era_rule |
| Sick_Bay | mech_ac | era_rule |
| Steering_Flat_3D | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Steering_Gear_2D | mech_supply_exhaust | era_rule |
| Top_House_Open | nat_supply | era_rule |
| Well_Cover_Open | mech_exhaust | sheet_read |
| Well_Deck | mech_exhaust | sheet_read |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| BALLAST TANKS (wing, floodable) | unknown | Well_Deck |
| DIESEL OIL STORAGE | fuel | Officers_Qtrs_Bridge |
| F.O. TANK | fuel | HD_Officers_MD |
| MAIN FEED TANK | unknown | General_Stores_3D |
| FRESH WATER | freshwater | Sick_Bay |
| PEAK TANK | unknown | Chain_Locker |

## Plumbing drains

- Crew_Mess_SSD (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_SSD
- Galley_SSD (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_SSD
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Crew_SSD (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_SSD
- HD_Officers_MD (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers_MD
- HD_Army_MD_Port (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Army_MD_Port
- HD_Army_MD_Stbd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Army_MD_Stbd
- HD_Army_2D (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Army_2D

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
