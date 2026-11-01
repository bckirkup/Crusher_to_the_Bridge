# Naval General-Plan → Ship Class Import

> Index: [README.md](README.md). Companion Contam path: [CONTAM_INTEROP.md](CONTAM_INTEROP.md).

Standalone tooling under `tools/ship_blueprint_import/` digests messy naval
general arrangements (scanned PDFs, hand markup) into coarse simulation-scale
ship classes, then authors a **ContamW 3.4 starter project** for CtB Path A
and engineer handoff.

Human zone correction uses **GIMP / Krita / Inkscape** SVG overlays — not the
LCARS dashboard. After overlays are approved, Crusher JSON synthesis and Contam
starter emission are deterministic.

## Product targets

| Target | What the tool does |
|--------|--------------------|
| **A** | Crusher `spatial_layout` + `air_flow_paths` |
| **B** | ContamW-openable starter `.prj` + openings checklist + Path A `path_map` |
| **C** | **Out of scope** — ducts, fan curves, measured leakage, NBC elements (not on GAs); engineers finish in ContamW |

## Pipeline

```text
PDF / images
  → ingest (raster pages)
  → digest (vision LLM or mock → ShipDigest + draft SVG)
  → edit overlays in GIMP/Krita/Inkscape → page_NN_approved.svg
  → synthesize (SVG + digest → platform JSON)
  → author_contam (Target B ContamW starter + openings_draft + handoff)
  → validate (schemas + sanity_checker [+ Contam offline gate])
```

## CLI

All paths are resolved under the repository root (Sonar-safe I/O).

```bash
# 1. Rasterize a GA PDF (or an image folder)
python3 -m tools.ship_blueprint_import ingest \
  --input path/to/ac3.pdf \
  --workdir work/blueprints/ac3 \
  --dpi 150

# 2. Draft digest + SVG overlays
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/ac3 --provider mock
# Live: --provider gemini|openai_compat|anthropic (+ API key env)

# 3. Edit overlays (templates/EDITOR_NOTES.md), save page_NN_approved.svg

# 4. Synthesize (+ optional Contam in one step)
python3 -m tools.ship_blueprint_import synthesize \
  --workdir work/blueprints/ac3 \
  --platform-id america_class_lha \
  --output data/platforms/america_class_lha \
  --require-approved \
  --author-contam

# 4b. Or author Contam separately after synthesize
python3 -m tools.ship_blueprint_import author_contam \
  --platform-dir data/platforms/america_class_lha \
  --workdir work/blueprints/ac3

# 5. Validate (+ Contam offline parse gate)
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/america_class_lha \
  --contam-gate
```

## Contam starter outputs (`contam/`)

| Path | Role |
|------|------|
| `platform.prj` | ContamW 3.4 project (zones, typed openings, AHS) |
| `path_map.json` | ContamX ↔ Crusher path index |
| `openings_draft.json` | Engineer checklist of orifice areas / status |
| `hobbyist_overrides.json` | Naval starter overrides (`skip_duct_spines: true`, `zone_aliases` for post-prj zone renames) |
| `CONTAM_HANDOFF.md` | What was drafted vs ContamW handwork |
| `author_contam_provenance.json` | Gate results / timestamps |

Fiction Darcy **duct spines are omitted by default** (`skip_duct_spines`) so
engineers author real ducts from HVAC drawings — those details are not on GAs.

## Intermediate files (workdir)

| Path | Role |
|------|------|
| `source/` | Copied originals + sha256 in manifest |
| `pages/page_NN.png` | Raster plates |
| `pages_manifest.json` | Page sizes / DPI / hashes |
| `ship_digest.json` | ShipDigest IR (`schemas/ship_digest.schema.json`) incl. `opening_hints` / `contam_hints` |
| `overlays/page_NN_draft.svg` | LLM/mock draft polygons |
| `overlays/page_NN_approved.svg` | Human-corrected polygons (preferred) |
| `digest_meta.json` | Provider / model / digest hash |

## Design notes

- **Naval Room berthing** only (well-mixed). No cruise `Cabin_Corridor`.
- Intentionally **coarse** (~10–30 zones). Ignore hatch-level GA detail.
- Contam starter is **PRJ-primary Path A ready**, not as-built HVAC.
- Agent skill: `.agents/skills/importing-naval-blueprint/SKILL.md`.

## Digest fields for real GA sheets (2026-10 additions)

- `decks[].plan_bbox_norm` — normalized `[x0,y0,x1,y1]` box of the drawn
  deck-plan view inside a sheet. Real GA sheets carry title blocks, margins,
  and stacked views (R-338 sheet 9 draws Mission Platform above Main Deck;
  the Castle-class sheet packs five deck views on one page). With
  `hull_x_span_m` / `hull_y_span_m` (which metres of hull that box covers,
  stern datum at x=0) each zone is mapped through *its own deck's* box, so
  several decks may share one sheet. Omit all three to keep the legacy
  whole-page = whole-hull mapping.
- `zones[].type` now admits `Sanitary` (matching `spatial_layout.schema.json`)
  and `zones[].serves` lists the zones a head block provisions — the
  `HD_*` pattern used by the other naval platforms.
- `complement` — proposed `{passengers, crew}` written into
  `spatial_layout.json` as `nominal_complement`, plus a class-level manifest
  (`class_id`, `role_group`, `count`, `berth_zone`, `duty_zone`) emitted as
  `crew_manifest.json` with a declared-vs-listed consistency check. This is
  how a sheet's "20 officers/crew + 15 scientists" becomes a proposed crew
  manifest for the `agent_classes` machinery. Emitted only when both counts
  are nonzero (the declaration is run-scored); all-crew hulls source their
  complement from `crew_manifest.json`.
- `systems` — era-typed systems inference for what the sheet DOES draw:
  `era` (`usn_ww2`, `rn_ww2`, `usn_coldwar`, `usn_modern`, `noaa_research`,
  `merchant_ww2`, `generic`), `vent_markers` (cowls/mushrooms/goosenecks,
  skylights, air ports, vent trunks, air shafts, fan rooms, uptakes, the
  funnel — each with page position, `facing`, optional `serves_zone`, and
  `evidence` `sheet_read`|`era_plausible`) and `tanks` (named tank labels as
  plumbing anchors). `tools/ship_blueprint_import/systems.py` maps them
  through per-era ventilation-practice tables: markers resolve to a served
  zone (explicit `serves_zone`, else nearest zone on the marker's deck in
  display coordinates), direction comes from the sheet label else the cowl
  facing, each zone gets a `vent_mode` and every HVAC group gains
  `vent_mode` + `evidence` + an `oa_fraction` prior — a hint that declares
  its own `oa_fraction` always wins. Marker-attributed modes beat era-rule
  modes on a mixed branch; marker kind refines the mode (funnel/gooseneck
  on Engineering → `mech_supply_exhaust`, skylight/air_port → `nat_supply`).
  Sewage/waste/gray-labeled tanks join `graywater_zones`; every step lands
  in `systems_notes.json` + `systems_notes.md` with its evidence grade
  (`sheet_read` / `era_plausible` / `era_rule`), which is the engineering
  starting point for the plumbing/duct handwork.
- Agent-authored digests: an agent can read rasterized sheets directly and
  write `ship_digest.json` + `page_NN_approved.svg` programmatically (the
  GIMP loop stays available for engineer refinement). Worked imports and the
  roadmap live in `GA_IMPORT_APPROACH.md`.

## PDF raster extras

```bash
pip install pypdfium2
# or: sudo apt-get install poppler-utils
```
