# Systems inference notes — pce_874

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Engine_Rm | sheet_read |
| Cowl_Fwd | cowl | fore | supply | Focsle_Deck | sheet_read |
| Vent_Stern | vent_trunk | unknown | unknown | Fantail | sheet_read |
| Gooseneck_Eng | gooseneck | down | supply | Engine_Rm | era_plausible |
| Mushroom_Mess | mushroom | fore | supply | Mess_Hall | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| CPO_Quarters | nat_supply | era_rule |
| Crew_Quarters | nat_supply | era_rule |
| Eng_Casing | mech_supply_exhaust | era_rule |
| Engine_Rm | mech_supply_exhaust | sheet_read |
| Fantail | nat_supply | sheet_read |
| Focsle_Deck | nat_supply | sheet_read |
| Fuel_Tanks | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Gen_Rm | mech_supply_exhaust | era_rule |
| HD_Crew | exhaust_only | era_rule |
| Mess_Hall | nat_supply | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Passage_Main | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Bridge | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stores_Platform | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANK | fuel | Fuel_Tanks |

## Plumbing drains

- Mess_Hall (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Mess_Hall
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
