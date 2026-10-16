# Systems inference notes — savannah_ns

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| VM_gooseneck_fwd | gooseneck | fore | supply | Bosun_Stores_A | sheet_read |
| VM_masthouse_skylight | skylight | unknown | supply | Fwd_Deck_Promenade | sheet_read |
| VM_funnel_sav | funnel | unknown | exhaust | Funnel_Casing | sheet_read |
| VM_hold_supply | cowl | fore | supply | Holds_Fwd_A | era_plausible |
| VM_er_exhaust | air_shaft | unknown | exhaust | Engine_Room | era_plausible |
| VM_reactor_vent | air_shaft | unknown | exhaust | Reactor_Containment | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| A_Deck_Lobby | mech_ac | era_rule |
| Aft_Peak_D | mech_ac | era_rule |
| Aux_Machinery_D | mech_supply_exhaust | era_rule |
| Aux_Machinery_Flat | mech_supply_exhaust | era_rule |
| Bakery_Scullery | mech_ac | era_rule |
| Boat_Cabins | mech_ac | era_rule |
| Boat_Deck_Aft | nat_supply | era_rule |
| Boat_Deck_Fwd | nat_supply | era_rule |
| Bosun_Stores_A | nat_supply | sheet_read |
| Bosun_Stores_C | mech_ac | era_rule |
| Bridge_Wings | nat_supply | era_rule |
| Carpenter_Elec_Shops | mech_ac | era_rule |
| Chart_Radio_NB | mech_ac | era_rule |
| Crew_Cabins_C_Port | mech_ac | era_rule |
| Crew_Cabins_C_Stbd | mech_ac | era_rule |
| Crew_Mess_B | mech_exhaust | era_rule |
| Crew_Mess_C | mech_exhaust | era_rule |
| Crew_Stores_C | mech_ac | era_rule |
| Deep_Tank_Fwd | mech_ac | era_rule |
| Dining_Saloon | mech_exhaust | era_rule |
| Docking_Bridge_Aft | nat_supply | era_rule |
| Emergency_Gen_Rm | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_plausible |
| Fantail_Aft | nat_supply | era_rule |
| Fore_Peak_Tank | mech_ac | era_rule |
| Forecastle_A | nat_supply | era_rule |
| Funnel_Casing | mech_supply_exhaust | sheet_read |
| Fwd_Deck_Promenade | nat_supply | sheet_read |
| Galley_A | mech_exhaust | era_rule |
| Galley_B | mech_exhaust | era_rule |
| HD_B_Deck | exhaust_only | era_rule |
| HD_Boat_Deck | exhaust_only | era_rule |
| HD_C_Deck | exhaust_only | era_rule |
| HD_Promenade | exhaust_only | era_rule |
| Hold_Bottom_Aft | nat_supply | era_rule |
| Hold_Bottom_Fwd | nat_supply | era_rule |
| Holds_Aft_A | nat_supply | era_rule |
| Holds_Aft_B | nat_supply | era_rule |
| Holds_Aft_C | nat_supply | era_rule |
| Holds_Aft_D | nat_supply | era_rule |
| Holds_Fwd_A | nat_supply | era_plausible |
| Holds_Fwd_B | nat_supply | era_rule |
| Holds_Fwd_C | nat_supply | era_rule |
| Holds_Fwd_D | nat_supply | era_rule |
| Lounge_Fwd | mech_ac | era_rule |
| Machinery_Bottom | mech_supply_exhaust | era_rule |
| Machinery_Casing_A | mech_supply_exhaust | era_rule |
| Machinery_Casing_B | mech_supply_exhaust | era_rule |
| Machinery_Casing_P | mech_supply_exhaust | era_rule |
| Machinery_Space_C | mech_supply_exhaust | era_rule |
| Pax_Cabins_A_Port | mech_ac | era_rule |
| Pax_Cabins_A_Stbd | mech_ac | era_rule |
| Pax_Cabins_B_Port | mech_ac | era_rule |
| Pax_Cabins_B_Stbd | mech_ac | era_rule |
| Promenade_Aft_Open | nat_supply | era_rule |
| Promenade_House | mech_ac | era_rule |
| Promenade_Walkway_Port | nat_supply | era_rule |
| Promenade_Walkway_Stbd | nat_supply | era_rule |
| Radiation_Sampling | mech_ac | era_rule |
| Reactor_Containment | mech_supply_exhaust | era_plausible |
| Reactor_Control_Rm | mech_supply_exhaust | era_rule |
| Reactor_Space_A | mech_supply_exhaust | era_rule |
| Reactor_Space_C | mech_supply_exhaust | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Steering_Gear_B | mech_supply_exhaust | era_rule |
| Stevedores_Toilet | exhaust_only | era_rule |
| Swimming_Pool | nat_supply | era_rule |
| Top_Of_House | nat_supply | era_rule |
| Verandah_Lounge | mech_exhaust | era_rule |
| Weather_Deck_Port_A | nat_supply | era_rule |
| Weather_Deck_Stbd_A | nat_supply | era_rule |
| Wheelhouse | nat_supply | era_rule |
| Windlass_Room_B | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FORE PEAK TANK | unknown | Fore_Peak_Tank |
| DEEP TANK N1 SW BALLAST | unknown | Fore_Peak_Tank |
| AFT PEAK | unknown | Aft_Peak_D |
| DEEP TANK | unknown | Fore_Peak_Tank |

## Plumbing drains

- Verandah_Lounge (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Verandah_Lounge
- HD_Promenade (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Promenade
- HD_Boat_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Boat_Deck
- Galley_A (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_A
- Stevedores_Toilet (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Stevedores_Toilet
- Dining_Saloon (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Dining_Saloon
- Galley_B (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_B
- Crew_Mess_B (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_B
- HD_B_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_B_Deck
- Crew_Mess_C (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_C
- HD_C_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_C_Deck

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
