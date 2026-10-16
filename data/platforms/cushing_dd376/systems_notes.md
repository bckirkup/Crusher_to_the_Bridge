# Systems inference notes — cushing_dd376

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_fwd | funnel | up | exhaust | Fwd_Boiler_Room | sheet_read |
| funnel_aft | funnel | up | exhaust | Aft_Boiler_Room | sheet_read |
| blower_uptake_aft | fan_room | unknown | supply | Aft_Boiler_Room | sheet_read |
| blower_uptake_fwd | fan_room | unknown | supply | Fwd_Boiler_Room | sheet_read |
| galley_vent | gooseneck | up | exhaust | Galley | sheet_read |
| cowl_aft_deckhouse | cowl | fore | supply | Gun_Crew_Shelter_Aft | sheet_read |
| cowl_focsle_1 | cowl | fore | supply | CPO_Quarters | sheet_read |
| cowl_waist | cowl | fore | supply | Radio_Central | sheet_read |
| mag_vent_fwd | mushroom | up | exhaust | Fwd_Magazine | era_plausible |
| mag_vent_aft | mushroom | up | exhaust | Aft_Magazines | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AA_Shelter_Mag | nat_supply | era_rule |
| Aft_Ammo_2 | nat_supply | era_rule |
| Aft_Boiler_Room | mech_supply_exhaust | sheet_read |
| Aft_Magazines | mech_exhaust | era_plausible |
| Blower_Room | nat_supply | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| CPO_Quarters | nat_supply | sheet_read |
| Chart_House | nat_supply | era_rule |
| Cold_Stores | nat_supply | era_rule |
| Commissary_Stores | nat_supply | era_rule |
| Crew_Berthing_Aft | nat_supply | era_rule |
| Crew_Berthing_Mid | nat_supply | era_rule |
| Crew_Mess_Fwd | mech_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Focsle_Open | nat_supply | era_rule |
| Fwd_Boiler_Room | mech_supply_exhaust | sheet_read |
| Fwd_Magazine | mech_exhaust | era_plausible |
| Fwd_Stores_1P | nat_supply | era_rule |
| Galley | mech_exhaust | sheet_read |
| General_Workshop | nat_supply | era_rule |
| Gun_Crew_Shelter_Aft | nat_supply | sheet_read |
| HD_CPO | exhaust_only | era_rule |
| HD_Crew_Washroom | exhaust_only | era_rule |
| IC_Room | nat_supply | era_rule |
| MG_DC_Room | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Provisions_1P | nat_supply | era_rule |
| Provisions_2P | nat_supply | era_rule |
| Radio_Central | nat_supply | sheet_read |
| Second_Plat_Stores_Fwd | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Ships_Service | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_Bridge | nat_supply | era_rule |
| Sound_Room | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| WR_Staterooms | nat_supply | era_rule |
| Wardroom_Mess | mech_exhaust | era_rule |
| Windlass_Room | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL OR BALLAST D-9-F | fuel | Aft_Ammo_2 |
| FUEL OIL OR BALLAST D-7-F | fuel | Aft_Ammo_2 |
| RES. FEED WATER D-2-W / D-3-W | unknown | Aft_Ammo_2 |
| FUEL OIL A-6-P / A-5-P | fuel | IC_Room |
| OIL OR BALLAST A-4-P / A-4-F | fuel | IC_Room |
| PEAK TANK A-414-W | unknown | Fwd_Stores_1P |
| CONTAMINATED FUEL OIL TANK A-2-P&S | fuel | Fwd_Boiler_Room |
| FRESH WATER (fwd double bottoms) | freshwater | Sound_Room |

## Plumbing drains

- HD_Crew_Washroom (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Washroom
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- HD_CPO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Crew_Mess_Fwd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_Fwd
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
