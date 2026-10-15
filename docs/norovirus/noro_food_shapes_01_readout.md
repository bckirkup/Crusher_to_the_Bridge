# NORO-FOOD-SHAPES-01 readout — final (exp + cls + spr)

> **Status:** Measured — scored on the full 3-hull grid at engine
> `45b2bf18` (image `sha256:bb962a42…a981`, jobdef
> `picard-noro-food-shapes-01:1`). 25,000/25,000 cells landed, 0
> FAILED; 25,000/25,000 parsed, 0 errors, 0 corrupt rows. 1,000 zips
> under each of 11 arm prefixes on exp (seeds 8000–8999) and 7 arm
> prefixes on cls + spr (seeds 8105–9104) at
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_food_shapes_01/`
> (same-seed pairing). Design of record:
> [noro_food_shapes_01_sweep_design.md](noro_food_shapes_01_sweep_design.md)
> — §7.1 scored criteria, §7.4 integrity gates, §7.5 thin-cell rule
> and §11 readout plan are the contract this document answers. The
> wave-1 exp readout
> [noro_food_shapes_01_wave1_readout.md](noro_food_shapes_01_wave1_readout.md)
> remains the exp reference: its numbers are carried verbatim here
> (the 11,000 exp zips were not re-parsed); cls/spr numbers are a
> fresh census re-parse of the 14,000 landed cells on the same
> tooling. The cadence/extent arms (`redraw`, `fx_wide`, `fx_narrow`,
> `redraw_mint`) were PRUNED on cls/spr by the wave-2 amendment —
> cadence and extent measured null on exp — so those legs exist on
> exp only and the cls/spr grid scores the 7 remaining arms.

Readout tooling: `tools/noro_diag/food_shapes_01_scan.py` (one-pass
streaming census decode — summary + witness + mint/titre census +
early-event rows + integrity), `tools/noro_diag/food_shapes_01_report.py`
(the per-hull tables below), `tools/noro_diag/food_shapes_01_bridge.py`
(paired-seed bridge compare vs `noro_entrain_01` prefixes at
`dbbd5395`, hull-parameterized by `--hull`), plus
`entrain_01_dose_audit.py` re-run on the dose-relevant arms. Every
cls/spr number below is pooled per cell over n=1,000 seeds unless a
smaller n is printed; excursion conversion denominators follow the
SCORE-01 convention (voyage with ≥1 `common_source_food`
dominant-route infection). exp numbers are quoted from the wave-1
readout, not re-derived.

## 1. Scored-criteria verdicts up front

Per-hull headline table (`*` = under the 0.4–0.9 pp D1 band, `†` = thin
n per §7.5 — pooled/flagged reads only):

| §7.1 | exp (wave-1, n=1,000/arm) | cls (n=1,000/arm) | spr (n=1,000/arm) |
|---|---|---|---|
| D1 posting marginal vs `off` | `off` 1.00%; thin arms in band (ship +0.60, bg +0.40, redraw +0.60, fx_wide +0.60; fx_narrow +0.30 borderline under); mint family over at ind level (+7.2–+7.6) | `off` 0.00%; thin arms **under** band (ship +0.20*, bg +0.20*); mint family over at ind level (+4.4–+4.9) | `off` 0.10%; thin arms **under** band (ship +0.10*, bg +0.10*); mint family over at ind level (+2.1–+3.0) |
| D2 posted pax-AR pooled med ≥0.04 | **mint 0.0411 — only arm over**; ind 0.0380 | **no arm over** — mint 0.0389 (top), ind itself 0.0352 | **no arm over** — and `ind` tops the table (0.0310 > mint 0.0243) |
| D3 excursion→posting conv vs `ind` | recovered at/above ind: mint 92.7% (1.19×), bg_mint 87.8% (1.13×), redraw_mint 93.9% (1.21×); ind ref 77.7% (n=94) | recovered at ind level: mint 51.0% (1.02×), bg_mint 44.0% (0.88×); ind ref 50.0% (n=96) | recovered at ind level: mint 28.0% (1.07×), bg_mint 20.0% (0.76×); ind ref 26.3% (n=99) |
| D4 cs-excursion burst48 vs rest | recovered: ind 0.489 vs 0.409; mint-family posted 0.70–0.75 | recovered, compressed: ind 0.307 vs 0.285; mint posted 0.454 | exc-vs-rest separation **gone on `ind` itself** (0.257 vs 0.271); posted mints still burst above rest (0.326 vs 0.272) |
| §7.4 gates | all pass | all pass | all pass |
| bridges vs `dbbd5395` | `off` 1000/1000; diverged ⊆ object-active both sides (34/34, 78/78 mint parity) | `off` 1000/1000; diverged ⊆ cs-active both sides (ind_bg 470, bg 445) | `off` 1000/1000; diverged ⊆ cs-active both sides (ind_bg 545, bg 519) |

**Campaign-level verdict (measured):** the mint gate reproduces the
`ind` posting/excursion signature *relative to the in-campaign `ind`
denominator* on every hull — posting rate at `ind` level, excursion
conversion at/above `ind`, posted voyages carry the burst shape — but
every absolute margin compresses with hull scale. The D2 ≥0.04 edge
was met only on exp (mint 0.0411); on cls `mint` lands 0.0389 *and
the `ind` reference itself sits at 0.0352* — the recovered signature
tracks `ind` faithfully, and `ind` on cls is below the edge. This is
the SCORE-01 hull-compression ordering (ind conversion 62.8→42.7→13.3
exp→cls→spr at `40862b8c`; re-measured here 77.7→50.0→26.3 —
systematically higher at this image because `two_mode` lifts the v1
draw path too, but the ordering holds): the
mechanism is hull-invariant relative to its own denominator, and the
absolute posting/AR magnitudes are not. Whether the implicated-band
grammar is "enough" is therefore a statement about the hull: on exp
the mint family reaches the declared edge; on the big hulls the same
machinery reproduces `ind` exactly — and `ind` is what is below band.
The cadence and extent axes remain measured nulls (exp-only cells;
pruned after wave 1 measured them flat).

**Hull-scaling read (measured vs inferred vs hypothesis):**

- *Measured:* posting marginals, posted-AR medians, excursion
  conversion and burst48 separation all shrink monotonically exp→
  cls(→spr) on every arm — e.g. `ind` posting 8.2→4.8→2.7%, `mint`
  8.6→4.9→3.1%, posted b48 med on mint 0.708→0.454→0.326, exc-vs-rest
  b48 gap on ind +0.080→+0.022→−0.015 (separation gone on spr), worst
  non-cs route-share drift fomite −16.07→−3.92→−2.23 pp. The *relative* structure (mint ≈ ind ×1.0–1.2
  on every D-metric, mint-family ≫ thin arms) is hull-stable.
- *Measured:* `off` floor re-measured 1.0→0.0% (design §7.1 last
  measure 1.0/0.0/0.1% at `dbbd5395` — reproduced); `ind` posting
  4.8% vs the ENTRAIN-01 cls baseline 3.9% (the +Δ vs `ind_bg` 3.8%
  is again the declared two_mode margin, ~1.0 pp).
- *Inferred:* the compression is the same epidemic-density effect
  SCORE-01 measured — on bigger hulls postings arrive earlier in a
  voyage's epidemic (more competing routes, earlier sanitary wires),
  so marginal lift from any single cs pathway shrinks. The mechanism
  recoveries that matter (D3 ratio, D4 separation) read off the
  in-campaign `ind` and hold; the absolute gates calibrated on exp do
  not carry across hulls.
- *Hypothesis (not measured):* whether a hull-rescaled D2 edge
  (e.g. tracking `ind`'s own posted-AR median per hull) is the right
  scoring convention — flagged for the ledger, not decided here.

## 2. Coverage

| hull | arms | cells | parsed | errors |
|---|---|---|---|---|
| exp | 11 | 11,000 | 11,000 | 0 (wave-1, carried) |
| cls | 7 | 7,000 | 7,000 | 0 |
| spr | 7 | 7,000 | 7,000 | 0 |

No failure or corruption class on any hull. The 4 pruned arms have no
cls/spr cells — declared, not shortfall.

## 3. D1 — posting marginal vs in-campaign `off`

exp table carried verbatim from the wave-1 readout; cls/spr marginal =
arm − `off` per paired seeds 8105–9104, Wilson 95% on the arm rate.

**exp** (n=1,000/arm, `off` = 10/1,000):

| arm | posted | Wilson 95% | marginal pp | in 0.4–0.9 band |
|---|---|---|---|---|
| ind | 82 (8.20%) | [6.66%,10.06%] | +7.20 | over |
| ind_bg | 69 (6.90%) | [5.49%,8.64%] | +5.90 | over |
| ship | 16 (1.60%) | [0.99%,2.58%] | +0.60 | yes |
| bg | 14 (1.40%) | [0.84%,2.34%] | +0.40 | yes |
| mint | 86 (8.60%) | [7.02%,10.50%] | +7.60 | over |
| bg_mint | 82 (8.20%) | [6.66%,10.06%] | +7.20 | over |
| redraw | 16 (1.60%) | [0.99%,2.58%] | +0.60 | yes |
| redraw_mint | 86 (8.60%) | [7.02%,10.50%] | +7.60 | over |
| fx_wide | 16 (1.60%) | [0.99%,2.58%] | +0.60 | yes |
| fx_narrow | 13 (1.30%) | [0.76%,2.21%] | +0.30 | under (borderline) |

**cls** (n=1,000/arm, `off` = 0/1,000 — the floor re-measured to zero,
so the marginal is the raw posting rate):

| arm | posted | Wilson 95% | paired gained/lost vs off | marginal pp | in 0.4–0.9 band |
|---|---|---|---|---|---|
| ind | 48 (4.80%) | [3.64%,6.31%] | +48/−0 | +4.80 | over |
| ind_bg | 38 (3.80%) | [2.78%,5.17%] | +38/−0 | +3.80 | over |
| ship | 2 (0.20%) | [0.05%,0.73%] | +2/−0 | +0.20 | under |
| bg | 2 (0.20%) | [0.05%,0.73%] | +2/−0 | +0.20 | under |
| mint | 49 (4.90%) | [3.73%,6.42%] | +49/−0 | +4.90 | over |
| bg_mint | 44 (4.40%) | [3.29%,5.86%] | +44/−0 | +4.40 | over |

**spr** (n=1,000/arm, `off` = 1/1,000):

| arm | posted | Wilson 95% | paired gained/lost vs off | marginal pp | in 0.4–0.9 band |
|---|---|---|---|---|---|
| ind | 27 (2.70%) | [1.86%,3.90%] | +26/−0 | +2.60 | over |
| ind_bg | 16 (1.60%) | [0.99%,2.58%] | +15/−0 | +1.50 | over |
| ship | 2 (0.20%) | [0.05%,0.73%] | +1/−0 | +0.10 | under |
| bg | 2 (0.20%) | [0.05%,0.73%] | +1/−0 | +0.10 | under |
| mint | 31 (3.10%) | [2.19%,4.37%] | +30/−0 | +3.00 | over |
| bg_mint | 22 (2.20%) | [1.46%,3.31%] | +21/−0 | +2.10 | over |

Reads: the mint family posts at `ind`-level on every hull (8.6 vs 8.2
exp; 4.9 vs 4.8 cls) — the D1 over-band verdict on mint-family cells is
structural (the mint gate is the posting-rate control, not a defect).
Thin arms were calibrated to the 0.4–0.9 band on exp; on cls the same
machinery produces +0.20 pp — hull compression carries them below the
exp-calibrated band. `ind` itself overshoots the band on both hulls —
the band describes honest thin-object posting, not the `ind` ceiling.

## 4. D2 — posted pax-AR pooled medians

Pooled per-voyage pax AR over posted cells per arm; median [IQR], p90.

**exp** (carried):

| arm | n_posted | posted pax-AR med [IQR] | p90 | ≥0.04 |
|---|---|---|---|---|
| ind | 82 | 0.0380 [0.0071,0.0506] | 0.0567 | no |
| ind_bg | 69 | 0.0348 [0.0063,0.0475] | 0.0570 | no |
| ship | 16 | 0.0205 [0.0047,0.0324] | 0.0443 | no |
| bg | 14 | 0.0205 [0.0040,0.0316] | 0.0370 | no |
| mint | 86 | 0.0411 [0.0040,0.0633] | 0.0839 | **yes** |
| bg_mint | 82 | 0.0332 [0.0040,0.0554] | 0.0854 | no |
| redraw | 16 | 0.0158 [0.0000,0.0316] | 0.0411 | no |
| redraw_mint | 86 | 0.0379 [0.0063,0.0657] | 0.0902 | no |
| fx_wide | 16 | 0.0143 [0.0024,0.0316] | 0.0348 | no |
| fx_narrow | 13 | 0.0222 [0.0063,0.0316] | 0.0342 | no |
| obj pooled | 329 | 0.0316 [0.0032,0.0538] | 0.0823 | no |

**cls** (n=1,000/arm):

| arm | n_posted | posted pax-AR med [IQR] | p90 | ≥0.04 |
|---|---|---|---|---|
| ind | 48 | 0.0352 [0.0164,0.0396] | 0.0480 | no |
| ind_bg | 38 | 0.0336 [0.0187,0.0379] | 0.0426 | no |
| ship | 2 | 0.0195 [0.0105,0.0284] | 0.0338 | no |
| bg | 2 | 0.0086 [0.0058,0.0114] | 0.0131 | no |
| mint | 49 | 0.0389 [0.0172,0.0516] | 0.0549 | no |
| bg_mint | 44 | 0.0374 [0.0185,0.0448] | 0.0521 | no |
| obj pooled | 97 | 0.0374 [0.0142,0.0501] | 0.0541 | no |

**spr** (n=1,000/arm):

| arm | n_posted | posted pax-AR med [IQR] | p90 | ≥0.04 |
|---|---|---|---|---|
| ind | 27 | 0.0310 [0.0126,0.0355] | 0.0390 | no |
| ind_bg | 16 | 0.0198 [0.0149,0.0303] | 0.0359 | no |
| ship | 2 | 0.0114 [0.0064,0.0164] | 0.0194 | no |
| bg | 2 | 0.0114 [0.0064,0.0164] | 0.0194 | no |
| mint | 31 | 0.0243 [0.0098,0.0353] | 0.0448 | no |
| bg_mint | 22 | 0.0198 [0.0042,0.0333] | 0.0387 | no |
| obj pooled | 57 | 0.0214 [0.0067,0.0338] | 0.0442 | no |

Reads: `mint` is the top object arm on exp+cls and lands *above* `ind`
there (0.0411 vs 0.0380; 0.0389 vs 0.0352); on spr `ind` flips on top
(0.0310 vs 0.0243) — `mint` still posts slightly *more often* (31 vs
27) so its median dilutes into the bigger-hull tail. The 0.04 edge is
cleared only on exp, where `ind` itself nearly reaches it. The
SCORE-01 thin-tail signature (0.016–0.021) persists on every thin arm.

## 5. D3 — excursion → posting conversion

Excursion voyage = ≥1 `common_source_food` dominant-route infection
(SCORE-01 basis). Object voyage = ≥1 armed object row (witness census).

**exp** (carried): `ind` reference 94 excursion voyages, 77.7% post.

| arm | exc voy | posted | conv % | vs ind | obj voy | obj posted | obj conv % |
|---|---|---|---|---|---|---|---|
| ind | 94 | 73 | 77.7 | 1.00× | 0 | 0 | — |
| ind_bg | 94 | 60 | 63.8 | 0.82× | 0 | 0 | — |
| ship | 6 | 6 | 100.0 | 1.29× | 670 | 16 | 2.4 |
| bg | 6 | 5 | 83.3 | 1.07× | 670 | 14 | 2.1 |
| mint | 82 | 76 | 92.7 | 1.19× | 702 | 86 | 12.3 |
| bg_mint | 82 | 72 | 87.8 | 1.13× | 702 | 82 | 11.7 |
| redraw | 6 | 6 | 100.0 | 1.29× | 670 | 16 | 2.4 |
| redraw_mint | 82 | 77 | 93.9 | 1.21× | 702 | 86 | 12.3 |
| fx_wide | 6 | 6 | 100.0 | 1.29× | 670 | 16 | 2.4 |
| fx_narrow | 6 | 4 | 66.7 | 0.86× | 670 | 13 | 1.9 |

**cls** (n=1,000/arm): `ind` reference 96 excursion voyages, 50.0% post.

| arm | exc voy | posted | conv % | vs ind | obj voy | obj posted | obj conv % |
|---|---|---|---|---|---|---|---|
| ind | 96 | 48 | 50.0 | 1.00× | 0 | 0 | — |
| ind_bg | 96 | 38 | 39.6 | 0.79× | 0 | 0 | — |
| ship | 20 | 2 | 10.0 | 0.20× | 999 | 2 | 0.2 |
| bg | 20 | 1 | 5.0 | 0.10× | 999 | 2 | 0.2 |
| mint | 96 | 49 | 51.0 | 1.02× | 999 | 49 | 4.9 |
| bg_mint | 100 | 44 | 44.0 | 0.88× | 999 | 44 | 4.4 |

**spr** (n=1,000/arm): `ind` reference 99 excursion voyages, 26.3% post.

| arm | exc voy | posted | conv % | vs ind | obj voy | obj posted | obj conv % |
|---|---|---|---|---|---|---|---|
| ind | 99 | 26 | 26.3 | 1.00× | 0 | 0 | — |
| ind_bg | 98 | 15 | 15.3 | 0.58× | 0 | 0 | — |
| ship | 31 | 1 | 3.2 | 0.12× | 1000 | 2 | 0.2 |
| bg | 32 | 1 | 3.1 | 0.12× | 1000 | 2 | 0.2 |
| mint | 107 | 30 | 28.0 | 1.07× | 1000 | 31 | 3.1 |
| bg_mint | 105 | 21 | 20.0 | 0.76× | 1000 | 22 | 2.2 |

Reads: on cls nearly every voyage is object-active on armed arms
(999/1000) and cs-excursion counts roughly doubled per arm (ind 96 vs
ship-family 20–100); the mint family still converts excursions at
`ind` rate (1.02×/0.88×) while the shipped-rate thin arms collapse
(0.10–0.20×) — the mint gate, not the object channel alone, is what
carries conversion. On spr the same shape at half the level again:
mint 1.07× / bg_mint 0.76× of a 26.3% `ind` reference, thin arms
0.12×. Object-voyage conversion (4.4–4.9%→2.2–3.1% mint family vs
0.2% thin) compresses but keeps the ~15–25× mint/thin ordering on both
big hulls.

## 6. D4 — burst48 discriminator

burst48 = max 48-epoch window share of the voyage's infections, median
[IQR]; `rest` = non-excursion cells.

**exp** (carried):

| arm | excursion b48 med [IQR] | rest b48 med [IQR] | posted b48 med | exc n |
|---|---|---|---|---|
| off | — | 0.412 [0.357,0.500] | 0.360 | 0 |
| ind | 0.489 [0.387,0.699] | 0.409 [0.357,0.500] | 0.538 | 94 |
| ind_bg | 0.485 [0.362,0.605] | 0.409 [0.357,0.500] | 0.523 | 94 |
| ship | 0.743 [0.606,0.850] | 0.412 [0.357,0.500] | 0.391 | 6 |
| bg | 0.576 [0.516,0.690] | 0.412 [0.357,0.500] | 0.391 | 6 |
| mint | 0.714 [0.531,0.820] | 0.412 [0.357,0.500] | 0.708 | 82 |
| bg_mint | 0.700 [0.494,0.793] | 0.412 [0.357,0.500] | 0.700 | 82 |
| redraw | 0.793 [0.703,0.892] | 0.412 [0.357,0.500] | 0.391 | 6 |
| redraw_mint | 0.757 [0.558,0.842] | 0.412 [0.357,0.500] | 0.748 | 82 |
| fx_wide | 0.634 [0.536,0.714] | 0.412 [0.357,0.500] | 0.391 | 6 |
| fx_narrow | 0.512 [0.404,0.577] | 0.412 [0.357,0.500] | 0.372 | 6 |

**cls** (n=1,000/arm):

| arm | excursion b48 med [IQR] | rest b48 med [IQR] | posted b48 med | exc n |
|---|---|---|---|---|
| off | — | 0.2857 [0.2705,0.3043] | — | 0 |
| ind | 0.3068 [0.2672,0.3621] | 0.2847 [0.2696,0.3033] | 0.343 | 96 |
| ind_bg | 0.2783 [0.2525,0.3236] | 0.2857 [0.2698,0.3033] | 0.333 | 96 |
| ship | 0.2870 [0.2664,0.2976] | 0.2869 [0.2708,0.3065] | 0.573 | 20 |
| bg | 0.2909 [0.2653,0.3214] | 0.2868 [0.2708,0.3058] | 0.532 | 20 |
| mint | 0.2906 [0.2535,0.4586] | 0.2857 [0.2703,0.3050] | 0.454 | 96 |
| bg_mint | 0.2950 [0.2639,0.3805] | 0.2868 [0.2708,0.3058] | 0.416 | 100 |

**spr** (n=1,000/arm):

| arm | excursion b48 med [IQR] | rest b48 med [IQR] | posted b48 med | exc n |
|---|---|---|---|---|
| off | — | 0.2722 [0.2584,0.2865] | 0.235 | 0 |
| ind | 0.2569 [0.2458,0.2901] | 0.2714 [0.2587,0.2857] | 0.304 | 99 |
| ind_bg | 0.2562 [0.2424,0.2791] | 0.2723 [0.2590,0.2862] | 0.251 | 98 |
| ship | 0.2689 [0.2540,0.2905] | 0.2723 [0.2577,0.2872] | 0.486 | 31 |
| bg | 0.2681 [0.2529,0.2902] | 0.2727 [0.2576,0.2873] | 0.530 | 32 |
| mint | 0.2556 [0.2417,0.2846] | 0.2727 [0.2581,0.2865] | 0.326 | 107 |
| bg_mint | 0.2547 [0.2376,0.2802] | 0.2723 [0.2576,0.2868] | 0.324 | 105 |

Reads: the whole burst48 scale compresses with hull size (rest median
0.41→0.29 exp→cls — epidemics on big hulls spread over more epochs, so
no 48-epoch window holds the same share). The *ordering* survives:
posted-mint cells carry elevated b48 on every hull (0.454 cls,
0.326 spr, vs rest ~0.27–0.29). On spr the *excursion-vs-rest*
separation is gone on the `ind` reference itself (0.257 vs 0.271 —
inverted within noise): epidemics on the 3,000-agent hull are broad
enough that no 48-epoch window isolates them, so D4's excursion half
cannot read there; its posting half still does (posted mints 0.326 vs
rest 0.272 — they do not collapse to the rest rate). On cls/spr the
thin-arm posted b48 (ship 0.573/0.486, bg 0.532/0.530 on n=20–32)
reads *high* — thin-arm postings are rare and cs-heavy by selection,
flagged thin per §7.5.

## 7. Mint census + §7.4 integrity gates (per hull)

`provisioned_lot` census: objects minted / voyages minting / windows /
pan titre draws vs the implicated band [1.5e2, 5e3].

**exp** (carried): ship 6 cells/7 obj; bg 6/7; redraw 6/7; fx_wide 6/7;
fx_narrow 6/7; mint 82 cells/93 obj (1,794 windows, 1,765 draws 100%
in-band); bg_mint 82/93 (52.8% in-band); redraw_mint 82/93 (100%).

**cls** (n=1,000/arm):

| arm | lot-obj cells | objects | windows | pan draws | in-band obj | in-band pan | draw range |
|---|---|---|---|---|---|---|---|
| off | 0 | 0 | 0 | 0 | — | — | — |
| ind | 0 | 0 | 0 | 471 | — | 471/471 | (v1 path) |
| ind_bg | 0 | 0 | 0 | 471 | — | 226/471 | (v1 path) |
| ship | 6 | 7 | 35 | 37 | 7/7 | 37/37 | [162.2, 3898.8] |
| bg | 6 | 7 | 35 | 37 | 2/7 | 11/37 | [11.7, 6126.0] |
| mint | 84 | 96 | 1,123 | 1,181 | 96/96 | 1,181/1,181 | [154.9, 4986.7] |
| bg_mint | 84 | 96 | 1,120 | 1,182 | 52/96 | 677/1,182 | [10.7, 9947.8] |

**spr** (n=1,000/arm):

| arm | lot-obj cells | objects | windows | pan draws | in-band obj | in-band pan | draw range |
|---|---|---|---|---|---|---|---|
| off | 0 | 0 | 0 | 0 | — | — | — |
| ind | 0 | 0 | 0 | 478 | — | 478/478 | (v1 path) |
| ind_bg | 0 | 0 | 0 | 478 | — | 228/478 | (v1 path) |
| ship | 6 | 7 | 52 | 58 | 7/7 | 58/58 | [162.2, 3898.8] |
| bg | 6 | 7 | 57 | 60 | 2/7 | 18/60 | [11.7, 6126.0] |
| mint | 84 | 96 | 1,433 | 1,479 | 96/96 | 1,479/1,479 | [154.9, 4986.7] |
| bg_mint | 84 | 96 | 1,427 | 1,466 | 52/96 | 806/1,466 | [10.7, 9947.8] |

*Measured consistency check:* cls and spr mint counts are **identical**
(ship/bg 6 cells → 7 objects; mint/bg_mint 84 cells → 96 objects) —
the mint gate draws off the seed-paired RNG partition and is
hull-invariant by construction, and the census confirms it verbatim.

**Re-mint witness (per-window titre variance):** on cls+spr all
multi-window objects are constant-titre (cls ship 7/7, bg 7/7, mint
95/95, bg_mint 96/96; spr ship 7/7, bg 7/7, mint 95/95, bg_mint
94/94) — correct: the redraw arms are pruned off cls/spr, so the
varying-titre gate has no cell to fire on; the `per_object` clause
(exactly one titre per `object_id`) holds on every minted object.

**§7.4 gate-by-gate (cls and spr — identical outcomes on both):**

1. *Witness echo* — `parameters.transmission.common_source` matches the
   frozen arm override verbatim on 14,000/14,000 cells. PASS.
2. *Re-mint band* — every `two_mode` titre draw inside [150, 5000] on
   mint-family (96/96 obj, 1,181/1,181 pan on `mint`); `bg`/`bg_mint`/
   `ind_bg` background-mode draws spill outside as declared
   (cls: `bg` 11/37 pan in-band; spr: 18/60 — background mode, not a
   violation). PASS.
3. *Declared-extent bookkeeping* — no `fx_*` cells on cls/spr; gate
   vacuous here, PASS by construction.
4. *Per-window re-mint* — all objects `per_object` (constant titre),
   as configured; the redraw side of the gate is vacuous on cls/spr.
   PASS.
5. *Witness census* — 0 missing/unresolved `object_id`, 0 missing
   serial, 0 open objects, 0 `servings_served > lot_servings`, 0
   non-norwalk objects on all 7 arms on both hulls; `ind`/`ind_bg`
   carry only v1 rows (object_id null as designed). PASS.
6. *Bit-identity bridges* — §10. `off` 1,000/1,000 bit-identical on
   both hulls; cs-active divergences confined to the declared
   machinery delta. PASS on the binding invariant.
7. *Mint echo* — `mint`-family cells mint lots at 8.4% on both hulls
   (84/1,000 cells, 96 objects) vs shipped-rate ~0.6% (ship/bg 6
   cells) — the (0.02,0.15) gate reached the engine. PASS.

**Vacuity declarations:** none on cls or spr — every lot-capable arm
minted (`ship`/`bg` 7 objects on 6 cells; `mint`/`bg_mint` 96 on 84).
`off` and the `ind` family mint nothing by construction (the zero/v1
witness clauses, PASS).

## 8. Margin attribution (paired seeds, n=1,000)

**exp** (carried): ship−bg +0.20 pp; ind−ind_bg +1.30 pp
(+13.8 pp conv); mint−bg_mint +0.40 pp (+4.9 pp conv); ship−redraw
+0.00 (cadence null); ship−fx_wide +0.00, ship−fx_narrow +0.30
(extent null→thin dip); mint-rate margins −7.00/−6.80/−7.00 pp.

**cls**:

| margin pair | axis | A posted | B posted | gained/lost | Δposted pp | A exc conv | B exc conv |
|---|---|---|---|---|---|---|---|
| ship − bg | titre denom (thin) | 2 | 2 | +1/−1 | +0.00 | 10.0% (n=20) | 5.0% (n=20) |
| ind − ind_bg | titre denom (powered) | 48 | 38 | +15/−5 | +1.00 | 50.0% (n=96) | 39.6% (n=96) |
| mint − bg_mint | titre denom (powered) | 49 | 44 | +8/−3 | +0.50 | 51.0% (n=96) | 44.0% (n=100) |
| ship − mint | mint rate | 2 | 49 | +0/−47 | −4.70 | 10.0% (n=20) | 51.0% (n=96) |
| bg − bg_mint | mint rate | 2 | 44 | +1/−43 | −4.20 | 5.0% (n=20) | 44.0% (n=100) |

**spr**:

| margin pair | axis | A posted | B posted | gained/lost | Δposted pp | A exc conv | B exc conv |
|---|---|---|---|---|---|---|---|
| ship − bg | titre denom (thin) | 2 | 2 | +0/−0 | +0.00 | 3.2% (n=31) | 3.1% (n=32) |
| ind − ind_bg | titre denom (powered) | 27 | 16 | +13/−2 | +1.10 | 26.3% (n=99) | 15.3% (n=98) |
| mint − bg_mint | titre denom (powered) | 31 | 22 | +10/−1 | +0.90 | 28.0% (n=107) | 20.0% (n=105) |
| ship − mint | mint rate | 2 | 31 | +0/−29 | −2.90 | 3.2% (n=31) | 28.0% (n=107) |
| bg − bg_mint | mint rate | 2 | 22 | +0/−20 | −2.00 | 3.1% (n=32) | 20.0% (n=105) |

Reads: every margin survives in sign and relative size on both hulls —
titre denominator ~+1.0 pp posting / +8–11 pp conversion on the v1
path (ind−ind_bg: +1.00 pp cls, +1.10 pp spr), ~+0.5–0.9 pp on the
object path; the mint-rate margins shrink with the hull
(−7.0→−4.7→−2.9 pp on ship−mint) but dominate posting frequency
everywhere. Cadence/extent margins don't exist off exp (arms pruned —
their exp nulls stand).

## 9. Dose position (posted vs unposted acquisitions)

`entrain_01_dose_audit.py` rows on the dose-relevant arms (n=1,000
each). Hill position `p` only — no absolute dose figures while the
dose ledger is withdrawn.

**exp** (carried): unposted acq p≈0.22–0.23 everywhere; posted p
0.34–0.56; posted/unposted cum-median ratio ~6× (ship) to ~400×
(mint/redraw_mint).

| arm | posted acq n | p med (posted) | frac p>0.50 | cum-median ratio |
|---|---|---|---|---|
| ind | 3,167 | 0.481 | 0.481 | ~73× |
| ind_bg | 2,587 | 0.418 | 0.378 | ~22× |
| ship | 527 | 0.340 | 0.366 | ~6× |
| mint | 4,439 | 0.558 | 0.659 | ~400× |
| bg_mint | 3,929 | 0.512 | 0.530 | ~138× |
| redraw_mint | 4,495 | 0.558 | 0.670 | ~396× |

**cls** (ind/ind_bg/ship/mint/bg_mint; n=1,000 cells each; posted acq =
acquisitions on posted voyages; ratio = posted/unposted cum med):

| arm | posted acq n | p med (posted) | frac p>0.50 | cum-median ratio |
|---|---|---|---|---|
| ind | 8,364 | 0.319 | 0.294 | ~3× |
| ind_bg | 6,446 | 0.309 | 0.232 | ~3× |
| ship | 304 | 0.460 | 0.470 | ~37× |
| mint | 8,726 | 0.401 | 0.425 | ~12× |
| bg_mint | 7,744 | 0.376 | 0.361 | ~8× |

Reads: unposted acquisitions still sit at p≈0.24 everywhere (exp
0.22–0.23 — the Hill tail framing carries). The posted-voyage tail
compresses with the hull (mint p med 0.558→0.401; ratio ~400×→~12×):
on the big hull a posted voyage's typical acquisition is much further
into the epidemic, so the median posted acq sits at lower Hill
position even though posting still tracks the dose tail (the mint
family still leads: 0.40/0.38 vs `ind` 0.319; `ship`'s 0.460 is 2
posted voyages — thin, flagged). The signature "posted rides the
tail" survives; the tail itself is hull-compressed.

**spr** (ind/ind_bg/ship/mint/bg_mint; n=1,000 cells each; same
method):

| arm | posted acq n | p med (posted) | frac p>0.50 | cum-median ratio |
|---|---|---|---|---|
| ind | 6,850 | 0.295 | 0.229 | ~2× |
| ind_bg | 4,022 | 0.289 | 0.177 | ~2× |
| ship | 409 | 0.320 | 0.308 | ~3× |
| mint | 7,722 | 0.323 | 0.316 | ~3× |
| bg_mint | 5,204 | 0.329 | 0.327 | ~4× |

Reads: unposted p ≈ 0.246 everywhere — the same tail base as cls.
The posted-voyage tail compresses once more with hull (mint p med
0.558→0.401→0.323; cum ratio ~400×→~12×→~3×): on spr a posted
voyage's typical acquisition is nearly at unposted Hill position.
The mint family still leads `ind` on p med (0.323/0.329 vs 0.295)
but the margin narrows to ~0.03 — the "posted rides the tail"
signature survives in direction only; the tail itself is almost
fully hull-compressed. (`ship`'s 0.320 is 2 posted voyages — thin,
flagged.)

## 10. Bridge checks (cls + spr)

Per-seed summary compare vs `noro_entrain_01` prefixes at `dbbd5395`
(same seeds 8105–9104), normalizing declared fields; the bridge rows
carry every per-seed verdict and the diverging field set.

| bridge | paired | identical | diverged | structure |
|---|---|---|---|---|
| cls `off` ↔ entrain `off` | 1,000 | 1,000 | 0 | — |
| cls `ind_bg` ↔ entrain `ind` | 1,000 | 530 | 470 | 470/470 seeds cs-active on **both** sides; diverged seeds carry more cs events (A-side med 25.5 vs 20.0 on identical); diffs confined to dose-downstream fields (events/takers/dose_share/cost/detection) |
| cls `bg` ↔ entrain `ship` | 1,000 | 555 | 445 | same — 445/445 cs-active both sides (med 94 vs 69 events); same field set |
| spr `off` ↔ entrain `off` | 1,000 | 1,000 | 0 | — |
| spr `ind_bg` ↔ entrain `ind` | 1,000 | 455 | 545 | 545/545 cs-active both sides (med 39 vs 37); same field set |
| spr `bg` ↔ entrain `ship` | 1,000 | 481 | 519 | 519/519 cs-active both sides (med 146 vs 130); same field set |

Reading: the binding invariant from wave 1 holds on both new hulls —
**no diverged seed lacks cs activity on both sides** (0 exceptions in
4,000 pairs), `off` stays bit-identical end-to-end, and the diverging
fields are all downstream of cs dose. What changes vs exp is the
*divergence fraction* (ind_bg 3.4% → 47.0% → 54.5%): on the big hulls
cs events fire in nearly every voyage (992–1,000/1,000 seeds cs-active
on both sides vs ~9% excursion share on exp), and the #990/#991 draw
path engages stochastically per cs event — more events, more chances
to fire. Same declared machinery delta, amplified by cs-activity
density; consistent with the exp reading where diverged seeds were
exactly the minted voyages.

## 11. Must-not-move (cls and spr)

- `off` zero-witness: 1,000 censused cells per hull, 0 objects, 0
  events, `dose_credited` sum 0.000000 — PASS on both.
- `ind`/`ind_bg` v1-only witness: 0 object-linked rows over 2,000
  cells per hull — PASS on both.
- Median paired Δinf-AR vs `off`: +0.0000 on all 6 non-off arms on
  both hulls (cls worst p90 |Δ| 0.0119 on `mint`; spr 0.0104) — total
  epidemiology unmoved.
- Worst non-cs pooled route-share drift vs `off`: **fomite −3.92 pp on
  `mint` (cls), −2.23 pp on `mint` (spr)** — vs exp's −16.07 pp on
  `redraw_mint`; composition shift inside a fixed total, shrinking
  with hull, not a non-cs rate move.
- `ship` vs `bg` witness identity: 563/1,000 (cls) and 462/1,000 (spr)
  seeds identical on object/event/taker/pan/window/acquisition counts
  and end reasons; every diff inside cs-active voyages (the
  titre-denom arm's RNG stream).
- No failure/corruption class in 14,000 cls+spr zips.

## 12. Per-hull admissibility + campaign verdict

| hull | D1 | D2 | D3 | D4 | §7.4 | admissibility verdict |
|---|---|---|---|---|---|---|
| exp | held on thin arms (fx_narrow borderline); mint over at ind level | met on `mint` only | recovered ≥ind (1.13–1.21×) | recovered | all pass | **admissible — all four signatures recovered on the mint family; thin-cell rule applied** |
| cls | thin arms under band (+0.20); mint over at ind level | **not met on any arm — `ind` itself 0.0352** | recovered at ind (1.02×) | recovered, compressed | all pass | **admissible-with-caveat — relative signatures recover; the exp-calibrated absolute bands do not carry to this hull** |
| spr | thin arms under band (+0.10); mint over at ind level | **not met — `ind` tops the table (0.0310 > mint 0.0243)** | recovered at ind (1.07×) | partial — exc-vs-rest gone on `ind` (0.257 vs 0.271); posted mints still above rest (0.326 vs 0.272) | all pass | **admissible-with-caveat — same caveat; D4's excursion discriminator is unreadable at this hull scale** |

**Campaign summary verdict (measured):** the three-knob grammar
answers the design question the same way on every hull — **the mint
gate is the signature carrier**: given a minted `provisioned_lot`
object in the implicated titre band, posting lands at `ind`-level
rates (3.1 vs 2.7% spr), excursion conversion recovers to
`ind`×1.0–1.2 (1.02–1.07× cls/spr), posted voyages carry burst48
above rest, and posted acquisitions ride the dose tail. **Titre
denominator** is a real but second-order margin (+~1 pp posting,
+~5–14 pp conversion). **Cadence and extent are measured nulls** (exp
only). What the big hulls add is the compression measurement: every
*absolute* gate calibrated on exp (0.4–0.9 pp band, ≥0.04 AR edge)
fails on cls and spr — including on `ind` itself (0.0352 / 0.0310),
and on spr `ind` out-ranks `mint` on the D2 median outright — while
every *relative* signature survives. Read against the frozen criteria
the campaign is: **exp admissible; cls and spr admissible-with-caveat**
— the caveat being the hull-scaling compression: the mechanism
recovers `ind` on every hull, and `ind` is what the big hulls
compress. On spr the compression is deep enough that D4's excursion
discriminator has no signal even on the reference arm — only the
posting-side burst read (0.326 vs rest 0.272) survives.

## 13. Method notes

- Coverage: 11 arms × 1,000 seeds on exp (carried from #996); 7 arms ×
  1,000 on cls + spr = 14,000 new zips this readout, streaming census
  decode, one JSONL row per voyage; aggregation in
  `food_shapes_01_report.py`; bridge compare in
  `food_shapes_01_bridge.py` (`--hull` parameterized); dose rows via
  `entrain_01_dose_audit.py` (5 arms × 1,000 per hull).
- Posted = `summary.summary.sanitary_activity` wires (A9 thresholds),
  same as SCORE-01/ENTRAIN-01 readouts; excursion and object-voyage
  denominators identical to the wave-1 conventions.
- Seed pairing: cls/spr arms share seeds 8105–9104 exactly; every
  margin diff and bridge check is paired on the seed; gained/lost is
  the raw sign-split of the per-seed posting difference.
- Power: thin arms (`ship`, `bg`) minted 6–7 lot cells per hull —
  §7.5 pooled reads only; powered reads run on mint family (84–96
  cells/hull) and ind family (~96 excursion voyages/hull).
- Baselines cited: SCORE-01 at `40862b8c`, ENTRAIN-01 at `dbbd5395`,
  DOSE-POS-01 (2/1,620 lot-mint rate), canary 108/108 at `45b2bf18`,
  wave-1 readout PR #996.
- exp figures are quoted verbatim from the wave-1 readout; they were
  not re-derived from the exp zips.
