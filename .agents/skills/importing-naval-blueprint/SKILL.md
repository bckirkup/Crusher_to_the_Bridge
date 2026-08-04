---
name: importing-naval-blueprint
description: Import naval general-arrangement drawings (PDF/images) into Crusher ship classes and ContamW Path A starter projects via digest + GIMP/Krita SVG overlays + synthesize + author_contam. Use when adding a naval platform from ship drawings/blueprints/GAs or expediting ContamW tracing.
---

# Importing a Naval Blueprint → Ship Class + Contam Starter

## Prerequisites

- Repo root working directory
- Python 3.11+
- For PDF: `pypdfium2` **or** `pdftoppm` (poppler-utils)
- For live digest: `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
- Overlay editor: Krita, GIMP, or Inkscape
- ContamW 3.4 (for engineer handoff); ContamX optional for Path A sims

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
python3 -m tools.ship_blueprint_import digest \
  --workdir work/blueprints/<ship_slug> --provider mock
# or: --provider gemini --hint "…"
```

Optional Contam IR in `ship_digest.json`: `opening_hints`, `contam_hints`
(`skip_duct_spines: true` by default for naval GAs).

### 3. Human overlay correction

1. Open `pages/page_NN.png` in Krita/GIMP/Inkscape.
2. Import `overlays/page_NN_draft.svg`.
3. Edit polygons to simulation-scale zones; **path id = zone id**.
4. Save as `overlays/page_NN_approved.svg`.

See `tools/ship_blueprint_import/templates/EDITOR_NOTES.md`.

### 4. Synthesize + Contam starter (Target B)

```bash
python3 -m tools.ship_blueprint_import synthesize \
  --workdir work/blueprints/<ship_slug> \
  --platform-id <snake_case_id> \
  --output data/platforms/<snake_case_id> \
  --require-approved \
  --author-contam
```

Or separately:

```bash
python3 -m tools.ship_blueprint_import author_contam \
  --platform-dir data/platforms/<snake_case_id> \
  --workdir work/blueprints/<ship_slug>
```

Emits `contam/platform.prj`, `path_map.json`, `openings_draft.json`,
`CONTAM_HANDOFF.md`. Ducts omitted by default — engineers author them in ContamW.

### 5. Validate

```bash
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/<snake_case_id> \
  --contam-gate
```

Then: precompute deck assets / agent preferences (`adding-new-platform`);
open `contam/platform.prj` in ContamW for Target C handwork; run ContamX Path A
when ready (`contamx-interop` skill).

## Non-goals

- Cruise cabin-corridor generation
- As-built duct/fan/leakage digitization from GAs (Target C — ContamW handwork)
- LCARS / Streamlit integration

## Docs

- `docs/SHIP_BLUEPRINT_IMPORT.md`
- `docs/CONTAM_INTEROP.md`
- `schemas/ship_digest.schema.json`
