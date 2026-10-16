# Systems inference notes — liberty_cargo_ec2

Era: **Merchant / aux WW2 practice** (`merchant_ww2`)

Natural cowl supply to accommodation; mechanical exhaust to galley and machinery spaces.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| VM_focsle_cowl | cowl | fore | supply | Focsle_Stores | era_plausible |
| VM_house_supply | cowl | fore | supply | PO_Mess | era_plausible |
| VM_house_exhaust | gooseneck | aft | exhaust | Berthing_Port | era_plausible |
| VM_funnel | funnel | unknown | exhaust | Boiler_Casing_UD | sheet_read |
| VM_engine_skylight | skylight | unknown | exhaust | Machinery_Casing_Bt | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Deck_Open | nat_supply | era_rule |
| Aft_Peak | nat_supply | era_rule |
| Berthing_Port | mech_exhaust | era_plausible |
| Berthing_Port_Lower | nat_supply | era_rule |
| Berthing_Stbd | nat_supply | era_rule |
| Boat_Deck_Lobby | nat_supply | era_rule |
| Boat_Deck_Open | nat_supply | era_rule |
| Boiler_Casing_Br | mech_supply_exhaust | era_rule |
| Boiler_Casing_UD | mech_supply_exhaust | sheet_read |
| Boiler_Room | mech_supply_exhaust | era_rule |
| Bridge_Cabins_Port | nat_supply | era_rule |
| Bridge_Wings | nat_supply | era_rule |
| CO2_Rm | nat_supply | era_rule |
| Captain_Suite | nat_supply | era_rule |
| Chain_Locker | nat_supply | era_rule |
| Chart_Radio_Rm | nat_supply | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Deep_Tanks_Fwd | nat_supply | era_rule |
| Deep_Tanks_Mid | nat_supply | era_rule |
| Dry_Provisions | nat_supply | era_rule |
| Engine_Casing_2D | mech_supply_exhaust | era_rule |
| Engine_Casing_UD | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| Focsle_Stores | nat_supply | era_plausible |
| Forecastle_Deck | nat_supply | era_rule |
| Forepeak | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Gun_Platform | nat_supply | era_rule |
| Gunners_Berth_Aft | nat_supply | era_rule |
| HD_Bridge_Deck | exhaust_only | era_rule |
| HD_Deck | exhaust_only | era_rule |
| HD_Eng | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| HD_PO | exhaust_only | era_rule |
| Holds_Aft | nat_supply | era_rule |
| Holds_Fwd | nat_supply | era_rule |
| Hospital | mech_supply_exhaust | era_rule |
| Machinery_Casing_Bt | nat_supply | sheet_read |
| Machinery_Flats_UD | mech_supply_exhaust | era_rule |
| Officer_Cabins_Port | nat_supply | era_rule |
| Officer_Cabins_Stbd | nat_supply | era_rule |
| PO_Mess | nat_supply | era_plausible |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Ships_Stores_UD | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Top_Of_House | nat_supply | era_rule |
| Tween_Cargo_Aft | nat_supply | era_rule |
| Tween_Cargo_Fwd | nat_supply | era_rule |
| Tween_Hatch_1 | nat_supply | era_rule |
| Tween_Hatch_2 | nat_supply | era_rule |
| Tween_Hatch_3 | nat_supply | era_rule |
| Tween_Hatch_4 | nat_supply | era_rule |
| Tween_Hatch_5 | nat_supply | era_rule |
| Wheelhouse | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FO SETTLING TK | unknown | Boiler_Room |
| RESERVE FEED WATER TK | freshwater | Engine_Room |
| FO/BALLAST DEEP TK N2 | unknown | Deep_Tanks_Fwd |
| FO/BALLAST DEEP TK N3 | unknown | Deep_Tanks_Mid |
| FORE PEAK | unknown | Forepeak |
| AFT PEAK | unknown | Aft_Peak |

## Plumbing drains

- HD_Bridge_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Bridge_Deck
- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- Hospital (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Hospital
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess
- PO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: PO_Mess
- HD_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Deck
- HD_PO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_PO
- HD_Eng (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Eng

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
