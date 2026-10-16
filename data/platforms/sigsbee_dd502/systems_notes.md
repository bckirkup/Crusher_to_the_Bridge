# Systems inference notes — sigsbee_dd502

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| UPT_AftStack | uptake | up | exhaust | Fire_Rm_Aft | sheet_read |
| UPT_FwdStack | uptake | up | exhaust | Fire_Rm_Fwd | sheet_read |
| FUN_Aft | funnel | up | exhaust | Superstructure_Radio | sheet_read |
| FUN_Fwd | funnel | up | exhaust | Mt2_Deck | sheet_read |
| AI_Main_Port | air_port | up | supply | Uptake_Aft | sheet_read |
| VFS_Aft | fan_room | up | supply | HD_Crew_Aft | sheet_read |
| VENT_Laundry | vent_trunk | up | exhaust | Mid_Shops | sheet_read |
| FAN_Deckhouse | fan_room | up | supply | After_Deckhouse | sheet_read |
| CWL_Focsle | cowl | fore | supply | Focsle_Deck | era_plausible |
| MSH_Washroom | mushroom | up | exhaust | HD_Crew_Aft | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Shops | nat_supply | era_rule |
| Aft_Stores_2P | nat_supply | era_rule |
| Aft_Util | nat_supply | era_rule |
| After_Deckhouse | mech_supply_exhaust | sheet_read |
| Boatswain_Chain_3P | nat_supply | era_rule |
| CIC | nat_supply | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Crew_Berthing_Aft | nat_supply | era_rule |
| Crew_Berthing_Fwd | nat_supply | era_rule |
| Engine_Rm_Aft | mech_supply_exhaust | era_rule |
| Engine_Rm_Fwd | mech_supply_exhaust | era_rule |
| Fantail | nat_supply | era_rule |
| Fire_Rm_Aft | mech_supply_exhaust | sheet_read |
| Fire_Rm_Fwd | mech_supply_exhaust | sheet_read |
| Focsle_Deck | nat_supply | era_plausible |
| Fuel_Tanks_2P | mech_supply_exhaust | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_Hold | nat_supply | era_rule |
| Galley_Mess | mech_exhaust | era_rule |
| HD_Crew_Aft | exhaust_only | sheet_read |
| HD_Fwd | exhaust_only | era_rule |
| Magazine_Aft_2P | mech_supply_exhaust | era_rule |
| Magazine_Fwd_2P | mech_supply_exhaust | era_rule |
| Magazine_Fwd_3P | mech_supply_exhaust | era_rule |
| Magazines_Hold | mech_supply_exhaust | era_rule |
| Mid_Shops | mech_exhaust | sheet_read |
| Midship_Deckhouse | nat_supply | era_rule |
| Mt2_Deck | mech_supply_exhaust | sheet_read |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Peak_Hold | mech_supply_exhaust | era_rule |
| Provisions_2P | nat_supply | era_rule |
| Provisions_3P | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sound_Rm | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Superstructure_Radio | mech_supply_exhaust | sheet_read |
| Tanks_Hold | mech_supply_exhaust | era_rule |
| Torpedo_Workshop | nat_supply | era_rule |
| Uptake_Aft | nat_supply | sheet_read |
| Uptake_Fwd | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANKS (under machinery) | fuel | Fuel_Tanks_2P |
| RESERVE FEED + F.W. TANKS | freshwater | Fuel_Tanks_2P |
| PEAK TANK | unknown | Magazine_Fwd_2P |
| F.W./LUB OIL (hold) | freshwater | Tanks_Hold |

## Plumbing drains

- HD_Crew_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft
- Galley_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Mess
- HD_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
