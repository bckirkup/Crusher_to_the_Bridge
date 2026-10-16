# Systems inference notes — erie_pg50

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| STACK | funnel | up | exhaust | Boiler_Room | sheet_read |
| COWL_ENG | cowl | fore | supply | Engine_Room | era_plausible |
| MUSH_BERTH | mushroom | up | supply | Crew_Berthing_Main | era_plausible |
| VENT_GALLEY | vent_trunk | unknown | exhaust | Galley | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AA_Gun_Tub_Top | nat_supply | era_rule |
| Admirals_Quarters | nat_supply | era_rule |
| Aft_Oil_Tanks | nat_supply | era_rule |
| Ammo_Handling_2 | mech_supply_exhaust | era_rule |
| Aux_Machinery_Room | mech_supply_exhaust | era_rule |
| Boat_Skids | nat_supply | era_rule |
| Boat_Stowage_Port | nat_supply | era_rule |
| Boiler_Room | mech_supply_exhaust | sheet_read |
| Clipping_Room_Aft | nat_supply | era_rule |
| Crew_Berthing_Main | nat_supply | era_plausible |
| Crews_Locker_Stores | nat_supply | era_rule |
| Crews_Marine_Berthing | nat_supply | era_rule |
| Crews_Mess | mech_exhaust | era_rule |
| Emergency_Cabin | nat_supply | era_rule |
| Emergency_Radio | nat_supply | era_rule |
| Engine_Room | mech_supply_exhaust | era_plausible |
| FW_Tanks_Fwd | nat_supply | era_rule |
| Fantail_Aft | nat_supply | era_rule |
| Flag_Plot_Bridge | nat_supply | era_rule |
| Focsle_Main | nat_supply | era_rule |
| Focsle_Stores | nat_supply | era_rule |
| Fore_Top | nat_supply | era_rule |
| Fuel_Water_Tanks | nat_supply | era_rule |
| Galley | mech_exhaust | era_plausible |
| Gun_Crew_Shelter_Aft | nat_supply | era_rule |
| Gun_Deck_Aft | nat_supply | era_rule |
| HD_Crew | exhaust_only | era_rule |
| HD_Crew_2nd | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| Hold_Stores_Aft | nat_supply | era_rule |
| Laundry | nat_supply | era_rule |
| Marine_Quarters | nat_supply | era_rule |
| Mess_Attendants | nat_supply | era_rule |
| Motion_Picture_Room | nat_supply | era_rule |
| Navigators_Stores | nat_supply | era_rule |
| Office_Block | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Powder_Magazine | nat_supply | era_rule |
| Provisions_Magazine | nat_supply | era_rule |
| Provisions_Platform | nat_supply | era_rule |
| Pyrotechnic_Magazine | nat_supply | era_rule |
| Reefer_Stores | nat_supply | era_rule |
| Service_Stores | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Stores_Aft_2 | nat_supply | era_rule |
| Sup_Deck_Open | nat_supply | era_rule |
| Tanks_Fwd_Platform | nat_supply | era_rule |
| Uptake_Trunk | mech_supply_exhaust | era_rule |
| WR_Stores_Block | nat_supply | era_rule |
| Wardroom_Mess | mech_exhaust | era_rule |
| Whaleboat_Stowage | nat_supply | era_rule |
| Workshop_Block | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL TANK | fuel | Aft_Oil_Tanks |
| D.O. STORES C-106.A | unknown | Aft_Oil_Tanks |
| FUEL OIL TANK | fuel | Fuel_Water_Tanks |
| RESERVE FEED WATER TANK | freshwater | Shaft_Alley |
| FRESH WATER TANK A-415 | freshwater | Fuel_Water_Tanks |
| FRESH WATER TANK A-414 | freshwater | Crews_Locker_Stores |
| LUBRICATING OIL C.107.GA | fuel | Boiler_Room |
| GASOLINE COMPT K-107 | unknown | Aux_Machinery_Room |

## Plumbing drains

- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Crews_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crews_Mess
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy PG-50 USS Erie, Booklet of General Plans, 1936 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [pg50.pdf](https://maritime.org/doc/plans/pg50.pdf).
