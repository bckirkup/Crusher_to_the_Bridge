# Systems inference notes — jupiter_ac3

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_Port | funnel | up | exhaust | Fire_Room_Port | sheet_read |
| Funnel_Stbd | funnel | up | exhaust | Fire_Room_Stbd | sheet_read |
| Vent_Trunk_Hold | vent_trunk | up | supply | Coal_Bunkers_Hold | sheet_read |
| Vent_Deckhouse | vent_trunk | up | exhaust | Officers_Galley | sheet_read |
| Cowl_Poop | cowl | fore | supply | Crews_Berthing_Main | sheet_read |
| Coaling_Hatch_Marker | air_port | up | supply | Cargo_Holds | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Blower_Rm | mech_supply_exhaust | era_rule |
| Boiler_Casing | mech_supply_exhaust | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| Captain_Suite | nat_supply | era_rule |
| Cargo_Hatch_Apron | nat_supply | era_rule |
| Cargo_Holds | nat_supply | sheet_read |
| Chain_Locker | nat_supply | era_rule |
| Coal_Bunkers_Hold | nat_supply | sheet_read |
| Coal_Bunkers_Plat | nat_supply | era_rule |
| Crews_Berthing_2nd | nat_supply | era_rule |
| Crews_Berthing_Main | nat_supply | sheet_read |
| Crews_Berthing_Plat | nat_supply | era_rule |
| Crews_Galley | mech_exhaust | era_rule |
| Donkey_Boiler_Rm | mech_supply_exhaust | era_rule |
| Eng_Casing_DH | mech_supply_exhaust | era_rule |
| Eng_Casing_Main | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| FW_Tanks_Aft | nat_supply | era_rule |
| Fire_Room_Port | mech_supply_exhaust | sheet_read |
| Fire_Room_Stbd | mech_supply_exhaust | sheet_read |
| Focsle_Deck_Open | nat_supply | era_rule |
| Forepeak_Tank | nat_supply | era_rule |
| Generator_Room | mech_supply_exhaust | era_rule |
| HD_Firemens | exhaust_only | era_rule |
| HD_Seamens | exhaust_only | era_rule |
| HD_Wardroom | exhaust_only | era_rule |
| HD_Warrant_Crews | exhaust_only | era_rule |
| Hospital | mech_supply_exhaust | era_rule |
| Lamp_Paint_Oil | nat_supply | era_rule |
| Machinist_Cabins | nat_supply | era_rule |
| Motor_Room | mech_supply_exhaust | era_rule |
| Officers_Galley | mech_exhaust | sheet_read |
| Officers_Quarters | nat_supply | era_rule |
| Oil_Cargo_Tanks | nat_supply | era_rule |
| Oil_Trunks_Fwd | nat_supply | era_rule |
| Passage_Deckhouse | nat_supply | era_rule |
| Plat_Stores_Aft | nat_supply | era_rule |
| Poop_Deck_Open | nat_supply | era_rule |
| Reefer_Stores | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Spare_Berthing_2nd | nat_supply | era_rule |
| Spare_Berthing_Fwd | nat_supply | era_rule |
| Spare_Berthing_Plat | nat_supply | era_rule |
| Steering_Gear_Rm | mech_supply_exhaust | era_rule |
| Stores_2nd | nat_supply | era_rule |
| Topside_Tanks | nat_supply | era_rule |
| Wardroom | mech_exhaust | era_rule |
| Warrant_Mess | mech_exhaust | era_rule |
| Wireless_Room | nat_supply | era_rule |
| Work_Shop | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.W. | freshwater | FW_Tanks_Aft |
| AFT TRIMMING TANK | unknown | Shaft_Alley |
| FORD TRIMMING TANK | unknown | Forepeak_Tank |
| OIL CARGO | fuel | Oil_Cargo_Tanks |
| COAL | unknown | Coal_Bunkers_Plat |

## Plumbing drains

- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Warrant_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Warrant_Mess
- Officers_Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Galley
- Crews_Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crews_Galley
- HD_Wardroom (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Wardroom
- HD_Warrant_Crews (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Warrant_Crews
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess
- Hospital (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Hospital
- HD_Seamens (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Seamens
- HD_Firemens (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Firemens

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy AC-3 USS Jupiter (later USS Langley CV-1), Plans, 1913 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [ac3.pdf](https://maritime.org/doc/plans/ac3.pdf).
