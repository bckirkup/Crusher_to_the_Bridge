# Systems inference notes — apl_24

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Diesel_Stack | uptake | up | exhaust | Galley_Bakery | sheet_read |
| Engine_Exhaust_2 | uptake | up | exhaust | Crew_Cafeteria_Mess | sheet_read |
| Galley_Smoke_Pipe | uptake | up | exhaust | Galley_Bakery | sheet_read |
| Boiler_Casing_Vent | uptake | up | exhaust | CPO_Pantry | sheet_read |
| Radio_Trunk | vent_trunk | up | exhaust | Gun_Platforms | sheet_read |
| MH_Main_1 | mushroom | up | exhaust | Galley_Bakery | sheet_read |
| MH_Main_2 | mushroom | up | exhaust | HD_Crew_1 | sheet_read |
| MH_Main_3 | mushroom | up | exhaust | Library | sheet_read |
| MH_Upper_1 | mushroom | up | exhaust | HD_CPO_1 | sheet_read |
| Vent_Crews_Lock | vent_trunk | up | supply | Crews_Locker_Office | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Barber_Shop | nat_supply | era_rule |
| Brig | nat_supply | era_rule |
| CPO_Berthing | nat_supply | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| CPO_Pantry | mech_supply_exhaust | sheet_read |
| Crew_Cafeteria_Mess | mech_supply_exhaust | sheet_read |
| Crew_Quarters | nat_supply | era_rule |
| Crew_Washroom | exhaust_only | era_rule |
| Crews_Locker_Office | nat_supply | sheet_read |
| Dental_Office | mech_supply_exhaust | era_rule |
| Dispensary_Lab | mech_supply_exhaust | era_rule |
| Fantail_Main | nat_supply | era_rule |
| Fantail_Upper | nat_supply | era_rule |
| Forecastle | nat_supply | era_rule |
| Galley_Bakery | mech_supply_exhaust | sheet_read |
| Gun_Platforms | mech_exhaust | sheet_read |
| HD_CPO_1 | exhaust_only | sheet_read |
| HD_CPO_2 | exhaust_only | era_rule |
| HD_Crew_1 | exhaust_only | sheet_read |
| HD_Crew_2 | exhaust_only | era_rule |
| Isolation_Ward | mech_supply_exhaust | era_rule |
| Laundry | nat_supply | era_rule |
| Library | mech_exhaust | sheet_read |
| Officers_Mess_Pantry | mech_exhaust | era_rule |
| Officers_Staterooms | nat_supply | era_rule |
| Post_Office | nat_supply | era_rule |
| Receiving_Rm | nat_supply | era_rule |
| Recreation_Room | nat_supply | era_rule |
| Scullery | nat_supply | era_rule |
| Ships_Office | nat_supply | era_rule |
| Ships_Service | nat_supply | era_rule |
| Ships_Store | nat_supply | era_rule |
| Shower_Room | exhaust_only | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| SEWAGE MACH | sewage | HD_Crew_1 |
| GASOLINE STOWAGE | unknown | Laundry |

## Plumbing drains

- Galley_Bakery (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Crew_Cafeteria_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- HD_Crew_1 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- HD_Crew_2 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Shower_Room (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- HD_CPO_1 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- HD_CPO_2 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Officers_Mess_Pantry (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Isolation_Ward (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Dental_Office (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Dispensary_Lab (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1
- Crew_Washroom (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
