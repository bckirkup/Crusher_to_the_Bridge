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

## What this fix is and is not

This fix removes duct coupling from the six cruise platforms while retaining
architectural adjacency. It adds no outdoor-air-change rate, dilution factor,
ambient path, exposure class, UV/solar constant, humidity/salt effect,
recreational-water route, or surface-decay behavior. None of proposal §3(a),
§3(b), or §3(c) was selected. The Contam PRJ remains untouched and still has
no ambient path. The model intentionally asserts less than before.
