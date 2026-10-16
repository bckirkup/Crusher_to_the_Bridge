# Systems inference notes — esteem_mso438

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| STACK | funnel | up | exhaust | Uptake_Trunk | sheet_read |
| FANRM_01 | fan_room | unknown | supply | Radio_Room | sheet_read |
| FANRM_MAIN | fan_room | unknown | supply | Deck_House_Main | sheet_read |
| VENT_MESS | vent_trunk | unknown | exhaust | Wardroom_Mess | sheet_read |
| MUSH_FWD | mushroom | up | supply | Stores_Fwd | era_plausible |
| MUSH_ENG | cowl | fore | supply | Fwd_Machinery_Room | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| After_Machinery_Room | mech_supply_exhaust | era_rule |
| Boat_Deck_Aft | nat_supply | era_rule |
| CPO_Quarters | mech_ac | era_rule |
| Captains_Cabin | mech_ac | era_rule |
| Chart_Room | nat_supply | era_rule |
| Chem_Canvas_Stores | nat_supply | era_rule |
| Crew_Berthing | mech_ac | era_rule |
| Crew_Berthing_2 | mech_ac | era_rule |
| Crews_Mess | mech_exhaust | era_rule |
| Crews_Shelter | mech_ac | era_rule |
| Deck_House_Main | mech_supply_exhaust | sheet_read |
| FW_Chain_Fwd | nat_supply | era_rule |
| Focsle_01 | nat_supply | era_rule |
| Focsle_Store | nat_supply | era_rule |
| Fuel_Tanks_Aft | nat_supply | era_rule |
| Fuel_Tanks_Fwd | nat_supply | era_rule |
| Fwd_Machinery_Room | mech_supply_exhaust | era_plausible |
| Galley | mech_exhaust | era_rule |
| HD_CPO | exhaust_only | era_rule |
| HD_Crew | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| Hold_Stores | nat_supply | era_rule |
| Laundry | nat_supply | era_rule |
| Officers_Country | mech_ac | era_rule |
| Pharmacy | mech_ac | era_rule |
| Pilot_House | nat_supply | era_rule |
| Radio_Room | mech_supply_exhaust | sheet_read |
| Reel_Deck | nat_supply | era_rule |
| Reel_Well | mech_supply_exhaust | era_rule |
| Sonar_Room | mech_supply_exhaust | era_rule |
| Steering_Flat | mech_supply_exhaust | era_rule |
| Stores_01 | nat_supply | era_rule |
| Stores_Fwd | nat_supply | era_plausible |
| Stores_Fwd_Platform | nat_supply | era_rule |
| Sweep_Deck | nat_supply | era_rule |
| Uptake_Trunk | mech_supply_exhaust | sheet_read |
| Wardroom_Mess | mech_exhaust | sheet_read |
| Windlass_Room | mech_supply_exhaust | era_rule |
| Workshop | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| DIESEL OIL TANK 3-68-0-F | fuel | Fuel_Tanks_Aft |
| D.O. TANK COMPT 3-67 | unknown | Chem_Canvas_Stores |
| DIESEL OIL TANK 3-27-2-F | fuel | Fuel_Tanks_Fwd |
| DIESEL OIL TANK 3-27-1-F | fuel | Fuel_Tanks_Fwd |
| D.O. TANK COMPT 3-26-0-F | unknown | Fuel_Tanks_Fwd |
| F.W. TANK 3-13-2-W | freshwater | Sonar_Room |
| F.W. TANK 3-18-1-W | freshwater | FW_Chain_Fwd |
| L.O. STORAGE TANK | unknown | After_Machinery_Room |
| D.O. SERVICE TANK | unknown | Fwd_Machinery_Room |
| F.O. SERVICE TANK | fuel | Steering_Flat |

## Plumbing drains

- Pharmacy (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Pharmacy
- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Crews_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crews_Mess
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew
- HD_CPO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
