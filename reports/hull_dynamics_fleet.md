# Hull dynamics audit — fleet report

## Drainage fingerprint (check 7)

| platform | zones | retained 12h | retained 24h | retained final | top accumulating |
|---|---|---|---|---|---|
| bolster_ars38 | 24 | 0.431 | 0.398 | 0.371 | HD_Main(7), Focsle_Deck_Open(1), Focsle_Open_Aft(1) |
| cannon_de701 | 32 | 0.169 | 0.149 | 0.132 | HD_Crew(3), Gun_Deck_Open(1), Focsle_Deck(0) |
| castle_class_corvette | 19 | 0.381 | 0.364 | 0.349 | HD_Upper(3), HD_Foc(3), Quarterdeck(0) |
| classic_cruise_1900 | 79 | 0.269 | 0.267 | 0.265 | HD_4M_M(1), HD_5L_F(1), HD_9L_F(1) |
| davison_dd618 | 39 | 0.268 | 0.262 | 0.259 | HD_Crew_Aft(3), HD_Fwd(3), After_Deckhouse_Top(1) |
| destroyer_baseline | 9 | 0.548 | 0.548 | 0.548 | HD_MAIN_M(2), HD_MAIN_F(2), HD_UPPER_M(1) |
| enterprise_constitution_tos | 63 | 0.413 | 0.413 | 0.413 | HD_4S_F(2), HD_4S_M(2), HD_6S_M(2) |
| enterprise_galaxy_tng | 127 | 0.356 | 0.356 | 0.356 | HD_13S_F(1), HD_6S_M(1), HD_13S_M(1) |
| expedition_cruise_300 | 36 | 0.374 | 0.370 | 0.364 | HD_5P_F(1), HD_5P_M(1), HD_6E_F(1) |
| expedition_cruise_450 | 47 | 0.379 | 0.377 | 0.373 | HD_5P_F(2), HD_5P_M(2), HD_7S_F(1) |
| fletcher_class_destroyer | 33 | 0.561 | 0.561 | 0.561 | HD_MAINDEC_M(2), HD_02L_M(2), HD_MAINDEC_F(2) |
| gordon_gunter_r338 | 35 | 0.455 | 0.443 | 0.425 | HD_Focsle(3), HD_Upper(3), HD_Bridge(3) |
| independence_cvl26 | 46 | 0.183 | 0.182 | 0.182 | HD_Main(3), HD_3rd(3), HD_2nd(2) |
| legend_class_nsc | 27 | 0.418 | 0.418 | 0.418 | HD_MAINDEC_M(2), HD_MAINDEC_F(2), HD_01L_F(1) |
| mega_cruise_5000 | 192 | 0.381 | 0.381 | 0.380 | HD_6A_M(1), HD_6A_F_2(1), HD_6A_F_1(1) |
| messy_cruise_500 | 130 | 0.540 | 0.540 | 0.539 | HD_5P_F_1(1), HD_5P_F_3(1), HD_5P_F_2(1) |
| midway_cv41 | 65 | 0.112 | 0.112 | 0.112 | HD_02(3), HD_2nd(2), HD_3rd(2) |
| nields_dd616 | 39 | 0.262 | 0.251 | 0.243 | HD_Crew_Aft(3), HD_Fwd(3), After_Deckhouse_Top(1) |
| passumpsic_ao106 | 27 | 0.202 | 0.189 | 0.172 | HD_Crew(3), Working_Deck(1), Island_Deck(1) |
| pce_874 | 20 | 0.229 | 0.215 | 0.211 | HD_Crew(4), Fantail(0) |
| raven_am55 | 21 | 0.375 | 0.360 | 0.339 | HD_Main(3), Bosn_Gear(1), Foc_Deck_Fwd(1) |
| ruchamkin_apd89 | 32 | 0.177 | 0.156 | 0.140 | HD_Crew(3), Boat_Deck_Open(1), Focsle_Deck(0) |
| san_antonio_class_lpd | 29 | 0.277 | 0.277 | 0.277 | HD_2N_M(1), HD_2N_F(1), HD_07L_M(1) |
| sigsbee_dd502 | 41 | 0.233 | 0.219 | 0.211 | HD_Crew_Aft(4), HD_Fwd(3), Midship_Deckhouse(1) |
| spirit_cruise_3000 | 115 | 0.318 | 0.317 | 0.313 | HD_6C_F(1), HD_10L_M(1), HD_5L_M(1) |

## Occupancy smoke (check 6)

### bolster_ars38 (manifest=90)
- **unresolvable duty pins: engine_room→Engine_Rm, corpsman→Sick_Bay**
- `default`: visited=17 never_occupied=6 overflow=6 home_distinct=5 manifest_berth_hit=0.567
  - never entered: Engine_Rm, HD_Main, Motor_Rm, Shaft_Alley, Sick_Bay, Steering_Gear
  - over cap: Radio_Rm 19/2, Wardroom 50/8, Bridge_Lower 20/4, Officers_Qtrs 18/8, CPO_Quarters 17/10
  - night top: Bridge_Lower 19%, Radio_Rm 16%, Officers_Qtrs 16%
- `manifest`: visited=15 never_occupied=8 overflow=4 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Bridge_Lower, Engine_Rm, HD_Main, Motor_Rm, Radio_Rm, Shaft_Alley, Sick_Bay, Steering_Gear
  - over cap: Mess_Deck 47/30, CPO_Quarters 14/10, Galley 7/5, Crew_Quarters 68/55
  - night top: Crew_Quarters 52%, Salvage_Deck 16%, CPO_Quarters 11%
### cannon_de701 (manifest=216)
- **unresolvable duty pins: engine_room→Engine_Rm, medical→Sick_Bay, radio_signal→Radio_Rm**
- `default`: visited=24 never_occupied=8 overflow=6 home_distinct=7 manifest_berth_hit=0.713
  - never entered: Engine_Rm, Fire_Rm_Aft, Fire_Rm_Fwd, HD_Crew, Shaft_Alley, Sick_Bay, Steering_Gear, Upper_Machinery
  - over cap: Radio_Rm 32/2, Wardroom 126/14, Armory_Offices 28/4, Officers_Qtrs 37/10, CPO_Quarters 42/16
  - night top: CPO_Quarters 16%, Officers_Qtrs 13%, Radio_Rm 12%
- `manifest`: visited=19 never_occupied=12 overflow=5 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Armory_Offices, Crew_Berthing_1P, Crew_Berthing_Mid, Engine_Rm, Fire_Rm_Aft, Fire_Rm_Fwd, HD_Crew, Radio_Rm
  - over cap: Aft_Berthing_1P 170/40, Officers_Qtrs 19/10, Galley 15/8, Mess_Hall 112/60, CPO_Quarters 27/16
  - night top: Aft_Berthing_1P 54%, Focsle_Deck 16%, CPO_Quarters 9%
### castle_class_corvette (manifest=99)
- **unresolvable duty pins: stokers→Engine_Rm**
- `default`: visited=12 never_occupied=7 overflow=4 home_distinct=5 manifest_berth_hit=0.747
  - never entered: Boiler_Rm, Engine_Rm, HD_Foc, HD_Upper, Shaft_Stores, Sick_Bay, Steering_Gear
  - over cap: Galley 57/4, Officer_Cabins 15/6, Foc_Cabins 24/14, Mess_Mid 24/20
  - night top: Foc_Cabins 21%, Mess_Mid 19%, Seamen_Mess 18%
- `manifest`: visited=10 never_occupied=9 overflow=4 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Boiler_Rm, Engine_Rm, HD_Foc, HD_Upper, Mess_Mid, Seamen_Mess, Shaft_Stores, Sick_Bay
  - over cap: Galley 56/4, Stokers_Mess 71/18, Officer_Cabins 10/6, Foc_Cabins 18/14
  - night top: Stokers_Mess 49%, Foc_Deck_Open 19%, Foc_Cabins 13%
### classic_cruise_1900 (nominal_complement=1910)
- `default`: visited=60 never_occupied=19 overflow=28 home_distinct=42 manifest_berth_hit=None
  - never entered: HD_0E_M, HD_10B_M, HD_1C_F, HD_1C_M, HD_2C_F, HD_2C_M, HD_4M_F_1, HD_4M_F_2
  - over cap: Engine_Room 199/20, CC_D1_F 225/95, MainGalley 103/60, Bridge 16/10, Library 42/30
  - night top: MainTheater 7%, Engine_Room 7%, CC_D3_F 5%
### davison_dd618 (manifest=283)
- **unresolvable duty pins: officers→Nav_Bridge_Sonar, cpo→Mid_Services, engine_room→Engine_Rm_Fwd, ops_radio→CIC_Block, medical→Mid_Services, supply→Provisions_2P**
- `default`: visited=23 never_occupied=16 overflow=9 home_distinct=16 manifest_berth_hit=0.261
  - never entered: Engine_Rm_Aft, Engine_Rm_Fwd, Fire_Rm_Aft, Fire_Rm_Fwd, Fuel_Tanks_2P, Fuel_Tanks_Hold, HD_Crew_Aft, HD_Fwd
  - over cap: Aft_Shops 21/6, Galley_Mess 166/50, Mid_Services 14/6, Radio_Central 17/8, Workshops_Mid 15/8
  - night top: WR_Block 7%, Nav_Bridge_Sonar 6%, Fwd_Stores_1P 6%
- `manifest`: visited=8 never_occupied=29 overflow=2 home_distinct=1 manifest_berth_hit=1.0
  - never entered: Aft_Shops, Aft_Stores_2P, CIC_Block, CPO_Quarters, Crew_Berthing_1P, Crew_Qtrs_1P, Engine_Rm_Aft, Engine_Rm_Fwd
  - over cap: WR_Block 283/20, Galley_Mess 162/50
  - night top: WR_Block 68%, Focsle_Open 17%, Galley_Mess 4%
### expedition_cruise_450 (nominal_complement=450)
- `default`: visited=33 never_occupied=14 overflow=8 home_distinct=16 manifest_berth_hit=None
  - never entered: HD_2C_F, HD_2C_M, HD_3C_F, HD_3C_M, HD_4V_F, HD_4V_M, HD_5P_F, HD_5P_M
  - over cap: Engine_Room 47/15, CC_D2_A 60/40, PC_D5_P_A 33/25, PC_D4_P_A 32/25, PC_D6_P_A 32/25
  - night top: CC_D2_A 9%, TheaterLng 8%, Engine_Room 7%
### gordon_gunter_r338 (manifest=35)
- **unresolvable duty pins: engineers→Main_Gen_Rm, medical_officer→Med_Trtmt**
- `default`: visited=18 never_occupied=17 overflow=2 home_distinct=4 manifest_berth_hit=0.771
  - never entered: AC_Mchry, Bosn_Workshop, Crew_Lounge, Emer_Gen_Rm, Exercise_Rm, Genl_Workshop, HD_Bridge, HD_Focsle
  - over cap: Crew_SR_Foc 8/6, Officer_SR 12/10
  - night top: Officer_SR 28%, Scientist_SR 19%, Crew_SR_Foc 17%
- `manifest`: visited=15 never_occupied=20 overflow=0 home_distinct=3 manifest_berth_hit=1.0
  - never entered: AC_Mchry, Bosn_Workshop, Crew_Lounge, Crew_SR_Foc, Emer_Gen_Rm, Exercise_Rm, Genl_Workshop, HD_Bridge
  - night top: Scientist_SR 32%, Crew_SR_Main 20%, Officer_SR 19%
### independence_cvl26 (manifest=1566)
- **unresolvable duty pins: officers→Nav_Bridge, warrant_officers→Shops_Aft, engine_room_gang→Aft_Engine_Rm, medical_admin→Sick_Bay, seamen_general→Shops_Aft**
- `default`: visited=34 never_occupied=12 overflow=9 home_distinct=16 manifest_berth_hit=0.322
  - never entered: Aft_Engine_Rm, Aft_Fire_Rm, Funnel_Uptake, Fwd_Engine_Rm, Fwd_Fire_Rm, HD_2nd, HD_3rd, HD_Main
  - over cap: Wardroom 856/114, Nav_Bridge 105/15, Air_Ops_Rooms 91/30, Island_Upper 40/15, Galley 98/40
  - night top: Crew_Berthing_3D 6%, Officers_Country 5%, Nav_Bridge 5%
- `manifest`: visited=19 never_occupied=25 overflow=5 home_distinct=1 manifest_berth_hit=1.0
  - never entered: Aft_Engine_Rm, Aft_Fire_Rm, Air_Ops_Rooms, CPO_Berthing, Central_Station, Crew_Berthing_1P, Crew_Berthing_2D, Crew_Berthing_3D
  - over cap: Officers_Country 1566/85, Island_Upper 84/15, Galley 141/40, CPO_Mess 177/60, Crew_Mess 674/300
  - night top: Officers_Country 69%, Gallery_Deck 9%, Hangar_Fwd 8%
### mega_cruise_5000 (nominal_complement=7000)
- `default`: visited=127 never_occupied=65 overflow=21 home_distinct=93 manifest_berth_hit=None
  - never entered: HD_0E_M, HD_0T_F, HD_0T_M, HD_14S_F, HD_14S_M, HD_14Y_F, HD_14Y_M, HD_15P_F_1
  - over cap: Engine_Room_Aft 727/60, CC_D3_F 716/170, SpecGalley 209/100, EngControl 32/16, Bridge 27/16
  - night top: Engine_Room_Aft 7%, Royal_Promenade 4%, CC_D3_F 4%
### midway_cv41 (manifest=4712)
- **unresolvable duty pins: officers→Nav_Bridge, air_wing_officers→Air_Ops_Rooms, cpo→CPO_3D, engine_room_gang→Aft_Machinery_2P, medical_admin→Sick_Bay, radio_ops→PriFly_FlagPlot, seamen_general→Work_Centers_Main**
- `default`: visited=43 never_occupied=22 overflow=21 home_distinct=31 manifest_berth_hit=0.194
  - never entered: AC_Machinery_02, Aft_Diesel_3D, Aft_Machinery_2P, Aux_Machinery_1P, Catapult_Accum_01, Catapult_Machinery_02, Elev_Mach_3D, Evaporator_1P
  - over cap: Wardroom_02 1190/60, Wardroom_2D 1570/80, Galley_2D 330/40, Island_Upper 111/15, Nav_Bridge 137/20
  - night top: Hangar_Fwd 4%, Hangar_Mid 4%, Flight_Deck 3%
- `manifest`: visited=13 never_occupied=46 overflow=9 home_distinct=1 manifest_berth_hit=1.0
  - never entered: AC_Machinery_02, ADP_3D, AIMD_01, Aft_Diesel_3D, Aft_Machinery_2P, Air_Ops_Rooms, Aux_Machinery_1P, Av_Stores_1P
  - over cap: Officers_Country_02 4712/80, Galley_2D 451/40, Island_Upper 149/15, Hangar_Mid 1585/400, Fwd_Messing_2D 1055/300
  - night top: Officers_Country_02 69%, Hangar_Mid 10%, Flight_Deck 6%
### nields_dd616 (manifest=262)
- **unresolvable duty pins: officers→Nav_Bridge, cpo→Mid_Services, engine_room→Engine_Rm_Fwd, ops_radio→Radar_Plot, medical→Mid_Services, supply→Provisions_2P**
- `default`: visited=23 never_occupied=16 overflow=8 home_distinct=16 manifest_berth_hit=0.256
  - never entered: Engine_Rm_Aft, Engine_Rm_Fwd, Fire_Rm_Aft, Fire_Rm_Fwd, Fuel_Tanks_2P, Fuel_Tanks_Hold, HD_Crew_Aft, HD_Fwd
  - over cap: Aft_Shops 20/6, Galley_Area 159/50, Radio_Central 19/8, Mid_Services 14/6, Radar_Plot 15/8
  - night top: Fwd_Stores_1P 7%, Aft_Shops 6%, Nav_Bridge 6%
- `manifest`: visited=9 never_occupied=28 overflow=2 home_distinct=2 manifest_berth_hit=1.0
  - never entered: Aft_Shops, Aft_Stores_2P, Crew_Berthing_1P, Crew_Qtrs_1P, Engine_Rm_Aft, Engine_Rm_Fwd, Fire_Rm_Aft, Fire_Rm_Fwd
  - over cap: WR_Block 249/20, Galley_Area 156/50
  - night top: WR_Block 65%, Focsle_Open 16%, Galley_Area 4%
### passumpsic_ao106 (manifest=280)
- **unresolvable duty pins: senior_rates→Cargo_Control, engine_room→Engine_Rm, medical→Sick_Bay, radio_signal→Radio_Rm, cargo_pump→Cargo_Pump_Rm**
- `default`: visited=20 never_occupied=7 overflow=6 home_distinct=6 manifest_berth_hit=0.643
  - never entered: Boiler_Rm, Cargo_Pump_Rm, Engine_Rm, HD_Crew, Shaft_Alley, Sick_Bay, Steering_Gear
  - over cap: Radio_Rm 51/3, Cargo_Control 45/4, Wardroom 159/16, CPO_Quarters 45/14, Officers_Country 41/20
  - night top: Radio_Rm 15%, Crew_Qtrs_Fwd 14%, Cargo_Control 13%
- `manifest`: visited=17 never_occupied=10 overflow=4 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Boiler_Rm, Cargo_Control, Cargo_Pump_Rm, Crew_Qtrs_Fwd, Engine_Rm, HD_Crew, Radio_Rm, Shaft_Alley
  - over cap: CPO_Quarters 218/14, Galley 23/10, Mess_Hall 146/80, Officers_Country 29/20
  - night top: CPO_Quarters 54%, Working_Deck 17%, Crew_Qtrs_Aft 8%
### pce_874 (manifest=99)
- **unresolvable duty pins: engine_room→Engine_Rm, corpsman→Sick_Bay**
- `default`: visited=13 never_occupied=7 overflow=4 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Eng_Casing, Engine_Rm, Gen_Rm, HD_Crew, Shaft_Alley, Sick_Bay, Steering_Gear
  - over cap: Wardroom 57/8, Officers_Country 34/8, CPO_Quarters 35/10, Galley 5/4
  - night top: CPO_Quarters 29%, Officers_Country 27%, Crew_Quarters 22%
- `manifest`: visited=12 never_occupied=8 overflow=5 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Eng_Casing, Engine_Rm, Gen_Rm, HD_Crew, Shaft_Alley, Sick_Bay, Signal_Bridge, Steering_Gear
  - over cap: Mess_Hall 51/30, Officers_Country 13/8, Galley 6/4, CPO_Quarters 14/10, Crew_Quarters 72/55
  - night top: Crew_Quarters 50%, Fantail 19%, CPO_Quarters 10%
### raven_am55 (manifest=105)
- **unresolvable duty pins: senior_rates→Clipping_Rm, engine_room→Engine_Rm, corpsman→Sick_Bay**
- `default`: visited=14 never_occupied=7 overflow=4 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Clipping_Rm, Engine_Rm, Gen_Rm, HD_Main, Sick_Bay, Steering_Gear, Steering_Gen
  - over cap: Wardroom 60/8, Officers_Country 31/8, CPO_Quarters 32/12, Galley 8/4
  - night top: Crew_Quarters 30%, CPO_Quarters 24%, Officers_Country 24%
- `manifest`: visited=13 never_occupied=7 overflow=5 home_distinct=3 manifest_berth_hit=1.0
  - never entered: Clipping_Rm, Engine_Rm, Gen_Rm, HD_Main, Sick_Bay, Steering_Gear, Steering_Gen
  - over cap: Mess_Tables 58/30, CPO_Quarters 23/12, Officers_Country 13/8, Galley 6/4, Crew_Quarters 69/60
  - night top: Crew_Quarters 46%, Sweep_Deck 20%, CPO_Quarters 15%
### ruchamkin_apd89 (manifest=357)
- **unresolvable duty pins: engine_room→Engine_Rm, medical→Sick_Bay**
- `default`: visited=24 never_occupied=8 overflow=7 home_distinct=8 manifest_berth_hit=0.597
  - never entered: Boiler_Rm_Aft, Boiler_Rm_Fwd, Engine_Rm, HD_Crew, Shaft_Alley, Sick_Bay, Steering_Gear, Upper_Machinery
  - over cap: Radio_Rm 51/2, Wardroom 202/12, Armory_Offices 39/4, Officers_Qtrs 44/10, Galley 18/8
  - night top: Crew_Berthing_Aft 12%, Radio_Rm 11%, Troop_Berthing_Mid 11%
- `manifest`: visited=20 never_occupied=12 overflow=7 home_distinct=4 manifest_berth_hit=1.0
  - never entered: Armory_Offices, Boiler_Rm_Aft, Boiler_Rm_Fwd, Crew_Berthing_Aft, Engine_Rm, HD_Crew, Radio_Rm, Shaft_Alley
  - over cap: Wardroom 130/12, Crew_Berthing_1P 152/40, Troop_Berthing_Fwd 162/70, Galley 17/8, Officers_Qtrs 18/10
  - night top: Troop_Berthing_Fwd 37%, Crew_Berthing_1P 30%, Fantail 10%
### sigsbee_dd502 (manifest=322)
- **unresolvable duty pins: officers→Nav_Bridge, cpo→Mid_Shops, engine_room→Engine_Rm_Fwd, ops_radio→CIC, medical→Mid_Shops, supply→Provisions_2P**
- `default`: visited=24 never_occupied=17 overflow=12 home_distinct=19 manifest_berth_hit=0.22
  - never entered: Engine_Rm_Aft, Engine_Rm_Fwd, Fire_Rm_Aft, Fire_Rm_Fwd, Fuel_Tanks_2P, HD_Crew_Aft, HD_Fwd, Magazine_Aft_2P
  - over cap: Provisions_2P 22/4, Sound_Rm 13/3, After_Deckhouse 15/4, Galley_Mess 196/60, Aft_Util 13/4
  - night top: Aft_Shops 6%, Mt2_Deck 6%, Crew_Berthing_Fwd 6%
- `manifest`: visited=6 never_occupied=34 overflow=2 home_distinct=1 manifest_berth_hit=1.0
  - never entered: Aft_Shops, Aft_Stores_2P, Aft_Util, After_Deckhouse, Boatswain_Chain_3P, CIC, CPO_Quarters, Crew_Berthing_Aft
  - over cap: Officers_Country 322/16, Galley_Mess 195/60
  - night top: Officers_Country 68%, Focsle_Deck 19%, Galley_Mess 6%
### spirit_cruise_3000 (nominal_complement=3000)
- `default`: visited=85 never_occupied=30 overflow=29 home_distinct=57 manifest_berth_hit=None
  - never entered: HD_0E_M, HD_10L_F_1, HD_10L_F_2, HD_10L_M, HD_11S_F, HD_11S_M, HD_12S_F, HD_12S_M
  - over cap: Engine_Room 304/25, CC_D3_F 308/100, CC_D1_A 199/100, MainGalley 149/80, SmallLounge 156/100
  - night top: Engine_Room 7%, MainTheater 6%, CC_D1_A 5%
