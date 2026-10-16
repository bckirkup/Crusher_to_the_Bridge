# Systems inference notes — saratoga_cv60

Era: **USN modern practice** (`usn_modern`)

Mechanical conditioning shipwide except open weather decks.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| VM_HangarDoor_Port_1 | hangar_door | port | supply | Hangar_Bay_1 | sheet_read |
| VM_HangarDoor_Port_2 | hangar_door | port | supply | Hangar_Bay_2 | sheet_read |
| VM_HangarDoor_Port_3 | hangar_door | port | supply | Hangar_Bay_3 | sheet_read |
| VM_HangarDoor_Stbd_1 | hangar_door | starboard | supply | Hangar_Bay_1 | sheet_read |
| VM_HangarDoor_Stbd_2 | hangar_door | starboard | supply | Hangar_Bay_2 | sheet_read |
| VM_HangarDoor_Stbd_3 | hangar_door | starboard | supply | Hangar_Bay_3 | sheet_read |
| VM_Uptake_1_2 | uptake | up | exhaust | Funnel_Uptake | sheet_read |
| VM_Uptake_3_4 | uptake | up | exhaust | Funnel_Uptake | sheet_read |
| VM_Funnel | funnel | up | exhaust | Funnel_Uptake | sheet_read |
| VM_FanRoom_Island | fan_room | unknown | supply | Island_Upper | sheet_read |
| VM_VentInlet_02 | vent_trunk | unknown | supply | Crew_Berthing_02_Aft | sheet_read |
| VM_VentInlet_01 | vent_trunk | unknown | supply | HD_01 | sheet_read |
| VM_Cowl_Wx_Aft | cowl | aft | supply | Flight_Deck | era_plausible |
| VM_Cowl_Wx_Fwd | cowl | fore | supply | Flight_Deck | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| AC_Machinery_01 | mech_supply_exhaust | era_rule |
| AG_Machinery_03 | mech_supply_exhaust | era_rule |
| AIMD_Shops_01 | mech_ac | era_rule |
| Aft_Stores_4D | mech_ac | era_rule |
| Aux_Machinery_1P_Aft | mech_supply_exhaust | era_rule |
| Aux_Machinery_1P_Fwd | mech_supply_exhaust | era_rule |
| Aviation_Support_Main | mech_ac | era_rule |
| Avionics_Shops_Main | mech_ac | era_rule |
| Bakery_FoodPrep_2D | mech_exhaust | era_rule |
| Bosn_Strm_Main | mech_supply_exhaust | era_rule |
| Brig_3D | mech_ac | era_rule |
| CIC_03 | mech_ac | era_rule |
| CPO_Berthing_02 | mech_ac | era_rule |
| CPO_Country_3D | mech_ac | era_rule |
| CPO_Mess_2D | mech_exhaust | era_rule |
| Catapult_Accum_Main | mech_supply_exhaust | era_rule |
| Catapult_Machinery_03 | mech_supply_exhaust | era_rule |
| Central_Control_4D | mech_ac | era_rule |
| Crew_Berthing_01 | mech_ac | era_rule |
| Crew_Berthing_02_Aft | nat_supply | sheet_read |
| Crew_Berthing_02_Mid | mech_ac | era_rule |
| Crew_Berthing_03_Aft | mech_ac | era_rule |
| Crew_Berthing_03_Mid | mech_ac | era_rule |
| Crew_Berthing_2D_Aft | mech_ac | era_rule |
| Crew_Berthing_2D_Fwd | mech_ac | era_rule |
| Crew_Berthing_3D_Aft | mech_ac | era_rule |
| Crew_Berthing_3D_Fwd | mech_ac | era_rule |
| Crew_Berthing_3D_Mid | mech_ac | era_rule |
| Crew_Mess_Galley_2D | mech_exhaust | era_rule |
| Crew_Rec_Library_2D | mech_ac | era_rule |
| Distilling_1P | mech_supply_exhaust | era_rule |
| Dry_Provision_4D | mech_ac | era_rule |
| Emergency_Generator_2D | mech_supply_exhaust | era_rule |
| Flag_Country_03 | mech_ac | era_rule |
| Flight_Deck | nat_supply | era_plausible |
| Funnel_Uptake | mech_supply_exhaust | sheet_read |
| HD_01 | exhaust_only | sheet_read |
| HD_02 | exhaust_only | era_rule |
| HD_03 | exhaust_only | era_rule |
| HD_2nd | exhaust_only | era_rule |
| HD_3rd | exhaust_only | era_rule |
| Hangar_Bay_1 | nat_supply | sheet_read |
| Hangar_Bay_2 | nat_supply | sheet_read |
| Hangar_Bay_3 | nat_supply | sheet_read |
| Heater_AC_02 | mech_supply_exhaust | era_rule |
| Inert_Stow_Hold | mech_ac | era_rule |
| Island_Upper | mech_supply_exhaust | sheet_read |
| JP5_Tanks_Hold | mech_supply_exhaust | era_rule |
| Laundry_3D | mech_ac | era_rule |
| Machinery_2D_Aft | mech_supply_exhaust | era_rule |
| Machinery_2P_Aft | mech_supply_exhaust | era_rule |
| Machinery_2P_Fwd | mech_supply_exhaust | era_rule |
| Machinery_3D | mech_supply_exhaust | era_rule |
| Machinery_Elec_4D | mech_supply_exhaust | era_rule |
| Magazines_1P | mech_ac | era_rule |
| Magazines_2P_Fwd | mech_ac | era_rule |
| Magazines_4D_Aft | mech_ac | era_rule |
| Magazines_4D_Fwd | mech_ac | era_rule |
| Main_Machinery_1P_Aft | mech_supply_exhaust | era_rule |
| Main_Machinery_1P_Fwd | mech_supply_exhaust | era_rule |
| Marine_Berthing_3D | mech_ac | era_rule |
| Marine_Office_01 | mech_ac | era_rule |
| Medical_2D | mech_ac | era_rule |
| Nav_Bridge | mech_ac | era_rule |
| Officers_Country_03 | mech_ac | era_rule |
| PriFly_FlagPlot | mech_ac | era_rule |
| Pump_Room_Hold | mech_supply_exhaust | era_rule |
| Shaft_Alley_Hold | mech_supply_exhaust | era_rule |
| Ship_Store_2D | mech_ac | era_rule |
| Shops_3D | mech_ac | era_rule |
| Sply_Offices_02 | mech_ac | era_rule |
| Sply_Strm_01 | mech_ac | era_rule |
| Sply_Strm_3D_Fwd | mech_ac | era_rule |
| Squadron_Ready_03 | mech_ac | era_rule |
| Squadron_Ready_2D | mech_ac | era_rule |
| Steering_Gear_3D | mech_supply_exhaust | era_rule |
| Steering_Gear_4D | mech_supply_exhaust | era_rule |
| Switchboard_1P | mech_supply_exhaust | era_rule |
| Tanks_2P | mech_supply_exhaust | era_rule |
| WO_Mess_3D | mech_exhaust | era_rule |
| Wardroom_03 | mech_exhaust | era_rule |
| Wardroom_Country_2D | mech_ac | era_rule |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| JP-5 OR BLST TK 8-69-7-J | unknown | Pump_Room_Hold |
| JP-5 OR BLST TK 8-84-7-J | unknown | Inert_Stow_Hold |
| JP-5 OVFL OR 8-84-8-J | unknown | Inert_Stow_Hold |
| JP-5 OR BLST TANK 8-49-0-J | unknown | Pump_Room_Hold |
| JP-5 SERVICE TK 6-90-1-J | unknown | Magazines_2P_Fwd |
| OILY WASTE HOLDING TK 8-117-F | sewage | Shaft_Alley_Hold |
| PEAK TANK 6-50-W | unknown | Sply_Strm_3D_Fwd |
| PEAK TANK 8-0-0-W | unknown | Sply_Strm_3D_Fwd |
| BREAKWATER TANK NO.4 | unknown | Wardroom_03 |
| F.O. SETTLING TK 7-141-?-F | fuel | Main_Machinery_1P_Aft |
| SUMP TK (AIR EJECTOR) | unknown | Shaft_Alley_Hold |
| UNDERWATER LOG STWG | unknown | Inert_Stow_Hold |
| POTABLE WATER TK | freshwater | Pump_Room_Hold |
| VOID DC | unknown | Shaft_Alley_Hold |

## Plumbing drains

- Wardroom_03 (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_03 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_02 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_01 (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- Crew_Mess_Galley_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- Bakery_FoodPrep_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- Medical_2D (Medical) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- CPO_Mess_2D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_2nd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- WO_Mess_3D (Dining) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold
- HD_3rd (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: Shaft_Alley_Hold

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
