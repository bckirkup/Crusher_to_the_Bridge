# Systems inference notes — hunter_killer_dd692

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel_Fwd | funnel | up | exhaust | Fwd_Machinery_1P | sheet_read |
| Funnel_Aft | funnel | up | exhaust | Aft_Machinery_1P | sheet_read |
| Vents_01 | air_shaft | up | supply | Radio_Block_01 | sheet_read |
| Vent_Focsle | cowl | fore | supply | Fwd_Peak_1P | era_plausible |
| Mag_Vent_3P | mushroom | unknown | exhaust | Ammo_Mag_3P | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_1P | nat_supply | era_rule |
| Aft_Deckhouse | nat_supply | era_rule |
| Aft_Machinery_1P | mech_supply_exhaust | sheet_read |
| Aft_Voids_2P | nat_supply | era_rule |
| Ammo_Mag_3P | mech_exhaust | era_plausible |
| Berthing_Mid | nat_supply | era_rule |
| Boat_Deck_01 | nat_supply | era_rule |
| CIC_01 | nat_supply | era_rule |
| CPO_1P | nat_supply | era_rule |
| CPO_Ship_Office | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_2P | nat_supply | era_rule |
| Crew_Berthing_Fwd | nat_supply | era_rule |
| Emerg_Diesel_2P | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Focsle_Fwd | nat_supply | era_rule |
| Fuel_Tanks_Hold | mech_supply_exhaust | era_rule |
| Fwd_Hold | nat_supply | era_rule |
| Fwd_Machinery_1P | mech_supply_exhaust | sheet_read |
| Fwd_Mount_Deck | nat_supply | era_rule |
| Fwd_Peak_1P | nat_supply | era_plausible |
| Fwd_Stores_2P | nat_supply | era_rule |
| Fwd_Tanks_Hold | mech_supply_exhaust | era_rule |
| Galley | mech_exhaust | era_rule |
| HD_Crew_1P | exhaust_only | era_rule |
| HD_Crew_Main | exhaust_only | era_rule |
| HD_Officers_1P | exhaust_only | era_rule |
| HD_WR_Main | exhaust_only | era_rule |
| IC_Plot_1P | nat_supply | era_rule |
| Launcher_Deck_01 | nat_supply | era_rule |
| Machinery_2P | mech_supply_exhaust | era_rule |
| Machinery_Bottom_Hold | mech_supply_exhaust | era_rule |
| Messing_Mid | mech_exhaust | era_rule |
| Officers_01 | nat_supply | era_rule |
| Officers_1P | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Paint_3P | nat_supply | era_rule |
| Peak_3P | nat_supply | era_rule |
| Peak_Hold | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Provisions_2P | nat_supply | era_rule |
| Radio_Block_01 | mech_supply_exhaust | sheet_read |
| Ready_Svc_1P | nat_supply | era_rule |
| Rocket_Mags_3P | nat_supply | era_rule |
| Sea_Cabin | nat_supply | era_rule |
| Shop_1P | nat_supply | era_rule |
| Shop_Fwd_1P | nat_supply | era_rule |
| Signal_Bridge | nat_supply | era_rule |
| Signal_Lookout | nat_supply | era_rule |
| Sonar_2P | nat_supply | era_rule |
| Sonar_3P | nat_supply | era_rule |
| Sonar_Fwd_3P | nat_supply | era_rule |
| Stack_Uptake_01 | mech_supply_exhaust | era_rule |
| Stores_2P | nat_supply | era_rule |
| Tactical_Plot | nat_supply | era_rule |
| Torpedo_Deck | nat_supply | era_rule |
| Torpedo_Room | nat_supply | era_rule |
| UWB_Plot_2P | nat_supply | era_rule |
| Uptake_Mid | mech_supply_exhaust | era_rule |
| WR_Mess | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL SERVICE TANK | fuel | Fwd_Machinery_1P |
| RESERVE FEED WATER | freshwater | Machinery_2P |
| FRESH WATER | freshwater | Emerg_Diesel_2P |
| FUEL OIL OR BALLAST | fuel | Fuel_Tanks_Hold |
| LUB OIL SETTLING TANK | fuel | Emerg_Diesel_2P |

## Plumbing drains

- HD_Crew_1P (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_1P
- HD_Officers_1P (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers_1P
- HD_Crew_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Main
- Messing_Mid (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Messing_Mid
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- WR_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: WR_Mess
- HD_WR_Main (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_WR_Main

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
