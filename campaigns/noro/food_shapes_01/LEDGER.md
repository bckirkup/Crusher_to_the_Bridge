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
| wave 1 — exp, all 11 arms | done | 11,000 cells (11×1,000) on `picard-campaign-queue`, 0 FAILED; job IDs + early spot-check below |
| wave 2 — cls/spr factorial core | done — submitted | **PRUNED**: 7 arms × 2 hulls × 1,000 = 14,000 cells (`redraw_mint` dropped by amendment); job IDs + probe spot-check below |
| wave 3 — cls/spr remainder | **dropped** | `redraw`, `fx_wide`, `fx_narrow` × 2 hulls (6,000 cells) — dropped by the same user-approved amendment; cadence and extent margins measured null on exp (wave-1 readout) |
| wave-1 readout (exp) | done — measured | `docs/norovirus/noro_food_shapes_01_wave1_readout.md`; tools `tools/noro_diag/food_shapes_01_{scan,report,bridge}.py` |
| final readout (exp+cls+spr) | done — measured | `docs/norovirus/noro_food_shapes_01_readout.md`; 25,000/25,000 cells scored — exp carried verbatim from wave-1, 14,000 cls+spr cells census re-parsed (0 errors); bridges + dose audits on both hulls |

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

### Wave 1 — exp, all 11 arms (11,000 cells)

Submitted 2026-10-12 ~19:59 UTC on `picard-campaign-queue` (Spot FIFO,
strict submit order) under jobdef `picard-noro-food-shapes-01:1`
(digest-pinned `picard-campaign@sha256:bb962a4282accd9ca848c32465e861314f9ddf798dec6d63353c17791427a981`
@ `45b2bf18`, retry ×10 `Host EC2*`). One array per block, literal
`containerOverrides` argv identical in shape to the canary submit
(`campaign_entrypoint.py --campaign noro/food_shapes_01 --block
<block> --seeds 8000…8999 --manifest … --pathogen-id norwalk_gi
--epochs 288`), `arrayProperties.size: 1000`. Manifest mirrored at
`s3://…/campaign/noro_food_shapes_01/manifest.json`; all 11 fleet
prefixes were empty at submit (canary zips live under distinct
`canary_exp_*` prefixes — no key collisions).

| block | cells | array job ID |
|-------|-------|--------------|
| `fl_exp_12d_scr_off` | 1,000 (8000–8999) | `8728fa4c-f398-40c9-a5ac-9e26a945549c` |
| `fl_exp_12d_scr_ind` | 1,000 (8000–8999) | `e94b2ef8-26b0-4b40-8d57-5beaf9b180dc` |
| `fl_exp_12d_scr_ind_bg` | 1,000 (8000–8999) | `a694abaa-2e0a-4beb-b021-e43e59e87a01` |
| `fl_exp_12d_scr_ship` | 1,000 (8000–8999) | `fb63c8b1-8aeb-4f23-8fb0-730343a11655` |
| `fl_exp_12d_scr_bg` | 1,000 (8000–8999) | `2775e75f-44e1-4d7e-b139-55af2464cc22` |
| `fl_exp_12d_scr_mint` | 1,000 (8000–8999) | `67f6966f-d6ff-4311-bb38-68f684417f68` |
| `fl_exp_12d_scr_bg_mint` | 1,000 (8000–8999) | `9962142b-404b-4232-b4c7-0bc3e82b74cc` |
| `fl_exp_12d_scr_redraw` | 1,000 (8000–8999) | `9bdbb1f0-6478-41ce-9b58-c986e7d33e0d` |
| `fl_exp_12d_scr_redraw_mint` | 1,000 (8000–8999) | `e226fc04-dded-45a2-9be9-15f58ac5a39d` |
| `fl_exp_12d_scr_fx_wide` | 1,000 (8000–8999) | `363c1a40-21ba-4e6b-af90-7633cec22ebd` |
| `fl_exp_12d_scr_fx_narrow` | 1,000 (8000–8999) | `fd390b53-4bad-43ce-9e6d-5735aee23eaa` |

Dispatch health: `off` completed 1000/1000 SUCCEEDED, 0 FAILED in
~35 min (~45 cells/min observed). `ind` landing next; armed
object-mode arms (`ship` onward) drain FIFO after `ind`/`ind_bg`.
Wave ETA ~4 h at the observed rate.

Early-landing spot-check — 5 `off` zips (seeds 8000–8004) + 3 `ind`
zips (first landed): 3-member zip contract on all (`summary.json`,
`growth_census.json.gz`, `rss_samples.json`). `off`: override echo
`parameters.common_source {"mode": "off"}` verbatim; zero-witness
holds — 0 `objects`, 0 `events`, `telemetry.dose_credited 0.0` on
every sampled cell. `ind`: armed override echo `{"lot_mode":
"independent", "handler_mode": "independent", "diner_mode":
"independent"}` verbatim on all 3; v1 event rows present on 2/3
(`source_kind: ill_diner`, `object_id: null` throughout — the §8
"zero `object_id` witness rows" expectation for independent-mode
cells; a zero-event `ind` cell is within per-voyage mint
expectation). Object-row witness fields (`extent_mode`/`redraw`/
titre) verified on this same image by the canary at identical seeds
and re-verify at readout as the `ship`-family blocks land. No
non-Spot-reclaim failure class observed; no zero-witness violations
on landed cells.

### Wave 2 — cls + spr factorial core (14,000 cells)

**User-approved amendment to the frozen wave order (design §8), recorded
2026-10-13:** wave 3 (`redraw`, `fx_wide`, `fx_narrow` on cls + spr —
6,000 cells) is **dropped**, and `redraw_mint` is dropped from wave 2 —
the cadence and extent margins were measured null on exp (wave-1
readout: `mint − redraw_mint` Δposted +0.00 pp) and the conjunction
cell is answered (`redraw_mint` ≈ `mint` on every D-metric). Wave 2
runs the remaining 7 factorial-core arms on cls + spr:
`ship`, `mint`, `bg_mint`, `ind_bg`, `ind`, `off`, `bg` — 7 arms ×
2 hulls × 1,000 seeds = **14,000 cells**. Total campaign spend under
the amendment: 25,000 of the frozen 33,000 voyages (11,000 exp wave-1
+ 14,000 wave-2; 8,000 pruned cells never submitted).

Submitted 2026-10-13 ~15:56–16:08 UTC on `picard-campaign-queue` (Spot
FIFO, strict submit order; queue empty at submit — wave-1 fully
drained) under jobdef `picard-noro-food-shapes-01:1` (digest-pinned
`picard-campaign@sha256:bb962a4282accd9ca848c32465e861314f9ddf798dec6d63353c17791427a981`
@ `45b2bf18`, retry ×10 `Host EC2*` — verified ACTIVE and the only
revision in the family; every array's `jobDefinition` resolved to
that pinned rev at submit). One array per block, literal
`containerOverrides` argv identical in shape to wave-1
(`campaign_entrypoint.py --campaign noro/food_shapes_01 --s3-prefix
s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_food_shapes_01/
--block <block> --seeds 8105…9104 --manifest
picard_framework/runs/mega_cruise_campaign/noro_food_shapes_01_manifest.json
--pathogen-id norwalk_gi --epochs 288`), `arrayProperties.size: 1000`.
Manifest mirrored at `s3://…/campaign/noro_food_shapes_01/manifest.json`
(byte-identical to the frozen local file, verified by `cmp`); all 14
fleet prefixes were empty at submit. §3.4 bridge condition re-checked:
between `dbbd5395` and eval image `45b2bf18` the only mechanism merges
are this campaign's declared machinery (#990 `two_mode`, #991
extent/redraw, #992 pin) — no foreign default-ON mechanism; the
bit-identity bridge declarations stand as frozen.

`fl_cls_12d_scr_ship` went first as the probe array (armed override
echo + object witnesses on the new hull); the remaining 13 followed
after its early zips verified clean.

| block | cells | array job ID |
|-------|-------|--------------|
| `fl_cls_12d_scr_ship` | 1,000 (8105–9104) | `c3249f6b-59e1-4789-b4eb-170d34e63d84` |
| `fl_cls_12d_scr_off` | 1,000 (8105–9104) | `75189ff8-b0b5-492f-b11a-353b92e6e151` |
| `fl_cls_12d_scr_ind` | 1,000 (8105–9104) | `299e1b19-8642-47c5-a9cc-99d331b1e127` |
| `fl_cls_12d_scr_ind_bg` | 1,000 (8105–9104) | `95130826-6cc1-4a13-beab-511621bae4be` |
| `fl_cls_12d_scr_bg` | 1,000 (8105–9104) | `8318d90d-cb7f-4bcf-a238-f0172ec5e863` |
| `fl_cls_12d_scr_mint` | 1,000 (8105–9104) | `3e792ba8-9145-4135-a552-bcd36c757456` |
| `fl_cls_12d_scr_bg_mint` | 1,000 (8105–9104) | `7e1cc94f-d1a8-4af7-86fe-f728402bade8` |
| `fl_spr_12d_scr_off` | 1,000 (8105–9104) | `843041ef-bd05-473a-af7e-f425843be2a3` |
| `fl_spr_12d_scr_ind` | 1,000 (8105–9104) | `9eabbe4e-1e74-499d-952c-2a455fab89a9` |
| `fl_spr_12d_scr_ind_bg` | 1,000 (8105–9104) | `28f70ff9-e140-41a3-9f97-be10726075f1` |
| `fl_spr_12d_scr_ship` | 1,000 (8105–9104) | `86ed82ff-1aa7-4470-b235-5700226458a7` |
| `fl_spr_12d_scr_bg` | 1,000 (8105–9104) | `97bec759-d26e-427e-959a-fe8daf165c91` |
| `fl_spr_12d_scr_mint` | 1,000 (8105–9104) | `f7bd9231-ff35-440d-ab5e-dab2d3880e8f` |
| `fl_spr_12d_scr_bg_mint` | 1,000 (8105–9104) | `1efecf41-a7fc-4d99-84d2-7e08d144f8e5` |

Probe spot-check — 4 `fl_cls_12d_scr_ship` zips (seeds 8105–8108,
first landed): 3-member zip contract on all (`summary.json`,
`growth_census.json.gz`, `rss_samples.json`). Armed override echo
`parameters.common_source {"lot_mode": "object", "handler_mode":
"object", "diner_mode": "object", "lot_object_probability":
[0.001, 0.02]}` verbatim on all 4; `titre_draw_mode` absent → shipped
`two_mode` (the `ship` contract). Object witness rows carry the
canary-verified schema (`extent_mode`/`redraw`/`extent_windows`/
`lot_titre_gec_per_g` present, null on non-lot rows); handler/diner
objects mint on every sampled cell (7–35/voyage: `ill_handler` +
`ill_diner`, `object_id` + `seeded_epoch` populated); 0
`provisioned_lot` — expected at shipped mint (~1%/voyage). Voyages
non-degenerate: `cumulative_ever_infected` 141–196 on
`classic_cruise_1900` (n1910), 288 epochs. Dispatch health at
spot-check: 117 zips landed / 103 RUNNING / 0 FAILED within ~10 min
of the first dispatch (~12 cells/min — the measured spr/cls drain
rate; full-wave ETA ~19 h at that rate across 14,000 cells).
No non-Spot-reclaim failure class observed on landed cells.

## Findings

Wave-1 exp readout (11,000 cells, 0 errors, at `45b2bf18`):
`docs/norovirus/noro_food_shapes_01_wave1_readout.md`. Headlines:

- **Mint rate is the posting-rate control**: 82/1,000 mint-family
  voyages mint a `provisioned_lot` object and ~93% of those post →
  posting lands at `ind`-like 8.2–8.6%, over the D1 band. Thin arms
  hold D1 (+0.3–0.6 pp marginal; `fx_narrow` borderline under).
- **Titre denominator**: material on the v1 draw path
  (`ind − ind_bg` +1.3 pp posting, +13.8 pp excursion conversion),
  modest on the object path (`mint − bg_mint` +0.4 pp / +4.9 pp conv —
  background titres still convert).
- **Cadence (`per_window` re-mint) and extent are measured nulls** on
  every D-metric (`mint − redraw_mint` Δposted +0.00 pp).
- **D3 recovered**: excursion→posting conversion at/above `ind`
  (77.7%) on every armed arm — mint family 87.8–93.9% (n=82, powered);
  thin arms 66.7–100% on n=6 (thin-cell pooled read).
- **D4 recovered**: excursion burst48 0.49–0.79 vs rest 0.41 on every
  armed arm; mint-family postings themselves burst (0.70–0.75).
- **D2**: met on `mint` only (0.0411); `ind` itself sits just under
  (0.0380). Thin posted-AR signature persists on thin arms.
- **`redraw_mint` conjunction**: posting 8.6% vs `ind` 8.2%, conv
  93.9% vs 77.7%, posted burst48 0.748 vs 0.538 — the closest
  object-grammar reproduction of `ind` measured.
- **Bridges**: non-object voyages bit-identical; object-voyage
  interiors carry the declared #990/#991 machinery delta with exact
  minted-voyage parity (34/34 `ind_bg`, 78/78 `bg`) — not an RNG break.
- All six §7.4 integrity gates PASS; no vacuity; no corruption class.

Final 3-hull readout (25,000 cells, `45b2bf18`;
`docs/norovirus/noro_food_shapes_01_readout.md`):

- **The mint gate is the signature carrier on every hull** — posting
  at `ind` level (8.6/4.9/3.1% vs `ind` 8.2/4.8/2.7%
  exp→cls→spr), excursion conversion recovered at `ind`×1.0–1.2
  (1.02× cls, 1.07× spr), posted voyages burst above rest
  (0.708/0.454/0.326 on `mint`), posted acq ride the dose tail.
- **Every absolute gate calibrated on exp compresses with hull**:
  thin-arm posting marginals +0.6→+0.2→+0.1 pp (D1 band only held on
  exp); D2 ≥0.04 met only on exp (`mint` 0.0411) — on cls `mint`
  0.0389 *and `ind` itself 0.0352*, on spr `ind` tops the table
  (0.0310 vs `mint` 0.0243). `ind` excursion conversion re-measured
  77.7→50.0→26.3%.
- **D4 splits on spr**: excursion-vs-rest separation gone on `ind`
  itself (0.257 vs 0.271) — unreadable at that hull scale — while
  posted mints still sit above rest (0.326 vs 0.272).
- Titre denominator margin consistent: `ind−ind_bg` +1.0/+1.1 pp
  posting, +8–11 pp conversion; object path `mint−bg_mint`
  +0.5/+0.9 pp.
- Bridges: `off` 1,000/1,000 bit-identical on cls+spr; all 1,489
  diverged bridge seeds are cs-active on **both** sides (divergence
  fraction tracks cs-activity density, diffs downstream-only) — the
  declared #990/#991 machinery delta, amplified not changed.
- Mint census: identical mint decisions across cls+spr on the shared
  seed list (84 cells/96 objects mint-family; 6 cells/7 objects thin)
  — the seed-paired mint stream is hull-invariant as designed.
- All §7.4 gates PASS on cls+spr; zero vacuity; zero corruption.
- **Verdict**: exp admissible; cls/spr admissible-with-caveat — the
  relative signatures recover on every hull, the exp-calibrated
  absolute bands do not carry; hull compression is measured, not
  hypothesized.

Margin map (design §7.2): titre denominator →
`mint − bg_mint`, `ind − ind_bg` (powered), `ship − bg` (thin);
cadence → `redraw_mint − mint` (powered), `ship − redraw`,
`fx_wide − ship − fx_narrow` (iso-dose); mint → `mint − ship`,
`redraw_mint − redraw`, `bg_mint − bg`; conjunction → `redraw_mint`
vs `ind`.
