# Systems inference notes — gordon_gunter_r338

Era: **NOAA / research vessel practice** (`noaa_research`)

Hotel spaces AC; laboratories fume-biased exhaust; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Main_Gen_Rm | sheet_read |
| AC_Mchry_Intake | fan_room | unknown | supply | AC_Mchry | sheet_read |
| Vent_Sewage | vent_trunk | up | exhaust | Sewage_Mchry | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Mchry | mech_supply_exhaust | sheet_read |
| Aft_Working_Deck | nat_supply | era_rule |
| Boat_Deck | nat_supply | era_rule |
| Bosn_Workshop | mech_supply_exhaust | era_rule |
| Crew_Lounge | nat_supply | era_rule |
| Crew_SR_Foc | mech_ac | era_rule |
| Crew_SR_Main | mech_ac | era_rule |
| Emer_Gen_Rm | mech_supply_exhaust | era_rule |
| Exercise_Rm | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Genl_Mess | mech_exhaust | era_rule |
| Genl_Workshop | mech_supply_exhaust | era_rule |
| HD_Bridge | exhaust_only | era_rule |
| HD_Focsle | exhaust_only | era_rule |
| HD_Main | exhaust_only | era_rule |
| HD_Upper | exhaust_only | era_rule |
| Laundry | nat_supply | era_rule |
| Main_Gen_Rm | mech_supply_exhaust | sheet_read |
| Med_Trtmt | mech_ac | era_rule |
| Mission_Deck | nat_supply | era_rule |
| Officer_SR | mech_ac | era_rule |
| Passage_Main | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Prov_Reefers | nat_supply | era_rule |
| Prpln_Motor | mech_supply_exhaust | era_rule |
| Recreation | nat_supply | era_rule |
| Science_Labs | nat_supply | era_rule |
| Scientist_SR | mech_ac | era_rule |
| Sewage_Mchry | mech_supply_exhaust | era_plausible |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Shelter_Deck | nat_supply | era_rule |
| Ships_Office | nat_supply | era_rule |
| Ships_Store | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Wet_Lab | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. TANK | freshwater | Shaft_Alley |
| SEWAGE HOLDING | sewage | Main_Gen_Rm |
| F.O. TANK | fuel | Main_Gen_Rm |

## Plumbing drains

- HD_Bridge (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- HD_Upper (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- HD_Focsle (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- Genl_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- Med_Trtmt (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm
- HD_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Main_Gen_Rm

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
