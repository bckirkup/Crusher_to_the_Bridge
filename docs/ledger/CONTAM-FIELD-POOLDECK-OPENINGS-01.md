# CONTAM-FIELD-POOLDECK-OPENINGS-01
**Date:** 2026-11-15
**Commit:** 5f323c05
**Pathogens:** all
**Status:** measured
**Measured at:** 5f323c05

## Scope

Class (b) only from `docs/proposals/contam_field_adjudication_audit_and_fix_plan.md`:
Expedition pool-deck opening authoring. Class (d) is descoped from this change by
coordinator ruling and is recorded below only as deferred evidence. No
`flow_rate_m3h` magnitude, `Sanitary_Makeup` mechanism, `envelope_leak.area_m2`,
exporter, schema, engine, campaign, S3, or frozen-artifact change is made.

Before/after diagnostics are local measurements on the PR working tree at base
`5f323c05`; committed ledgers remain the durable record.

## Stage-2 resolution from committed data

- `CasualDining_Open_Doorway` and the adjacency `CasualDining -> PoolDeck`
  `doorway` are the same physical door. The cross-zone link is the authored
  Grade-C declaration (`flow_rate_m3h: 400.0`,
  `direction: "bidirectional"`, `mechanism: "pressure_opening"`,
  `filtered: false`); the adjacency entry duplicated that doorway in the
  hobbyist field export. The adjacency entry is removed.
- `ObsLounge -> PoolDeck` is not an intended 10 m² always-open promenade void.
  `PoolDeck` is the semi-open exterior deck (`exterior_zones: ["PoolDeck"]`,
  "Pool deck, semi-open"), while `ObsLounge` is an enclosed forward observation
  lounge on the same deck. The Expedition `orifice_type_map` sent `open_deck`
  to `promenade` (10 m², `ShaftOpenW`), which produced the implausible
  always-open field path. The adjacency type is corrected to `doorway`; native
  adjacency rate is unchanged because `doorway` and `open_deck` both fall to
  the default 10 m³/h native adjacency rate, while the field orifice becomes
  the 1.8 m² `DoorTrafficW` doorway.

## Data and bundle changes

- `data/platforms/expedition_cruise_450/air_flow_paths.json`: adjacency only.
  - `ObsLounge -> PoolDeck`: `open_deck` → `doorway`.
  - Removed duplicate adjacency `CasualDining -> PoolDeck` `doorway`.
- Regenerated only `data/platforms/expedition_cruise_450/contam/platform.prj`
  and `contam/path_map.json` with `--ahs-terminal-mode commissioned`.
  `path_map.json` entries move 344 → 343: `p048` becomes `doorway`
  `ObsLounge -> PoolDeck`, the duplicate `p050 doorway` is gone, and
  `CasualDining_Open_Doorway` renumbers to `p132`. Subsequent `path_nr` values
  shift by one; no other platform bundle is touched.

## Witnesses

`tools/contam_flow_compare.py --platform expedition_cruise_450 --run-contamx`:

| witness | before | after |
|---|---:|---:|
| path_map entries | 344 | 343 |
| native links | 274 | 272 |
| ContamX kept Crusher paths | 105 | 106 |
| `ObsLounge -> PoolDeck` field flow | +1683.5257628785732 m³/h (`open_deck`) | +923.8013569951521 m³/h (`doorway`) |
| `PoolDeck -> CasualDining` duplicate adjacency field flow | 1060.3181857644354 m³/h | removed |
| `CasualDining_Open_Doorway` `PoolDeck -> CasualDining` field flow | 899.3218855502752 m³/h | 1199.91557623014 m³/h |
| combined `PoolDeck -> CasualDining` field flow | 1959.6400713147863 m³/h | 1199.91557623014 m³/h |

Native declaration remains `CasualDining <-> PoolDeck` 400 m³/h each way and
`ObsLounge <-> PoolDeck` 10 m³/h each way; the residual field/native pressure
difference is the representation gap tracked by the deferred pressure-review
stage, not an unchanged authored duplicate.

`tools/diag/contam_paired_diagnostic.py --hull expedition_cruise_450` wrote 24
cells before and after (filter efficiency 0.3, natural decay 0.10 /h, horizon
12 h). `authored` equals `commissioned` after the change. Key `pulse_t0`
whole-hull material-time values:

| source | lane | before | after |
|---|---|---:|---:|
| `MainDining` | native | 0.17675557495167304 h | 0.17675337418717954 h |
| `MainDining` | commissioned/authored | 0.1912604906581144 h | 0.19126053096243287 h |
| `PoolDeck` | native | 2.569332379975662 h | 2.602185735640335 h |
| `PoolDeck` | commissioned/authored | 0.7740977157007225 h | 1.07139233428175 h |

Closure error stayed at solver round-off (≤ ~1.4e-15 h). The PoolDeck-source
increase is consistent with removing the duplicate CasualDining doorway and
the 10 m² open-deck void: less spurious export to CasualDining leaves more
PoolDeck source mass local, while the declared 400 m³/h CasualDining opening
remains authored.

## Checks

- `tools/diag/forced_exhaust_audit.py audit`: `platforms=82 links=1018
  recount=82/1018 reconciled=True` (cross-zone link audit unchanged; this edit
  touches adjacency only).
- `tools/contam_commissioned_check.py --platform expedition_cruise_450`:
  `PASS: every commissioned terminal solved inside 5% of declared.`

## Deferred class-(d) evidence

Coordinator ruling descoped class (d) from this PR; it follows the proposal's
stage 1 pressure diagnostic (`CONTAM-FIELD-PRESSURE-REVIEW-01`) and stage 6
per-hull envelope/make-up authoring (`CONTAM-FIELD-ENVELOPE-MAKEUP-01`) after
the stage-5 envelope-boundary sibling lands. Measured options, kept here so the
next session does not re-derive them:

- Re-pointing `Sanitary_Makeup` to `mechanism: "prescribed_flow"` makes the
  sanitary head make-up pairing exact in local commissioned exports, but at the
  current envelope area it worsens solved fan/envelope ΔP (Expedition max
  ≈ −1.75e6 Pa; destroyer ≈ −182707 Pa). It is also blocked in this PR because
  S1 tests/ledgers pin `Sanitary_Makeup` as `oneway`/`pressure_opening`/unfiltered.
- Raising the shared hobbyist `envelope_leak.area_m2` from the pinned 0.0001 m²
  Jacobian reference to ≈0.1 m² reduced local commissioned ΔP to Expedition max
  ≈20–26 Pa and destroyer <1 Pa, but the constant is shared by all 77 committed
  bundles, is pinned by `tests/test_contam_hobbyist_destroyer.py`, and would
  force a fleet re-sync outside this class-(b) PR.
- A per-hull leak area is not expressible in committed data today; it needs a
  small exporter/hobbyist-override code path, which is outside the proposal's
  data-only stage-6 wording and was not authorized here.

## Pre-stage-5 dependency

These witnesses are **pre-stage-5**. The sibling
`CONTAM-FIELD-ENVELOPE-BOUNDARY-01` session is changing path_map/lane sink
handling for positive outward `envelope_leak` flow. If it merges first, this
branch should rebase and re-run the Expedition witnesses above; the class-(b)
opening correction itself is independent of envelope-leak boundary semantics.
