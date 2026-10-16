# Systems inference notes — nields_dd616

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| UPT_AftStack | uptake | up | exhaust | Fire_Rm_Aft | sheet_read |
| UPT_FwdStack | uptake | up | exhaust | Fire_Rm_Fwd | sheet_read |
| AI_Main_Aft | air_port | up | supply | Uptake_Aft | sheet_read |
| AI_Main_Fwd | air_port | up | supply | Uptake_Fwd | sheet_read |
| VFS_Aft | fan_room | up | supply | Aft_Ammo | sheet_read |
| VENT_Laundry | vent_trunk | up | exhaust | Galley_Area | sheet_read |
| FAN_Deckhouse | fan_room | up | supply | Midship_Deckhouse | sheet_read |
| CWL_Focsle | cowl | fore | supply | Focsle_Open | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Ammo | mech_supply_exhaust | sheet_read |
| Aft_Shops | nat_supply | era_rule |
| Aft_Stores_2P | nat_supply | era_rule |
| After_Deckhouse_Top | nat_supply | era_rule |
| Bow_Focsle | nat_supply | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Qtrs_1P | nat_supply | era_rule |
| Engine_Rm_Aft | mech_supply_exhaust | era_rule |
| Engine_Rm_Fwd | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Fire_Rm_Aft | mech_supply_exhaust | sheet_read |
| Fire_Rm_Fwd | mech_supply_exhaust | sheet_read |
| Focsle_Open | nat_supply | era_plausible |
| Fuel_Tanks_2P | mech_supply_exhaust | era_rule |
| Fuel_Tanks_Hold | mech_supply_exhaust | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_Hold | nat_supply | era_rule |
| Galley_Area | mech_exhaust | sheet_read |
| HD_Crew_Aft | exhaust_only | era_rule |
| HD_Fwd | exhaust_only | era_rule |
| Magazine_Aft_2P | mech_supply_exhaust | era_rule |
| Magazine_Fwd_2P | mech_supply_exhaust | era_rule |
| Magazines_Hold | mech_supply_exhaust | era_rule |
| Mid_Services | nat_supply | era_rule |
| Midship_Deckhouse | mech_supply_exhaust | sheet_read |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country_Focsle | nat_supply | era_rule |
| Peak_Hold | mech_supply_exhaust | era_rule |
| Provisions_2P | nat_supply | era_rule |
| Radar_Plot | nat_supply | era_rule |
| Radio_Central | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Super_Open | nat_supply | era_rule |
| Uptake_Aft | nat_supply | sheet_read |
| Uptake_Fwd | nat_supply | sheet_read |
| WR_Block | nat_supply | era_rule |
| Workshops_Mid | nat_supply | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O./BALLAST + LUB OIL TANKS | fuel | Fuel_Tanks_2P |
| RESERVE FEED + F.W. TANKS | freshwater | Fuel_Tanks_2P |
| PEAK TANK A-1W | unknown | Magazine_Fwd_2P |

## Plumbing drains

- HD_Crew_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft
- Galley_Area (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Area
- HD_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
