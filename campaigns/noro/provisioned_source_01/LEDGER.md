# NORO-PROVISIONED-SOURCE-01 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Mechanism
contract: `docs/provisioned_source_01_design.md`. Frozen eval design:
`docs/norovirus/noro_provisioned_source_01_sweep_design.md`. Ledger
entry: `docs/ledger/PROVISIONED-SOURCE-01.md`. Mega spec:
`campaigns/noro/provisioned_source_01_mega/` (same manifest, elevated
memory — AGE-FOOD split precedent).

**Grid:** 3 small hulls × 12 arms + mega × 10 arms × 1,000 seeds =
46,000 cells + ~128 canary. Seeds exp 8000–8999, cls/spr/mega
8105–9104 (SCORE-01 lists). Fixed coordinates: shipped bp
0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65, dose 7.57,
embarkation 2026-01-10.

**Submit gate:** NO cells submit until the implementation leg lands
the `provisioned_source` mechanism + witness fields
(`common_source.provisioned_source` voyage block,
`provisioned_source_id` on object rows, `reported_cases_by_dominant_route`
summary) and the image pins a SHA containing them. Canary (~128
cells) then STOP — user gates wave 1.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 6 exp + 1 meg | 128 | done 2026-10-16 — all gates pass |
| 1 | exp ×12 arms | 12,000 | done 2026-10-16 — all cells landed, readout below |
| 2 | cls + spr ×12 arms | 24,000 | submitted 2026-10-16 — 24 arrays in flight |
| 3 | mega ×10 arms | 10,000 | not submitted |

## Readout log

### canary — submitted 2026-10-16, awaiting cells

Image `picard-campaign:noro-provisioned-source01@sha256:97d99be4c1abf362af1f9914f476740bd1086e7b73491b371f8741bfb1ac95de`
(pinned in campaign.json `image_tag`; ENGINE_GIT_SHA=a9f4a517).
Manifest mirrored to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_source_01/manifest.json`.

| block | jobdef | cells | job id |
|---|---|---|---|
| canary_exp_mint | picard-noro-provisioned-source-01:1 | 48 | 970ef763-ef33-4d65-830e-9451eb8860f3 |
| canary_exp_q30 | :2 | 24 | 69cbe84b-2bf5-4126-8f25-5289aba99ee2 |
| canary_exp_q03 | :3 | 24 | f270b39b-0e83-45f0-86b6-5b3fafdd0775 |
| canary_exp_ps_ship | :4 | 8 | 157f3d0a-a38e-45c8-8579-e6368c9640ab |
| canary_exp_ind | :5 | 8 | 84c16c5c-e3ed-49f1-a300-d9dd61a2638d |
| canary_exp_off | :6 | 4 | 9c70c1d1-45c4-4505-abe9-4f39fc7200f7 |
| canary_meg_q30 | picard-noro-provisioned-source-01-mega:1 | 12 | bf212817-ce81-4323-b269-421996164788 |

Canary gates (design §5.3-2 as amended A1): q-source echo present in
run provenance; provisioned_source witness blocks (stations/objects)
written; minted-set parity vs landed mint cells per shared seed;
objects-bind-stations consistency; mega cells RSS within 8192 MB.

### canary readout — exp cells (116/116 SUCCEEDED, measured 2026-10-16)

- Echo: `lot_mint_model` echoed per arm (`provisioned_source` on
  q03/q30/ps_ship, `fiat` on mint, absent on ind/off);
  `provisioned_source: {source_id, q_source}` in run provenance.
- Witness: `common_source.provisioned_source` written per voyage —
  `n_stations: 21` (exp census), `n_contaminated`, `q_source_drawn`
  on every provisioned cell; objects carry
  `provisioned_source_id: generic_cruise_port`.
- Draw statistics (measured): q30 2/24 voyages minted exactly 1
  object (E = 21·0.003 ≈ 0.063 ⇒ ~1.5 expected); q03 0/24
  (E ≈ 0.006); ps_ship per-ship q resolved [2e-4, 5e-4], 0/8;
  ind/off 0 objects, 0 events. Consistent with Binomial(21, q).
- objects-bind-stations: `n_contaminated` == `provisioned_lot`
  objects on every provisioned cell, no exceptions.
- Attribution blocks live: `reported_cases_by_dominant_route` +
  `reported_cases_by_channel` (`supply_chain` populated on minted
  voyages).
- RSS: peak 516 MB across all exp cells (limit 4096).
- Minted-set parity vs MINT-RATE-01 `fl_exp_12d_scr_mint` (seeds
  8000–8047 paired): **45/48 bit-identical** object sets + event
  counts. Seeds 8026/8032/8046 diverge — attribution: landed cells
  ran image SHA `49e1993b` (81 commits older than canary `a9f4a517`),
  including the ndarray rate-vector truthiness fix (#1013) and
  phylodynamics founder draws (#1025) which perturb the shared RNG
  stream; seed 8026 shows the signature (identical minted set,
  divergent downstream acquired) — upstream stream shift, not a
  mint-mechanism change. Gate read: PASS-with-note (parity axis)
  pending user call.

### canary readout — mega cells (12/12 SUCCEEDED, measured 2026-10-16)

- Witness: `n_stations: 70` on every cell; `n_contaminated` 10×0 +
  2×1 (seeds 8115, 8116 — the latter produced 4 provisioned_lot
  events, `supply_chain: 7` passenger cases in
  `reported_cases_by_channel`). E = 70·0.003 = 0.21 ⇒ ~2.5
  contaminated voyages expected in 12; 2 measured —
  Binomial-consistent.
- RSS: peak 6431–6588 MB (limit 8192).
- objects-bind-stations: exact on the 2 minted cells.

### canary verdict

All canary gates pass; the single note is the 45/48 minted-set
parity (attributed to the 81-commit SHA gap — upstream stream
perturbation, not the mechanism). Wave 1 decision is the user's.

### wave 1 — submitted 2026-10-16, awaiting cells

User approved after the canary readout ("merge 1058, launch wave
1"). 12 exp arrays × 1,000 seeds, digest-pinned jobdef revs.

| block | jobdef rev | job id |
|---|---|---|
| fl_exp_12d_scr_off | picard-noro-provisioned-source-01:7 | cc4af336-485a-4d5e-99b3-d109ad77c5c1 |
| fl_exp_12d_scr_ind | :8 | 1756adfc-2681-4196-962f-73ae67f6cea0 |
| fl_exp_12d_scr_ship | :9 | 42d478cf-9805-4fcc-9a61-f9f3562bd6c4 |
| fl_exp_12d_scr_mint | :10 | 74793cb0-e711-4fec-8228-352081a14967 |
| fl_exp_12d_scr_ps_ship | :11 | 29e2e349-304b-4913-9498-06177a024645 |
| fl_exp_12d_scr_q01 | :12 | 4ccc47b7-ad07-420d-8017-b22f83b93e44 |
| fl_exp_12d_scr_q02 | :13 | a8af78b8-fbfc-495d-9973-2a46e663c6d4 |
| fl_exp_12d_scr_q03 | :14 | f688db70-16c0-4859-91ec-7719a348d468 |
| fl_exp_12d_scr_q05 | :15 | d0329bf5-fbda-4fac-998f-964f43ce534f |
| fl_exp_12d_scr_q08 | :16 | 6eec0fa0-b7b4-4539-a53a-19ef87c5b6f4 |
| fl_exp_12d_scr_q15 | :17 | dbfbaedb-b2ba-4991-af19-da27ac0b852b |
| fl_exp_12d_scr_q30 | :18 | 1de736ce-fa69-47b6-9d21-0c9805ac917d |

### wave-1 readout — exp, 12,000 cells, 0 failures (measured 2026-10-16)

Cells landed 15:58 UTC (~2h). Scan: `food_shapes_01_scan.py` per arm
→ `campaign/noro_provisioned_source_01/_scan_rows/` (12-child EC2
array `ps01-w1-scan-exp-ec2` on picard-campaign-queue; the Fargate
queue's ECR route was unreachable mid-day — two 12/12-failed
submits, `dial tcp …i/o timeout` on ECR auth — so the scan ran on
the Spot CE that ran the cells). Report:
`food_shapes_01_report.py --arm-set ps01`. Supplement: per-voyage
`reported_cases_by_channel`/`by_dominant_route` pulled locally for
all 212 minted voyage zips (scan image predates those row fields).

**Draw statistics — Binomial(21,q) confirmed on exp (measured).**
Minted-voyage fractions: q01 0 (E 2.1), q02 2 (E 4.2), q03 4
(E 6.3), q05 8 (E 10.4), q08 13 (E 16.7), q15 29 (E 31.0), q30 63
(E 61.1) per 1,000 — all within Binomial sampling error. Objects ≈
1 per minted voyage (q15 30 obj/29 voyages, q30 65/63 — rare pairs,
Binomial tail). `provisioned_source` witness `n_contaminated` ==
`provisioned_lot` object count on every minted cell. **Nested
station draws: 0 violations across all 6 adjacent rung pairs
(6,000 seed-pairs)** — shared station uniforms hold at full scale.

**Posting window (D1, off floor 7/1,000 = 0.70%, band +0.4–0.9pp).**

| arm | posted | marginal pp | band |
|---|---:|---:|---|
| off | 7 | — | floor |
| q01 | 7 | +0.00 | under |
| q02 | 9 | +0.20 | under |
| q03 | 10 | +0.30 | under |
| **q05** | **14** | **+0.70** | **in band** |
| q08 | 20 | +1.30 | over |
| q15 | 35 | +2.80 | over |
| q30 | 63 | +5.60 | over |
| **ps_ship** | **12** | **+0.50** | **in band** |
| ship (fiat) | 12 | +0.50 | in band |
| mint (fiat) | 87 | +8.00 | over |
| ind | 80 | +7.30 | over |

**In-band rung set on exp: {q05} (+ ps_ship; fiat ship also
in-band).** Design predicted {q03}±edges; the measured band-centre
lands one rung higher — operative per-station q for the observed
marginal ≈ 0.0004–0.0006. `ps_ship` (U[2e-4,5e-4] per ship) posts
+0.50 — inside the predicted +0.45–0.85 interval; the shipped
interval is calibrated about right on exp.

**P(post|minted) — rate-independent on exp (measured):** mint 97.6%
[91.5,99.3], ps_ship 5/5, q05 87.5%, q08 100%, q15 100%, q30 90.5%
[80.7,95.6] — consistent with the 0.93 anchor; conversion is
per-minted-voyage, not per-q.

**Signature at powered q:** posted pax-AR median reaches the ≥0.04
edge at q08+ (q08 0.0411, q15 0.0506, q30 0.0443; ind 0.038) —
same shape as MINT-RATE-01 exp: at in-band rate (q05 0.0316 <0.038)
D2's posted-AR signature needs powered rate. Excursion→posting
conversion recovers ind-level at q15/q30 (96.7%/89.1% vs ind 78.5%,
mint 96.4%) — conversion scales with minted count, not mechanism.
D4 burst48 separation holds on every minted arm (excursion medians
~0.68–0.77 vs 0.41 rest).

**Baseline bridge — exact.** off/ind/ship/mint posted counts
reproduce MINT-RATE-01's exp wave-1 verbatim (7/80/12/87 on both
campaigns) — shared baseline arms are voyage-identical across the
81-commit SHA gap.

**Minted-set parity (gate 5.3.2 as amended):** `mint` arm minted-
voyage flags + `provisioned_lot` object counts identical to the
landed MINT-RATE-01 exp cells on **1,000/1,000 shared seeds**;
canary-vs-wave-1 mint arm also bit-identical on flag+count. The
canary's 3/48 residual was station-*identity* divergence (which
stations minted, same count) at seeds 8026/8032/8046 — attributed
to the SHA-gap stream perturbation downstream of the mint draw;
the voyage-level mint gate is bit-stable. Read: parity gate PASS
on flag+count; station-identity caveat carried from canary.

**Channel decomposition (212 minted voyage zips, measured):**
`reported_cases_by_channel.supply_chain` = 80–97% of reported
passenger cases on minted voyages — ship 83%, mint 83%, ps_ship
91%, q03 88%, q05 86%, q08 85%, q15 82%, q30 80% — mechanism-
agnostic lot attribution (fiat and provisioned_source produce the
same channel shape). `reported_cases_by_dominant_route
.common_source_food` ≈ supply_chain one-for-one (the two blocks
agree; kept distinct per the separable-dimensions convention).

**Must-not-move:** paired median Δinf-AR vs `off` = +0.0000 on all
12 arms (p90 |Δ| ≤0.013); `off` zero-witness PASS; `ind` v1-only
witness PASS; override echo exact 12,000/12,000; integrity tallies
clean (0 unresolved oids, 0 open objects).

**Wave-1 verdict:** mechanism is Binomial-clean end-to-end on exp;
the common band exists with operative q ∈ ~[0.0004, 0.0006]
(rung q05) and the ps_ship interval in band. Wave 2 (cls+spr —
the hull-free test) is the user's decision.

### wave 2 — submitted 2026-10-16, read out 2026-10-17

User approved after the wave-1 readout ("yes, wave 2"). 24 arrays
(cls + spr × 12 arms) × 1,000 seeds = 24,000 cells, same
digest-pinned image (a9f4a517). Jobdef
`picard-noro-provisioned-source-01` revs registered per submit.
cls landed 12,000/12,000 ~11:14 UTC Oct 17; spr 12,000/12,000
~20:36 UTC; 0 failed cells. Census scan ran as a 24-child array on
`picard-noro-scan-readout-ec2:3` (memory 8192, workers 16 — the
first :2 attempt OOM'd on the ~50MB cls zips; rev :3 went
24/24 SUCCEEDED, job `eb643d8b-5821-4471-9581-46ada3b6b256`).

| block | job id |
|---|---|
| fl_cls_12d_scr_off | 408c7547-ee00-4506-b715-12df882f0be4 |
| fl_cls_12d_scr_ind | 161c6743-59ef-469b-9bc5-62dcf14af6e5 |
| fl_cls_12d_scr_ship | d8efd14f-4109-4a43-a366-d32c72a8fc43 |
| fl_cls_12d_scr_mint | e850915b-c90f-452a-a62c-a8302db1662a |
| fl_cls_12d_scr_ps_ship | d1ec4f52-ab67-43fc-a2b8-1bb91da3a5fe |
| fl_cls_12d_scr_q01 | aebf255c-2569-49f3-89dc-fc412e047886 |
| fl_cls_12d_scr_q02 | 1e7d7957-27d6-431b-97e8-2cd78e81c13e |
| fl_cls_12d_scr_q03 | 65843391-1164-4ad1-b4cc-7f71d66dba53 |
| fl_cls_12d_scr_q05 | f35ec95f-5825-4671-a705-76680252670e |
| fl_cls_12d_scr_q08 | 375b3fdf-5344-4dde-b5df-7d34f1d64700 |
| fl_cls_12d_scr_q15 | d9a450e7-a585-4e15-b449-a9dab692cb1d |
| fl_cls_12d_scr_q30 | 1ba16547-22b9-4ed0-bd0c-cce5fa86f349 |
| fl_spr_12d_scr_off | 0feb2758-9b27-40c3-b3bd-5c579ddd4edb |
| fl_spr_12d_scr_ind | a0130fd9-e82f-4990-9783-284d0c7df13a |
| fl_spr_12d_scr_ship | 25d25311-9cd2-4b54-a37e-22068ad1ecb3 |
| fl_spr_12d_scr_mint | 015ec470-68a3-45a1-b04f-9f0e85a4412d |
| fl_spr_12d_scr_ps_ship | de70a2b4-10c7-4fa9-bec1-3af0e64bcc36 |
| fl_spr_12d_scr_q01 | 95b48b3f-ec97-4ec7-8bda-0dea2a052d6c |
| fl_spr_12d_scr_q02 | 46187993-5dfd-4dd6-884c-83dc4186abcc |
| fl_spr_12d_scr_q03 | b41aa71c-8fa7-41ca-b9ef-08d1fdfdfe5a |
| fl_spr_12d_scr_q05 | f748b6b9-ec27-4ead-a36a-7fbcaefb17a8 |
| fl_spr_12d_scr_q08 | edb8d96e-329b-4b37-9c76-4a85992aef66 |
| fl_spr_12d_scr_q15 | e7f47ca4-500f-4e79-adb7-ccc29e848641 |
| fl_spr_12d_scr_q30 | df3828c6-1e26-4726-b8b6-8bc6dbcf1825 |

### wave 2 readout — 2026-10-17, all measured at image a9f4a517, 1,000 seeds/arm/hull

**Posting window (band +0.4–0.9pp, inclusive upper edge):**

| arm | cls posted | cls marginal | cls in-band | spr posted | spr marginal | spr in-band |
|---|---|---|---|---|---|---|
| off | 3 (0.30%) | +0.00 | – | 0 (0.00%) | +0.00 | – |
| ind | 59 (5.90%) | +5.60 | no | 28 (2.80%) | +2.80 | no |
| ship | 4 (0.40%) | +0.10 | no | 2 (0.20%) | +0.20 | no |
| mint | 54 (5.40%) | +5.10 | no | 30 (3.00%) | +3.00 | no |
| ps_ship | 7 (0.70%) | +0.40 | yes | 5 (0.50%) | +0.50 | yes |
| q01 | 5 (0.50%) | +0.20 | no | 2 (0.20%) | +0.20 | no |
| q02 | 7 (0.70%) | +0.40 | yes | 3 (0.30%) | +0.30 | no |
| q03 | 11 (1.10%) | +0.80 | yes | 5 (0.50%) | +0.50 | yes |
| q05 | 12 (1.20%) | +0.90 | edge | 7 (0.70%) | +0.70 | yes |
| q08 | 23 (2.30%) | +2.00 | no | 13 (1.30%) | +1.30 | no |
| q15 | 31 (3.10%) | +2.80 | no | 23 (2.30%) | +2.30 | no |
| q30 | 60 (6.00%) | +5.70 | no | 47 (4.70%) | +4.70 | no |

cls `q05` marginal is exactly +0.90 — the inclusive upper edge —
flagged `no` in the tool by a 1-ulp float boundary
(`0.009*100 = 0.8999999999999999`); reported here as edge-in-band.
In-band sets: cls {q02, q03, ps_ship} (+q05 at the edge), spr
{q03, q05, ps_ship}. With wave-1 exp {q05, ps_ship, ship}:
**`ps_ship` is the only arm in-band on all three hulls** — the
per-ship U[0.0002,0.0005] draw covers the drifting band where no
single scalar rung does (exp q05 ↔ cls q02–q03 ↔ spr q03–q05).

**Presence ladder vs Binomial(N_lots,q) — clean on both hulls:**

| arm | cls N=35 minted (E) | spr N=63 minted (E) |
|---|---|---|
| ship | 6 (10.5) | 6 (10.5) |
| mint | 84 (85.0) | 84 (85.0) |
| ps_ship | 12 (12.2) | 21 (21.8) |
| q01 | 1 (3.5) | 5 (6.3) |
| q02 | 7 (7.0) | 13 (12.6) |
| q03 | 12 (10.4) | 21 (18.9) |
| q05 | 17 (17.4) | 28 (31.5) |
| q08 | 30 (27.6) | 50 (50.4) |
| q15 | 49 (51.2) | 80 (94.5) |
| q30 | 106 (99.8) | 172 (172.4) |

Fiat `mint`/`ship` minted counts are bit-identical across hulls
(84 and 6 on both) — same-seed discrete draws are cross-hull
stable. ~1 object per minted voyage on all rungs. Nested-set
violations: **0 in 6,000 rung-pairs per hull**.

**P(post|minted) — hull constant, mechanism-independent:**

| arm | cls | spr |
|---|---|---|
| mint | 63.1% [52.4,72.6] | 34.5% [25.2,45.2] |
| ps_ship | 50.0% [25.4,74.6] | 23.8% [10.6,45.1] |
| q03 | 58.3% [32.0,80.7] | 23.8% [10.6,45.1] |
| q05 | 47.1% [26.2,69.0] | 25.0% [12.7,43.4] |
| q30 | 53.8% [44.3,63.0] | 27.3% [21.2,34.4] |

Pooled cls ≈ 0.50–0.63 vs re-anchored 0.58; spr ≈ 0.24–0.40 vs
~0.36–0.37; wave-1 exp ≈ 0.90–1.00 vs 0.93. The marginal =
minted fraction × P(post|minted) identity holds mechanism-
agnostically on all three hulls — provisioned draws inherit the
same per-hull conversion constant as fiat mints.

**D3 excursion→posting conversion (vs ind per hull):** cls tops
at 0.88× ind (q30 50.0% vs ind 56.57%); spr tops at 0.82×
(q30 23.38% vs ind 28.57%). Posted pax-AR ≥0.04 edge unmet on
every arm (cls ind itself only 0.0351). The signature gap
measured on MINT-RATE-01 persists: presence/marginal is
reproduced, but no mint mechanism — fiat or provisioned —
produces ind-level excursion AR or conversion on the big hulls
at in-band rates. Conversion scales with minted count, not
mechanism.

**Minted-voyage channel decomposition** (804 voyages pulled —
`reported_cases_by_channel` pax totals, supply_chain / aboard /
boarding): cls mint 1890/1329/70, q30 2020/1642/82,
ps_ship 257/229/8; spr mint 1273/2373/132, q30 2759/4687/223,
ps_ship 305/567/34. `supply_chain` is live and dominant on
every minted arm (58% of reported pax on cls mint, 34% on spr
mint); aboard amplification grows relative to the supply seed as
hull size grows — mechanism-agnostic, same as wave-1 exp.

**Must-not-move + integrity:** all median paired Δinf-AR vs off
+0.0000 on both hulls (cls p90|Δ| ≤0.019, spr ≤0.0133); `off`
zero-witness and `ind` v1-only witness PASS both hulls; worst
non-cs route-share drift −4.61pp (cls fomite q30) / −3.71pp
(spr fomite q30); echo 12,000/12,000 per hull; `ship` vs `bg`
witness identity 0/0 — clean.

**Wave-2 verdict:** the hull-free-q claim survives in the
distribution-arm form — `ps_ship` (U[0.0002,0.0005] per-ship)
covers the band on all three hulls while no scalar rung does;
the band drifts ~1 rung per hull under station-N scaling.
Presence stays Binomial-exact at N=35 and N=63, conversion is a
fixed per-hull constant on every mint mechanism. Wave 3 = mega
×10 arms (10,000 cells): the near-absence test (~0.02
objects/voyage at common q) plus the multi-lot lift and the
mega-window extrapolation q ≈ [1.5e-3, 4.1e-3] — user's call.

### wave 3 — submitted 2026-10-18, awaiting cells

User approved after the wave-2 readout ("sure launch wave 3").
10 mega arrays (`campaigns/noro/provisioned_source_01_mega/` spec —
fl_meg_12d_scr_{off,ind,ps_ship,q01,q02,q03,q05,q08,q15,q30}) ×
1,000 seeds (8105–9104) = 10,000 cells, same digest-pinned image
(a9f4a517). Jobdef `picard-noro-provisioned-source-01-mega` revs
:2–:11 (memory 8192 — canary RSS read 6.4–6.6GB). Fiat bridges
omitted per design (mega's fiat cells are vacuous). Every jobId
verified against `describe-jobs` pre-commit.

| block | job id |
|---|---|
| fl_meg_12d_scr_off | f0e5957b-c31f-4011-927d-d39e3266094b |
| fl_meg_12d_scr_ind | 19bb450c-af57-43ce-bc23-98349a1997bf |
| fl_meg_12d_scr_ps_ship | d99b8454-d7c8-4d0e-b568-7a0cdc8f929e |
| fl_meg_12d_scr_q01 | 977e2fdf-6371-484a-aa8f-d6b96c239819 |
| fl_meg_12d_scr_q02 | 9f659325-b2cb-4561-81bb-123caf614b43 |
| fl_meg_12d_scr_q03 | 299ba541-0dcc-4d5e-b8db-a7d90fb4c4a3 |
| fl_meg_12d_scr_q05 | 51f9acea-971d-48ae-b40c-a8715bad7829 |
| fl_meg_12d_scr_q08 | cb284ba8-d3d4-4bef-a81d-74ccf1b6eb66 |
| fl_meg_12d_scr_q15 | 77a6dbcc-461a-45d1-9cd8-45e78f51f91a |
| fl_meg_12d_scr_q30 | 31602b0e-c5d6-4a91-8df6-2ac73dfa0665 |

Wave-3 readout gates (design §3.3 / frozen eval): the near-absence
test — ~0.02 objects/voyage at common q on mega's N=70 census —
vs the mega in-band window extrapolation q ∈ [1.5e-3, 4.1e-3];
the multi-lot lift where minted voyages carry >1 object (P(≥2|
minted) rises with q); whether ps_ship stays in-band on the fourth
hull; D4 posted-burst discriminator declared TBD (mega bursts
unmeasured). Mega cells ~8GB, ~50min/voyage — full drain is the
slowest wave.
