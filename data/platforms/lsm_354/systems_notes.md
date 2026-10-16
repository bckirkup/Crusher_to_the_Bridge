# Systems inference notes — lsm_354

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Smoke_Pipe | uptake | unknown | exhaust | Radar_Radio_Chart | sheet_read |
| Vents_TankWell | mushroom | unknown | supply | Tank_Well | sheet_read |
| Funnel | funnel | unknown | exhaust | Weather_Fwd_Super | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aux_Machinery_Hold | mech_supply_exhaust | era_rule |
| Aux_Machinery_Main | mech_supply_exhaust | era_rule |
| Ballast_Tanks_Hold | nat_supply | era_rule |
| Bosun_Chain_Fwd | mech_supply_exhaust | era_rule |
| Bosuns_Stores | nat_supply | era_rule |
| Bow_Door_Mach | mech_supply_exhaust | era_rule |
| Bow_Ramp_Area | nat_supply | era_rule |
| Bridge_Wings | nat_supply | era_rule |
| Canteen_Stores | nat_supply | era_rule |
| Conning_Station | nat_supply | era_rule |
| Crew_Berthing_Hold | nat_supply | era_rule |
| Crew_Mess_Hold | mech_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| Engineers_Stores | nat_supply | era_rule |
| Forecastle_Weather | nat_supply | era_rule |
| Galley_Hold | mech_exhaust | era_rule |
| Galley_Stores_Main | nat_supply | era_rule |
| General_Work_Shop | nat_supply | era_rule |
| Gunners_Ordnance | nat_supply | era_rule |
| HD_Crew_Hold | exhaust_only | era_rule |
| HD_Troop_Hold | exhaust_only | era_rule |
| Magazine_Hold | nat_supply | era_rule |
| Passage_Stbd_Fwd | nat_supply | era_rule |
| Radar_Radio_Chart | mech_supply_exhaust | sheet_read |
| Ramp_Gate_Mach | mech_supply_exhaust | era_rule |
| Ships_Office | nat_supply | era_rule |
| Signal_Bridge | nat_supply | era_rule |
| Steering_Gear_Flat | mech_supply_exhaust | era_rule |
| Stern_Rooms_Main | nat_supply | era_rule |
| Tank_Well | nat_supply | sheet_read |
| Troop_Berthing_Hold | nat_supply | era_rule |
| Troop_Mess_Hold | mech_exhaust | era_rule |
| Void_Forepeak | nat_supply | era_rule |
| WC_Space_Fwd | exhaust_only | era_rule |
| WT_Room_Services | nat_supply | era_rule |
| Washroom_Main | exhaust_only | era_rule |
| Weather_Aft_Super | nat_supply | era_rule |
| Weather_Fwd_Super | mech_supply_exhaust | era_plausible |
| Wheel_House | nat_supply | era_rule |
| Windlass_Mach_Rm | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| BALLAST TANK | unknown | Ballast_Tanks_Hold |
| D.O. SETTLING TANK | unknown | Troop_Berthing_Hold |
| POTABLE H2O | freshwater | Aux_Machinery_Main |

## Plumbing drains

- Washroom_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Washroom_Main
- WC_Space_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: WC_Space_Fwd
- Crew_Mess_Hold (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_Hold
- HD_Crew_Hold (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Hold
- Troop_Mess_Hold (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Troop_Mess_Hold
- HD_Troop_Hold (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_Hold
- Galley_Hold (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Hold

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy LSM-354 (LSM-1 class), Booklet of General Plans, 1944 (incomplete) — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [lsm354.pdf](https://maritime.org/doc/plans/lsm354.pdf).
