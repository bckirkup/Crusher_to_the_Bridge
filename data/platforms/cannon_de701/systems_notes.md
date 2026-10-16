# Systems inference notes — cannon_de701

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Engine_Rm | sheet_read |
| Cowl_Focsle | cowl | fore | supply | Focsle_Deck | sheet_read |
| Vent_Fantail | vent_trunk | unknown | unknown | Aft_Stores | sheet_read |
| Gooseneck_Eng | gooseneck | down | supply | Fire_Rm_Fwd | era_plausible |
| Mushroom_Mess | mushroom | fore | supply | Mess_Hall | era_plausible |
| Mag_Vent_Aft | mushroom | unknown | unknown | Magazines_Aft | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Berthing_1P | nat_supply | era_rule |
| Aft_Stores | nat_supply | sheet_read |
| Armory_Offices | nat_supply | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Chain_Locker | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_Mid | nat_supply | era_rule |
| Engine_Rm | mech_supply_exhaust | sheet_read |
| Fantail | nat_supply | era_rule |
| Fire_Rm_Aft | mech_supply_exhaust | era_rule |
| Fire_Rm_Fwd | mech_supply_exhaust | era_plausible |
| Focsle_Deck | nat_supply | sheet_read |
| Fuel_Tanks | nat_supply | era_rule |
| Fwd_Hold | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Gun_Deck_Open | nat_supply | era_rule |
| HD_Crew | exhaust_only | era_rule |
| Island_Open_Aft | nat_supply | era_rule |
| Magazines_Aft | nat_supply | era_plausible |
| Magazines_Fwd | nat_supply | era_rule |
| Mess_Hall | nat_supply | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Qtrs | nat_supply | era_rule |
| Passage_Main | nat_supply | era_rule |
| Radio_Rm | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Deck | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stores_2P | nat_supply | era_rule |
| Upper_Machinery | mech_supply_exhaust | era_rule |
| Wardroom | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANK | fuel | Fuel_Tanks |
| F.W. TANK | freshwater | Fwd_Hold |

## Plumbing drains

- Mess_Hall (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Mess_Hall
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy DE-701 USS Osmus (Buckley class), Booklet of General Plans, 1958 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [de701.pdf](https://maritime.org/doc/plans/de701.pdf).
