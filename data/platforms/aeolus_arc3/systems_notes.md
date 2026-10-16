# Systems inference notes — aeolus_arc3

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| VM_buoy_deck_cowl | cowl | fore | supply | Cable_Working_Deck | era_plausible |
| VM_house_supply | cowl | fore | supply | Deck_House_Upper | era_plausible |
| VM_funnel_arc | funnel | unknown | exhaust | Top_Of_House | sheet_read |
| VM_er_intake | air_shaft | unknown | supply | Boiler_Casing_M | era_plausible |
| VM_hold_vent | gooseneck | up | exhaust | Cable_Tanks | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| After_Repair_Locker | mech_ac | era_rule |
| Armory | mech_ac | era_rule |
| Aux_Machinery_2P | mech_supply_exhaust | era_rule |
| Berth_1P | mech_ac | era_rule |
| Boiler_Casing_M | mech_supply_exhaust | era_plausible |
| Boiler_Room | mech_supply_exhaust | era_rule |
| Bow_Sheave_Area | nat_supply | era_rule |
| Bridge_Chart_Rms | mech_ac | era_rule |
| Butcher_Meats | mech_ac | era_rule |
| Cable_Tanks | mech_exhaust | era_plausible |
| Cable_Testing_Rm | mech_ac | era_rule |
| Cable_Working_Deck | nat_supply | era_plausible |
| Cable_Workshop | mech_ac | era_rule |
| Crew_Berth_M | mech_ac | era_rule |
| Crew_Messing | mech_exhaust | era_rule |
| Crew_Recreation | mech_ac | era_rule |
| Deck_House_Upper | nat_supply | era_plausible |
| Elec_Switchboard | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| Escape_Trunk_2P | mech_supply_exhaust | era_rule |
| Flam_Liquid_Stores | mech_ac | era_rule |
| Fwd_Stores_1P | mech_ac | era_rule |
| Fwd_Stores_2P | mech_ac | era_rule |
| Fwd_Stores_M | mech_ac | era_rule |
| Galley | mech_exhaust | era_rule |
| HD_Bridge | exhaust_only | era_rule |
| HD_First_Platform | exhaust_only | era_rule |
| HD_Main_Deck | exhaust_only | era_rule |
| HD_Upper_Deck | exhaust_only | era_rule |
| Ice_Machinery_Rm | mech_supply_exhaust | era_rule |
| Provisions_Stores_2P | mech_ac | era_rule |
| Radio_Electronic_Shops | mech_ac | era_rule |
| Rope_Stowage | mech_ac | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Storeroom_Hold | mech_ac | era_rule |
| Superstructure_Cabins | mech_ac | era_rule |
| Top_Of_House | mech_supply_exhaust | sheet_read |
| Washroom_Locker_1P | mech_ac | era_rule |
| Wheelhouse | nat_supply | era_rule |
| Workshops_1P | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANK C-3F | fuel | Armory |
| CABLE TANK NO.1 | unknown | Cable_Tanks |
| FORE PEAK | unknown | — |
| F.W. TANK | freshwater | Flam_Liquid_Stores |

## Plumbing drains

- HD_Bridge (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Bridge
- HD_Upper_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Upper_Deck
- Crew_Messing (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Messing
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- HD_Main_Deck (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Main_Deck
- HD_First_Platform (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_First_Platform

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
