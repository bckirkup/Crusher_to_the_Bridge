# Systems inference notes — rolla_pc483

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| funnel | funnel | up | exhaust | Engine_Rm | sheet_read |
| vent_trunk_mid | gooseneck | up | exhaust | Wardroom | sheet_read |
| galley_vent | gooseneck | up | exhaust | Galley | era_plausible |
| cowl_fwd | cowl | fore | supply | Crew_Quarters | era_plausible |
| mag_vent | mushroom | up | exhaust | Mag_3in | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Ammo_Stow_2P | nat_supply | era_rule |
| Berthing_2P | nat_supply | era_rule |
| Berthing_Fwd | nat_supply | era_rule |
| Berthing_Mid | nat_supply | era_rule |
| Chart_House | nat_supply | era_rule |
| Cont_Oil | nat_supply | era_rule |
| Crew_Head | exhaust_only | era_rule |
| Crew_Mess | mech_exhaust | era_rule |
| Crew_Quarters | nat_supply | era_plausible |
| Eng_Casing | mech_supply_exhaust | era_rule |
| Engine_Rm | mech_supply_exhaust | sheet_read |
| Engineers_Stores | nat_supply | era_rule |
| Fantail | nat_supply | era_rule |
| Focsle_Deck | nat_supply | era_rule |
| Fore_Peak | nat_supply | era_rule |
| Fuel_Oil_Aft | nat_supply | era_rule |
| Fuel_Oil_Fwd | nat_supply | era_rule |
| Galley | mech_exhaust | era_plausible |
| Galley_Stores | nat_supply | era_rule |
| Mag_3in | mech_exhaust | era_plausible |
| Officers_Berthing | nat_supply | era_rule |
| Officers_WC | exhaust_only | era_rule |
| Peak_2P | nat_supply | era_rule |
| Pilot_House | nat_supply | era_rule |
| Radio_Room | nat_supply | era_rule |
| Steering_Gear | nat_supply | era_rule |
| Stores_2P | nat_supply | era_rule |
| Stowage_Mid | nat_supply | era_rule |
| Void_Shaft | nat_supply | era_rule |
| Wardroom | mech_exhaust | sheet_read |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL OIL C-202-F | fuel | Mag_3in |
| FUEL OIL C-302-F | fuel | Fuel_Oil_Fwd |
| CONT OIL C-303-T | fuel | Cont_Oil |
| F.O. / L.O. SETTLING | fuel | Stores_2P |
| PEAK TANK A-301-W | unknown | Officers_Berthing |
| FRESH WATER | freshwater | Ammo_Stow_2P |

## Plumbing drains

- Wardroom (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom
- Officers_WC (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Officers_WC
- Crew_Head (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Head
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy PC-483 USS Rolla (Bluffton sub-chaser class), Booklet of General Plans, 1942 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [pc483.pdf](https://maritime.org/doc/plans/pc483.pdf).
