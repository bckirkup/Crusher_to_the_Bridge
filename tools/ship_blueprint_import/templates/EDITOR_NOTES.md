# Overlay editor notes (GIMP / Krita / Inkscape)

Crusher naval blueprint import uses **named SVG paths** as the human
correction surface. Geometry in `page_NN_approved.svg` drives synthesis;
metadata (ACH, occupancy, type) stays in `ship_digest.json`.

## Naming rule

Every zone shape **must** have an `id` equal to the ShipDigest zone id
(e.g. `Bridge`, `Berthing`, `Engine_Room`). Spaces become underscores.

Decorative helpers may use underscore-prefixed ids (`_page_bounds`) — they
are ignored by the importer.

## Recommended workflow

1. After `digest`, open `pages/page_01.png` in your editor.
2. Import `overlays/page_01_draft.svg` as a vector/path layer
   (Inkscape: File → Import; Krita: add as vector layer / paste SVG;
   GIMP: File → Open as Layers or import paths from SVG).
3. Move/reshape polygons so they cover the **simulation-scale** spaces only
   (ignore hatches, fittings, hand markup).
4. Keep path/layer names = zone ids.
5. Export / save as `overlays/page_01_approved.svg` (paths only is fine).
6. Optionally edit `ship_digest.json` occupancy / HVAC hints.
7. Run `synthesize` then `validate`.

## Contam-friendly ids

When practical, keep zone ids ≤ 15 characters for Contam fiction bootstrap.
Existing naval platforms often use longer names (`Enlisted_Berthing_Fwd`);
that is allowed for Crusher JSON.
