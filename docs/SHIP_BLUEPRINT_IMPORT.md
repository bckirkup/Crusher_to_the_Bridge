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
| `hobbyist_overrides.json` | Naval starter overrides (`skip_duct_spines: true`) |
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

## PDF raster extras

```bash
pip install pypdfium2
# or: sudo apt-get install poppler-utils
```
