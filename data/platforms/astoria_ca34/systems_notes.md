# Systems inference notes — astoria_ca34

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| vm_vent_exhaust_36 | vent_trunk | up | exhaust | Upper_Deck_Aft | sheet_read |
| vm_vent_supply_duct | vent_trunk | up | supply | Upper_Deck_Aft | sheet_read |
| vm_blower_room | fan_room | unknown | supply | Flag_Quarters | sheet_read |
| vm_er_supply | fan_room | unknown | supply | Engine_Room_Aft | sheet_read |
| vm_er_exhaust | vent_trunk | unknown | exhaust | Engine_Room_Aft | sheet_read |
| vm_uptake_port | uptake | up | exhaust | Fire_Rooms | sheet_read |
| vm_uptake_stbd | uptake | up | exhaust | Fire_Rooms | sheet_read |
| vm_funnel | funnel | up | exhaust | Offices_2nd | sheet_read |
| vm_cowl_focsle | cowl | aft | exhaust | Focsle_Deck | sheet_read |
| vm_mushroom_wx | mushroom | up | exhaust | Boat_Deck | era_plausible |
| vm_mag_vents_aft | mushroom | unknown | exhaust | Aft_Magazines | era_plausible |
| vm_mag_vents_fwd | mushroom | unknown | exhaust | Fwd_Magazines | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Magazines | mech_exhaust | era_plausible |
| Aft_Stores_3rd | nat_supply | era_rule |
| After_Deckhouse | nat_supply | era_rule |
| Battery_Rooms | mech_supply_exhaust | era_rule |
| Bilge_Spaces_Aft | nat_supply | era_rule |
| Boat_Deck | mech_exhaust | era_plausible |
| Bridge_Wings | nat_supply | era_rule |
| CPO_Mess | mech_exhaust | era_rule |
| CPO_Quarters | nat_supply | era_rule |
| Catapult_Deck | nat_supply | era_rule |
| Chain_Locker | nat_supply | era_rule |
| Chart_House | nat_supply | era_rule |
| Cold_Storage | nat_supply | era_rule |
| Crew_Berthing_1P | nat_supply | era_rule |
| Crew_Berthing_1P_Fwd | nat_supply | era_rule |
| Crew_Berthing_Aft | nat_supply | era_rule |
| Crew_Berthing_Fwd | nat_supply | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Crew_Space_Fwd | nat_supply | era_rule |
| Dental_Unit | mech_supply_exhaust | era_rule |
| Engine_Room_Aft | mech_supply_exhaust | sheet_read |
| Engine_Room_Fwd | mech_supply_exhaust | era_rule |
| FW_Tanks_2P | nat_supply | era_rule |
| Fantail | nat_supply | era_rule |
| Fire_Rooms | mech_supply_exhaust | sheet_read |
| Flag_Plot | nat_supply | era_rule |
| Flag_Quarters | mech_supply_exhaust | sheet_read |
| Focsle_Deck | mech_exhaust | sheet_read |
| Forecastle_Stores | nat_supply | era_rule |
| Forepeak_1P | nat_supply | era_rule |
| Forepeak_Hold | nat_supply | era_rule |
| Forepeak_Stores | nat_supply | era_rule |
| Fuel_Oil_Tanks_Aft | nat_supply | era_rule |
| Fuel_Oil_Tanks_Mid | nat_supply | era_rule |
| Fwd_Gear_Stores | nat_supply | era_rule |
| Fwd_Magazines | mech_exhaust | era_plausible |
| Fwd_Stores_1P | nat_supply | era_rule |
| Fwd_Stores_3rd | nat_supply | era_rule |
| Fwd_Tanks | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| Gasoline_Room | nat_supply | era_rule |
| Gasoline_Tanks | nat_supply | era_rule |
| Gun_Gallery_01 | nat_supply | era_rule |
| HD_CPO | exhaust_only | era_rule |
| HD_Crew_2nd | exhaust_only | era_rule |
| HD_Crew_Fwd | exhaust_only | era_rule |
| HD_Crew_Upper | exhaust_only | era_rule |
| Hangar | nat_supply | era_rule |
| Hangar_Spares_Stbd | nat_supply | era_rule |
| Mid_Magazines | nat_supply | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Country | nat_supply | era_rule |
| Offices_2nd | mech_supply_exhaust | sheet_read |
| Peak_Tank | nat_supply | era_rule |
| Plot_Room | nat_supply | era_rule |
| Provisions_Low | nat_supply | era_rule |
| Provisions_Main | nat_supply | era_rule |
| Repair_Space | nat_supply | era_rule |
| SA_Magazines_Hold | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Superstructure_01 | nat_supply | era_rule |
| Upper_Deck_Aft | mech_exhaust | sheet_read |
| Wardroom | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. TANKS (stern rows) | fuel | Fuel_Oil_Tanks_Aft |
| F.O. TANKS (under machinery) | fuel | Fuel_Oil_Tanks_Mid |
| F.O. + FEED WATER (fwd) | fuel | Fwd_Tanks |
| A-1-GAS GASOLINE TANKS | unknown | Gasoline_Tanks |
| F.W. TANKS | freshwater | FW_Tanks_2P |
| PEAK TANK A-1-W | unknown | Peak_Tank |
| DIESEL OIL SERVICE TANK D-503-F | fuel | Shaft_Alley |
| RESERVE FEED WATER | freshwater | Shaft_Alley |

## Plumbing drains

- HD_Crew_Upper (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Upper
- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- CPO_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: CPO_Mess
- HD_CPO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Dental_Unit (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Dental_Unit
- HD_Crew_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CA-34 USS Astoria (New Orleans class), Booklet of General Plans, 1941 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [ca34.pdf](https://maritime.org/doc/plans/ca34.pdf).
