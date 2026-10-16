# Systems inference notes — midway_cv41

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_1 | funnel | up | exhaust | Funnel_Uptake | sheet_read |
| Uptakes_Main_row | uptake | up | exhaust | Uptakes_Main | sheet_read |
| HangarDoor_div1 | hangar_door | unknown | supply | Hangar_Mid | sheet_read |
| HangarDoor_div2 | hangar_door | unknown | supply | Hangar_Aft | sheet_read |
| FanRoom_2D | fan_room | unknown | supply | Galley_2D | sheet_read |
| FanRoom_02 | fan_room | unknown | supply | AC_Machinery_02 | sheet_read |
| VentTrunk_Main | vent_trunk | up | exhaust | Hangar_Fwd | sheet_read |
| MagVent_1P_Fwd | vent_trunk | up | exhaust | Magazine_1P_Fwd | era_plausible |
| Cowl_FD_1 | cowl | up | supply | Flight_Deck | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Machinery_02 | mech_supply_exhaust | sheet_read |
| ADP_3D | nat_supply | era_rule |
| AIMD_01 | nat_supply | era_rule |
| Aft_Diesel_3D | mech_supply_exhaust | era_rule |
| Aft_Machinery_2P | mech_supply_exhaust | era_rule |
| Air_Ops_Rooms | nat_supply | era_rule |
| Aux_Machinery_1P | mech_supply_exhaust | era_rule |
| Av_Stores_1P | nat_supply | era_rule |
| Aviation_Shops_Main | nat_supply | era_rule |
| Aviation_Stores_01 | nat_supply | era_rule |
| CPO_2D | nat_supply | era_rule |
| CPO_3D | nat_supply | era_rule |
| Catapult_Accum_01 | mech_supply_exhaust | era_rule |
| Catapult_Machinery_02 | mech_supply_exhaust | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_3D_Aft | nat_supply | era_rule |
| Crew_Berthing_3D_Fwd | nat_supply | era_rule |
| Crew_Berthing_3D_Mid | nat_supply | era_rule |
| Crew_Living_02 | nat_supply | era_rule |
| Crew_Mess_2D | mech_exhaust | era_rule |
| Elev_Mach_3D | mech_supply_exhaust | era_rule |
| Evaporator_1P | mech_supply_exhaust | era_rule |
| Flight_Deck | nat_supply | era_plausible |
| Focsle_Stores_2D | nat_supply | era_rule |
| Funnel_Uptake | mech_supply_exhaust | sheet_read |
| Fwd_Diesel_2D | mech_supply_exhaust | era_rule |
| Fwd_Machinery_2P | mech_supply_exhaust | era_rule |
| Fwd_Machinery_4D | mech_supply_exhaust | era_rule |
| Fwd_Messing_2D | mech_exhaust | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_4D | nat_supply | era_rule |
| Galley_2D | mech_supply_exhaust | sheet_read |
| HD_02 | exhaust_only | era_rule |
| HD_2nd | exhaust_only | era_rule |
| HD_3rd | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | sheet_read |
| Hangar_Fwd | mech_exhaust | sheet_read |
| Hangar_Mid | nat_supply | sheet_read |
| Hold_Tanks | nat_supply | era_rule |
| Island_Upper | nat_supply | era_rule |
| Jet_Test_01 | mech_supply_exhaust | era_rule |
| Laundry_3D | nat_supply | era_rule |
| Magazine_1P_Aft | nat_supply | era_rule |
| Magazine_1P_Fwd | mech_exhaust | era_plausible |
| Magazine_2P_Fwd | nat_supply | era_rule |
| Magazine_Hold | nat_supply | era_rule |
| Magazines_4D | nat_supply | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country_02 | nat_supply | era_rule |
| PriFly_FlagPlot | nat_supply | era_rule |
| Provisions_4D | nat_supply | era_rule |
| Shaft_Alley_Hold | mech_supply_exhaust | era_rule |
| Shaft_Alleys_2P | mech_supply_exhaust | era_rule |
| Shops_2D | nat_supply | era_rule |
| Shops_4D | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Steering_Gear_4D | mech_supply_exhaust | era_rule |
| Stern_Hold | nat_supply | era_rule |
| Supply_Offices_01 | nat_supply | era_rule |
| Tanks_2P | nat_supply | era_rule |
| Turbo_Gen_1P | mech_supply_exhaust | era_rule |
| Uptakes_Main | mech_supply_exhaust | sheet_read |
| Wardroom_02 | mech_exhaust | era_rule |
| Wardroom_2D | mech_exhaust | era_rule |
| Work_Centers_Main | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. OR BALLAST | fuel | Hold_Tanks |
| JP-5 OR BALLAST | unknown | Hold_Tanks |
| F.O. OR BALLAST | fuel | Tanks_2P |
| JP-5 SERVICE TANK / AFS STA (JP-5) | unknown | Flight_Deck |
| D.B. TANK CELLS (F.O./BALLAST/F.W.) | freshwater | Shaft_Alley_Hold |

## Plumbing drains

- Wardroom_02 (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_02
- HD_02 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_02
- Wardroom_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_2D
- Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_2D
- Crew_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2D
- Fwd_Messing_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Fwd_Messing_2D
- HD_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2nd
- HD_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3rd
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CV-41 USS Midway, Booklet of General Plans, 1987 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cv41.pdf](https://maritime.org/doc/plans/cv41.pdf).
