# Systems inference notes — squier_ap130

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| sup_fan_rm_port | fan_room | unknown | supply | Officers_Country_Sup | sheet_read |
| sup_fan_rm_stbd | fan_room | unknown | supply | Officers_Country_Sup | sheet_read |
| main_stack | funnel | unknown | exhaust | Engines_Boiler_Casing_2D | sheet_read |
| hatch_trunks | vent_trunk | unknown | unknown | Troop_Berthing_1P_B | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Peak_3D | nat_supply | era_rule |
| Chain_Locker_Stores_2D | nat_supply | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_Fwd_Up | nat_supply | era_rule |
| Crew_Berthing_Up | nat_supply | era_rule |
| Crew_Troop_Mess_2D | mech_exhaust | era_rule |
| Engine_Casing_1P | mech_supply_exhaust | era_rule |
| Engines_Boiler_Casing_2D | mech_supply_exhaust | sheet_read |
| Fan_Hatch_Block_Sup | nat_supply | era_rule |
| Forepeak_1P | nat_supply | era_rule |
| Forepeak_3D | nat_supply | era_rule |
| Forepeak_TT | nat_supply | era_rule |
| Fwd_Gun_Platform_Sup | nat_supply | era_rule |
| Fwd_Stores_Up | nat_supply | era_rule |
| Galley_Bakery_3D | mech_exhaust | era_rule |
| Galley_Complex_Up | mech_exhaust | era_rule |
| HD_Troop_2D | exhaust_only | era_rule |
| HD_Troop_3D | exhaust_only | era_rule |
| HD_Upper | exhaust_only | era_rule |
| Hold_Vegetable_TT | nat_supply | era_rule |
| Lounge_Sup | nat_supply | era_rule |
| Machinery_Hatch_3D | mech_supply_exhaust | era_rule |
| Machinery_Hatch_Sup | mech_supply_exhaust | era_rule |
| Machinery_Hatch_Up | mech_supply_exhaust | era_rule |
| Machinery_Tanks_TT | mech_supply_exhaust | era_rule |
| Med_Attend_Berthing | nat_supply | era_rule |
| Medical_Complex_2D | mech_supply_exhaust | era_rule |
| NCO_Berthing_2D | nat_supply | era_rule |
| NCO_Berthing_Up | nat_supply | era_rule |
| NCO_Mess_Up | mech_exhaust | era_rule |
| Officers_Country_Sup | mech_supply_exhaust | sheet_read |
| Provisions_1P | nat_supply | era_rule |
| Reefer_Block_1P | nat_supply | era_rule |
| Shaft_Alley_Aft | mech_supply_exhaust | era_rule |
| Ship_Troop_Off_Mess | mech_exhaust | era_rule |
| Steering_Gear_Mach | mech_supply_exhaust | era_rule |
| Stern_Deck_Up | nat_supply | era_rule |
| Stores_Aft_Up | nat_supply | era_rule |
| Sup_Gun_Tub_Aft | nat_supply | era_rule |
| Sup_House_Aft | nat_supply | era_rule |
| Tanks_Aft_TT | nat_supply | era_rule |
| Tanks_Fwd_TT | nat_supply | era_rule |
| Troop_Berthing_1P_A | nat_supply | era_rule |
| Troop_Berthing_1P_B | nat_supply | era_plausible |
| Troop_Berthing_1P_C | nat_supply | era_rule |
| Troop_Berthing_2D | nat_supply | era_rule |
| Troop_Berthing_3D_A | nat_supply | era_rule |
| Troop_Berthing_3D_B | nat_supply | era_rule |
| Troop_Berthing_3D_C | nat_supply | era_rule |
| Troop_Berthing_Up | nat_supply | era_rule |
| Troop_Mess_2D | mech_exhaust | era_rule |
| Troop_Off_Qtrs_Top | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. SETTLING TANK | fuel | Machinery_Tanks_TT |
| DEEP TANK | unknown | Tanks_Aft_TT |
| FOREPEAK TANK | unknown | Forepeak_TT |
| FUEL OIL (TANK ARRANGEMENT) | fuel | Ship_Troop_Off_Mess |
| S.W. BALLAST | unknown | Troop_Berthing_Up |

## Plumbing drains

- NCO_Mess_Up (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: NCO_Mess_Up
- Galley_Complex_Up (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Complex_Up
- Ship_Troop_Off_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Ship_Troop_Off_Mess
- HD_Upper (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Upper
- Medical_Complex_2D (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Medical_Complex_2D
- Crew_Troop_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Troop_Mess_2D
- Troop_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Troop_Mess_2D
- HD_Troop_2D (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_2D
- Galley_Bakery_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Bakery_3D
- HD_Troop_3D (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_3D

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy AP-130 USS General G.O. Squier, Booklet of General Plans, 1942 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [ap130.pdf](https://maritime.org/doc/plans/ap130.pdf).
