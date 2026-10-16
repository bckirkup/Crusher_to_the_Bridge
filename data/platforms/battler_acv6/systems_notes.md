# Systems inference notes — battler_acv6

Era: **Royal Navy WW2 practice** (`rn_ww2`)

Mushroom/cowl natural supply; mech exhaust galley/heads/engines; magazines sprinkled + vented.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel_island | funnel | up | exhaust | Funnel_Island | sheet_read |
| uptake_focsle | uptake | up | exhaust | Uptakes_Focsle | sheet_read |
| blower_rm_stbd | fan_room | unknown | supply | Focsle_Shops | sheet_read |
| portable_vent | fan_room | unknown | supply | Hangar_Fwd | sheet_read |
| cowls_bow | cowl | fore | supply | Bosns_1P | era_plausible |
| mag_vents_fwd | mushroom | up | exhaust | Magazine_Fwd | era_plausible |
| hangar_side | hangar_door | starboard | supply | Hangar_Fwd | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Amm_Fwd_Hold | nat_supply | era_rule |
| Arresting_Gear_Rm | mech_supply_exhaust | era_rule |
| Asdic_Office | nat_supply | era_rule |
| Aviation_Fwd_2P | nat_supply | era_rule |
| Bomb_Assembly | nat_supply | era_rule |
| Bomb_Magazine_Aft | nat_supply | era_rule |
| Bosns_1P | nat_supply | era_plausible |
| Bosns_2D | nat_supply | era_rule |
| Bosns_2P | nat_supply | era_rule |
| CPO_Berthing | nat_supply | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| Captains_Quarters | nat_supply | era_rule |
| Cold_Stores | nat_supply | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_2P | nat_supply | era_rule |
| Crew_Berthing_Fwd | nat_supply | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Crew_Shelters_Gal | nat_supply | era_rule |
| Diesel_Gen_Lower | mech_supply_exhaust | era_rule |
| Engine_Room | mech_supply_exhaust | era_rule |
| Flight_Deck | nat_supply | era_rule |
| Focsle_Shops | mech_supply_exhaust | sheet_read |
| Fuel_Oil_Fwd | nat_supply | era_rule |
| Funnel_Island | mech_supply_exhaust | sheet_read |
| GD_Stores_Hold | nat_supply | era_rule |
| Galley_2D | mech_exhaust | era_rule |
| Gasoline_Tanks | nat_supply | era_rule |
| Gun_Gallery_Fwd | nat_supply | era_rule |
| HD_2D_Aft | exhaust_only | era_rule |
| HD_2D_Fwd | exhaust_only | era_rule |
| HD_WR | exhaust_only | era_rule |
| Hangar_Aft | nat_supply | era_rule |
| Hangar_Fwd | mech_supply_exhaust | sheet_read |
| Hangar_Shops | nat_supply | era_rule |
| Island_Galley_Rm | nat_supply | era_rule |
| Island_Upper | nat_supply | era_rule |
| Laundry | nat_supply | era_rule |
| Machinery_Tanks | nat_supply | era_rule |
| Magazine_Fwd | mech_exhaust | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Ordnance_2P | nat_supply | era_rule |
| PO_Berthing_1P | nat_supply | era_rule |
| Parachute_Canvas_2P | nat_supply | era_rule |
| Peak_Tank | nat_supply | era_rule |
| Services_2P | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stores_Flat_Aft | nat_supply | era_rule |
| Uptakes_Focsle | mech_supply_exhaust | sheet_read |
| WR_Mess | mech_exhaust | era_rule |
| WR_Staterooms | nat_supply | era_rule |
| Walkways_Focsle | nat_supply | era_rule |
| Workshops_2D | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL (P&S) | fuel | Fuel_Oil_Fwd |
| CARGO FUEL OIL OR WATER BALLAST | fuel | Fuel_Oil_Fwd |
| GASOLINE TANK (P&S) | unknown | Gasoline_Tanks |
| DIESEL OIL (P) | fuel | Machinery_Tanks |
| DISTILLED WATER TK. (P) | unknown | Machinery_Tanks |
| CONT. OIL TANK (P&S) | fuel | Diesel_Gen_Lower |
| RESERVE FEED WATER (P&S) | freshwater | Machinery_Tanks |
| PEAK TANK | unknown | Peak_Tank |
| FIXED BALLAST | unknown | GD_Stores_Hold |
| F.W. & LUB. OIL (S) | freshwater | Hangar_Fwd |
| HYDROPHONE TANK (S) | unknown | Bomb_Magazine_Aft |

## Plumbing drains

- HD_2D_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Aft
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess
- Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_2D
- HD_WR (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_WR
- WR_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: WR_Mess
- HD_2D_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_2D_Fwd
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy ACV-6 HMS Battler D-18 (Attacker/Bogue class), Reference Plans, 1943 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [acv6.pdf](https://maritime.org/doc/plans/acv6.pdf).
