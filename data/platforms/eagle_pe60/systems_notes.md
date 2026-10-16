# Systems inference notes — eagle_pe60

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel | funnel | up | exhaust | Boiler_Rm | sheet_read |
| blower_mach | fan_room | unknown | supply | Engine_Rm | era_plausible |
| galley_vent | gooseneck | up | exhaust | Galley | era_plausible |
| cowl_fwd | cowl | fore | supply | Berthing_Main_2 | era_plausible |
| cowl_aft | cowl | fore | supply | Berthing_Main_1 | era_plausible |
| mag_vent | mushroom | up | exhaust | Magazine | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AA_Gun_Platforms | nat_supply | era_rule |
| After_Gun_Platform | nat_supply | era_rule |
| Aux_Radio_Room | nat_supply | era_rule |
| Berthing_Lwr | nat_supply | era_rule |
| Berthing_Main_1 | nat_supply | era_plausible |
| Berthing_Main_2 | nat_supply | era_plausible |
| Boiler_Rm | mech_supply_exhaust | sheet_read |
| Boiler_Rm_Lwr | mech_supply_exhaust | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Chain_Locker | nat_supply | era_rule |
| Chart_House | nat_supply | era_rule |
| Crew_Mess_Lwr | mech_exhaust | era_rule |
| Crew_WC | exhaust_only | era_rule |
| Eng_Rm_Lwr | mech_supply_exhaust | era_rule |
| Engine_Rm | mech_supply_exhaust | era_plausible |
| FO_Aft_Port | nat_supply | era_rule |
| FO_Aft_Stbd | nat_supply | era_rule |
| FO_Fwd | nat_supply | era_rule |
| FO_Tanks_Platform | nat_supply | era_rule |
| Fantail | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Fore_Peak_Plat | nat_supply | era_rule |
| Galley | mech_exhaust | era_plausible |
| Gun_Deck_Fwd | nat_supply | era_rule |
| Gun_Platform_Fwd | nat_supply | era_rule |
| Magazine | mech_exhaust | era_plausible |
| Mess_Room | mech_exhaust | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Head | exhaust_only | era_rule |
| Officers_Staterooms | nat_supply | era_rule |
| Open_Bridge | nat_supply | era_rule |
| Radio_Room | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Steering_Gear | nat_supply | era_rule |
| Stores_2P_1 | nat_supply | era_rule |
| Stores_2P_2 | nat_supply | era_rule |
| Stores_Aft | nat_supply | era_rule |
| Stores_Hold | nat_supply | era_rule |
| Sub_Signal_Rm | nat_supply | era_rule |
| WR_Staterooms | nat_supply | era_rule |
| Wardroom_Mess | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL D-106/D-107 | fuel | FO_Aft_Port |
| FUEL OIL A-104/A-105 | fuel | FO_Fwd |
| FRESH WATER | freshwater | Eng_Rm_Lwr |
| LUB OIL | fuel | Stores_2P_1 |
| FORE PEAK TANK | unknown | Fore_Peak |

## Plumbing drains

- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Officers_Head (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_Head
- Mess_Room (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Mess_Room
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- Crew_WC (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_WC
- Crew_Mess_Lwr (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_Lwr

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy PE-60 USS Eagle No. 60, Booklet of General Plans, 1918 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [pe60.pdf](https://maritime.org/doc/plans/pe60.pdf).
