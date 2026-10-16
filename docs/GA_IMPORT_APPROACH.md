Status: in use (2026-10-16). Nine maritime.org general arrangements imported end-to-end (latest: CVL-26 Independence-class light carrier — first carrier-scale import). Tool changes in `tools/ship_blueprint_import/`; this document is the plan for turning GA booklets into engineer-ready ContamW starters at scale.

# GA → .prj: approach and plan

## What we have today

`tools.ship_blueprint_import` (docs: `SHIP_BLUEPRINT_IMPORT.md`) already splits the problem into:

1. **ingest** — rasterize PDF sheets to page PNGs + manifest.
2. **digest** — an intermediate `ShipDigest` IR: ship dims, deck list, ~10–30 simulation-scale zones with normalized page polygons, HVAC/adjacency/opening hints. Produced by a vision LLM or mock.
3. **human overlay edit** — GIMP/Krita/Inkscape on `page_NN_*.svg`, saved as `*_approved.svg`.
4. **synthesize** — deterministic geometry: polygon pixel area × per-deck plan mapping → `floor_area_m2`, `volume_m3`, `display` coords; touching-polygon adjacency; HVAC groups → `spatial_layout.json` + `air_flow_paths.json`.
5. **author_contam** — ContamW 3.4 starter `.prj` + `path_map.json` + `openings_draft.json` + `CONTAM_HANDOFF.md` (hobbyist orifice catalog).
6. **validate** — JSON-schema + sanity-checker + offline PRJ parse gate.

## What maritime.org GAs actually give — and what they don't

Addendum (2026-10-15): the "systems they don't give" line needed a split.
Ventilation *terminations* are drawn on these sheets — mushroom cowls and
ventilators on weather decks, `VENT`/`VENT TRUNK`/`AIR SHAFT` labels, fan
rooms, skylights, air ports, the funnel over the machinery space — along
with plumbing anchors: heads/galleys/sculleries and named tanks (`F.W.`,
`F.O.`, `SEWAGE`). What they do NOT draw is the ductwork and pipework
between terminations. The digest's `systems` block records what the sheet
shows (`vent_markers` + `tanks`, each graded `sheet_read` vs
`era_plausible`); `tools/ship_blueprint_import/systems.py` maps it through
per-era practice tables (`usn_ww2`, `rn_ww2`, `usn_coldwar`, `usn_modern`,
`noaa_research`, `merchant_ww2`) into `vent_mode`/`oa_fraction`/
`evidence` on every HVAC group plus `systems_notes.{json,md}` — the
evidence-graded ledger that is the engineering starting point for the duct
and plumbing handwork. See `SHIP_BLUEPRINT_IMPORT.md` §Digest fields.

Measured on R-338 (13 sheets) and the Castle-class single-sheet GA:

- **Given:** compartment directory with Navy designations (deck + frame range + type), deck heights in feet above baseline, hull dims/speed, accommodation counts (R-338 sheet 2: "20 officers/crew + 15 scientists"), frame-stationed deck plans per level.
- **Not given:** duct routing, AHU counts, fan capacities, door/orifice schedules, leakage classes. This is acknowledged engineer handwork — the tool's job is a plausible, validated starting point, not as-built HVAC (Target C in `SHIP_BLUEPRINT_IMPORT.md`).

## Proposed tool approach: agent-driven digest, deterministic geometry

The GIMP loop is the bottleneck: a human traces ~20 polygons per sheet. The approach proven this session replaces the manual first pass while keeping every gate:

- **The agent acts as the vision digest.** Sheets are rasterized at 150 dpi; the agent reads deck-height tables, compartment directories and plan views directly, and authors `ship_digest.json` plus `page_NN_approved.svg` overlays programmatically (normalized coords → pixel polys). The GIMP path remains for engineer refinement — the convention is unchanged.
- **Per-deck plan mapping is now data, not a convention.** GA sheets are not clean plan views: they carry title blocks, margins, stacked views (R-338 sheet 9 = Mission Platform over Main Deck; the corvette puts 5 deck views on one page). `DeckInfo` now carries `plan_bbox_norm` (the drawn region inside the sheet) and `hull_x/y_span_m` (which metres of hull it covers). Synthesize maps each zone through *its own deck's* box — multi-view sheets now work per-deck rather than forcing one sheet = one deck = whole-hull mapping. Omitted fields keep the legacy full-page behaviour.
- **Crew manifests are first-class digest output.** `ShipDigest.complement` proposes `nominal_complement {passengers, crew}` (emitted into `spatial_layout.json` — the platform property the simulator reads) plus a class-level manifest → `crew_manifest.json`: `class_id`, `role_group` (crew/passenger), `count`, `berth_zone`, `duty_zone`, notes, and a declared-vs-listed consistency check. This is the bridge between "20 officers/crew + 15 scientists" on the sheet and the `agent_classes` machinery in `crusher_labs/config.yaml`. `nominal_complement` is only emitted when both groups are nonzero — the declaration is run-scored (VSP passenger/crew denominators require positive counts), so all-crew naval hulls keep their complement in `crew_manifest.json` and source it, matching the other naval platforms.
- **Zone ontology extended:** `Sanitary` is now a digest ZoneType (schema already allowed it in `spatial_layout.json`), and zones carry `serves` for head-block provisioning maps — matching the established `HD_*_M/F` naval pattern.

## Engineer handwork that remains (by design)

- Duct spines, AHU sizing, fan schedules, leakage classes — `skip_duct_spines` default stays on; `openings_draft.json` + `CONTAM_HANDOFF.md` is the checklist.
- Zone-split decisions where a coarse block matters epidemiologically (e.g. splitting a stateroom row into per-officer cabins).
- `crew_manifest.json` → run-config `agent_classes` wiring (schedule templates, free-zone preferences) is still manual.

## Imported this session

| Platform | Source | Zones | Complement | Contam starter |
|---|---|---|---|---|
| `gordon_gunter_r338` | R-338, 13 sheets, NOAA T-AGOS research vessel | 35 | 20 crew / 15 scientists, 6 classes | `.prj` 226 paths, 4 HVAC groups |
| `castle_class_corvette` | Castle-class GA, single-sheet multi-view | 19 | 99 crew, 5 classes | `.prj` 138 paths, 2 HVAC groups |
| `raven_am55` | AM-55 Raven minesweeper (sheets 3-5; platform deck zoned on the inboard profile with explicit ests) | 21 | 105 crew, 6 classes | `.prj` 137 paths, 2 HVAC groups |
| `bolster_ars38` | ARS-38 Bolster rescue/salvage tug, single-sheet multi-view (5 deck bands on one plate) | 24 | 90 crew incl. divers, 6 classes | `.prj` 175 paths, 2 HVAC groups |
| `ruchamkin_apd89` | APD-89 Ruchamkin fast transport (DE→APD conversion booklet, plates 5-10) | 32 | 213 crew + 162 troops, 7 classes | `.prj` 301 paths, 3 HVAC groups |
| `cannon_de701` | DE-701 Cannon-class destroyer escort (same 10-plate BuShips booklet family, unconverted) | 32 | 216 crew, 7 classes | `.prj` 255 paths, 3 HVAC groups |
| `passumpsic_ao106` | AO-106 Passumpsic fleet oiler (11-plate; cargo-tank block aggregated) | 27 | 280 crew incl. cargo deck force, 8 classes | `.prj` 202 paths, 4 HVAC groups |
| `pce_874` | PCE-874 patrol escort (6-plate; below-main at lower confidence) | 20 | 99 crew, 6 classes | `.prj` 172 paths, 2 HVAC groups |
| `independence_cvl26` | CVL-26 Monterey Independence-class light carrier (17-plate booklet; first carrier-scale import — island levels, hangar/fire-curtain segments, double-height machinery, air wing as `air_wing_*` crew classes) | 46 | 1566 crew incl. air wing, 11 classes | `.prj` 472 paths, 10 HVAC groups |
| `midway_cv41` | CV-41 Midway-class armored battle carrier (18-plate 1947 booklet; three hangar bays w/ fire curtains, armored-flight-deck vocabulary, single island funnel trunk, weapons/ordnance elevator chains, distributed modular magazines) | 65 | 4712 crew incl. air group + marines, 11 classes | `.prj` 802 paths, 10 HVAC groups |
| `texas_bb35` | BB-35 Texas New York-class battleship (13-plate 1944 booklet; wide ~91x19in plates; casemate-converted berthing, brig, engine/boiler/dynamo belt, double-bottom tank block) | 92 | 1810 crew incl. marines, 9 classes | `.prj` 1228 paths, 10 HVAC groups |
| `new_york_bb34` | BB-34 New York New York-class battleship (1942 booklet, portrait two-view plates; booklet plate 6 MAIN DECK absent from the scan — main-deck zones sister-derived from BB-35 plate 6 cross-checked against the inboard profile, flagged in uncertainties) | 83 | 1617 crew incl. marines, 9 classes | `.prj` 1173 paths, 10 HVAC groups |
| `astoria_ca34` | CA-34 Astoria New Orleans-class heavy cruiser (12-plate 1941 booklet; first heavy-cruiser import) | 65 | 982 crew, 4 classes | `.prj` 323 paths, 11 HVAC groups |
| `miami_cl89` | CL-89 Miami Cleveland-class light cruiser (13-plate 1946 booklet; superstructure drawn as local views — local bboxes + hull_x_span) | 81 | 1252 crew, 4 classes | `.prj` 389 paths, 11 HVAC groups |
| `chicago_cg11` | CG-11 Chicago guided-missile cruiser on Baltimore-class hull (16-plate 1964 booklet; Talos aft + Terrier fwd magazine systems, helo deck over aft mag, machinery zoned once on 2P) | 87 | 1302 crew incl. flag staff + marines, 4 classes | `.prj` 485 paths, 14 HVAC groups |
| `wright_cc2` | CC-2 Wright command ship on Saipan-class CVL hull (19-plate 1965 booklet; command/comms dominate gallery + hangar — Combat Operations Center, VIP suites, antenna farm) | 68 | 1768 crew, 5 classes | `.prj` 380 paths, 14 HVAC groups |
| `pope_ap110` | AP-110 General John Pope-class transport (14-plate 1943 booklet; holds 1-3,5-7 converted to troop berthing over three deck levels; sick bay on boat deck; first `nominal_complement` emission) | 88 | 479 crew + 5313 troops incl. 188 NCO + 261 troop officers, 9 classes | `.prj` 52 openings, 13 HVAC groups |
| `squier_ap130` | AP-130 General G.O. Squier-class C4-S-A1 transport (3 large sheets, Kaiser S9-0-1/2/3NC, hulls 17-30; multi-band plates — one band = one deck; hospital complex on second deck) | 52 | 482 crew + 3262 troops (223 officers + 117 NCO + 2922), 9 classes | `.prj` 50 openings, 8 HVAC groups |
| `lexington_cv2` | CV-2 Lexington-class carrier, 1941 17-plate booklet (battlecruiser-hull conversion, turbo-electric plant; 3 hangar fire-curtain bays, island stack on flight-deck plate, gallery-band main deck wrapping the hangar void) | 97 | 2370 crew incl. air group, 4 classes | `.prj` 196 path-map entries, 6 HVAC groups |
| `saratoga_cv3` | CV-3 Lexington-class carrier, Aug-1944 wartime refit, 19-plate booklet (same hull, heavier wartime fit — 40mm/rocket magazines, four fire rooms, emergency diesel gen, cross-section sheets) | 108 | 2954 crew incl. air wing + marines, 9 classes | `.prj` 207 path-map entries, 6 HVAC groups |
| `sigsbee_dd502` | DD-502 Sigsbee Fletcher-class destroyer (12-plate 1944 booklet; 3rd platform fwd-only sheet, tall ER/FR machinery zoned once on 1st platform) | 41 | 322 crew, 8 classes | `.prj` 303 paths, 4 HVAC groups |
| `nields_dd616` | DD-616 Nields Benson-class destroyer (10-plate 1942 booklet; raised forecastle deck carrying officers' country, deckhouse-top level, tall machinery) | 39 | 262 crew, 8 classes | `.prj` 258 paths, 3 HVAC groups |
| `davison_dd618` | DD-618 Davison ex-DMS-37 Gleaves-class FRAM destroyer (10-plate 1958 booklet; sonar control at bridge, CIC on superstructure deck, mine-sweep stern gear) | 39 | 283 crew, 8 classes | `.prj` 257 paths, 3 HVAC groups |
| `idaho_bb42` | BB-42 Idaho New Mexico-class battleship (incomplete 9-sheet set, ~1930s; no inboard profile/data sheet — deck heights era-typical, complement class-typical) | 114 | ~1084 crew class-typical (NOT plate-read), 7 classes | `.prj` 1819 paths, 13 HVAC groups |
| `west_virginia_bb48` | BB-48 West Virginia Colorado-class battleship (complete 13-plate 1939 booklet; complement + deck heights plate-read; casemate/magazine clusters aggregated) | 198 | 1340 crew plate-read, 10 classes | `.prj` 3518 paths, 19 HVAC groups |
| `south_dakota_bb49` | BB-49 South Dakota 1918 contract plans (never completed; engineering plates, arrangement bands p5-p7 only — LOW confidence; hold level omitted) | 55 | ~1191 crew class-typical, 6 classes | `.prj` 468 paths, 8 HVAC groups |
| `missouri_bb63` | BB-63 Missouri Iowa-class battleship (17-plate 1950 booklet; 13 deck levels incl. splinter citadel + third platform, turret barbette/trunk chain, era-tagged usn_coldwar) | 103 | 1561 crew, 5 classes | `.prj` 2248 paths, 11 HVAC groups |
| `wisconsin_bb64` | BB-64 Wisconsin Iowa-class battleship (15-plate 1956 booklet; zone layout affine-transferred from the BB-63 sheet-read digest into BB-64 page frames, era usn_coldwar) | 103 | ~2560 crew, 4 classes | `.prj` 2248 paths, 11 HVAC groups |
| `new_jersey_bb62` | BB-62 New Jersey Iowa-class battleship (18-plate 1984 NAVSEA reactivation booklet; affine-transferred layout, era usn_modern / mech_ac shipwide) | 103 | ~1781 crew, 4 classes | `.prj` 2248 paths, 11 HVAC groups |
| `liberty_cargo_ec2` | EC2-S-C1 Liberty cargo ship (partial 5-drawing set; first merchant hull, `merchant_ww2` era; aggregate holds like `passumpsic_ao106`) | 54 | 66 merchant crew, 8 classes | `.prj` 37 paths, 13 HVAC groups |
| `savannah_ns` | NS Savannah nuclear merchant/passenger demonstration ship 1967 (12-page booklet; first passenger hull — `nominal_complement`; `usn_coldwar` as `era_plausible`, merchant-service uncertainty flagged) | 73 | 60 passengers + 110 crew, 10 classes | `.prj` 47 paths, 14 HVAC groups |
| `aeolus_arc3` | ARC-3 USS Aeolus cable repair ship (ex-LST hull; cable tanks aggregated like cargo) | 40 | ~200 crew, 7 classes | `.prj` 23 paths, 11 HVAC groups |
| `alexander_henry_cgs119` | CGS Alexander Henry icebreaker (2 multi-view sheets, `usn_coldwar` as `era_plausible`; Canadian CG flagged; plate-read complement) | 28 | 31 crew + 20 passengers/officials (51 berths), 5 classes | `.prj` 13 paths, 10 HVAC groups |
| `olympia_c6` | C-6 Olympia protected cruiser (10-sheet 1895 booklet, coarse scan; six zoneable decks, coal-ring protective deck, era fallback flagged) | 104 | 440 crew era-typical flagship fit, 6 classes | `.prj` 805 paths, 11 HVAC groups |
| `montana_acr13` | ACR-13 Montana Tennessee-class armored cruiser (9-plate 1917 booklet; split lower-platform flats, coal bunkers, ~900-1100 class-typical complement) | 146 | 1000 crew class-typical, 7 classes | `.prj` 2474 paths, 17 HVAC groups |
| `jupiter_ac3` | AC-3 Jupiter collier later CV-1 Langley (4-sheet 1913 booklet; cargo holds dominate, first USN turbo-electric, split 2nd-platform flats) | 50 | 295 crew, 6 classes | `.prj` 538 paths, 8 HVAC groups |
| `antietam_cvs36` | CVS-36 Antietam Essex-class ASW carrier (17-plate 1955 angled-deck booklet; plate 18 double-bottom missing — inner bottom from plate 17; three hangar segments at roller curtains, air wing as `air_wing_*` classes, 12 deck plates incl. island and third bottom) | 66 | 2998 crew incl. air group + marines, 7 classes | `.prj` 858 paths, 10 HVAC groups |

All thirty carry a `systems` block (era + sheet-read vent markers + tank labels); inference emits `systems_notes.md` per platform — e.g. R-338's `SEWAGE HOLDING` tank joins `graywater_zones` automatically, Castle's forecastle cowls tag the accommodation branch `nat_supply`/`sheet_read`. All pass `validate --contam-gate` (schema + sanity + offline PRJ parse). Intermediates (rasters, digests, overlays) stay in gitignored `work/blueprints/`; digest JSONs are regenerable via the author scripts there — a follow-up could commit them under `tests/fixtures/` if replay value is wanted.

