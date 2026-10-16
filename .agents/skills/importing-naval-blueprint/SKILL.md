---
name: importing-naval-blueprint
description: Import naval general-arrangement drawings (PDF/images) into Crusher ship classes and ContamW Path A starter projects via agent-authored digest + synthesize + author_contam. Use when adding a naval platform from ship drawings/blueprints/GAs or expediting ContamW tracing.
---

# Importing a Naval Blueprint → Ship Class + Contam Starter

Primary path (proven on ~70 hulls, maritime.org "Booklet of General Plans"):
the agent IS the vision digest — no LLM API key, no GIMP round-trip. Rasterize
pages, read them yourself with grid PNGs (+ OCR on big sheets), author
`ship_digest.json` and `page_NN_approved.svg` programmatically, then synthesize
and validate. The human overlay loop (Krita/GIMP) remains for engineer
refinement only.

## Prerequisites

- Repo root working directory; repo `.venv/bin/python` (system python lacks jsonschema)
- `pypdfium2` for PDF rasterization
- Optional: `tesseract-ocr` + `pytesseract` for OCR label reading on sheets >~6000px
- ContamW 3.4 (engineer handoff only); ContamX optional for Path A sims

## Devin Secrets Needed

None. The `--provider live` digest backends need `GEMINI_API_KEY` /
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, but the agent-authored path supersedes
them for sheet reading.

## Steps

### 1. Ingest

```bash
.venv/bin/python -m tools.ship_blueprint_import ingest \
  --input work/blueprints/<slug>/source/<booklet>.pdf \
  --workdir work/blueprints/<slug> --dpi 150
```

`--input` takes a LOCAL path under the repo root — URLs and /tmp paths are
rejected. Download the PDF into the workdir's `source/` dir first. Big BB/CV
rasters reach ~22k px wide — keep `Image.MAX_IMAGE_PIXELS=None` in scripts.

`work/` is gitignored — digests, author scripts, overlays and source PDFs
never commit. Only `data/platforms/<pid>/*` + docs do.

### 2. Sheet reading (the agent is the digest)

- Draw 5%/10% red grid PNGs over page rasters to read normalized polygon coords.
- On wide sheets (>~6000px): OCR first — `image_to_data` TSV → cluster into
  y-row label dumps — gives the whole label map in one pass; use grid crops
  only to spot-verify. Grep out raw TSV numeric echoes.
- Sheets are not clean plan views. Title blocks, margins, and stacked
  multi-deck views mean every deck needs `DeckInfo.plan_bbox_norm` +
  `hull_x_span_m`/`hull_y_span_m`; each zone maps through ITS deck's box
  (deck-keyed, page-fallback). A zone's page must equal its deck's page.
- Single-sheet multi-band plates → one DeckInfo per band, each with its own
  `plan_bbox_norm` + local `hull_x_span`. Fragment sheets (several separated
  deck strips) → one DeckInfo per fragment.
- Below-main-deck spaces existing only in the inboard profile → zone ON the
  profile page WITH explicit `volume_m3_est` + `floor_area_m2_est`; the polygon
  then fixes only fore-aft position.
- A level drawn on another deck's plate but physically one storey up (deckhouse
  on the main-deck plate) → model as its own deck at the right elevation;
  cross-sections pin it.
- Bow direction: pin from the raked stem on the inboard profile — every
  maritime.org booklet read so far is bow-at-right.
- Deck-name ordering varies by booklet family — follow the booklet's own
  deck list / fire-plug order, not class assumptions.

### 3. Author ship_digest.json + approved SVGs (scripted)

Build the digest as a plain dict → `ShipDigest.model_validate`, then emit the
approved overlays directly:

```python
from tools.ship_blueprint_import import draft_svgs_from_digest
draft_svgs_from_digest(digest, manifest, overlays_dir,
                       allowed_roots=(REPO,), suffix="approved")
```

Schema traps (ZoneDigest): fields are `type`/`deck` (NOT `zone_type`/`deck_id`);
`traffic`/`notes` must be non-None literals; `adjacency_hints` keys are
`from`/`to`/`type` dicts; `CrewClassBlock.role_group` is only `crew`/`passenger`
and `berth_zone` is a single zone id; `max_occupancy` must be ≥1 or omitted —
0 is a pydantic rejection.

Zone conventions:
- Tall spaces (hangars ~5-6 m clear, machinery rooms spanning two deck heights)
  keep the 2.6 m sheet ceiling WITH explicit `volume_m3_est`; synthesize
  auto-raises `floor_area_m2` to volume/ceiling. Zone such rooms ONCE on one
  deck and note it in `uncertainties`. Only `volume_m3_est` is consumed —
  `floor_area_m2_est` is ignored by `_zone_geometry`.
- Explicit volumes must be ≥ polygon_area × ceiling or the sanity GEOMETRY
  check warns (for cargo holds use real height, e.g. ×4.2 m, not floor bumps).
- Zone page == its deck's page. Multi-band sheets → one DeckInfo per band.
- Adjacency canonical vocab: `passageway|ladder|door|deck_walkway|hatch|elevator`
  (+`stairwell`/`doorway`/`service_hatch`); anything else falls back to the
  default orifice type — don't invent verbs.
- Sanitary zones: inset polygons ~0.005x / sub-band y so bbox-touch never
  edges a head; the invariant test requires base_ach≈19.15, ceiling 2.3, own
  exhaust-only `AHU_HD_<id>`, exactly one `Sanitary_Makeup` link, no adjacency
  edges. `serves` refs across decks are legal.
- Carrier conventions (§Carrier-scale in GA_IMPORT_APPROACH.md): flight deck =
  open-air Free zone (nat_supply, oa 1.0); hangar = Free (1–3 fire-curtain
  segments + hangar_door markers or explicit VENT_Hangar mech_exhaust hint);
  island = thin deck above flight deck; aircraft/bomb elevators = adjacency
  `type:"elevator"`; air wing = `air_wing_*` crew classes.
- LSD well deck = ONE Free zone at floor level with explicit ~13,000 m³ volume;
  floodable wing ballast tanks zoned once.

### 4. Synthesize + Contam starter

```bash
.venv/bin/python -m tools.ship_blueprint_import synthesize \
  --workdir work/blueprints/<slug> \
  --platform-id <snake_case_id> \
  --output data/platforms/<snake_case_id> \
  --require-approved --author-contam
```

`synthesize` writes `graphics/graphics.json` itself with `plan_overview.png`
and EMPTY `deck_plans:{}` — the per-deck crop step fills it in the same PR.

### 5. Complement & crew_manifest

- Read the booklet's accommodation/complement table FIRST (BuShips plate-2
  data sheets also carry deck elevations "HEIGHTS ABOVE BASE LINE").
- Printed tables that disagree with their own row sums → use the printed
  TOTAL, flag in uncertainties. No table → class-/era-typical complement,
  flagged NOT plate-read in uncertainties and the manifest `source:` field.
- Troops/embarked passengers = `role_group:"passenger"` manifest classes
  (transports, LSDs, APAs); `nominal_complement` appears in `spatial_layout`
  ONLY when BOTH passengers>0 AND crew>0 — all-crew naval hulls keep the
  complement in `crew_manifest.json` only (the campaign smoke refuses
  non-positive declared complements).
- `role_group` is only `crew`/`passenger`; split manifest classes by
  officer/CPO/enlisted/marines/air-wing as the plate shows.

### 6. Systems notes & era tagging

- `systems.py` + `digest.systems` infer vent markers: sheet label direction >
  cowl facing (fore→supply, aft→exhaust) > kind table. Markers carry
  `evidence: sheet_read|era_plausible`.
- Pre-WWI / contract-plan hulls have no era row: keep `usn_ww2` era, tag
  groups `era_plausible`, flag in uncertainties — never edit ERA_RULES or
  systems.py as part of an import.
- SEWAGE-token tank labels auto-join `graywater_zones`.
- Non-GA booklets (contract plans, incomplete sets) still import: zone only
  the drawn bands, omit undrawn levels entirely, flag LOW confidence +
  never-completed in uncertainties.

### 7. Validate

```bash
.venv/bin/python -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/<snake_case_id> --contam-gate
```

Battery per hull: contam-gate + platform tests (sanitary/complement/schema) +
sanity_checker + dashboard tests + pre-commit. Expect warn-level
`SOP-007/009 GRAPH_REF` on naval platforms — pre-existing, not a failure.

### 8. Deck GUI assets — land IN the import PR

Per-deck crops ride in the same PR, not a follow-up:

1. Read each deck's `plan_bbox_norm` from the workdir digest; crop
   `pages/page_NN.png` +2% pad (≤2000px) → `graphics/deck_<deck_id>.png`;
   register `graphics.json.deck_plans[deck_id]`.
2. Add the pid to `scripts/precompute_deck_assets.py` PLATFORMS (hardcoded).
3. Run `.venv/bin/python scripts/precompute_deck_assets.py --platform <pid>`
   — writes geojson/hull/blueprint_bg/manifest AND regenerates
   `data/platforms/deck_provenance.json` over the whole catalog.
4. Gate: `plan_for_deck(<deck>)` per deck + dashboard tests.
   `plan_overview.png` may need a manual ~8000px downscale first (the 13 MB
   castle precedent).

### 9. PR + sibling-merge discipline

One PR per leg; do NOT merge (owner/coordinator merges after CI green).
Shared-file collision surface on every import PR: `README.md` platforms table,
`docs/GA_IMPORT_APPROACH.md` import table, `docs/AGENTS.md` count sentence,
PLATFORMS list, `deck_provenance.json`. On sibling conflicts union-merge the
rows (keep both sets), take their deck_provenance and re-run
`--platform <pid>` to regenerate. `git rebase --continue` needs
`GIT_EDITOR=true`. Transient index-pack push failures → retry.

Report immediately if the booklet is non-GA, missing sheets, or illegible —
then proceed with the flagged-low-confidence convention if workable
(sister-derived zones for a missing plate; contract-plan zoning for
engineering-plate booklets).

## Non-goals

- Cruise cabin-corridor generation
- As-built duct/fan/leakage digitization from GAs (Target C — ContamW handwork)
- LCARS / Streamlit feature work (deck assets only)
- Engine/config/epidemiology changes — imports are data-only
- Submarines (ss*/alligator booklets) — out of scope per owner

## Docs

- `docs/GA_IMPORT_APPROACH.md` — the full recipe + per-hull conventions
- `docs/SHIP_BLUEPRINT_IMPORT.md`
- `docs/CONTAM_INTEROP.md`
- `schemas/ship_digest.schema.json`
