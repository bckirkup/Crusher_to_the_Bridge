# CONTAM-CONNECT-01
**Date:** 2026-11-01
**Commit:** 338b5634
**Pathogens:** all
**Status:** measured
**Measured at:** ec3036d9

Implements ranked fix #3 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): lexington_cv2 / saratoga_cv3 disconnected-compartment
blocks.

## Defect

The GA import synthesized only the openings whose traced polygons touched
plus a handful of digest hints: 50 adjacency edges each on lexington_cv2
(97 zones) and saratoga_cv3 (108 zones). Result: **78 zones unreachable
on lexington_cv2, 92 on saratoga_cv3 — in BOTH engines** (native,
commissioned-export, and committed-prj graphs all agreed). Entire deck
levels — third_deck, inclined platform, both machinery platforms, most of
the hold — had zero airflow paths, so no incidence could reach them.

## Fix (data, not engine)

New adjacency edges authored from the GA source record conventions:

- **Same-deck `passageway`** between each zone and its two nearest
  same-deck neighbours by overlay-display position — the same rule the
  synthesizer applied (`polygons_touch` same-page proximity), applied to
  the committed zone geometry. This models compartments opening onto the
  drawn fore-aft PASSAGE corridors visible on every deck sheet.
- **Cross-deck `ladder`** between vertically adjacent deck levels,
  preferring named circulation zones (`*_Trunk`, `*_Hoist`,
  `Elevator_*`, `Flats_*`, `Uptakes_*`) at matching fore-aft positions —
  the trunks/hoists drawn on the GA sheets.
- Cross-deck pairs that would have been typed `passageway` are emitted as
  `ladder`.

Same mechanism both hulls: net +104 edges on lexington_cv2 (50 → 154)
and +113 on saratoga_cv3 (50 → 163). `Sanitary`-type zones are
excluded from new adjacency — they connect only via their
`Sanitary_Makeup` cross-zone links and own exhaust (the shared-sanitary
wiring invariant), so the generator's drafted head edges were dropped
and the compartments they orphaned re-attached to non-sanitary
neighbours. Contam artifacts regenerated via
`author_contam --platform-dir` so `openings_draft.json`, `path_map.json`
and `platform.prj` mirror the new adjacency (offline PRJ gate PASS:
97/108 zones, 300/320 paths).

## Honesty note

Edge positions are geometric reconstructions from the committed zone
overlays — the import workdir digests were not retained (`work/` is
gitignored). Individual door positions are NOT sheet-verified; every
opening lands in `openings_draft.json` as `status: draft` pending ContamW
engineer confirmation, same as the original 50. Deck-level connectivity
structure (fore-aft passages + vertical trunks at circulation spaces) is
sheet-consistent; treat as `era_plausible` grade.

## Measured

Post-fix re-audit (`tools/museum_hull_audit.py`):

| hull | lane | unreachable before | after |
|---|---|---|---|
| lexington_cv2 | native | 78 | 0 |
| lexington_cv2 | export | 78 | 0 |
| lexington_cv2 | committed prj | 78 | 5 |
| saratoga_cv3 | native | 92 | 0 |
| saratoga_cv3 | export | 92 | 0 |
| saratoga_cv3 | committed prj | 92 | 4 |

Residual committed-prj unreachable counts are the 15-char /
underscore-stripping name-normalization drift (ranked fix #6), not real
disconnection — the export lane proves the connectivity is present.
