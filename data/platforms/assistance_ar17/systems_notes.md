# Systems inference notes — assistance_ar17

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Boiler_Casing_Main | sheet_read |
| Vents_Stern | vent_trunk | unknown | unknown | Stern_Working_Deck | sheet_read |
| Fan_Rm_8_Vent | mushroom | up | supply | Fan_Rm_8 | sheet_read |
| Fan_Rm_5_Vent | mushroom | up | supply | Fwd_Working_Deck | sheet_read |
| Cowl_Focsle | cowl | fore | supply | Forecastle_Main | era_plausible |
| Gooseneck_ER | gooseneck | down | supply | Engine_Room_Hold | era_plausible |
| Shop_Vents_2nd | mushroom | up | exhaust | Foundry_Blacksmith | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Ballast_Hold | mech_supply_exhaust | era_rule |
| Aft_Shops_1P | nat_supply | era_rule |
| Aft_Tanks_2P | mech_supply_exhaust | era_rule |
| Boat_Deck_Fwd | nat_supply | era_rule |
| Boat_Gun_Deck_Aft | nat_supply | era_rule |
| Boiler_Casing_Main | mech_supply_exhaust | sheet_read |
| CPO_Galley_U | mech_exhaust | era_rule |
| Carpenter_Shop | nat_supply | era_rule |
| Clipping_Empty_Shell | nat_supply | era_rule |
| Code_Communications | nat_supply | era_rule |
| Crew_Berthing_2nd | nat_supply | era_rule |
| Crew_Berthing_Main | nat_supply | era_rule |
| Crew_Mess_2nd | mech_exhaust | era_rule |
| Electrical_Shop_2nd | nat_supply | era_rule |
| Emerg_Radio_Rm | nat_supply | era_rule |
| Engine_Room_Hold | mech_supply_exhaust | era_plausible |
| Fan_Rm_8 | mech_supply_exhaust | sheet_read |
| Flat_Aft_Berthing | nat_supply | era_rule |
| Forecastle_Main | nat_supply | era_plausible |
| Foundry_Blacksmith | mech_supply_exhaust | era_plausible |
| Fuel_Water_Hold | mech_supply_exhaust | era_rule |
| Fwd_House_Upper | nat_supply | era_rule |
| Fwd_Peak_2P | nat_supply | era_rule |
| Fwd_Peak_Hold | nat_supply | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Working_Deck | nat_supply | sheet_read |
| Galley_Main | mech_exhaust | era_rule |
| Gun_Crew_Quarters | nat_supply | era_rule |
| Gun_Repair_40mm | nat_supply | era_rule |
| Gun_Tubs_Sup | nat_supply | era_rule |
| HD_Crew_2nd | exhaust_only | era_rule |
| HD_Upper | exhaust_only | era_rule |
| Hatch_5_4_Working | nat_supply | era_rule |
| House_Top_Passage | nat_supply | era_rule |
| Machine_Shop_2P | nat_supply | era_rule |
| Machine_Shop_Main | nat_supply | era_rule |
| Machine_Shop_Upper | nat_supply | era_rule |
| Machinery_1P | mech_supply_exhaust | era_rule |
| Machinery_2P | mech_supply_exhaust | era_rule |
| Navigators_Office | nat_supply | era_rule |
| Officers_Country_U | nat_supply | era_rule |
| Officers_Mess_Lounge | mech_exhaust | era_rule |
| Paravane_Hatch3 | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Radio_Receiving | nat_supply | era_rule |
| Refrig_Provisions_2nd | nat_supply | era_rule |
| Repair_Parts_Hold | nat_supply | era_rule |
| Repair_Stores_2P | nat_supply | era_rule |
| Scullery_2nd | nat_supply | era_rule |
| Shipfitter_2P | nat_supply | era_rule |
| Shipfitter_Upper | nat_supply | era_rule |
| Sky_Lookout | nat_supply | era_rule |
| Spare_Parts_1P | nat_supply | era_rule |
| Stack_Space | mech_supply_exhaust | era_rule |
| Stern_Working_Deck | nat_supply | sheet_read |
| Stores_Fwd_2nd | nat_supply | era_rule |
| WRSR_Main | exhaust_only | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANKS (hold midship) | fuel | Fuel_Water_Hold |
| SETTLING TANK | unknown | Fuel_Water_Hold |
| F.W. TANKS | freshwater | Fuel_Water_Hold |
| AFT BALLAST TANK | unknown | Aft_Ballast_Hold |
| OXYGEN/ACETYLENE DECK RACKS | unknown | Clipping_Empty_Shell |
| D.B. TANKS (inner bottom) | unknown | Machinery_2P |

## Plumbing drains

- CPO_Galley_U (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Galley_U
- HD_Upper (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Upper
- Officers_Mess_Lounge (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Mess_Lounge
- Galley_Main (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Main
- WRSR_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: WRSR_Main
- Crew_Mess_2nd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2nd
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy AR-17 USS Assistance (EC2-S-C1 repair ship), Booklet of General Plans, 1944 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [ar17.pdf](https://maritime.org/doc/plans/ar17.pdf).
