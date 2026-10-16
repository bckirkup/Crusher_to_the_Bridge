# NORO-MINT-RATE-01 — campaign ledger

Design of record:
`docs/norovirus/noro_mint_rate_01_sweep_design.md` (frozen before any
cell ran). Question: channel presence — the provisioned_lot voyage
gate `lot_object_probability` — is the measured operative margin on
the object grammar. Where along the gate does the D1 posting marginal
land in the 0.4–0.9 pp band per hull, and does the D2/D3/D4 signature
(`ind`-level posted pax-AR, excursion→posting conversion, posted
burst48) survive at that rate?

## Stage table

| stage | state | evidence |
|-------|-------|----------|
| design frozen | done | `docs/norovirus/noro_mint_rate_01_sweep_design.md`; this package (27 tiers, 33 blocks) |
| image built | done | `picard-campaign:noro-mint-rate01` @ `49e1993b` → digest `sha256:05cba8f22b747ca47c13a1e885581263e51b5320ab931250767a33b82bac38ea`; jobdef `picard-noro-mint-rate-01:1` (digest-pinned, ACTIVE, retry ×10 `Host EC2*`); manifest mirrored to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mint_rate_01/manifest.json` |
| local smoke | done | `fl_exp_12d_scr_p012` index 0: 3-member zip contract + scalar echo `"lot_object_probability": 0.012` + object modes; 31 infected, 0 cs objects at E≈0.012 — passed |
| canary (116 cells, exp) | done — 5/6 gates green; `off` bit-identity FAILED (see Findings: host-level nondeterminism) | arrays `42a34b4d` mint 48, `08a78c9c` p024 24, `745b3af6` p005 24, `6304cc2f` ind 8, `30229fac` ship 8, `4a7bff20` off 4 — 116/116 SUCCEEDED, 0 retries |
| wave 1 — exp, all 9 arms | done | 9,000/9,000 cells SUCCEEDED; readout below (D1 bracket ≈[0.005, 0.0105]) |
| wave 2 — cls + spr, all 9 arms | done | 18,000/18,000 cells SUCCEEDED; census scan partitioned as 27-child Fargate array `picard-noro-scan-readout` (rows → `campaign/noro_mint_rate_01/_scan_rows/`); readout `docs/norovirus/noro_mint_rate_01_readout.md` |

## Grid

3 hulls (exp 8000–8999, cls/spr 8105–9104, 1,000 seeds/cell; mega
excluded — objects never armed there) × 9 arms = 27,000 voyages,
fixed coordinates identical to FOOD-01/02, AGE-FOOD-01, SCORE-01,
ENTRAIN-01 and FOOD-SHAPES-01 (rung `shipped`, bp32.5c18.5, nsf29,
288 epochs, comp65, dose 7.57, embarkation 2026-01-10, shipped class
mix stamped).

| arm | `lot_object_probability` | role |
|-----|--------------------------|------|
| `off` | `mode: off` | mechanism-absence floor; bit-identical to prior `off` |
| `ind` | — (v1 `lot_event_probability` U(0.02,0.15)) | the per-hull signature denominator |
| `ship` | U(0.001, 0.02) — shipped | bracket bottom anchor; SHAPES-01 `ship` bridge |
| `p005` | 0.005 | rung — E[minted] 5/1,000 |
| `p008` | 0.008 | rung — 8/1,000 |
| `p012` | 0.012 | rung — 12/1,000 |
| `p017` | 0.017 | rung — 17/1,000 |
| `p024` | 0.024 | rung — 24/1,000 |
| `mint` | U(0.02, 0.15) — powered | bracket top anchor; signature carrier; SHAPES-01 `mint` bridge |

Per-rung E[objects] and per-hull margin expectations: design §3.2/§3.3.
Scalar rungs gate on the same stream position per seed — minted sets
must nest p005 ⊆ p008 ⊆ p012 ⊆ p017 ⊆ p024 (integrity gate, design
§5.4-3).

## Mechanism contracts

None required — every arm is a shipped `common_source` config
override (verified against `engines/transmission_core.py` @
`9039e234`; `_cs_plan_objects` ≈:12538, `_cs_draw_voyage_rates`
≈:3491, `lot_posture_coupling` default `false`). Rung values are
declared arm configuration, not provenance-registered constants.
Pruned (design §3.5): `bg`/`ind_bg`/`bg_mint` titre margin,
`redraw`/`fx` cadence-extent arms, `extra_lot` ladder, handler/diner
mint, `ind`-gate mint, mega.

## Canary readout

Submitted 2026-10-15 on `picard-noro-mint-rate-01:1`, image digest
`sha256:05cba8f22b…` @ `49e1993b` (merge of #999). 116/116 cells
SUCCEEDED first attempt. `parameters.common_source` echo verified
verbatim in every cell.

| block | cells | gate | result |
|-------|------:|------|--------|
| `canary_exp_mint` | 48 | ≥1 `provisioned_lot`; echo `[0.02,0.15]`; titres in (1.5e2,5e3); single titre/object | PASS — 4 objects (E≈4.1), titres 272.7/605.0/3213.3/4635.8 GEC/g all in band, 84 minted events, single titre each, interval echo verbatim |
| `canary_exp_p024` | 24 | scalar echo `0.024` verbatim; zero-lot declared non-failing | PASS — echo verbatim, 0 objects (P(0)≈0.50) |
| `canary_exp_p005` | 24 | scalar echo `0.005` verbatim; zero-lot declared non-failing | PASS — echo verbatim, 0 objects (P(0)≈0.87) |
| `canary_exp_ind` | 8 | independent-modes echo; `object_id: null` rows; no object mint | PASS — echo verbatim, 9 events all `object_id: null`, 0 objects minted |
| `canary_exp_ship` | 8 | shipped echo + `titre_draw_mode` → `two_mode`; handler/diner objects | PASS — echo `[0.001,0.02]` + object modes, `titre_draw_mode` absent→default, 20 handler + 4 diner objects |
| `canary_exp_off` | 4 | zero-witness + bit-identical to prior `off` | HALF — zero-witness PASS (0 objects, 0 events, dose 0.0); **bit-identity FAIL — see Findings** |

## Wave submissions

User go for wave 1 with bridges read statistically (host-level
determinism, F0). Submitted 2026-10-15 on `picard-noro-mint-rate-01:1`
(digest `sha256:05cba8f22b…`), FIFO order — `mint` probe first:

| block | cells | array job |
|-------|------:|-----------|
| `fl_exp_12d_scr_mint` | 1,000 | `9624d755-f6c5-4a26-b75b-ae1598874ac9` |
| `fl_exp_12d_scr_off` | 1,000 | `e8880a23-dc31-4d1d-b190-38c5cdc6c30e` |
| `fl_exp_12d_scr_ind` | 1,000 | `969edcdd-5c9e-4ecc-8031-8de14a62b4a7` |
| `fl_exp_12d_scr_ship` | 1,000 | `880f3367-0fac-48c2-b994-efc1b33141dc` |
| `fl_exp_12d_scr_p005` | 1,000 | `f084d87f-124d-4ceb-b49f-6178fa70328f` |
| `fl_exp_12d_scr_p008` | 1,000 | `5115cca1-847e-4321-9603-c5a1b75a6897` |
| `fl_exp_12d_scr_p012` | 1,000 | `6afc1691-4ded-4e2d-97dc-a9bdd943cae4` |
| `fl_exp_12d_scr_p017` | 1,000 | `002cf1d6-9e56-41d9-9149-befa48855a47` |
| `fl_exp_12d_scr_p024` | 1,000 | `f39ade53-79aa-4fef-8247-af5b1bae3132` |

ETA ~2.2h at the measured exp drain (~68 cells/min @ desired 256),
prefix `campaign/noro_mint_rate_01/fl_exp_12d_scr_*/`.

Wave 2 (cls + spr, all 9 arms) submitted 2026-10-15 on
`picard-noro-mint-rate-01:1` (digest `sha256:05cba8f22b…`), FIFO
order — cls mint probe first, then remaining cls arms, then spr
(same arm order per hull as wave 1):

| block | cells | array job |
|-------|------:|-----------|
| `fl_cls_12d_scr_mint` | 1,000 | `2e292b39-02b2-494b-9f8d-29831095937a` |
| `fl_cls_12d_scr_off` | 1,000 | `c3f68d36-2ee0-4343-8f4a-5bbd8b909168` |
| `fl_cls_12d_scr_ind` | 1,000 | `53fe3989-310d-47d7-ba4c-bb797f386964` |
| `fl_cls_12d_scr_ship` | 1,000 | `abadcae7-468b-4b1f-bf23-51ab96a42432` |
| `fl_cls_12d_scr_p005` | 1,000 | `4712edcd-5332-4558-b773-012d08ec96fa` |
| `fl_cls_12d_scr_p008` | 1,000 | `49c09e3b-50bb-4800-b316-e7d177516876` |
| `fl_cls_12d_scr_p012` | 1,000 | `ae85814d-72e5-4629-b603-89dff86f95b0` |
| `fl_cls_12d_scr_p017` | 1,000 | `024ebb59-1370-4ebe-a5cb-c743609af980` |
| `fl_cls_12d_scr_p024` | 1,000 | `373ec4ce-98b8-493f-b30d-6d05b86c853b` |
| `fl_spr_12d_scr_mint` | 1,000 | `d5f1b1a2-66c7-4794-bb2d-37e022075f32` |
| `fl_spr_12d_scr_off` | 1,000 | `da590afb-b5e8-4c76-87cf-260b1ac1130a` |
| `fl_spr_12d_scr_ind` | 1,000 | `5098156f-1afc-42ab-9df7-376e2457853b` |
| `fl_spr_12d_scr_ship` | 1,000 | `dafbf8bf-0155-4fed-8561-55acef6fadee` |
| `fl_spr_12d_scr_p005` | 1,000 | `634ce6c3-4ebe-4eeb-9faa-4128ec65fe27` |
| `fl_spr_12d_scr_p008` | 1,000 | `7a6a1995-f269-47a7-92db-0aa883e80e80` |
| `fl_spr_12d_scr_p012` | 1,000 | `83707c35-57f5-4abe-b29b-8ddfccaf31c0` |
| `fl_spr_12d_scr_p017` | 1,000 | `e4ca2515-52af-43ea-bdea-20960c93e3d4` |
| `fl_spr_12d_scr_p024` | 1,000 | `e3e2af64-4dc5-4c6d-978a-50d7f0f66c16` |

First-landing spot-check (cls probe `mint` + `off`):

- 3-member zip contract (`summary.json` + `growth_census.json.gz` +
  `rss_samples.json`) clean on 25 mint + 3 off cells.
- `parameters.common_source` echo verbatim: mint `{lot_mode/handler_mode/
  diner_mode: object, lot_object_probability: [0.02, 0.15]}` on 60
  cells; off `{"mode": "off"}` on 3 cells.
- Armed-arm witnesses: 5/60 cls-mint voyages minted provisioned_lot
  objects — E ≈ 5.1 at the U(0.02,0.15) gate (wave-1 exp minted
  82/1,000); every minted object single-titre, titres in the
  (1.5e2, 5e3) band.
- `off` zero-witness on all 3 cells: 0 events, 0 objects,
  `dose_credited` 0.0; voyages non-degenerate (122–174 infected).
- No non-Spot-reclaim failures on early cells (0 FAILED fleet-wide at
  probe completion). Echo coverage of the remaining arms is a readout
  check, per-arm as their first cells land.

Probe drain: `fl_cls_12d_scr_mint` 1,000 cells landed 15:30→16:16 UTC
= ~46 min ≈ 21.5 cells/min at desired 256 (cls ≈ 11–12 min wall/cell
vs ~3 on exp — heavier hull than wave-1's ~68 cells/min). cls fleet
ETA ≈ 7–8 h if the drain holds; spr cells heavier still.

## Findings

### F0 (2026-10-15, canary) — bit-identity across runs is host-level,
not image-level

§9 report-immediately trigger. `canary_exp_off` s8000–8003 diverge
wholesale from SHAPES-01 `fl_exp_12d_scr_off` (same seeds): ~9k field
diffs per cell (e.g. s8000 infected 31 vs 38). Controlled
measurements on the same cell (off, s8000):

- SHAPES-01 canary (`45b2bf18`, Oct-12 Batch) vs SHAPES-01 wave
  (same image, Oct-12 Batch): near-identical — last-ulp dust in
  `removal_totals` + RSS/timing fields only.
- This repo's `.venv` (2× local runs): near-identical to each other
  and to the new `49e1993b` Batch canary (trajectory-equal).
- **`noro-food-shapes01` image run on this VM**: trajectory-equal to
  the `49e1993b` Batch cells (1 ulp-diff), **not** to its own Oct-12
  wave cells (~9k diffs).
- Code per-file sha256 inside both images: identical except the new
  manifest. Python 3.11.17 both; glibc 2.41-12+deb13u4 both; deps
  hash-locked via `uv sync --locked`.

Conclusion: same image on different hosts gives different
trajectories — the voyage is host-sensitive (CPU-dependent float
dispatch is the prime suspect; `PYTHONHASHSEED` is unset but
same-host reruns are stable, so hash-order does not feed draws).
Bit-identity bridge clauses (`off`/ship/mint/ind vs SHAPES-01 cells,
design §3.4) are **unmeasurable in this environment** — the same
image diverges by host. In-campaign statistical bridges remain valid:
D1 is defined vs in-campaign `off`, and every arm's cells in a wave
share the same fleet-day float path as that wave's `off`.

Implication for readout: cross-campaign pairing must be statistical
(distributional), not bitwise. A fix for true bit-identity would need
CPU-independent float behaviour or a pinned instance type — an
engineering change, not config; report to user before any wave.

## Wave-1 readout (exp, 9,000 cells — all 9 arms, 0 failures)

Scanned with `tools/noro_diag/food_shapes_01_scan.py` (two members per
zip, 0 errors). Off floor 0.70% posted; `ind` reference: 93
`common_source_food`-dominant excursions, 78.5% convert, posted-AR
median 0.0380.

### D1 ladder (posting marginal vs `off`, band +0.4–0.9 pp)

| arm | posted | marginal | minted | lot obj | verdict |
|-----|-------:|---------:|-------:|--------:|---------|
| ship | 12 | **+0.50 — in band** | 6 | 7 | thin (<20) |
| p005 | 16 | **+0.90 — in band, edge** | 9 | 11 | thin |
| p008 | 18 | +1.10 over | 11 | 13 | thin |
| p012 | 19 | +1.20 over | 13 | 15 | thin |
| p017 | 22 | +1.50 over | 17 | 19 | thin |
| p024 | 25 | +1.80 over | 20 | 25 | — |
| mint | 87 | +8.00 over | 82 | 93 | over |
| ind  | 80 | +7.30 over | 0 | 0 | over |

In-band gate window on exp ≈ p ∈ [0.005, ~0.0105] (design predicted
[0.004, 0.010]). The ladder is the margin: marginal ≈ minted count
(posted ≈ off + minted on every rung).

### Signature at rate (D2/D3/D4)

| arm | postAR med | conv(exc) | vs ind | b48 exc vs rest |
|-----|-----------:|----------:|-------:|----------------:|
| ind | 0.0380 | 0.785 | 1.00× | 0.526 vs 0.409 |
| ship | 0.0254 | 0.714 | 0.91× | 0.660 vs 0.409 |
| p005 | 0.0316 | 1.000 | 1.27× | 0.784 vs 0.409 |
| p008 | 0.0316 | 1.000 | 1.27× | 0.784 vs 0.409 |
| p012 | 0.0316 | 0.923 | 1.18× | 0.780 vs 0.409 |
| p017 | 0.0316 | 0.882 | 1.12× | 0.707 vs 0.409 |
| p024 | 0.0411 | 0.900 | 1.15× | 0.716 vs 0.409 |
| mint | 0.0411 | 0.976 | 1.24× | 0.712 vs 0.409 |

Pooled in-band (ship+p005, 28 posted cells) postAR median 0.0301 <
ind 0.0380 — **the posted-AR signature does NOT survive at in-band
rate on exp**; conversion (≥ind on every rung bar thin-cell ship) and
burst48 (0.66–0.78 vs 0.409 everywhere) DO survive at every rung.

### Integrity

- Nested mint sets perfect: p005 ⊆ p008 ⊆ p012 ⊆ p017 ⊆ p024
  (9 ⊆ 11 ⊆ 13 ⊆ 17 ⊆ 20 seeds).
- Minted census vs E: ship 6 (E 10.5), p005 9 (5.0), p008 11 (8.0),
  p012 13 (12.0), p017 17 (17.0), p024 20 (24.0), mint 82 (85.0) —
  all within binomial noise. `mint` 82 = SHAPES-01's 82: the
  seed-paired mint draw is a discrete RNG gate, float-path
  independent — minted SETS are bit-stable across fleet-days even
  where trajectories are not (F0 corollary).
- All lot-pan titres in band (oob = 0); every object single-titre
  (`titre_n` = 1, no remint); zero zero-serve objects; `off`
  zero-witness.
- Same-day float path confirmed: wave `fl_exp_12d_scr_mint` s8000 vs
  canary mint s8000 — 2 non-noise diffs, both 1-ulp accumulator dust
  in `removal_totals`.

### Bridges vs SHAPES-01 (statistical, per F0)

`ind` postAR med 0.0380 = 0.0380; `mint` postAR med 0.0411 = 0.0411;
ind excursions 93 vs 94; mint minted 82 = 82; off floor 0.70% vs
1.0%; mint marginal +8.0 vs +7.6 — all statistically consistent.

### Wave-1 verdict (exp only)

D1 lands in-band between gate ≈0.005 and ≈0.0105 — the bracket is
located. At in-band rate: conversion ≥ind and burst48 separation
survive; the posted-AR median does not (0.030 < 0.038) — D2's
signature needs the powered rate on exp. No §9 trigger beyond F0
(already reported).

## Wave-2 readout (cls + spr, 18,000 cells — all 9 arms, 0 failures)

Scanned via 27-child Fargate array `picard-noro-scan-readout` (same
image digest; per-arm prefix partitions →
`campaign/noro_mint_rate_01/_scan_rows/`); report
`food_shapes_01_report.py --arm-set mint_rate`. exp re-scanned on the
same array — reproduces wave-1 verbatim (off 0.70%, ship +0.50,
p005 +0.90, minted 6/9/11/13/17/20/82, postAR/ind 0.0380, nested 0).

### D1 ladder — cls (off floor 0.30%)

| arm | posted | marginal | minted | verdict |
|-----|-------:|---------:|-------:|---------|
| ship | 4 | **+0.10 under** | 6 | thin (<20) |
| p005 | 9 | **+0.60 — in band** | 9 | thin |
| p008 | 9 | **+0.60 — in band** | 12 | thin |
| p012 | 10 | **+0.70 — in band** | 14 | thin |
| p017 | 11 | **+0.80 — in band** | 18 | thin |
| p024 | 16 | +1.30 over | 21 | — |
| mint | 52 | +4.90 over | 84 | over |
| ind  | 59 | +5.60 over | 0 | over |

In-band window ≈ gate **[0.005, ~0.020]** — wider than predicted
[0.007, 0.015], shifted low: ship (presence 0.0105) lands UNDER the
band (+0.10): its U-mints sit the low end and P(post|minted)≈0.5–0.6
halves yield vs exp's 0.93.

### Signature at rate — cls

- D2 postAR: pooled in-band (p005–p017, 39 posted) med **0.0516 ≥
  `ind` 0.0359 → SURVIVES** (mirror of exp: per-rung 0.0508–0.0524).
- D3 conversion: pooled in-band 26.1% vs `ind` 57.1% → **0.46×,
  does NOT hold at ind level**; mint 51% (0.89×).
- D4 b48: posted 0.40–0.50 vs rest 0.287 every in-band rung — survives
  (excursion set itself ≈ rest; the gate selects bursty voyages).

### Integrity — cls

Nested mint sets 0 violations; minted 6/9/12/14/18/21/84 tracks E[p]
within binomial noise; echo verbatim 9,000/9,000 all arms; all object
+ pan titres in [1.5e2,5e3]; every object single-titre; `off`
zero-witness; `ind` v1-only (471 pans, 0 objects).

### P(post|minted) — rate independence

exp in-band 0.93 / cls in-band **0.585** (53 minted, 31 posted) — lands
on the SHAPES-01-anchored per-hull P1 (0.93/0.58); mint arm 0.99/0.61.
Marginal ≈ minted × P1 confirmed as the mechanism on both hulls.

### D1 ladder — spr (off floor 0.00%)

| arm | posted | marginal | minted | verdict |
|-----|-------:|---------:|-------:|---------|
| ship | 2 | +0.20 under | 6 | thin |
| p005 | 3 | +0.30 under | 9 | thin |
| p008 | 5 | **+0.50 — in band** | 12 | thin |
| p012 | 6 | **+0.60 — in band** | 14 | thin |
| p017 | 7 | **+0.70 — in band** | 18 | thin |
| p024 | 7 | **+0.70 — in band** | 21 | — |
| mint | 32 | +3.20 over | 84 | over |
| ind  | 27 | +2.70 over | 0 | over |

In-band window ≈ gate **[0.008, 0.024]** — shifted high vs predicted
[0.005, 0.012]: spr's P(post|minted)≈0.37 needs more mints per
posting.

### Signature at rate — spr

- D2 postAR: pooled in-band (p008–p024, 25 posted) med **0.0319 ≥
  `ind` 0.0310 → SURVIVES**, thin margin (+0.0009 within noise).
- D3 conversion: pooled in-band 25/172 = 14.5% vs `ind` 27.8% →
  **0.52×, does NOT hold at ind level**; mint 27.4% (0.99×).
- D4 b48: posted 0.303–0.504 vs rest ~0.271 every rung — survives
  (weak spr form: posted not collapsed to rest).

### Integrity — spr

Minted 6/9/12/14/18/21/84 — **bit-identical to cls per arm** (same
seed indices → same discrete mint sets; F0 cross-hull identity).
Nested sets 0 violations; echo verbatim 9,000/9,000; titres
154.9–4,986.7 ⊂ [1.5e2,5e3]; `off` zero-witness; `ind` v1-only.

### Wave-2 verdict — all three hulls

Per-hull brackets measured: **exp [0.005, 0.0105],
cls [0.005, ~0.020], spr [0.008, 0.024]** — the operative gate
rises as P(post|minted) falls (0.93/0.58/0.37).

Signatures SPLIT by hull (the designed discriminating read):
D2 postAR fails exp but survives cls + spr (spr thin); D3 conversion
survives exp but fails cls (0.46×) + spr (0.52×); D4 survives all.
**No hull satisfies D2+D3+D4 jointly at in-band rate.**
P(post|minted) re-anchors at 0.93/0.58/0.37 as per-hull
hull+mechanism constants — the linear marginal
(minted × P1) holds on every hull.

Full tables: `docs/norovirus/noro_mint_rate_01_readout.md`.
