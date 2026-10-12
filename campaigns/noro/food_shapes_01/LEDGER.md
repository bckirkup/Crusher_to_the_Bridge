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
| image built | done | `picard-campaign:noro-food-shapes01` @ `45b2bf18` → `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:bb962a4282accd9ca848c32465e861314f9ddf798dec6d63353c17791427a981`; jobdef `picard-noro-food-shapes-01:1` (digest-pinned, ACTIVE, retry ×10 `Host EC2*`) |
| local smoke | done | `fl_exp_12d_scr_redraw_mint` index 0 (seed 8000) on the eval image: 3-member zip contract + armed override echo (`lot_object_probability [0.02,0.15]`, `lot_state_redraw "per_window"`, object modes) + `redraw`/`extent_mode`/`extent_windows` witness fields on object rows; voyage minted 1 `ill_handler`, 0 `provisioned_lot` (expected at ~8.5%/voyage — the 48-cell block carries the lot gate) |
| canary (108 cells, exp) | done — **all §8 gates PASS** | 108/108 children SUCCEEDED, 0 failures, 108/108 zips; see Canary readout below |
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

Submitted 2026-10-12 on `picard-campaign-queue` (Spot FIFO) under jobdef
`picard-noro-food-shapes-01:1`; manifest mirrored to
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_food_shapes_01/manifest.json`.
Zips at `s3://…/campaign/noro_food_shapes_01/<block>/<run_id>_s<seed>.zip`.

| block | cells | array job ID | landed | failed | gate verdict |
|-------|-------|--------------|--------|--------|--------------|
| `canary_exp_redraw_mint` | 48 (seeds 8000–8047) | `327850aa-ab1f-4088-afdc-a6813cd5b444` | 48/48 | 0 | **PASS** |
| `canary_exp_bg_mint` | 24 (seeds 8000–8023) | `15d09b9c-f88c-4e33-a599-4341222dcbbe` | 24/24 | 0 | **PASS** |
| `canary_exp_fx_wide` | 24 (seeds 8000–8023) | `47ae40e9-18b9-4a34-9a9d-e06fe0a46d49` | 24/24 | 0 | **PASS** |
| `canary_exp_ship` | 8 (seeds 8000–8007) | `bd4f13a9-c818-44aa-843d-a9f25c853e0f` | 8/8 | 0 | **PASS** |
| `canary_exp_off` | 4 (seeds 8000–8003) | `77df8c83-b18b-4fd9-8e6e-309a09378e9c` | 4/4 | 0 | **PASS** |

Cross-cutting: 108/108 zips carry the 3-member contract
(`summary.json`, `growth_census.json.gz`, `rss_samples.json`) — 0
member violations. Every cell echoes its expected
`parameters.common_source` override verbatim (0 echo violations; ship
arm echoes `titre_draw_mode` absent → shipped `two_mode` at
`engines/transmission_core.py:3377` @ `45b2bf18`). Every voyage
non-degenerate (`cumulative_ever_infected` ≥ 4 all cells).

Gate detail vs design §8:

- **`redraw_mint`** — ≥1 `provisioned_lot`: 4 objects across 4/48 cells
  (E≈4, P(0)≈0.014) ✓. Every lot row `redraw:"per_window"` +
  `extent_mode:"emergent"` ✓. All 73 pan titres + 4 object-final
  titres inside the implicated band (1.5e2, 5e3) — 0 out-of-band, the
  #992 pin holds ✓. Multi-window varying titre: all 4 objects re-mint
  per served window — s8020 `cso-norwalk_gi-1` (salad_leaf, CrewMess)
  27 pans over 28 windows, per-window titres 151.8→4391.7; s8001
  (dairy, CrewMess) 21 pans / 22 windows; s8026 (bakery, CasualDining)
  19 pans / 19 windows; s8032 (fresh_produce, MainDining) 6 pans /
  5 windows. Titre constant within each served window, re-minted at
  each window boundary (two co-occurring meal windows in one epoch —
  e.g. s8026 Breakfast vs Lunch @ epoch 58 — each take their own
  re-mint, which is the declared semantics of `start_epoch` = pan
  emission epoch, not window id) ✓ — the end-to-end integration proof.
- **`bg_mint`** — `titre_draw_mode:"background"` echo on all 24 ✓;
  ≥1 lot object: 2 objects across 2/24 cells (E≈2, P(0)≈0.13) ✓ —
  s8001 dairy/CrewMess titre 156.02 constant over 21 pans (background
  spec, not band-gated), s8020 salad_leaf/CrewMess 4185.4 over 35 pans.
  Same-seed cross-check: the s8001 bg object mints at the same
  `seeded_epoch` 12 and item as the redraw_mint s8001 object — mint
  gate identical, only the titre spec differs.
- **`fx_wide`** — hard echoes `lot_extent_mode:"declared"` +
  `lot_extent_windows [12,24]` on all 24 ✓. 0 `provisioned_lot`
  objects — conditional witness, P(0)≈0.78 at shipped mint; not a
  failure. No serving-cap or `extent_met`-outside-declared violations
  (none minted to exercise them).
- **`ship`** — shipped-config echo on all 8 ✓; `titre_draw_mode`
  resolves `two_mode` (key absent → shipped default) ✓; handler/diner
  objects present: 18 `ill_handler` + 4 `ill_diner`; 0 lot objects at
  shipped mint (0.001–0.02, E≈0.07 over 8 cells) ✓.
- **`off`** — zero-witness: 0 objects, 0 events, `dose_credited` 0.0
  across all 4 cells ✓.

Failures: none — no resubmits were needed; no non-Spot-reclaim
failure class observed.

## Wave submissions

Pending — image digest, jobdef revisions, array job IDs, submit SHAs.

## Findings

Pending readout. Margin map (design §7.2): titre denominator →
`mint − bg_mint`, `ind − ind_bg` (powered), `ship − bg` (thin);
cadence → `redraw_mint − mint` (powered), `ship − redraw`,
`fx_wide − ship − fx_narrow` (iso-dose); mint → `mint − ship`,
`redraw_mint − redraw`, `bg_mint − bg`; conjunction → `redraw_mint`
vs `ind`.
