# Systems inference notes — wright_cc2

Era: **USN cold-war / early mechanical AC** (`usn_coldwar`)

Berthing/officers mechanically conditioned; ops/electronics rooms AC; machinery forced draft.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| vm_island_stack | funnel | up | exhaust | Machinery_2P | sheet_read |
| vm_plenums_main | vent_trunk | unknown | supply | Mid_Voids_Main | sheet_read |
| vm_mushrooms_fd | mushroom | up | supply | Flight_Deck_Mid | sheet_read |
| vm_air_cond_main | fan_room | unknown | supply | Aft_Rooms_Main | sheet_read |
| vm_uptakes_gal | vent_trunk | unknown | exhaust | VIP_Gal | sheet_read |
| vm_fan_rooms_hangar | fan_room | unknown | supply | Command_Support_Hangar | sheet_read |
| vm_whip_antennas | mushroom | up | supply | Flight_Deck_Aft | era_plausible |
| vm_ac_machy_1p | fan_room | unknown | supply | AC_Refrig_1P | sheet_read |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Refrig_1P | mech_supply_exhaust | sheet_read |
| Aft_Berthing_Main | mech_ac | era_rule |
| Aft_Cells_2P | mech_ac | era_rule |
| Aft_Gallery | mech_ac | era_rule |
| Aft_Rooms_2nd | mech_ac | era_rule |
| Aft_Rooms_Main | mech_supply_exhaust | sheet_read |
| Aft_Shops_Hangar | mech_ac | era_rule |
| Aux_Machinery_1P | mech_supply_exhaust | era_rule |
| Bow_Cells_1P | mech_ac | era_rule |
| Bow_Cells_Hangar | mech_ac | era_rule |
| Bow_Gal | mech_ac | era_rule |
| Bow_Gear_Main | mech_ac | era_rule |
| Bow_Stores_2nd | mech_ac | era_rule |
| Bridge_Island | mech_ac | era_rule |
| COC_Hangar | mech_ac | era_rule |
| Command_Support_Hangar | mech_supply_exhaust | sheet_read |
| Comms_Aft_Gal | mech_ac | era_rule |
| Comms_Fwd_Gal | mech_ac | era_rule |
| Crew_Berthing_Aft_2nd | mech_ac | era_rule |
| Crew_Berthing_Aft_3rd | mech_ac | era_rule |
| Crew_Berthing_Fwd_2nd | mech_ac | era_rule |
| Crew_Berthing_Fwd_3rd | mech_ac | era_rule |
| Crew_Mess_2nd | mech_exhaust | era_rule |
| Crews_Shelters_Gal | mech_ac | era_rule |
| Elevator_Aft_FD | nat_supply | era_rule |
| Elevator_Pit_Main | nat_supply | era_rule |
| Elevator_Wells_Gal | mech_ac | era_rule |
| Emerg_Gen_Hold | mech_supply_exhaust | era_rule |
| FO_Wing_Port_Hold | mech_ac | era_rule |
| FO_Wing_Stbd_Hold | mech_ac | era_rule |
| Flight_Deck_Aft | nat_supply | era_plausible |
| Flight_Deck_Fwd | nat_supply | era_rule |
| Flight_Deck_Mid | nat_supply | sheet_read |
| Fwd_Cells_Hold | mech_ac | era_rule |
| Fwd_Services_2nd | mech_ac | era_rule |
| Fwd_Stores_1P | mech_ac | era_rule |
| Fwd_Stores_2P | mech_ac | era_rule |
| Fwd_Stores_3rd | mech_ac | era_rule |
| Gen_Machinery_2P | mech_supply_exhaust | era_rule |
| HD_Crew_Aft_2nd | exhaust_only | era_rule |
| HD_Crew_Aft_3rd | exhaust_only | era_rule |
| HD_Crew_Fwd_2nd | exhaust_only | era_rule |
| HD_Crew_Fwd_3rd | exhaust_only | era_rule |
| HD_Crew_Mid_2nd | exhaust_only | era_rule |
| Hangar_Bay_Aft | nat_supply | era_rule |
| Hangar_Bay_Fwd | nat_supply | era_rule |
| Island_Base_FD | nat_supply | era_rule |
| Island_Gal | mech_ac | era_rule |
| Island_Rooms | mech_ac | era_rule |
| Issue_Amidships_2nd | mech_ac | era_rule |
| Machinery_2P | mech_supply_exhaust | sheet_read |
| Medical_Main | mech_ac | era_rule |
| Mid_Voids_Main | nat_supply | sheet_read |
| Officers_Main | mech_ac | era_rule |
| Peak_Tank_2P | mech_ac | era_rule |
| Peak_Tank_Hold | mech_ac | era_rule |
| Ready_Rooms_Gal | mech_ac | era_rule |
| Services_Aft_3rd | mech_ac | era_rule |
| Services_Mid_2nd | mech_ac | era_rule |
| Shaft_Alley_1P | mech_supply_exhaust | era_rule |
| Shaft_Alley_2P | mech_supply_exhaust | era_rule |
| Staterooms_Hangar | mech_ac | era_rule |
| Stern_Cells_Hold | mech_ac | era_rule |
| Steward_Mess_Main | mech_exhaust | era_rule |
| Uptakes_1P | mech_supply_exhaust | era_rule |
| Uptakes_3rd | mech_supply_exhaust | era_rule |
| VIP_Gal | mech_exhaust | sheet_read |
| Wardroom_Main | mech_exhaust | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| F.O. CELLS (machinery wings) | fuel | Machinery_2P |
| F.O. / BALLAST (hold) | fuel | FO_Wing_Stbd_Hold |
| AVIATION FUEL CELLS | fuel | Stern_Cells_Hold |
| PEAK TANK | unknown | Peak_Tank_Hold |
| VOIDS (fwd) | unknown | Fwd_Stores_2P |

## Plumbing drains

- Steward_Mess_Main (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Steward_Mess_Main
- Wardroom_Main (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Wardroom_Main
- Medical_Main (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Medical_Main
- HD_Crew_Aft_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft_2nd
- Crew_Mess_2nd (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Crew_Mess_2nd
- HD_Crew_Mid_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Mid_2nd
- HD_Crew_Fwd_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Fwd_2nd
- HD_Crew_Aft_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Aft_3rd
- HD_Crew_Fwd_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew_Fwd_3rd

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.

## Source

U.S. Navy CC-2 USS Wright, Booklet of General Plans, 1965 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cc2.pdf](https://maritime.org/doc/plans/cc2.pdf).
