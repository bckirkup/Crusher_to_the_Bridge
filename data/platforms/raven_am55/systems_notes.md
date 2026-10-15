# Systems inference notes — raven_am55

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Engine_Rm | sheet_read |
| Cowl_Fwd | cowl | fore | supply | Foc_Deck_Fwd | sheet_read |
| Vent_Stern | vent_trunk | unknown | unknown | Steering_Gen | sheet_read |
| Gooseneck_Eng | gooseneck | down | supply | Engine_Rm | era_plausible |
| Cowl_Mess | mushroom | fore | supply | Mess_Tables | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Bosn_Gear | nat_supply | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Clipping_Rm | mech_supply_exhaust | era_rule |
| Crew_Quarters | nat_supply | era_rule |
| Engine_Rm | mech_supply_exhaust | sheet_read |
| Foc_Deck_Fwd | nat_supply | sheet_read |
| Foc_Deck_Open | nat_supply | era_rule |
| Fwd_Magazines | nat_supply | era_rule |
| Fwd_Stores | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Gen_Rm | mech_supply_exhaust | era_rule |
| HD_Main | exhaust_only | era_rule |
| Mess_Tables | nat_supply | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Passage_Main | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Steering_Gen | mech_supply_exhaust | sheet_read |
| Sweep_Deck | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. TANK | freshwater | Fwd_Magazines |
| F.O. TANK | fuel | Engine_Rm |

## Plumbing drains

- Mess_Tables (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Mess_Tables
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Main

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
