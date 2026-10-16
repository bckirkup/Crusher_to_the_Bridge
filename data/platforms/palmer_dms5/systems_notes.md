# Systems inference notes — palmer_dms5

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_1 | funnel | up | exhaust | Boiler_Room_1 | era_plausible |
| funnel_2 | funnel | up | exhaust | Boiler_Room_2 | era_plausible |
| blower_machinery | fan_room | unknown | supply | Engine_Room | era_plausible |
| galley_vent | gooseneck | up | exhaust | Galley | sheet_read |
| cowl_fwd | cowl | fore | supply | Crew_Mess | era_plausible |
| cowl_aft | cowl | fore | supply | Crew_Berthing_Aft | era_plausible |
| mag_vent_aft | mushroom | up | exhaust | Magazine_Aft | era_plausible |
| mag_vent_fwd | mushroom | up | exhaust | Magazine_Fwd | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Ammo_Stowage_Aft | nat_supply | era_rule |
| Battery_Locker | nat_supply | era_rule |
| Berthing_Mid | nat_supply | era_rule |
| Boat_Deck_Uptakes | nat_supply | era_rule |
| Boiler_Room_1 | mech_supply_exhaust | era_plausible |
| Boiler_Room_2 | mech_supply_exhaust | era_plausible |
| CPO_Berthing_Main | nat_supply | era_rule |
| Chart_House | nat_supply | era_rule |
| Crew_Berthing_Aft | nat_supply | era_plausible |
| Crew_Berthing_Aft_2 | nat_supply | era_rule |
| Crew_Berthing_Fwd_1 | nat_supply | era_rule |
| Crew_Berthing_Fwd_2 | nat_supply | era_rule |
| Crew_Head | exhaust_only | era_rule |
| Crew_Mess | nat_supply | era_plausible |
| Crew_Stores_Hold | nat_supply | era_rule |
| Crew_Wash_Room | exhaust_only | era_rule |
| Engine_Room | mech_supply_exhaust | era_plausible |
| Engineering_Office | nat_supply | era_rule |
| Focsle_Chain | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Galley | mech_exhaust | sheet_read |
| Machinery_2P | nat_supply | era_rule |
| Magazine_Aft | mech_exhaust | era_plausible |
| Magazine_Fwd | mech_exhaust | era_plausible |
| Officers_Cabins | nat_supply | era_rule |
| Paravane_Handling | nat_supply | era_rule |
| Paravane_Smoke_Stow | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Radio_Room | nat_supply | era_rule |
| Ship_Fitters_Shop | nat_supply | era_rule |
| Sound_Compt | nat_supply | era_rule |
| Sound_Room_Bridge | nat_supply | era_rule |
| Store_1P_Aft | nat_supply | era_rule |
| Store_2P | nat_supply | era_rule |
| Store_Aft | nat_supply | era_rule |
| Stores_Hold_Fwd | nat_supply | era_rule |
| Vegetable_Lockers | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |
| Winch_Room | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL TANKS (midships double bottoms) | fuel | Boiler_Room_2 |
| F.O. STOWAGE | fuel | Stores_Hold_Fwd |
| RESERVE FEED WATER | freshwater | Crew_Stores_Hold |
| FORE PEAK TANK | unknown | Magazine_Fwd |

## Plumbing drains

- Crew_Wash_Room (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Wash_Room
- Crew_Head (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Head
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy DMS-5 USS Palmer (Dorsey class highspeed minesweeper), Booklet of General Plans, 1943 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [dms5.pdf](https://maritime.org/doc/plans/dms5.pdf).
