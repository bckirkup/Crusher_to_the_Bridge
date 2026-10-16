# Systems inference notes — river_class_frigate

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Room | sheet_read |
| Vent_Boiler | vent_trunk | up | supply | Boiler_Room | sheet_read |
| MechVent_ER | vent_trunk | up | supply | Engine_Room | sheet_read |
| Cowl_Foc | cowl | fore | supply | Seamen_Mess | sheet_read |
| Vent_Mag_Aft | vent_trunk | up | exhaust | Magazine_Aft | era_plausible |
| Vent_Mag_Fwd | vent_trunk | up | exhaust | Fwd_Magazine | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AS_Instrument | mech_supply_exhaust | era_rule |
| After_Peak_Ballast | mech_supply_exhaust | era_rule |
| Ammo_Lobby | nat_supply | era_rule |
| Asdic_Dome | mech_supply_exhaust | era_rule |
| Boiler_Room | mech_supply_exhaust | sheet_read |
| Bosun_Fwd | mech_supply_exhaust | era_rule |
| Bridge_House | nat_supply | era_rule |
| CPO_ERA_Mess | nat_supply | era_rule |
| Cabin_Block | nat_supply | era_rule |
| Canteen_Flat | nat_supply | era_rule |
| Chain_Locker | mech_supply_exhaust | era_rule |
| Cold_Stores | nat_supply | era_rule |
| DC_Flat | mech_supply_exhaust | era_rule |
| Drying_Room | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | sheet_read |
| Foc_Deck_Open | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Fwd_Magazine | mech_exhaust | era_plausible |
| Gyro_Diesel_Room | mech_supply_exhaust | era_rule |
| HD_Crew | exhaust_only | era_rule |
| HD_Fwd | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| Lamp_Paint_Decon | mech_supply_exhaust | era_rule |
| Magazine_Aft | mech_exhaust | era_plausible |
| Mess_Mid_P | nat_supply | era_rule |
| Mess_Mid_S | nat_supply | era_rule |
| PO_Mess | nat_supply | era_rule |
| Provision_Issue | nat_supply | era_rule |
| Quarterdeck | nat_supply | era_rule |
| Seamen_Mess | nat_supply | sheet_read |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Deck | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stewards_Mess | nat_supply | era_rule |
| Stokers_Mess | nat_supply | era_rule |
| Stores_Aft | nat_supply | era_rule |
| Wardroom_Flat | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| OIL FUEL | fuel | Fwd_Magazine |
| RESERVE FEED WATER | freshwater | Fwd_Magazine |
| FRESH WATER | freshwater | Fwd_Magazine |
| BALLAST TANK | unknown | After_Peak_Ballast |

## Plumbing drains

- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- HD_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Fwd
- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
