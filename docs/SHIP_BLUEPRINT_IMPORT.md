# Naval General-Plan → Ship Class Import

> Index: [README.md](README.md). Contam authoring from drawings remains
> **out of scope** ([CONTAM_INTEROP.md](CONTAM_INTEROP.md)); this tool emits
> Crusher native JSON only (optional fiction Contam bootstrap afterward).

Standalone tooling under `tools/ship_blueprint_import/` digests messy naval
general arrangements (scanned PDFs, hand markup) into coarse simulation-scale
ship classes: `spatial_layout.json` + `air_flow_paths.json`.

Human correction uses **GIMP / Krita / Inkscape** SVG overlays — not the LCARS
dashboard. After overlays are approved, synthesis is fully deterministic.

## Pipeline

```text
PDF / images
  → ingest (raster pages)
  → digest (vision LLM or mock → ShipDigest + draft SVG)
  → edit overlays in GIMP/Krita/Inkscape → page_NN_approved.svg
  → synthesize (SVG + digest → platform JSON)
  → validate (schemas + sanity_checker)
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
# Offline / CI:
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/ac3 --provider mock

# Live vision (pluggable):
#   GEMINI_API_KEY=…   --provider gemini [--model gemini-2.0-flash]
#   OPENAI_API_KEY=…   --provider openai_compat [--model gpt-4o]
#   ANTHROPIC_API_KEY=… --provider anthropic
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/ac3 --provider gemini

# 3. Edit overlays (see templates/EDITOR_NOTES.md), save approved SVGs

# 4. Synthesize platform JSON
python3 -m tools.ship_blueprint_import synthesize \
  --workdir work/blueprints/ac3 \
  --platform-id america_class_lha \
  --output data/platforms/america_class_lha \
  --require-approved

# 5. Validate
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/america_class_lha

# Optional fiction Contam bootstrap (not authentic Contam authoring):
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/america_class_lha \
  --contam-bootstrap
```

## Intermediate files (workdir)

| Path | Role |
|------|------|
| `source/` | Copied originals + sha256 in manifest |
| `pages/page_NN.png` | Raster plates |
| `pages_manifest.json` | Page sizes / DPI / hashes |
| `ship_digest.json` | ShipDigest IR (`schemas/ship_digest.schema.json`) |
| `overlays/page_NN_draft.svg` | LLM/mock draft polygons |
| `overlays/page_NN_approved.svg` | Human-corrected polygons (preferred) |
| `digest_meta.json` | Provider / model / digest hash |

## Output platform directory

| Path | Role |
|------|------|
| `spatial_layout.json` | Zones, volumes, display coords, graywater |
| `air_flow_paths.json` | HVAC branches, cross links, adjacency |
| `import_provenance.json` | Digests / SVG hashes |
| `graphics/plan_overview.png` | Optional plate copy |

## Design notes

- **Naval Room berthing** only (well-mixed). No cruise `Cabin_Corridor`.
- Intentionally **coarse** (~10–30 zones). Ignore hatch-level GA detail.
- Providers use stdlib `urllib` (no hard SDK deps). PDF rasterization needs
  optional `pypdfium2` or `pdftoppm` (poppler).
- Agent skill: `.agents/skills/importing-naval-blueprint/SKILL.md`.

## PDF raster extras

```bash
pip install pypdfium2
# or: sudo apt-get install poppler-utils
```
