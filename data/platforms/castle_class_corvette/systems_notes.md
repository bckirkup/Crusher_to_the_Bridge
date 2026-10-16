# Systems inference notes — castle_class_corvette

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Rm | sheet_read |
| Cowl_Foc_Bow | cowl | fore | supply | Officer_Cabins | sheet_read |
| Cowl_Foc_Mid | cowl | fore | supply | Foc_Cabins | sheet_read |
| Skylight_Mess | skylight | up | exhaust | Seamen_Mess | sheet_read |
| Gooseneck_Eng | gooseneck | down | supply | Engine_Rm | era_plausible |
| Vent_Mag | vent_trunk | up | exhaust | Fwd_Magazines | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Boiler_Rm | mech_supply_exhaust | sheet_read |
| Bridge_House | nat_supply | era_rule |
| Compass_Bridge | nat_supply | era_rule |
| Engine_Rm | mech_supply_exhaust | era_plausible |
| Foc_Cabins | nat_supply | sheet_read |
| Foc_Deck_Open | nat_supply | era_rule |
| Fwd_Magazines | mech_exhaust | era_plausible |
| Galley | mech_exhaust | era_rule |
| HD_Foc | exhaust_only | era_rule |
| HD_Upper | exhaust_only | era_rule |
| Mess_Mid | nat_supply | era_rule |
| Officer_Cabins | nat_supply | sheet_read |
| Quarterdeck | nat_supply | era_rule |
| Seamen_Mess | nat_supply | sheet_read |
| Shaft_Stores | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stokers_Mess | nat_supply | era_rule |
| Upper_Deck_Aft | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. TANK | freshwater | Shaft_Stores |

## Plumbing drains

- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- HD_Foc (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Foc
- HD_Upper (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Upper
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy Castle Class corvette, 1944 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [castle.pdf](https://maritime.org/doc/plans/castle.pdf).
