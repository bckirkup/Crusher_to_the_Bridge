Status: proposal + first proof (2026-10-15). Two maritime.org general arrangements imported end-to-end (R-338 NOAA Gordon Gunter, Castle-class corvette). Tool changes in `tools/ship_blueprint_import/`; this document is the plan for turning GA booklets into engineer-ready ContamW starters at scale.

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

All three carry a `systems` block (era + sheet-read vent markers + tank labels); inference emits `systems_notes.md` per platform — e.g. R-338's `SEWAGE HOLDING` tank joins `graywater_zones` automatically, Castle's forecastle cowls tag the accommodation branch `nat_supply`/`sheet_read`. All pass `validate --contam-gate` (schema + sanity + offline PRJ parse). Intermediates (rasters, digests, overlays) stay in gitignored `work/blueprints/`; digest JSONs are regenerable via the author scripts there — a follow-up could commit them under `tests/fixtures/` if replay value is wanted.

## Roadmap

1. **Now (this PR):** schema + model + synthesize changes above; two imported platforms; this doc.
2. **Next ship batch:** AM-55 Raven, APD-89 Ruchamkin, ARS-38 Bolster are already rasterized in `work/blueprints/` — same recipe, ~30–60 min of sheet reading each.
3. **Vision-LLM digest parity:** the `--provider gemini|openai_compat|anthropic` digest path should emit `plan_bbox_norm` + `complement` + `systems`; update `DIGEST_SYSTEM_PROMPT` and the providers' JSON schema so a real LLM can produce the same fields the agent authored by hand.
4. **Era-table provenance:** the `ERA_RULES` mode/oa priors are engineering priors, not sourced constants — a provenance pass should attach a naval-ventilation reference (e.g. BUSHIPS/NAVSHIPS ventilation standard practice) to each era row before the modes inform any fitted parameter.
5. **Auto-bbox detection:** detect the plan-view frame lines on each sheet to propose `plan_bbox_norm` automatically; agent/LLM only confirms.
6. **Manifest → run config:** a `scripts/` helper that expands `crew_manifest.json` classes into `config.yaml agent_classes` entries (fractions from counts, `home_zone_preference` from `berth_zone`, `duty_zone` direct) so manifests become runnable without hand YAML.
7. **Multi-frame fidelity:** when a sheet's plan view shows partial hull coverage, hull spans already handle it — but bow/stern overhang beyond frame 0/105 needs the same care on each new ship.
8. **Marker direction from geometry:** cowl facing is currently authored per marker; the SVG symbol's orientation could be read automatically (cowl mouth direction) when overlays carry marker glyphs.
