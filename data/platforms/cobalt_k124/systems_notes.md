# Systems inference notes — cobalt_k124

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Room | sheet_read |
| ER_Skylight | skylight | up | supply | Engine_Room | sheet_read |
| Galley_Skylight | skylight | up | supply | Galley | sheet_read |
| Cowls_Foc_Bow | cowl | fore | supply | Seamen_Mess | sheet_read |
| Vents_Waist | mushroom | up | supply | Engine_Room | sheet_read |
| Vent_Mag | vent_trunk | up | exhaust | Fwd_Magazines | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| After_Peak | mech_supply_exhaust | era_rule |
| Asdic_Compartment | mech_supply_exhaust | era_rule |
| Boiler_Room | mech_supply_exhaust | sheet_read |
| Bridge_House | nat_supply | era_rule |
| CO_Cabin | nat_supply | era_rule |
| CPO_PO_Mess | nat_supply | era_rule |
| Canteen | nat_supply | era_rule |
| Chain_Locker_Store | mech_supply_exhaust | era_rule |
| Compass_Bridge | nat_supply | era_rule |
| Engine_Room | nat_supply | sheet_read |
| Engineers_Store | mech_supply_exhaust | era_rule |
| Foc_Deck_Open | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Fwd_Magazines | mech_exhaust | era_plausible |
| Galley | nat_supply | sheet_read |
| HD_Crew | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| HD_PO | exhaust_only | era_rule |
| Minesweeping_Store | mech_supply_exhaust | era_rule |
| Officer_Cabins | nat_supply | era_rule |
| Paint_Lamp_Room | mech_supply_exhaust | era_rule |
| Provision_Issue | nat_supply | era_rule |
| Provision_Room | nat_supply | era_rule |
| Quarterdeck | nat_supply | era_rule |
| Seamen_Mess | nat_supply | sheet_read |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stern_Open | nat_supply | era_rule |
| Stokers_Mess | nat_supply | era_rule |
| Wardroom | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| OIL FUEL TANK | fuel | Fwd_Magazines |
| FRESH WATER TANK | freshwater | Asdic_Compartment |
| RESERVE FEED WATER TANK | freshwater | Fwd_Magazines |
| GALLEY FUEL TANK | fuel | Wardroom |

## Plumbing drains

- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew
- HD_PO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_PO

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy K124 HMCS Cobalt (Flower class corvette), 1941 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [k124.pdf](https://maritime.org/doc/plans/k124.pdf).
