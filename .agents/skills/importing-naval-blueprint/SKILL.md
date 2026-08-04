---
name: importing-naval-blueprint
description: Import naval general-arrangement drawings (PDF/images) into Crusher ship classes via digest + GIMP/Krita SVG overlays + deterministic synthesize. Use when adding a naval platform from ship drawings/blueprints/GAs.
---

# Importing a Naval Blueprint → Ship Class

## Prerequisites

- Repo root working directory
- Python 3.11+
- For PDF: `pypdfium2` **or** `pdftoppm` (poppler-utils)
- For live digest: `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
- Overlay editor: Krita, GIMP, or Inkscape

## Devin Secrets Needed

None for mock/fixture. Live providers need the matching API key env var.

## Steps

### 1. Ingest

```bash
python3 -m tools.ship_blueprint_import ingest \
  --input path/to/general_plan.pdf \
  --workdir work/blueprints/<ship_slug> \
  --dpi 150
```

### 2. Digest (draft ShipDigest + SVG)

```bash
# Offline
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/<ship_slug> --provider mock

# Live (example: Gemini)
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/<ship_slug> --provider gemini \
  --hint "Arleigh Burke Flight IIA destroyer; focus on berthing and engineering"
```

### 3. Human overlay correction

1. Open `pages/page_NN.png` in Krita/GIMP/Inkscape.
2. Import `overlays/page_NN_draft.svg`.
3. Edit polygons to simulation-scale zones only; **path id = zone id**.
4. Save as `overlays/page_NN_approved.svg`.
5. Optionally tweak `ship_digest.json` (occupancy, HVAC hints, ACH).

See `tools/ship_blueprint_import/templates/EDITOR_NOTES.md`.

### 4. Synthesize (fully automated)

```bash
python3 -m tools.ship_blueprint_import synthesize \
  --workdir work/blueprints/<ship_slug> \
  --platform-id <snake_case_id> \
  --output data/platforms/<snake_case_id> \
  --require-approved
```

### 5. Validate

```bash
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/<snake_case_id>
```

Expected: `VALIDATION PASSED`. Then continue with skill `adding-new-platform`
(precompute deck assets, agent class preferences, optional Contam fiction
bootstrap).

## Non-goals

- Cruise cabin-corridor generation
- Authentic ContamW authoring from drawings
- LCARS / Streamlit integration

## Docs

- `docs/SHIP_BLUEPRINT_IMPORT.md`
- `schemas/ship_digest.schema.json`
