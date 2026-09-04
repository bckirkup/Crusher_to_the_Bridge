# Exterior-zone AHU audit

> **Status:** Living. This audit records the structural change in Item 2.

The audit crossed each platform's `spatial_layout.json` descriptions with its
`air_flow_paths.json`. Exterior classification is description-based and uses
only the settled list below; no name-based expansion was used. Removing a room
from an AHU group removes its participation in AHU-to-AHU cross-zone links
through that group. Architectural `adjacency` links are independent and were
retained.

## Settled exterior classification

| Platform | Exterior zones | Effective `oa_fraction` |
|---|---|---:|
| `mega_cruise_5000` | `Main_Pool_Deck`, `Sports_Court`, `Waterpark`, `CentralPark`, `Aqua_Theater` | 0.2 |
| `messy_cruise_500` | `Main_Pool_Deck`, `Sports_Court`, `Waterpark`, `Central_Park_Open_Atrium`, `Aqua_Theater` | 0.2 fallback |
| `spirit_cruise_3000` | `MainPool`, `AftPool`, `SportsDeck` | 0.2 |
| `classic_cruise_1900` | `PoolDeck` | 0.2 |
| `expedition_cruise_300` | `Pool_Deck` | 0.2 fallback |
| `expedition_cruise_450` | `PoolDeck` | 0.2 |

The descriptions explicitly support these classifications as open-air,
semi-open, or open-aft/outdoor spaces. `Solarium` is retained because it is a
glazed enclosed lounge. `Royal_Promenade`, `Promenade`, and `ShopRetail` are
retained because their descriptions state that they are indoor. `Pool_Bar_Grill`
is retained because its dining-venue description asserts no open-air envelope.

## Per-platform membership audit

The following tables show every AHU group, ACH, and room membership. `*` marks
an exterior room in the before state. The after state removes every `*` room
from AHU membership and leaves all other rooms unchanged.

### `mega_cruise_5000` — `oa_fraction=0.2`

| Group (ACH) | Before rooms | After rooms removed |
|---|---|---|
| `AHU_Network_Forward_Public` (8) | Bridge, Solarium, SpaFitness, Main_Theater | — |
| `AHU_Network_Midship_Atrium` (6) | CentralPark*, Royal_Promenade, ShopRetail, Casino, LibraryCard, ComedyClub | CentralPark |
| `AHU_Network_Aft_Dining_Rec` (10) | Main_Pool_Deck*, Sports_Court*, Waterpark*, Pool_Bar_Grill, Kids_Club, Teen_Zone, MainDining_L, MainDining_U, Windjammer, SpecRest_A, SpecRest_B, CafeBakery, Aqua_Theater*, Ice_Rink_Studio | Main_Pool_Deck, Sports_Court, Waterpark, Aqua_Theater |
| `AHU_Dedicated_Service_Exhaust` (15) | Main_Galley_Aft, BuffetGal_U, SpecGalley, Central_Stores, Laundry_Main, WasteTreat | — |
| `AHU_Dedicated_Engine` (20) | Engine_Room_Aft, EngControl | — |
| Cabin and crew deck AHUs | Cabin/crew corridor groups | — |

Adjacency touching exterior zones is retained: pool-deck doorways, CentralPark
multi-deck/stair links, Aqua passageways, and corridor/elevator links.

### `messy_cruise_500` — `oa_fraction=0.2` fallback

| Group (ACH) | Before exterior rooms | After |
|---|---|---|
| `AHU_Network_Forward_Public` (8) | none | unchanged |
| `AHU_Network_Midship_Atrium` (6) | Central_Park_Open_Atrium* | removed |
| `AHU_Network_Aft_Dining_Rec` (10) | Main_Pool_Deck*, Sports_Court*, Waterpark*, Aqua_Theater* | removed |
| `AHU_Network_Cabins_Port` (6) | none | unchanged |
| `AHU_Network_Cabins_Stbd_Central` (6) | none | unchanged |
| `AHU_Network_Crew_Accommodation` (8) | none | unchanged |
| `AHU_Dedicated_Medical` (12) | none | unchanged |
| `AHU_Dedicated_Service_Exhaust` (15) | none | unchanged |
| `AHU_Dedicated_Engine` (20) | none | unchanged |

All adjacency entries touching the five settled exterior zones remain.

### `spirit_cruise_3000` — `oa_fraction=0.2`

| Group (ACH) | Before exterior rooms | After |
|---|---|---|
| `AHU_Public_Aft` (10) | MainPool*, AftPool*, SportsDeck* | removed |
| Other public, dining, medical, service, passenger and crew groups | none | unchanged |

Pool/deck door, stairwell, corridor, and elevator adjacency entries remain.

### `classic_cruise_1900` — `oa_fraction=0.2`

| Group (ACH) | Before exterior rooms | After |
|---|---|---|
| `AHU_Public_Aft` (10) | PoolDeck* | removed |
| Other passenger, public, dining, medical, service and crew groups | none | unchanged |

`LidoBuffet -> PoolDeck`, `PoolDeck -> SpaFit`, and
`PC_D9_P_A -> PoolDeck` remain as architectural links.

### `expedition_cruise_300` — `oa_fraction=0.2` fallback

| Group (ACH) | Before exterior rooms | After |
|---|---|---|
| `AHU_1_Upper` (8) | Pool_Deck* | removed |
| `AHU_2_Main` (6), `AHU_3_Service` (12), `AHU_MedBay_Dedicated` (15) | none | unchanged |

The open-deck and doorway adjacency entries remain.

### `expedition_cruise_450` — `oa_fraction=0.2`

| Group (ACH) | Before exterior rooms | After |
|---|---|---|
| `AHU_Public_Aft` (8) | PoolDeck* | removed |
| Other passenger, public, dining, medical, service and crew groups | none | unchanged |

`ObsLounge -> PoolDeck` and `CasualDining -> PoolDeck` remain.

## Non-cruise follow-up

`legend_class_nsc` and `san_antonio_class_lpd` have `Flight_Deck`
descriptions stating “open to weather”; both are currently members of
recirculating groups and have architectural links. They are a named follow-up
for a separate change. No non-cruise platform was modified here. The remaining
platform audit (destroyer and Enterprise variants) found no settled exterior
classification and therefore no changes.

For completeness, the unchanged-platform cross-check recorded the following
groups, ACH values, and memberships:

| Platform | HVAC groups (ID: ACH — rooms) |
|---|---|
| `destroyer_baseline` | `zone_upper`: 6 — Bridge; `zone_main`: 8 — MedBay, Mess_Hall, Galley; `zone_lower`: 10 — Engine_Room, Berthing |
| `fletcher_class_destroyer` | `HVAC_Superstructure`: 6 — Bridge, CIC, Radio_Room, Gun_Mount_51; `HVAC_Main_Deck_Fwd`: 5 — Officers_Quarters, Wardroom, Sickbay, CPO_Quarters; `HVAC_Main_Deck_Mid`: 8 — Galley, Torpedo_Mount_Midships, Passageway_Main; `HVAC_Berthing`: 4 — Enlisted_Berthing_Fwd, Enlisted_Berthing_Aft, Mess_Deck; `HVAC_Boiler_Rooms`: 25 — Boiler_Room_1, Boiler_Room_2; `HVAC_Engine_Rooms`: 18 — Engine_Room_Fwd, Engine_Room_Aft; `HVAC_Magazines`: 8 — Magazine_Fwd, Magazine_Aft |
| `enterprise_constitution_tos` | `AHU_EC_D4`–`AHU_EC_D6`: 7 — listed EC passenger branches; `AHU_Command`: 10 — Bridge, BriefRoom, Comms, Library; `AHU_Ops`: 9 — Science1, Science2, Transprt1, Transprt2, Security, Brig, NeckHub; `AHU_Living`: 8 — RecDeck, Gym, Mess_Hall, HeadsMain; `AHU_Medical`: 12 — Sickbay, IsolBay1, IsolBay2; `AHU_Service`: 15 — Galley, StoresDry, StoresCold, Armory; `AHU_Engineering`: 16 — EngMain, WarpCore, EPSDist, Jefferies, Airlock; `AHU_Crew`: 7 — OC_D5_F, OC_D5_M, OC_D5_A, OC_D6_F, OC_D6_M, OC_D6_A |
| `enterprise_galaxy_tng` | `AHU_EC_D7`–`AHU_EC_D12`: 7 — listed EC passenger branches; `AHU_FC_D23`–`AHU_FC_D25`: 7 — listed FC passenger branches; `AHU_Command`: 10 — Bridge, BriefRoom, Comms; `AHU_Public`: 9 — TenFwd, Arboretum, Holodeck1, Holodeck2, School, CrewLounge, StellarCart, Gym; `AHU_Ops`: 9 — Science1, Science2, Transprt1, Transprt2, Security, Brig, NeckHub; `AHU_Medical`: 12 — Sickbay, IsolBay1, IsolBay2, IsolBay3; `AHU_Service`: 14 — Galley, Mess_Hall, HeadsMain, StoresDry, StoresCold, Armory; `AHU_Engineering`: 16 — MainEng, WarpCore, EPSDist, Jefferies, Deflector; `AHU_Flight`: 12 — ShuttleBay, CargoMain, CargoAux, Airlock; `AHU_Crew`: 7 — OC_D8_F, OC_D8_M, OC_D8_A, OC_D9_F, OC_D9_M, OC_D9_A |
| `legend_class_nsc` | `HVAC_Superstructure`: 10 — Bridge, CIC; `HVAC_Officer_Spaces`: 8 — Officers_Quarters, Wardroom; `HVAC_Enlisted_Fwd`: 8 — CPO_Berthing, Enlisted_Berthing_Fwd, Crew_Mess; `HVAC_Enlisted_Aft`: 8 — Enlisted_Berthing_Aft, Aviation_Det_Berthing, Boarding_Team_Staging; `HVAC_Medical`: 12 — Sickbay; `HVAC_Galley`: 15 — Galley; `HVAC_Midships_Utility`: 6 — Passageway_Main, Armory; `HVAC_Aviation`: 8 — Helicopter_Hangar, Flight_Deck, Boat_Deck; `HVAC_Engine_Room`: 20 — Engine_Room |
| `san_antonio_class_lpd` | `HVAC_Superstructure`: 10 — Bridge, CIC, Marine_Planning; `HVAC_Officer_Berthing`: 8 — Ship_Officers_Quarters, Ship_CPO_Quarters, Wardroom; `HVAC_Crew_Habitable`: 8 — Ship_Enlisted_Berthing, Crew_Mess, Passageway_Main; `HVAC_Troop_Berthing`: 7 — Troop_Berthing_Fwd, Troop_Berthing_Mid, Troop_Berthing_Aft, Troop_Mess, Troop_Recreation; `HVAC_Medical`: 12 — Medical_Ward; `HVAC_Galley`: 15 — Galley; `HVAC_Vehicle_Deck`: 10 — Vehicle_Deck; `HVAC_Aviation`: 8 — Hangar, Flight_Deck; `HVAC_Well_Deck`: 6 — Well_Deck; `HVAC_Machinery`: 20 — Engine_Room_Fwd, Engine_Room_Aft |

Their cross-zone links (AHU-to-AHU or retained non-duct access paths) and
adjacency were unchanged. Effective OA is native fallback `0.2` except the
two Enterprise platforms, which explicitly declare `0.15`.

## What this fix is and is not

This fix removes duct coupling from the six cruise platforms while retaining
architectural adjacency. It adds no outdoor-air-change rate, dilution factor,
ambient path, exposure class, UV/solar constant, humidity/salt effect,
recreational-water route, or surface-decay behavior. None of proposal §3(a),
§3(b), or §3(c) was selected. The Contam PRJ remains untouched and still has
no ambient path. The model intentionally asserts less than before.
