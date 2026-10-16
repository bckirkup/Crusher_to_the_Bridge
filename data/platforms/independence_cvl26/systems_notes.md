# Systems inference notes — independence_cvl26

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_island | funnel | up | exhaust | Funnel_Uptake | sheet_read |
| uptake_main_port | uptake | up | exhaust | Uptakes_Main | sheet_read |
| uptake_main_stbd | uptake | up | exhaust | Uptakes_Main | sheet_read |
| hangar_door_p | hangar_door | port | supply | Hangar_Fwd | sheet_read |
| hangar_door_s | hangar_door | starboard | supply | Hangar_Fwd | sheet_read |
| hangar_door_aft | hangar_door | aft | supply | Hangar_Aft | sheet_read |
| vent_trunk_p | vent_trunk | up | supply | Uptakes_Main | sheet_read |
| vent_trunk_s | vent_trunk | up | supply | Uptakes_Main | sheet_read |
| fan_room_a104e | fan_room | up | supply | Officers_Country | sheet_read |
| cowls_forecastle | cowl | fore | supply | Forecastle_Deck | era_plausible |
| mag_vents_fwd | mushroom | up | exhaust | Bomb_Assembly | era_plausible |
| mag_vents_aft | mushroom | up | exhaust | Ordnance_Stores | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Engine_Rm | mech_supply_exhaust | era_rule |
| Aft_Fire_Rm | mech_supply_exhaust | era_rule |
| Air_Ops_Rooms | nat_supply | era_rule |
| Avgas_Tanks | nat_supply | era_rule |
| Bomb_Assembly | mech_exhaust | era_plausible |
| CPO_Berthing | nat_supply | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| Central_Station | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_3D | nat_supply | era_rule |
| Crew_Berthing_Main | nat_supply | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Focsle_Stores | nat_supply | era_rule |
| Forecastle_Deck | nat_supply | era_plausible |
| Fuel_Tanks_2P | nat_supply | era_rule |
| Funnel_Uptake | mech_supply_exhaust | sheet_read |
| Fwd_Engine_Rm | mech_supply_exhaust | era_rule |
| Fwd_Fire_Rm | mech_supply_exhaust | era_rule |
| Fwd_Rooms_2D | nat_supply | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Gallery_Deck | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| HD_2nd | exhaust_only | era_rule |
| HD_3rd | exhaust_only | era_rule |
| HD_Main | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | sheet_read |
| Hangar_Fwd | nat_supply | sheet_read |
| Hangar_Trunk_Space | mech_supply_exhaust | era_rule |
| Hold_Tanks | nat_supply | era_rule |
| Island_Upper | nat_supply | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | mech_supply_exhaust | sheet_read |
| Ordnance_Stores | mech_exhaust | era_plausible |
| Poop_Deck | nat_supply | era_rule |
| Provisions_1P | nat_supply | era_rule |
| Provisions_3D | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Shops_Aft | nat_supply | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Stern_Hold | nat_supply | era_rule |
| Stern_Stores_2P | nat_supply | era_rule |
| Uptakes_Main | mech_supply_exhaust | sheet_read |
| Wardroom | mech_exhaust | era_rule |
| Workshops_3D | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| GAS TANK A-601AS (AVGAS) | unknown | Avgas_Tanks |
| F.O. SERVICE B-925F | fuel | Fuel_Tanks_2P |
| F.O. & BALLAST B-930F | fuel | Fuel_Tanks_2P |
| PEAK TANK A-1W | unknown | Fuel_Tanks_2P |
| GASOLINE TANK (C-7V cofferdam) | unknown | Stern_Hold |
| F.O. C-11F / C-10F | fuel | Stern_Hold |
| FRESH WATER B-938T | freshwater | Hold_Tanks |
| DIESEL OIL B-932F | fuel | Hold_Tanks |
| RESERVE FEED WATER B-920T | freshwater | Hold_Tanks |
| CONTAMINATED OIL B-935V | fuel | Hold_Tanks |

## Plumbing drains

- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- HD_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Main
- HD_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2nd
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- HD_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_3rd
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CVL-26 USS Monterey (Independence class), Booklet of General Plans, 1950 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cvl26.pdf](https://maritime.org/doc/plans/cvl26.pdf).
