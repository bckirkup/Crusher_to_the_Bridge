# Systems inference notes — fletcher_dde_dd445

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_Fwd | funnel | up | exhaust | Fwd_Machinery_1P | sheet_read |
| Funnel_Aft | funnel | up | exhaust | Aft_Machinery_1P | sheet_read |
| Vent_Focsle | cowl | fore | supply | Fwd_Stores_1P | era_plausible |
| Mag_Vent_2P | mushroom | unknown | exhaust | Aft_Stores_2P | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Deckhouse | nat_supply | era_rule |
| Aft_Machinery_1P | mech_supply_exhaust | sheet_read |
| Aft_Stores_1P | nat_supply | era_rule |
| Aft_Stores_2P | mech_exhaust | era_plausible |
| Ammo_Handling_Aft | nat_supply | era_rule |
| Ammo_Handling_Fwd | nat_supply | era_rule |
| CPO_Berthing_1P | nat_supply | era_rule |
| CPO_Messing | mech_exhaust | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_2P | nat_supply | era_rule |
| Emerg_Diesel_Batt | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Focsle_Main | nat_supply | era_rule |
| Fuel_Oil_Svc_1P | mech_supply_exhaust | era_rule |
| Fuel_Tanks_Hold | mech_supply_exhaust | era_rule |
| Fwd_Hold | nat_supply | era_rule |
| Fwd_Machinery_1P | mech_supply_exhaust | sheet_read |
| Fwd_Stores_1P | nat_supply | era_plausible |
| Fwd_Stores_2P | nat_supply | era_rule |
| Fwd_Tanks_2P | mech_supply_exhaust | era_rule |
| Galley_Mess_Main | mech_exhaust | era_rule |
| Gen_Wkshop | nat_supply | era_rule |
| HD_Crew_Fwd | exhaust_only | era_rule |
| HD_WR_1P | exhaust_only | era_rule |
| IC_Plotting | nat_supply | era_rule |
| Machinery_2P | mech_supply_exhaust | era_rule |
| Machinery_Bottom_Hold | mech_supply_exhaust | era_rule |
| Officers_Country_1P | nat_supply | era_rule |
| Officers_Country_Main | nat_supply | era_rule |
| Pilot_House_CIC | nat_supply | era_rule |
| Radio_Room_01 | nat_supply | era_rule |
| Ships_Office | nat_supply | era_rule |
| Ships_Service_Store | nat_supply | era_rule |
| Sonar_Block_2P | nat_supply | era_rule |
| Uptakes_Mid | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL SERVICE TANK | fuel | Fuel_Oil_Svc_1P |
| RESERVE FEED WATER | freshwater | Fwd_Tanks_2P |
| FRESH WATER | freshwater | Fwd_Tanks_2P |
| FUEL OIL OR BALLAST | fuel | Fuel_Tanks_Hold |

## Plumbing drains

- Galley_Mess_Main (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Mess_Main
- HD_WR_1P (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_WR_1P
- CPO_Messing (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Messing
- HD_Crew_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy DD-445 USS Fletcher, DDE conversion study drawing, 1950 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [dd445.pdf](https://maritime.org/doc/plans/dd445.pdf).
