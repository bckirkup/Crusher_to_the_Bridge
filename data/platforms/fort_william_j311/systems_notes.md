# Systems inference notes — fort_william_j311

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Rooms | sheet_read |
| Engine_Vent | vent_trunk | up | supply | Engine_Room | sheet_read |
| Cowl_Foc | cowl | fore | supply | Seamen_Mess | sheet_read |
| Vent_Mag | vent_trunk | up | exhaust | Magazines_Fwd | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| After_Peak | mech_supply_exhaust | era_rule |
| Boiler_Rooms | mech_supply_exhaust | sheet_read |
| Bridge_House | nat_supply | era_rule |
| Cabins_Fwd | nat_supply | era_rule |
| Chain_Locker | mech_supply_exhaust | era_rule |
| Compressed_Air_Room | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | sheet_read |
| Foc_Deck_Open | nat_supply | era_rule |
| Foc_Superstructure | nat_supply | era_rule |
| Fwd_Store | mech_supply_exhaust | era_rule |
| Galley_Flat | mech_exhaust | era_rule |
| HD_Low | exhaust_only | era_rule |
| HD_Ups | exhaust_only | era_rule |
| Machinery_Casing | mech_supply_exhaust | era_rule |
| Magazine_Lobby_Fwd | mech_supply_exhaust | era_rule |
| Magazines_Fwd | mech_exhaust | era_plausible |
| Mess_Fwd | nat_supply | era_rule |
| Provision_Fwd | nat_supply | era_rule |
| Quarterdeck | nat_supply | era_rule |
| Seamen_Mess | nat_supply | sheet_read |
| Signal_Deck | nat_supply | era_rule |
| Stokers_Mess | nat_supply | era_rule |
| Stores_Aft | nat_supply | era_rule |
| Sweep_Deck | mech_supply_exhaust | era_rule |
| Wardroom_Flat | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| OIL FUEL | fuel | Compressed_Air_Room |
| FRESH WATER | freshwater | Chain_Locker |
| RESERVE FEED WATER | freshwater | Compressed_Air_Room |

## Plumbing drains

- Galley_Flat (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Flat
- HD_Ups (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Ups
- HD_Low (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Low

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
