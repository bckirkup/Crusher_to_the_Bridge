# Systems inference notes — mercury_aks20

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| Funnel | funnel | up | exhaust | Eng_Casing | sheet_read |
| KD_Vents_Fwd_P | mushroom | up | supply | Hatch_2 | sheet_read |
| KD_Vents_Fwd_S | mushroom | up | supply | Hatch_1 | sheet_read |
| Cowl_Focsle | cowl | fore | supply | Foredeck | sheet_read |
| Vent_Stern | vent_trunk | unknown | unknown | Fantail | sheet_read |
| Gooseneck_ER | gooseneck | down | supply | Engine_Room | era_plausible |
| Mushroom_Mess | mushroom | fore | supply | Crew_Mess | era_plausible |
| Mag_Vent | mushroom | up | exhaust | Magazines_Fwd | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Ammo_Fwd | mech_ac | era_rule |
| Bakery | mech_ac | era_rule |
| Ballast_Tanks_Aft | mech_supply_exhaust | era_rule |
| Boat_Stowage | nat_supply | era_rule |
| Bosns_Stores_3rd | mech_ac | era_rule |
| Bosuns_Stores_2nd | mech_ac | era_rule |
| CPO_Pantry_Issue | mech_ac | era_rule |
| CPO_Quarters | mech_ac | era_rule |
| Cargo_Aft_1P | nat_supply | era_rule |
| Cargo_Aft_2nd | nat_supply | era_rule |
| Cargo_Aft_3rd | nat_supply | era_rule |
| Cargo_Clothing | nat_supply | era_rule |
| Cargo_Fwd_1P | nat_supply | era_rule |
| Cargo_Fwd_3rd | nat_supply | era_rule |
| Cargo_Hold_Aft | nat_supply | era_rule |
| Cargo_Hold_Fwd | nat_supply | era_rule |
| Chain_Locker_Peak | nat_supply | era_rule |
| Crew_Berthing_2nd | mech_ac | era_rule |
| Crew_Berthing_3rd | mech_ac | era_rule |
| Crew_Berthing_Shelter | mech_ac | era_rule |
| Crew_Mess | nat_supply | era_plausible |
| Deep_Tanks | mech_ac | era_rule |
| Dry_Provisions | mech_ac | era_rule |
| Electronic_Stores | mech_ac | era_rule |
| Emerg_Gen_Rm | mech_supply_exhaust | era_rule |
| Emerg_Radio | mech_ac | era_rule |
| Eng_Bilge | mech_supply_exhaust | era_rule |
| Eng_Casing | mech_supply_exhaust | sheet_read |
| Eng_Casing_2nd | mech_supply_exhaust | era_rule |
| Eng_Casing_3rd | mech_supply_exhaust | era_rule |
| Eng_Office | mech_ac | era_rule |
| Eng_Stores_Laundry | mech_ac | era_rule |
| Engine_Room | mech_supply_exhaust | era_plausible |
| Fantail | nat_supply | sheet_read |
| Foredeck | nat_supply | sheet_read |
| Forepeak_2nd | nat_supply | era_rule |
| Galley | mech_exhaust | era_rule |
| HD_CPO | exhaust_only | era_rule |
| HD_Crew_2nd | exhaust_only | era_rule |
| HD_Crew_Shelter | exhaust_only | era_rule |
| Hatch_1 | nat_supply | sheet_read |
| Hatch_2 | nat_supply | sheet_read |
| Hatch_3 | nat_supply | era_rule |
| Magazines_Fwd | mech_exhaust | era_plausible |
| Nav_Bridge | nat_supply | era_rule |
| Nav_Store_Armory | mech_ac | era_rule |
| Officers_Country | mech_ac | era_rule |
| Pay_Supply_Office | mech_ac | era_rule |
| Post_Office_Disb | mech_ac | era_rule |
| Pump_Room | mech_supply_exhaust | era_rule |
| Refrig_Machinery | mech_supply_exhaust | era_rule |
| Refrigerated_2nd | nat_supply | era_rule |
| Refrigerated_3rd | nat_supply | era_rule |
| Refrigeration_Rm | mech_supply_exhaust | era_rule |
| Scullery | mech_ac | era_rule |
| Ships_Store_Cargo | mech_ac | era_rule |
| Sick_Bay | mech_ac | era_rule |
| Signal_Shelter | nat_supply | era_rule |
| Steering_Gear | mech_supply_exhaust | era_rule |
| Storeroom_Flat | mech_ac | era_rule |
| Stores_Fwd_3rd | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| STORM OIL TANK | fuel | Forepeak_2nd |
| SETTLING TANK B-851-F | unknown | Cargo_Hold_Aft |
| LIQUID BALLAST C-509-W | unknown | Ballast_Tanks_Aft |
| D.B. TANK P&S (inner bottom) | unknown | Cargo_Hold_Fwd |
| F.O. (inflatables F.O. drums hold fwd) | fuel | Dry_Provisions |
| T.W. tanks shelter house | unknown | HD_Crew_Shelter |

## Plumbing drains

- Sick_Bay (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Sick_Bay
- Galley (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Galley
- HD_CPO (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_CPO
- HD_Crew_Shelter (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Shelter
- Crew_Mess (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess
- HD_Crew_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_2nd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy AKS-20 USS Mercury, Booklet of General Plans, 1949 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [aks20.pdf](https://maritime.org/doc/plans/aks20.pdf).
