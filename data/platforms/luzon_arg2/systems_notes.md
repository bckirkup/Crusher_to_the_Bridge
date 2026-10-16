# Systems inference notes — luzon_arg2

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Eng_Casing_Main | sheet_read |
| Fan_Rm_Sup_Vent | mushroom | up | supply | Sup_Structure_House | sheet_read |
| Fan_Rm_Aft | mushroom | up | supply | CPO_Berthing_Main | sheet_read |
| Fan_Rm_Fwd | mushroom | up | supply | Clipping_20mm_Fwd | sheet_read |
| Gooseneck_ER | gooseneck | down | supply | Engine_Room | era_plausible |
| Shop_Vents_2nd | mushroom | up | exhaust | Weld_Shop_2nd | era_plausible |
| Cowl_Focsle | cowl | fore | supply | Chain_Locker_Focsle | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Room | mech_supply_exhaust | era_rule |
| Aft_DO_Tanks_2P | mech_supply_exhaust | era_rule |
| Aft_Peak_Hold | mech_supply_exhaust | era_rule |
| Aft_Peak_Stores_2nd | nat_supply | era_rule |
| Aft_Tanks_1P | mech_supply_exhaust | era_rule |
| Amm_Mags_2nd | nat_supply | era_rule |
| Bakery_2nd | nat_supply | era_rule |
| Boat_Deck_Aft | nat_supply | era_rule |
| CPO_Berthing_Fwd | nat_supply | era_rule |
| CPO_Berthing_Main | nat_supply | sheet_read |
| CPO_Pantry_Mess | mech_exhaust | era_rule |
| CPO_Stores_2nd | nat_supply | era_rule |
| Canvas_Store | nat_supply | era_rule |
| Cargo_DO_Hold_A | mech_supply_exhaust | era_rule |
| Cargo_DO_Hold_F | mech_supply_exhaust | era_rule |
| Cargo_DO_Tanks_2P | mech_supply_exhaust | era_rule |
| Carpenter_Radio_Shops | nat_supply | era_rule |
| Chain_Locker_Focsle | nat_supply | era_plausible |
| Clipping_20mm_Fwd | nat_supply | sheet_read |
| Crews_Berthing_2nd_A | nat_supply | era_rule |
| Crews_Berthing_2nd_F | nat_supply | era_rule |
| Crews_Berthing_Aft | nat_supply | era_rule |
| Crews_Berthing_Fwd | nat_supply | era_rule |
| Crews_Galley | mech_exhaust | era_rule |
| Crews_Mess | mech_exhaust | era_rule |
| Deep_Tank_2P | mech_supply_exhaust | era_rule |
| Deep_Tank_Hold | mech_supply_exhaust | era_rule |
| Diesel_Stores_2nd | nat_supply | era_rule |
| Electrical_Shop | nat_supply | era_rule |
| Electrical_Stowage_1P | nat_supply | era_rule |
| Eng_Boiler_Casing_2nd | mech_supply_exhaust | era_rule |
| Eng_Casing_Main | mech_supply_exhaust | sheet_read |
| Engine_Room | mech_supply_exhaust | era_plausible |
| Engineers_Office | nat_supply | era_rule |
| Flat_Chain_Locker | nat_supply | era_rule |
| Forepeak_Tank_2nd | mech_supply_exhaust | era_rule |
| Fwd_Mags_1P | nat_supply | era_rule |
| Fwd_Peak_1P | nat_supply | era_rule |
| Fwd_Stores_2P | nat_supply | era_rule |
| Galley_Upper | mech_exhaust | era_rule |
| Gen_Evap_Rm | mech_supply_exhaust | era_rule |
| Gun_Weather_Sup | nat_supply | era_rule |
| HD_Crew_2nd | exhaust_only | era_rule |
| HD_Crew_Main | exhaust_only | era_rule |
| HD_Sup | exhaust_only | era_rule |
| HD_Upper_Deck | exhaust_only | era_rule |
| ICE_Repair_Shop | nat_supply | era_rule |
| Laundry_Rec_Rm | nat_supply | era_rule |
| Lobby_Fwd | nat_supply | era_rule |
| Lumber_Stowage_2P | nat_supply | era_rule |
| Machine_Shop_1P | nat_supply | era_rule |
| Machinery_Bilge_Hold | mech_supply_exhaust | era_rule |
| Machinery_Lower_2P | mech_supply_exhaust | era_rule |
| Officer_State_Rms | nat_supply | era_rule |
| Officers_Mess_Lounge | mech_exhaust | era_rule |
| Pilot_House | nat_supply | era_rule |
| Post_Office | nat_supply | era_rule |
| Pump_Filter_Rms | mech_supply_exhaust | era_rule |
| Refrigerator_2nd | nat_supply | era_rule |
| Repair_Stores_1P | nat_supply | era_rule |
| Settling_Lub_Tanks | mech_supply_exhaust | era_rule |
| Ships_Store_2nd | nat_supply | era_rule |
| Signal_Flag_Room | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stern_Peak_1P | nat_supply | era_rule |
| Stern_Weather | nat_supply | era_rule |
| Sup_Structure_House | nat_supply | sheet_read |
| Surgical_Dressing | mech_supply_exhaust | era_rule |
| Weld_Shop_2nd | mech_supply_exhaust | era_plausible |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| DIESEL OIL SETTLING TANK | fuel | Settling_Lub_Tanks |
| LUB. OIL TANK P&S | fuel | Settling_Lub_Tanks |
| CARGO DIESEL OIL OR WATER BALLAST (aft cells) | fuel | Cargo_DO_Hold_A |
| CARGO DIESEL OIL OR WATER BALLAST (fwd cells) | fuel | Cargo_DO_Hold_F |
| D.P.&S DIESEL OIL W738 BBLS | fuel | Eng_Boiler_Casing_2nd |
| FORE PEAK TANK POTABLE WATER 141 TONS | freshwater | Forepeak_Tank_2nd |
| AFT PEAK TANK PORTABLE WATER | unknown | Aft_Peak_Stores_2nd |

## Plumbing drains

- HD_Sup (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Sup
- Officers_Mess_Lounge (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Mess_Lounge
- Galley_Upper (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Upper
- HD_Upper_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Upper_Deck
- Crews_Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crews_Galley
- Crews_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crews_Mess
- CPO_Pantry_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Pantry_Mess
- Surgical_Dressing (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Surgical_Dressing
- HD_Crew_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Main
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy ARG-2 USS Luzon, Booklet of General Plans, 1943 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [arg2.pdf](https://maritime.org/doc/plans/arg2.pdf).
