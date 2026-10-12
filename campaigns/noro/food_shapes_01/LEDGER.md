# NORO-FOOD-SHAPES-01 — campaign ledger

Design of record:
`docs/norovirus/noro_food_shapes_01_sweep_design.md` (frozen before any
cell ran). Question: do the implicated titre denominator (`two_mode`)
and the cadence dose shape (`per_window` re-mints + `declared` extent)
recover `ind`-like conversion and the D2 posted-AR signature on object
arms, with the mint gate re-expressed at the v1 interval — while D1
stays in band and D4 keeps?

## Stage table

| stage | state | evidence |
|-------|-------|----------|
| design frozen | done | `docs/norovirus/noro_food_shapes_01_sweep_design.md`; this package (33 tiers, 38 blocks) |
| image built | — | tag `noro-food-shapes01`; record digest + jobdef revision here at submit |
| local smoke | — | `fl_exp_12d_scr_redraw_mint` index 0: zip contract + override echo + `per_window` witness |
| canary (108 cells, exp) | — | gates: design §8; STOP and report after |
| wave 1 — exp, all 11 arms | — | 11,000 cells; user go required |
| wave 2 — cls/spr factorial core | — | 8 arms × 2 hulls × 1,000; user go required |
| wave 3 — cls/spr remainder | — | `redraw`, `fx_wide`, `fx_narrow` × 2 hulls; user go required |
| readout + findings | — | `docs/norovirus/noro_food_shapes_01_readout.md` |

## Grid

3 hulls (exp 8000–8999, cls/spr 8105–9104, 1,000 seeds/cell; mega
excluded — objects never armed there) × 11 arms = 33,000 voyages,
fixed coordinates identical to FOOD-01/02, AGE-FOOD-01, SCORE-01 and
ENTRAIN-01 (rung `shipped`, bp32.5c18.5, nsf29, 288 epochs, comp65,
dose 7.57, embarkation 2026-01-10, shipped class mix stamped).

| arm | common_source override | role |
|-----|------------------------|------|
| `off` | `mode: off` | mechanism-absence floor; bit-identical to prior `off` |
| `ind` | lot/handler/diner `independent` | v1 baseline at this image — lot events draw implicated band under shipped `two_mode` |
| `ind_bg` | `ind` + `titre_draw_mode: "background"` | powered titre-margin read on the converting channel; bit-identity bridge to ENTRAIN-01 `ind` @ `dbbd5395` |
| `ship` | objects, shipped intervals | scored shipped config: objects + `two_mode` + `emergent`/`per_object` |
| `bg` | `ship` + `titre_draw_mode: "background"` | titre axis at shipped mint; bridge to ENTRAIN-01 `ship` @ `dbbd5395` |
| `mint` | `ship` + `lot_object_probability (0.02,0.15)` | mint axis — v1 `lot_event_probability` interval on the object gate |
| `bg_mint` | `bg` + mint | {titre}×{mint} corner — powered titre read on objects |
| `redraw` | `ship` + `lot_state_redraw: "per_window"` | cadence axis at shipped mint (re-mints land implicated band under `two_mode` — #992 pin) |
| `redraw_mint` | `redraw` + mint | {cadence}×{mint} — the conjunction cell |
| `fx_wide` | `ship` + `lot_extent_mode: "declared"`, `lot_extent_windows (12,24)` | iso-dose extent, wide |
| `fx_narrow` | `ship` + `declared`, `(2,4)` | iso-dose extent, narrow |

## Mechanism contracts

None required — every arm is a shipped `common_source` config
override (verified against `engines/transmission_core.py` @ `36ce23c8`).
Pruned extension arms (declared in design §3.3): `redraw@background`,
`fx@{background,mint}`, `extra_lot` ladder, handler/diner mint, `ind`
mint — re-arm as new blocks on these seed lists if first-order
margins move.

## Canary readout

(Blocks: `canary_exp_redraw_mint` 48, `canary_exp_bg_mint` 24,
`canary_exp_fx_wide` 24, `canary_exp_ship` 8, `canary_exp_off` 4.)
Pending — jobdef/array IDs and gate results land here.

## Wave submissions

Pending — image digest, jobdef revisions, array job IDs, submit SHAs.

## Findings

Pending readout. Margin map (design §7.2): titre denominator →
`mint − bg_mint`, `ind − ind_bg` (powered), `ship − bg` (thin);
cadence → `redraw_mint − mint` (powered), `ship − redraw`,
`fx_wide − ship − fx_narrow` (iso-dose); mint → `mint − ship`,
`redraw_mint − redraw`, `bg_mint − bg`; conjunction → `redraw_mint`
vs `ind`.
