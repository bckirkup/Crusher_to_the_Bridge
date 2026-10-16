# Systems inference notes — bainbridge_dd1

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_1 | funnel | up | exhaust | Boiler_Room_Aft | sheet_read |
| funnel_2 | funnel | up | exhaust | Boiler_Room_Aft | sheet_read |
| funnel_3 | funnel | up | exhaust | Boiler_Room_Fwd | sheet_read |
| funnel_4 | funnel | up | exhaust | Boiler_Room_Fwd | sheet_read |
| cowl_crew | cowl | fore | supply | Crew_Quarters | era_plausible |
| cowl_aft | cowl | fore | supply | Officers_Country | era_plausible |
| galley_vent | gooseneck | up | exhaust | Galley_Mess_Deckhouse | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Berthing_Fwd | nat_supply | era_rule |
| Boiler_Room_Aft | mech_supply_exhaust | sheet_read |
| Boiler_Room_Fwd | mech_supply_exhaust | sheet_read |
| Chain_Hawse | nat_supply | era_rule |
| Chain_Locker_Plat | nat_supply | era_rule |
| Coal_Bunker_B3 | nat_supply | era_rule |
| Coal_Bunker_B5 | nat_supply | era_rule |
| Coal_Bunker_Hold_Aft | nat_supply | era_rule |
| Coal_Bunker_Hold_Fwd | nat_supply | era_rule |
| Crew_Quarters | nat_supply | era_plausible |
| Crew_WC | exhaust_only | era_rule |
| Engine_Rooms | mech_supply_exhaust | era_rule |
| Engineer_Stores | nat_supply | era_rule |
| Fore_Peak_A1 | nat_supply | era_rule |
| Galley_Mess_Deckhouse | mech_exhaust | era_plausible |
| Hold_Fwd_Peak | nat_supply | era_rule |
| Machinery_Lwr | mech_supply_exhaust | era_rule |
| Medical_Electrical_Stores | nat_supply | era_rule |
| Officers_Country | nat_supply | era_plausible |
| Officers_Mess_Dh | mech_exhaust | era_rule |
| Ordnance_Stores | nat_supply | era_rule |
| Paint_Oil_Stores | nat_supply | era_rule |
| Pilot_Chart_House | nat_supply | era_rule |
| Shell_Room | nat_supply | era_rule |
| Steering_Gear | nat_supply | era_rule |
| Stores_Hold_Fwd | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FRESH WATER 500 GALS | freshwater | Engineer_Stores |
| FRESH WATER 400 GALS | freshwater | Engineer_Stores |
| FEED TANK (fire room) | unknown | Boiler_Room_Aft |
| COAL BUNKERS (wing, berth deck) | unknown | Coal_Bunker_B3 |
| TRIM TANKS (double bottom) | unknown | Stores_Hold_Fwd |

## Plumbing drains

- Officers_Mess_Dh (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Mess_Dh
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Crew_WC (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_WC

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy DD-1 USS Bainbridge, Booklet of General Plans, 1901 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [dd1.pdf](https://maritime.org/doc/plans/dd1.pdf).
