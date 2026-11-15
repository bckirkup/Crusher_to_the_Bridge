# CONTAM-EXHAUST-SINK-01
**Date:** 2026-11-15
**Commit:** 800a1958
**Pathogens:** all
**Status:** open
**Measured at:** 800a1958af01bd99e9c932425656b05cd6846171

Doc-only audit of three further Edison claims on the forced-exhaust bundle
(#1209, #1213, #1214, #1216, #1217, #1219, #1220, #1221), with a versioned
fix proposal. Document of record:
`docs/proposals/exhaust_sink_audit_and_fix_plan.md`. No code, schema,
generator or hull data changed; nothing was regenerated; no AWS or S3 was
used. Every number below is deterministic (file reads or the exact linear
operator; no RNG) and reproduces from the appendix of that document.

## Verdicts

| Claim | Verdict |
|---|---|
| 1. `filtered: false` on an internal "once-through exhaust" link raises downstream delivery; the Legend / San Antonio medical and galley links end in berthing / mess rooms | Verified (measured) |
| 2. `path_map.json` carries only `is_hvac_ducted`; three links have `filtered ≠ ducted`; no double-filtering | Verified (measured); the count is exactly three |
| 3. Galley repairs are not generator-protected; sanitary is; both Enterprise recipes keep the reversed direction | Partially verified: understated for galleys, overstated for sanitary |

## Measured

Counts: 82 platforms, 1,011 `cross_zone_links`, 77 committed
`contam/path_map.json`, 5 hulls with no contam bundle
(`expedition_cruise_300`, `fletcher_class_destroyer`, `legend_class_nsc`,
`messy_cruise_500`, `san_antonio_class_lpd`).

Links with `filtered ≠ is_hvac_ducted` — three, all ducted and unfiltered,
all on hulls with no committed bundle:

| Hull | `path` | Link | m³/h |
|---|---|---|---:|
| `legend_class_nsc` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Enlisted_Fwd` | 100 |
| `san_antonio_class_lpd` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Crew_Habitable` | 200 |
| `san_antonio_class_lpd` | `galley_exhaust_to_mess` | `HVAC_Galley` → `HVAC_Crew_Habitable` | 400 |

On a fresh export they become nine path_map entries with
`is_hvac_ducted: true` and no `filtered` key; the ContamX lane resolves them
as filtered, native as unfiltered. The PRJ `filter_nr` on all nine is 0.

Native exact retained-mass material-time, hours per unit release in the
source room, summed over the link's three destination rooms; 12 h horizon,
η 0.5, decay 0:

| Link | `filtered: true` | `filtered: false` (current) | Overboard sink | Link deleted + source group OA 1.0 |
|---|---:|---:|---:|---:|
| Legend `medical_exhaust` | 0.037208 | 0.073125 | 0.001304 | 0.001452 |
| San Antonio `medical_exhaust` | 0.017689 | 0.032918 | 0.002465 | 0.002146 |
| San Antonio `galley_exhaust_to_mess` | 0.029474 | 0.055105 | 0.003868 | 0.003611 |

The whole-hull totals for the two medical links (0.195341 → 0.240702,
0.211200 → 0.229745) equal the before / after rows of
`CONTAM-FORCED-EXHAUST-DUCTED-01`. The last two columns are in-memory
variants, not authored data.

Exhaust-class links: 637 = 585 `Sanitary_Makeup` (every one ends at a
duty-0 / OA-1.0 `AHU_HD_*` extract terminal) + 52 others, none of which
ends at a sink. No duty-0 group other than the 585 heads exists.

Committed path_maps: all 58,223 entries carry the same seven keys. 74 of 77
equal a fresh export of the current hull JSON. Three are stale:
`enterprise_constitution_tos` `path_nr` 173 and `enterprise_galaxy_tng`
`path_nr` 320 (`Galley` → `Mess_Hall`, pre-#1219 sense), and
`mega_cruise_5000` `path_nr` 479–482 (`Medical_Door_Leakage`, pre-#1220
sense).

In-memory regeneration of the seven recipe-generated hulls
(`expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`,
`diamond_princess`, `enterprise_constitution_tos`, `enterprise_galaxy_tng`,
`mega_cruise_5000`): 99 of 319 links differ from committed data. Seven are
semantic reversions of #1219 / #1220 authoring (four
`Dining_Galley_Exhaust`, two `Galley_Service_Exhaust`, one
`Crew_to_Engine_Stairwell`); 92 lose only the explicit S1 keys. All 216
sanitary links regenerate identically. Non-link content also changes:
`hot_bunk_ratio` dropped on 12 Constitution zones, per-group `oa_fraction`
added to 7 `mega_cruise_5000` HVAC groups.

`scripts/build_enterprise_platforms.py`, run into a scratch directory,
writes the legacy 12-zone / 4-link and 16-zone / 6-link Enterprise layouts
over the committed 63 / 29 and 127 / 53.

## Inferred

- The lane-versus-native difference on the two affected hulls is the
  `(1 − η)` attenuation on nine paths. No ContamX field was solved for
  either hull, so its size is not measured.
- Regenerating a GA-importer hull would drop `direction: oneway` from its
  `Sanitary_Makeup` links (252 links on 68 hulls):
  `tools/ship_blueprint_import/synthesize.py` emits them without the S1
  fields. Code-path evidence only; the ship digests are not in the tree.
- The three stale path_maps are consistent with the PRJ beside them and
  stale only against the hull JSON, so the pair must be regenerated
  together.

## Hypothesis

- No committed PRJ contains a non-AHS fan path to ambient, so adding a sink
  kind to `path_map_from_prj` changes nothing on the 77 committed bundles.
- The `mega_cruise_5000` per-group OA drift is `messy_cruise_500` data
  gained after mega was last generated.

## Forward references (existing entries not edited)

- `CONTAM-FORCED-EXHAUST-DUCTED-01` and `CONTAM-FORCED-EXHAUST-GALLEY-01`
  record the `filtered: false` authoring on the three links accurately. This
  entry adds that the change moves downstream delivery up, not overboard.
- `CONTAM-FORCED-EXHAUST-GALLEY-01` does not record that the two Enterprise
  contam bundles still carry the pre-flip galley sense. This entry does.
- `CONTAM-FORCED-EXHAUST-DOORS-01` already records the `mega_cruise_5000`
  bundle.

## Status and blast radius

Status stays `open` until the proposal's stages land or are declined. No
recorded measurement is invalidated: the frozen Phase 1 / Phase 2 study
hulls carry none of the three links, both campaign directories, their S3
prefixes, the `_v1` field caches and the committed readouts are untouched,
and no pathogen open ledger needs a note. Whether a `_v2` field cache has
been produced in S3 was not checked.

Proposed stages and suggested IDs: `CONTAM-GENERATOR-PROTECT-01`,
`CONTAM-PATHMAP-FILTERED-01`, `CONTAM-EXHAUST-SINK-02` (schema, native,
exporter), `CONTAM-EXHAUST-SINK-03` (re-point the three links),
`CONTAM-BUNDLE-RESYNC-01`. Open decisions are listed in §6.3 of the
proposal.
