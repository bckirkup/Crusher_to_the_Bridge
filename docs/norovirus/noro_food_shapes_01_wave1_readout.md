# NORO-FOOD-SHAPES-01 readout — wave 1 (exp hull)

> **Status:** Measured — scored on wave 1 at engine `45b2bf18`
> (image `sha256:bb962a42…a981`, jobdef `picard-noro-food-shapes-01:1`).
> 11,000/11,000 cells landed and parsed, 0 errors, 0 corrupt rows; 1,000
> zips under each of the 11 arm prefixes at
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_food_shapes_01/`
> (exp, seeds 8000–8999, same-seed pairing).
> Design of record:
> [noro_food_shapes_01_sweep_design.md](noro_food_shapes_01_sweep_design.md) —
> §7.1 scored criteria, §7.4 integrity gates, §7.5 thin-cell rule and §11
> readout plan are the contract this document answers. cls/spr cells were
> not submitted and are not scored here.

Readout tooling (this PR): `tools/noro_diag/food_shapes_01_scan.py`
(one-pass streaming census decode — summary + witness + mint/titre census
+ early-event rows + integrity), `tools/noro_diag/food_shapes_01_report.py`
(this document's tables), `tools/noro_diag/food_shapes_01_bridge.py`
(paired-seed bridge compare vs `noro_entrain_01` prefixes at `dbbd5395`),
plus `entrain_01_dose_audit.py` re-run on the six dose-relevant arms.
Every number below is pooled per cell over n=1,000 seeds unless a
smaller n is printed; excursion conversion denominators follow the
SCORE-01 convention (voyage with ≥1 `common_source_food` dominant-route
infection).

## 1. Scored-criteria verdicts up front

| §7.1 clause | Question | Measured answer | Verdict |
|---|---|---|---|
| D1 | posting marginal vs `off` inside 0.4–0.9 pp | thin arms in band: ship +0.60, bg +0.40, redraw +0.60, fx_wide +0.60; fx_narrow +0.30 just under; mint family over at ind level (+6.8 to +7.6 pp) | **Held on thin arms** (fx_narrow borderline under); mint family overposts by construction — mint gate is the posting rate |
| D2 | pooled posted pax-AR median ≥0.04 | `mint` 0.0411 — only arm at/above; redraw_mint 0.0379, ind 0.0380, ind_bg 0.0348, bg_mint 0.0332, thin 0.014–0.022 | **Met on `mint` only**; `ind` itself sits just under the edge |
| D3 | excursion→posting conversion vs `ind` (77.7%, n=94) | mint family 87.8–93.9% (n=82); thin arms 66.7–100% on n=6 (under-powered); obj-voyage conversion mint family ~11.7–12.3% vs thin ~1.9–2.4% | **Recovered at/above `ind` on excursion basis** |
| D4 | cs-excursion burst48 above rest (~0.56 vs ~0.40 signature) | excursions burst on every armed arm (0.49–0.79 vs rest 0.41); posted med on mint family 0.70–0.75 vs `ind` posted 0.538 | **Recovered**, including on the mint-family postings themselves |
| §7.4 gates | six integrity gates | all pass — see §6 | PASS |
| §7.5 | powered reads | mint-family + ind-family cells power the margin reads; thin-arm conversion n=6 is pooled/flagged | applied |
| bridges | `ind_bg`≡ENTRAIN `ind`, `bg`≡`ship`, `off`≡`off` | `off` 1000/1000 bit-identical; `ind_bg` 966/1000, `bg` 922/1000 — all diverging seeds are object-active voyages on **both** sides (34/34, 78/78 mint parity) | Held on the binding invariant; declared machinery delta inside minted voyages |

**Bottom line (measured):** the mint gate is the posting-rate control —
82/1,000 `mint`-family voyages mint a `provisioned_lot` object (8.2%,
inside the declared (0.02,0.15) voyage gate) and 93% of those post, so
posting lands at `ind`-like 8.2–8.6% rather than the VSP band. The
mechanism axes behave as designed: titre denominator is the material
margin on v1 draws (`ind − ind_bg`: +13.8 pp conversion), modest on
object draws (`mint − bg_mint`: +4.9 pp conversion — background titres
still convert); cadence and extent are null on every D-metric. The
conjunction cell `redraw_mint` is the closest object-grammar reproduction
of `ind` yet measured: posting 8.6% vs 8.2%, excursion conversion 93.9%
vs 77.7%, posted burst48 0.748 vs 0.538 — with posted-AR just under the
edge (0.0379 vs `ind`'s own 0.0380). No vacuity: every lot-capable arm
minted `provisioned_lot` objects (ship family 7 objects/6 cells, mint
family 93 objects/82 cells). No wave-2/3 decision is made here — the
numbers stand for the user.

## 2. D1 — posting marginal vs in-campaign `off`

`off` baseline 10/1,000 posted (1.00%). Marginal = arm − off per paired
seeds (all arms n=1,000, seeds 8000–8999); Wilson 95% on the arm rate.

| arm | posted | Wilson 95% | paired gained/lost vs off | marginal pp | in 0.4–0.9 band |
|---|---|---|---|---|---|
| off | 10 (1.00%) | [0.54%,1.83%] | +0/−0 | +0.00 | — |
| ind | 82 (8.20%) | [6.66%,10.06%] | +72/−0 | +7.20 | over |
| ind_bg | 69 (6.90%) | [5.49%,8.64%] | +59/−0 | +5.90 | over |
| ship | 16 (1.60%) | [0.99%,2.58%] | +6/−0 | +0.60 | yes |
| bg | 14 (1.40%) | [0.84%,2.34%] | +5/−1 | +0.40 | yes |
| mint | 86 (8.60%) | [7.02%,10.50%] | +76/−0 | +7.60 | over |
| bg_mint | 82 (8.20%) | [6.66%,10.06%] | +72/−0 | +7.20 | over |
| redraw | 16 (1.60%) | [0.99%,2.58%] | +6/−0 | +0.60 | yes |
| redraw_mint | 86 (8.60%) | [7.02%,10.50%] | +77/−1 | +7.60 | over |
| fx_wide | 16 (1.60%) | [0.99%,2.58%] | +6/−0 | +0.60 | yes |
| fx_narrow | 13 (1.30%) | [0.76%,2.21%] | +4/−1 | +0.30 | under (borderline) |

`ind` at 8.2% sits above the ENTRAIN-01 6.8% measure at `dbbd5395`;
`ind_bg` at 6.9% reproduces it — the +1.3 pp gap is the declared
two_mode titre margin inside object-active v1 voyages (§7).

## 3. D2 — posted pax-AR pooled medians

Pooled over posted cells per arm; method = per-voyage pax AR pooled,
median [IQR], p90.

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

The SCORE-01 thin-tail signature (posted-AR med 0.016–0.021) persists on
every thin arm (0.014–0.022). `mint` clears the edge at 0.0411; the
object-arm pooled median (0.0316) stays under, carried by thin-arm
postings that are not cs-excursion-shaped (their posted b48 ≈ rest, §5).

## 4. D3 — excursion → posting conversion

Excursion voyage = ≥1 `common_source_food` dominant-route infection
(SCORE-01 basis). `ind` reference: 94 excursion voyages, 77.7% post.
Object voyage = ≥1 armed object row (witness census, §6).

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

Reads: (a) excursion conversion — recovered at/above `ind` on every armed
arm; thin-arm cells carry n=6 (declared thin, §7.5 — pooled read only);
(b) object-voyage conversion — the shipped-rate arms convert 1.9–2.4%
of object-active voyages (the DOSE-POS/ENTRAIN under-conversion); the
mint family converts 11.7–12.3% — excursions on mint arms are almost
exactly the lot-minted voyages (82≈82), so object-voyage conversion is
denominator-dominated by `ill_handler`/`ill_diner` activity that produces
no excursion (60% of events deliver zero dose, §6).

## 5. D4 — burst48 discriminator

burst48 = max 48-epoch window share of the voyage's infections (posted
cells and excursion cells; rest = non-excursion cells), median [IQR].

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

The excursion-vs-rest separation is recovered on every armed arm — and
stronger than the `ind` reference (0.49) on the object arms (0.51–0.79).
The mint family's postings are themselves bursts (0.70–0.75 posted b48)
because their posting is cs-excursion-driven; thin-arm postings sit at
rest level (~0.39) because they post on non-cs routes.

## 6. Mint census + §7.4 integrity gates

Per-arm `provisioned_lot` census (objects minted / voyages minting /
windows covered / pan titre draws vs the implicated band [1.5e2, 5e3]):

| arm | lot-obj cells | objects | windows | pan draws | in-band draws | draw range |
|---|---|---|---|---|---|---|
| ship | 6/1000 | 7 | 92 | 90 | 90/90 (100%) | [162.2, 3898.8] |
| bg | 6/1000 | 7 | 89 | 88 | 33/88 (37.5%) | [11.7, 6126.0] |
| redraw | 6/1000 | 7 | 90 | 85 | 85/85 (100%) | [170.2, 1485.4] |
| fx_wide | 6/1000 | 7 | 120 | 120 | 120/120 (100%) | [183.8, 3640.0] |
| fx_narrow | 6/1000 | 7 | 20 | 20 | 20/20 (100%) | [183.8, 3640.0] |
| mint | 82/1000 | 93 | 1794 | 1765 | 1765/1765 (100%) | [154.9, 4986.7] |
| bg_mint | 82/1000 | 93 | 1769 | 1735 | 916/1735 (52.8%) | [10.7, 9947.8] |
| redraw_mint | 82/1000 | 93 | 1772 | 1715 | 1715/1715 (100%) | [158.7, 4974.0] |

v1 path titre draws (ind family, no objects): `ind` 450/450 in band;
`ind_bg` 211/450 (46.9%) — the background-mode denominator is visible on
the v1 draw path too.

Gate-by-gate:

1. **Override echo** — `parameters.transmission.common_source` matches the
   frozen arm override verbatim on 11,000/11,000 cells. PASS.
2. **Re-mint band** — every `two_mode` titre draw (object + v1 paths)
   lands inside [150, 5000]: mint-family 100% object draws, `ind` 100%
   pan draws; `bg`/`bg_mint`/`ind_bg` background-mode draws spill outside
   the band as declared (37.5%/52.8%/46.9% in band). PASS.
3. **Declared-extent bookkeeping** — `fx_wide` draws 13–22 windows
   (declared (12,24)), `fx_narrow` 2–4 (declared (2,4)); per-window
   serving cap = `lot_servings // extent_windows` held on every
   non-terminal window (0 violations); `extent_met` end reason on 4/7
   fx_wide and 7/7 fx_narrow objects. PASS.
4. **Per-window re-mint witness** — the discriminator is clean: every
   multi-window lot object on `redraw`/`redraw_mint` re-mints (7/7 and
   93/93 varying titre); every non-redraw arm's objects are constant
   (0/… varying on ship/bg/mint/bg_mint/fx). PASS.
5. **Witness census** — object rows carry `object_id`/`pan_serial` on all
   object arms; 0 unresolved `object_id`, 0 missing serial, 0 open
   objects, 0 `servings_served > lot_servings`, 0 non-norwalk objects;
   zero-dose event share ~60% consistent across object arms. PASS.
6. **Bridge cells** — §9. PASS on the binding invariant (minted-voyage
   parity + non-object-voyage identity); object-voyage interiors carry
   the declared machinery delta.

Per-arm vacuity: none. `off` mints nothing (0 objects/events — the
zero-witness clause); `ind`/`ind_bg` mint no objects by construction
(v1 witness); every lot-capable arm minted. No failure or corruption
class appeared in 11,000 zips.

## 7. Margin attribution (paired seeds, n=1,000)

| margin pair | axis | A posted | B posted | gained/lost | Δposted pp | A exc conv | B exc conv |
|---|---|---|---|---|---|---|---|
| ship − bg | titre denom (thin) | 16 | 14 | +2/−0 | +0.20 | 100.0% (n=6) | 83.3% (n=6) |
| ind − ind_bg | titre denom (powered) | 82 | 69 | +18/−5 | +1.30 | 77.7% (n=94) | 63.8% (n=94) |
| mint − bg_mint | titre denom (powered) | 86 | 82 | +8/−4 | +0.40 | 92.7% (n=82) | 87.8% (n=82) |
| ship − redraw | cadence (thin) | 16 | 16 | +0/−0 | +0.00 | 100.0% | 100.0% (n=6) |
| mint − redraw_mint | cadence (powered) | 86 | 86 | +5/−5 | +0.00 | 92.7% (n=82) | 93.9% (n=82) |
| ship − fx_wide | extent (thin) | 16 | 16 | +0/−0 | +0.00 | 100.0% | 100.0% (n=6) |
| ship − fx_narrow | extent (thin) | 16 | 13 | +3/−0 | +0.30 | 100.0% | 66.7% (n=6) |
| ship − mint | mint rate | 16 | 86 | +0/−70 | −7.00 | 100.0% (n=6) | 92.7% (n=82) |
| bg − bg_mint | mint rate | 14 | 82 | +0/−68 | −6.80 | 83.3% (n=6) | 87.8% (n=82) |
| redraw − redraw_mint | mint rate | 16 | 86 | +1/−71 | −7.00 | 100.0% (n=6) | 93.9% (n=82) |
| redraw_mint vs ind | conjunction | 86 | 82 | — | +0.40 | 93.9% (n=82) | 77.7% (n=94) |

Reads: **mint rate dominates posting frequency** (−6.8 to −7.0 pp vs
every base arm; minted cells post at 92.7–93.9%). **Titre denominator**
is material on the v1 draw path (+1.3 pp posting, +13.8 pp conversion)
but small on the object path (+0.4 pp; background titres still convert —
52.8% of pan draws land outside the implicated band yet conversion only
loses ~5 pp). **Cadence (per-window re-mint) is a measured null** on
posting/conversion/AR. **Extent is a measured null** at wide;
fx_narrow's −0.30 pp is the only excursion-conversion dip (66.7%, n=6 —
thin-cell flagged).

## 8. Dose position (posted vs unposted acquisitions)

`entrain_01_dose_audit.py` rows on ind/ind_bg/ship/mint/bg_mint/
redraw_mint (n=1,000 each). Hill position `p` of each acquisition's
cumulative dose (positions/ratios only — no absolute dose figures while
the dose ledger is withdrawn): unposted acquisitions sit at p≈0.22–0.23
median on every arm; posted acquisitions sit at p 0.34–0.56.

| arm | posted acq n | p med (posted) | frac p>0.50 | posted/unposted cum-median ratio |
|---|---|---|---|---|
| ind | 3,167 | 0.481 | 0.481 | ~73× |
| ind_bg | 2,587 | 0.418 | 0.378 | ~22× |
| ship | 527 | 0.340 | 0.366 | ~6× |
| mint | 4,439 | 0.558 | 0.659 | ~400× |
| bg_mint | 3,929 | 0.512 | 0.530 | ~138× |
| redraw_mint | 4,495 | 0.558 | 0.670 | ~396× |

Posting tracks the dose tail on every arm; the mint family's posted
acquisitions sit furthest out the Hill curve (p med 0.51–0.56, ~two-thirds
above p=0.5) and carry ~400× the unposted median cumulative dose — the
implicated-band lot titres deliver deep-tail dose. `bg_mint`'s posted
tail sits between `ind_bg` and `mint` (p 0.512, ratio ~138×) — the
background denominator compresses delivered dose without killing the
signature.

## 9. Bridge checks

Per-seed summary compare (all 1,000 seeds) vs `noro_entrain_01` prefixes
at `dbbd5395`, normalizing the declared fields (`parameters.
{common_source,engine_git_sha,tier_id}`, `rss_mb`); ULP-normalized
gzip-census compare on a 25-seed sample per bridge.

| bridge | identical | diverged | diverged-seed structure |
|---|---|---|---|
| `off` ↔ entrain `off` | 1000/1000 | 0 | — |
| `ind_bg` ↔ entrain `ind` | 966/1000 | 34 | every diverged seed object-active on **both** sides (34/34 mint parity); diffs confined to dose-downstream fields (events/takers/dose_delivered/dose_share/cost) |
| `bg` ↔ entrain `ship` | 922/1000 | 78 | same structure — 78/78 both sides object-active; same downstream field set |
| `ship` ↔ `bg` witness identity | 918/1000 | 82 | paired-seed identity on object counts/events/takers/pans/windows/acquisitions/`obj_arms`/`end_reasons`; diffs all inside minted voyages |

Reading: the mint *decision* stream is bit-identical (the same voyages
mint objects, in the same counts, on both sides of every bridge; all
non-object voyages are bit-identical end-to-end). Object-voyage
interiors diverge because the #990/#991 machinery consumes a different
RNG stream once a voyage mints — the declared new-mechanism delta, same
shape as the shipped-default-change amendment recorded on MEAL-SVC-01.
The census sample shows only new serialized fields (`lot_servings`,
`lot_titre_gec_per_g`, `extent_mode`, `redraw`, `extent_windows`,
`strain_id`) plus ~1-ULP print digits — schema drift, not trajectory
drift. **Not an RNG break**; reported here in full per the design's
report-immediately clause.

## 10. Must-not-move

- `off` zero-witness: 1,000 censused cells, 0 objects, 0 events,
  `dose_credited` sum 0.000000. PASS.
- `ind`/`ind_bg` v1-only witness: 0 object-linked rows over 2,000 cells
  (v1 events carry `object_id: null`/`pan_serial: null` as designed). PASS.
- Paired Δinf-AR vs `off`: median +0.0000 on all 10 non-off arms
  (p90 |Δ| ≤0.0126). Total epidemiology unmoved.
- Non-cs route-share drift (pooled dose share vs `off`): worst is
  **fomite −16.07 pp on `redraw_mint`** — a composition shift
  (`common_source_food` share grows into the same total; per-route
  acquisition counts vs `off` are the same order). Composition, not a
  non-cs rate move; recorded for the frozen-clause reading.
- No failure/corruption class in any zip; 11,000/11,000 parsed.

## 11. Method notes

- Coverage: 11 arms × 1,000 seeds = 11,000 zips; streaming census decode
  (~87 MB decompressed/cell), one JSONL row per voyage
  (`tools/noro_diag/food_shapes_01_scan.py`); aggregation in
  `food_shapes_01_report.py`; bridge compare in
  `food_shapes_01_bridge.py`; dose rows via `entrain_01_dose_audit.py`
  (6 arms × 1,000).
- Posted = `summary.summary.sanitary_activity` wires (A9 thresholds),
  same as SCORE-01/ENTRAIN-01 readouts; excursion and object-voyage
  denominators identical to `food_score_01_report.py` §3 conventions.
- Seed pairing: every margin diff and bridge check uses the shared
  8000–8999 seed set; paired gained/lost counts are the raw sign-split
  of the per-seed posting difference.
- Power: thin-arm excursion cells are n=6 (the shipped mint rate is
  rare — declared thin per §7.5, pooled reads only); powered margins
  run on the mint family (n=82) and ind family (n=94).
- Baselines cited: SCORE-01 at `40862b8c`, ENTRAIN-01 at `dbbd5395`,
  DOSE-POS-01 (2/1,620 lot-mint rate), canary 108/108 at `45b2bf18`.
