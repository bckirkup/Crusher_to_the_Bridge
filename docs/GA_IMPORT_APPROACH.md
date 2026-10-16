Status: in use (2026-10-16). Twelve maritime.org general arrangements imported end-to-end (latest: amphibious bundle — APA-170 Haskell attack transport + LSD-21 Casa Grande dock landing ship, first embarked-troop `nominal_complement` platforms since APD-89). Tool changes in `tools/ship_blueprint_import/`; this document is the plan for turning GA booklets into engineer-ready ContamW starters at scale.

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
| `gosper_apa170` | APA-170 Gosper Haskell-class attack transport (13-plate VC2-S-AP5 booklet; troop berthing decks with standee-bunk densities, landing-craft boat deck, sick bay + isolation ward) | 71 | 534 crew + 1561 troops, 7 classes | `.prj` 1351 paths, 9 HVAC groups |
| `fort_mandan_lsd21` | LSD-21 Fort Mandan Casa Grande-class dock landing ship (12-plate 1951 booklet; well deck zoned once at floor level with explicit 13,000 m³ volume, floodable wing ballast tanks, stern gate) | 51 | 301 crew + 214 troops, 7 classes | `.prj` 502 paths, 9 HVAC groups |

All twelve carry a `systems` block (era + sheet-read vent markers + tank labels); inference emits `systems_notes.md` per platform — e.g. R-338's `SEWAGE HOLDING` tank joins `graywater_zones` automatically, Castle's forecastle cowls tag the accommodation branch `nat_supply`/`sheet_read`. All pass `validate --contam-gate` (schema + sanity + offline PRJ parse). Intermediates (rasters, digests, overlays) stay in gitignored `work/blueprints/`; digest JSONs are regenerable via the author scripts there — a follow-up could commit them under `tests/fixtures/` if replay value is wanted.

## Era-rule provenance

The `ERA_RULES` mode/oa tables in `tools/ship_blueprint_import/systems.py` are *practice* priors, not physical constants — graded and cited at the point of definition (repo convention):

| Claim | Source actually read | Grade | Origin |
|---|---|---|---|
| WW2 USN practice: cowled/mushroom natural supply + mechanical exhaust to galley/heads/machinery; magazine ventilators of the mushroom or cowl type | NAVARMEDGUARD "General Instructions" §3109 (~1942), via HyperWar transcription | B | Tr |
| Same practice, period authority (identified, **not read** — do not cite as read) | BuShips Technical Publication No. 6, *Pointers on Shipboard Ventilation* (1944) | — | ?nr |
| Modern/cold-war USN taxonomy: mechanical supply & exhaust, recirculating AC with outside-air makeup | NAVSEA S9086-RQ-STM-010 (NSTM ch. 510), ToC/§510-2 | B | Tr |
| Corroborating secondary of the above | "Ventilation Systems, US Navy Ships" (bluewaternavy.org, NSTM-derived) | C | Sec |
| `rn_ww2` row, `noaa_research` row, era cutoff years, `MODE_OA_FRACTION` values | none — declared engineering priors | C | — |

Standing liabilities (the Grade C rows): an Admiralty/BUSHIPS DDS reference for the RN and NOAA rows, and any sourced basis for the OA-fraction numbers. Until those surface, era-rule modes may shape a starter `.prj` but should not inform a fitted parameter.

## Carrier-scale conventions

Fleet/auxiliary carriers fit the same digest model with these conventions (first applied to CVL-26 / CV-41 booklets):

- **Flight deck** is a `Free` zone (often the whole weather surface, one or two polygons). Era mode gives `nat_supply` (oa_fraction 1.0), which is already the honest open-air approximation; do not invent conditioning plant for it.
- **Hangar deck** is `Free` — one large zone (Essex hangar ≈ 200×20×5.4 m ≈ 21,000 m³ is within the volume bound) or 2–3 fore/mid/aft segments where fire curtains are drawn. Ventilation: `usn_ww2`/`usn_coldwar` era gives `nat_supply`; refine with sheet-read markers — hangar-side roller doors are `kind: "hangar_door"` → `nat_supply`, and where the sheet labels forced hangar exhaust fans declare an explicit `VENT_Hangar` hvac_hint (`mech_exhaust`) instead. Fuel-vapor purge fans are the era-plausible fallback.
- **Island** is a thin deck level *above* the flight deck (elevation ≈ flight_deck + 3 m) carrying Nav_Bridge, flag plot, primary fly, funnel uptake zones.
- **Aircraft/bomb elevators** are adjacency `type: "elevator"` links (free string) between flight deck ↔ hangar ↔ hold/magazines.
- **Air wing** embarked squadrons are `role_group: "crew"` manifest classes (`air_wing_*`) — they are embarked personnel, not passengers.
- **Distributed magazines** (bomb/ammo rooms fore and aft below the waterline) each get a sheet-read marker entry; `Mag_Vent` era-plausible fallback per NAVARMEDGUARD §3109.
- **Below-main decks** on CV booklets run 2nd/3rd/4th deck + gallery deck conventions (USN deck numbering differs from merchant — flight deck is "main" in practice; keep repo `*_deck` ids ordered by elevation and record the booklet's own names in `DeckInfo.role`).
- **Complement** runs 1,500 (CVL) – 4,100+ (CV-41). `crew_estimate` and manifest counts are unbounded; declare `nominal_complement` only when passengers > 0, else manifest-only like other naval hulls.

## Roadmap

1. **Now (this PR):** schema + model + synthesize changes above; two imported platforms; this doc.
2. **Next ship batch:** AM-55 Raven, APD-89 Ruchamkin, ARS-38 Bolster are already rasterized in `work/blueprints/` — same recipe, ~30–60 min of sheet reading each. *(Done — PR #1023.)*
3. **Vision-LLM digest parity:** the `--provider gemini|openai_compat|anthropic` digest path should emit `plan_bbox_norm` + `complement` + `systems`; update `DIGEST_SYSTEM_PROMPT` and the providers' JSON schema so a real LLM can produce the same fields the agent authored by hand.
4. ~~**Era-table provenance**~~ **(done — §Era-rule provenance above; RN/NOAA/OA-fraction rows remain Grade C declarations).**
5. **Auto-bbox detection:** detect the plan-view frame lines on each sheet to propose `plan_bbox_norm` automatically; agent/LLM only confirms.
6. **Manifest → run config:** a `scripts/` helper that expands `crew_manifest.json` classes into `config.yaml agent_classes` entries (fractions from counts, `home_zone_preference` from `berth_zone`, `duty_zone` direct) so manifests become runnable without hand YAML.
7. **Multi-frame fidelity:** when a sheet's plan view shows partial hull coverage, hull spans already handle it — but bow/stern overhang beyond frame 0/105 needs the same care on each new ship.
8. **Marker direction from geometry:** cowl facing is currently authored per marker; the SVG symbol's orientation could be read automatically (cowl mouth direction) when overlays carry marker glyphs.
9. **Carrier import:** CVL-26 Independence-class light carrier and CV-41 Midway booklets are on the maritime.org index (`cv12.pdf` is a single mega-plate — deprioritize); apply §Carrier-scale conventions. Submarines remain out of scope (pressure-hull geometry semantics).
