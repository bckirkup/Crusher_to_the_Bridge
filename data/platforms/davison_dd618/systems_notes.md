# Systems inference notes — davison_dd618

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| UPT_AftStack | uptake | up | exhaust | Fire_Rm_Aft | sheet_read |
| UPT_FwdStack | uptake | up | exhaust | Fire_Rm_Fwd | sheet_read |
| AI_Main_Aft | air_port | up | supply | Uptake_Aft | sheet_read |
| AI_Main_Fwd | air_port | up | supply | Uptake_Fwd | sheet_read |
| EXTR_Fwd | fan_room | up | exhaust | Uptake_Fwd | sheet_read |
| VENT_PS | vent_trunk | up | exhaust | Super_Open | sheet_read |
| CWL_Focsle | cowl | fore | supply | Focsle_Open | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Ammo | mech_ac | era_rule |
| Aft_Shops | mech_ac | era_rule |
| Aft_Stores_2P | mech_ac | era_rule |
| After_Deckhouse_Top | nat_supply | era_rule |
| Bow_Focsle | nat_supply | era_rule |
| CIC_Block | mech_ac | era_rule |
| CPO_Quarters | mech_ac | era_rule |
| Crew_Berthing_1P | mech_ac | era_rule |
| Crew_Qtrs_1P | mech_ac | era_rule |
| Engine_Rm_Aft | mech_supply_exhaust | era_rule |
| Engine_Rm_Fwd | mech_supply_exhaust | era_rule |
| Fantail_MS | nat_supply | era_rule |
| Fire_Rm_Aft | mech_supply_exhaust | sheet_read |
| Fire_Rm_Fwd | mech_supply_exhaust | sheet_read |
| Focsle_Open | nat_supply | era_plausible |
| Fuel_Tanks_2P | mech_supply_exhaust | era_rule |
| Fuel_Tanks_Hold | mech_supply_exhaust | era_rule |
| Fwd_Stores_1P | mech_ac | era_rule |
| Fwd_Stores_Hold | mech_ac | era_rule |
| Galley_Mess | mech_exhaust | era_rule |
| HD_Crew_Aft | exhaust_only | era_rule |
| HD_Fwd | exhaust_only | era_rule |
| Magazine_Aft_2P | mech_supply_exhaust | era_rule |
| Magazine_Fwd_2P | mech_supply_exhaust | era_rule |
| Magazines_Hold | mech_supply_exhaust | era_rule |
| Mid_Services | mech_ac | era_rule |
| Midship_Deckhouse | nat_supply | era_rule |
| Nav_Bridge_Sonar | mech_ac | era_rule |
| Officers_Country_Focsle | mech_ac | era_rule |
| Peak_Hold | mech_supply_exhaust | era_rule |
| Provisions_2P | mech_ac | era_rule |
| Radio_Central | mech_ac | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Super_Open | mech_exhaust | sheet_read |
| Uptake_Aft | nat_supply | sheet_read |
| Uptake_Fwd | nat_supply | sheet_read |
| WR_Block | mech_ac | era_rule |
| Workshops_Mid | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O./F.W. TANKS (2P) | freshwater | Fuel_Tanks_2P |
| PEAK TANK | unknown | Magazine_Fwd_2P |

## Plumbing drains

- HD_Crew_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft
- Galley_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_Mess
- HD_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
