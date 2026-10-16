# Systems inference notes — gosper_apa170

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel | funnel | up | exhaust | Engine_Boiler_Room | sheet_read |
| v_main_deck_1 | cowl | fore | supply | Passage_Main | sheet_read |
| v_main_deck_2 | cowl | fore | supply | Troop_Berthing_Fwd | sheet_read |
| v_focsle | cowl | fore | supply | Focsle_Deck_Open | sheet_read |
| v_fan_room | fan_room | unknown | supply | Fan_Room_Boat | sheet_read |
| v_stores_flat | fan_room | unknown | exhaust | Emergency_Generator_Rm | sheet_read |
| v_magazines | mushroom | unknown | supply | Magazines_Aft | era_plausible |
| v_holds | gooseneck | up | exhaust | Cargo_Hold_4_Lower | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Aft_Deckhouse | nat_supply | era_rule |
| Aft_Peak_Tanks | nat_supply | era_rule |
| Ammunition_Fwd | nat_supply | era_rule |
| Aux_Machinery_Flat | mech_supply_exhaust | era_rule |
| Boat_Deck_Open | nat_supply | era_rule |
| Boat_Deck_Open_Fwd | nat_supply | era_rule |
| Boat_Stowage_Deck | nat_supply | era_rule |
| Bosuns_Stores_Fwd | nat_supply | era_rule |
| CIC | nat_supply | era_rule |
| CPO_Berthing | nat_supply | era_rule |
| Cargo_3D | nat_supply | era_rule |
| Cargo_Hold_4_Lower | mech_exhaust | era_plausible |
| Cargo_Hold_5_Lower | nat_supply | era_rule |
| Cargo_Hold_5_Top | nat_supply | era_rule |
| Crew_Berthing_2D | nat_supply | era_rule |
| Crew_Berthing_3D | nat_supply | era_rule |
| Crew_Mess_2D | mech_exhaust | era_rule |
| Diesel_FO_Tanks_Aft | nat_supply | era_rule |
| Dry_Stores_1P | nat_supply | era_rule |
| Emergency_Generator_Rm | mech_supply_exhaust | sheet_read |
| Engine_Boiler_Room | mech_supply_exhaust | sheet_read |
| Evaporator_Room | mech_supply_exhaust | era_rule |
| FO_Tanks_Fwd | nat_supply | era_rule |
| Fan_Room_Boat | mech_supply_exhaust | sheet_read |
| Fantail | nat_supply | era_rule |
| Focsle_Deck_Open | nat_supply | sheet_read |
| Focsle_Stores | nat_supply | era_rule |
| Focsle_Stores_2D | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Fore_Peak_1P | nat_supply | era_rule |
| Fore_Peak_Tank | nat_supply | era_rule |
| Fwd_Hold_1P | nat_supply | era_rule |
| Fwd_Stores_1P | nat_supply | era_rule |
| Galley_2D | mech_exhaust | era_rule |
| HD_Crew_Aft | exhaust_only | era_rule |
| HD_Crew_Fwd | exhaust_only | era_rule |
| HD_Officers | exhaust_only | era_rule |
| HD_Troop_Aft | exhaust_only | era_rule |
| HD_Troop_Fwd | exhaust_only | era_rule |
| HD_Troop_Officers | exhaust_only | era_rule |
| Isolation_Ward | mech_supply_exhaust | era_rule |
| Machinery_Casing | mech_supply_exhaust | era_rule |
| Machinery_Casing_2D | mech_supply_exhaust | era_rule |
| Magazines_Aft | nat_supply | era_plausible |
| Main_Deck_Open_Fwd | nat_supply | era_rule |
| Medical_Block | mech_supply_exhaust | era_rule |
| Nav_Bridge | nat_supply | era_rule |
| Officers_Offices_Main | nat_supply | era_rule |
| Officers_Qtrs_Boat | nat_supply | era_rule |
| Officers_Qtrs_Cabin | nat_supply | era_rule |
| Passage_2D | nat_supply | era_rule |
| Passage_Main | nat_supply | sheet_read |
| Provisions_3D | nat_supply | era_rule |
| Radio_Central | nat_supply | era_rule |
| Services_2D | nat_supply | era_rule |
| Shaft_Alley | mech_supply_exhaust | era_rule |
| Sick_Bay | mech_supply_exhaust | era_rule |
| Signal_TopHouse | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Stores_Flat_Aft | nat_supply | era_rule |
| Troop_Berthing_2D_Aft | nat_supply | era_rule |
| Troop_Berthing_2D_Fwd | nat_supply | era_rule |
| Troop_Berthing_3D_Aft | nat_supply | era_rule |
| Troop_Berthing_3D_Bow | nat_supply | era_rule |
| Troop_Berthing_3D_Mid | nat_supply | era_rule |
| Troop_Berthing_Fwd | nat_supply | sheet_read |
| Troop_Cargo_Hold | nat_supply | era_rule |
| Troop_Officers_Berthing | nat_supply | era_rule |
| Wardroom_Galley | mech_exhaust | era_rule |
| Wardroom_Mess | mech_exhaust | era_rule |
| Windlass_Room | mech_supply_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| AFT PEAK TANK C-1-W | unknown | Aft_Peak_Tanks |
| F.W. C-901-W | freshwater | Cargo_Hold_5_Top |
| F.O. tank A-501-1F | fuel | Troop_Berthing_Fwd |
| F.O. TANK A-502-M | fuel | Troop_Berthing_3D_Bow |
| FORE PEAK TANK A-1-W | unknown | Bosuns_Stores_Fwd |
| FRESH FROZEN 15F | freshwater | Wardroom_Galley |
| RESERVE FEED WATER B-908-W | freshwater | — |
| DIESEL OIL STORAGE | fuel | — |

## Plumbing drains

- HD_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Officers
- Medical_Block (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Medical_Block
- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Isolation_Ward (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Isolation_Ward
- HD_Troop_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_Aft
- Wardroom_Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Galley
- Wardroom_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Mess
- HD_Troop_Officers (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_Officers
- HD_Troop_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Troop_Fwd
- HD_Crew_Aft (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft
- Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley_2D
- Crew_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2D
- HD_Crew_Fwd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Fwd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy APA-170 USS Gosper (Haskell class), Booklet of General Plans, 1944 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [apa170.pdf](https://maritime.org/doc/plans/apa170.pdf).
