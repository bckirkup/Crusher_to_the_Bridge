# Systems inference notes — winnipeg_j337

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Rooms | sheet_read |
| Vent_ER | vent_trunk | up | supply | Engine_Room | sheet_read |
| Cowl_Foc | cowl | fore | supply | Seamens_Mess | sheet_read |
| Vent_Mag | vent_trunk | up | exhaust | Magazines_Fwd | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| After_Peak | mech_supply_exhaust | era_rule |
| Asdic_Fwd | mech_supply_exhaust | era_rule |
| Boiler_Rooms | mech_supply_exhaust | sheet_read |
| Bridge_House | nat_supply | era_rule |
| CPO_Mess | nat_supply | era_rule |
| Chain_Locker | mech_supply_exhaust | era_rule |
| Cold_Stores | nat_supply | era_rule |
| ERA_Flat | nat_supply | era_rule |
| Engine_Room | mech_supply_exhaust | sheet_read |
| Foc_Deck_Open | nat_supply | era_rule |
| Foc_Superstructure | nat_supply | era_rule |
| Fwd_Stores | mech_supply_exhaust | era_rule |
| Galley_Flat | mech_exhaust | era_rule |
| Generator_Store | mech_supply_exhaust | era_rule |
| HD_Aft | exhaust_only | era_rule |
| HD_Ups | exhaust_only | era_rule |
| MS_Mess | nat_supply | era_rule |
| Machinery_Casing | mech_supply_exhaust | era_rule |
| Magazine_Lobby_Up | mech_supply_exhaust | era_rule |
| Magazines_Fwd | mech_exhaust | era_plausible |
| PO_Mess | nat_supply | era_rule |
| Provision_Aft | nat_supply | era_rule |
| Quarterdeck | nat_supply | era_rule |
| Quarterdeck_Flat | mech_supply_exhaust | era_rule |
| Seamens_Mess | nat_supply | sheet_read |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Deck | nat_supply | era_rule |
| Signal_Stwd_Mess | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stokers_Mess | nat_supply | era_rule |
| Wardroom_Flat | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| OIL FUEL | fuel | Magazines_Fwd |
| FRESH WATER | freshwater | Provision_Aft |
| WATER BALLAST | unknown | Asdic_Fwd |
| RESERVE FEED WATER | freshwater | Magazines_Fwd |

## Plumbing drains

- HD_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Aft
- Galley_Flat (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Flat
- HD_Ups (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Ups
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
