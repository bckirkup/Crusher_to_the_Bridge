# Systems inference notes — passumpsic_ao106

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Engine_Rm | sheet_read |
| Cowl_Focsle | cowl | fore | supply | Focsle_Deck | sheet_read |
| Gooseneck_Eng | gooseneck | down | supply | Boiler_Rm | era_plausible |
| Mushroom_Mess | mushroom | fore | supply | Mess_Hall | era_plausible |
| Cargo_Vents | vent_trunk | up | exhaust | Main_Cargo_Tanks | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Open_Deck | nat_supply | era_rule |
| Boiler_Rm | mech_supply_exhaust | era_plausible |
| CPO_Quarters | nat_supply | era_rule |
| Cargo_Control | nat_supply | era_rule |
| Cargo_Pump_Rm | mech_supply_exhaust | era_rule |
| Crew_Qtrs_Aft | nat_supply | era_rule |
| Crew_Qtrs_Fwd | nat_supply | era_rule |
| Engine_Rm | mech_supply_exhaust | sheet_read |
| Focsle_Deck | nat_supply | sheet_read |
| Fuel_Tanks | nat_supply | era_rule |
| Fwd_Peak_Tanks | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| HD_Crew | exhaust_only | era_rule |
| Island_Deck | nat_supply | era_rule |
| Magazines | nat_supply | era_rule |
| Main_Cargo_Tanks | mech_exhaust | sheet_read |
| Mess_Hall | nat_supply | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Radio_Rm | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Deck | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stores_2D | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |
| Working_Deck | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| MAIN CARGO TANK NO.1-6 | unknown | Main_Cargo_Tanks |
| F.O. TANK | fuel | Fuel_Tanks |
| F.W. TANK | freshwater | Fwd_Peak_Tanks |

## Plumbing drains

- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Mess_Hall (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Mess_Hall
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy AO-106 USS Navasota (Cimarron class), Booklet of General Plans, 1960 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [ao106.pdf](https://maritime.org/doc/plans/ao106.pdf).
