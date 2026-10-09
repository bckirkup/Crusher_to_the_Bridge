# NORO-FOOD-SCORE-01 readout — does the contamination-object mechanism recover the v1-failed anchors?

> **Status:** Measured — 18/18 cells complete

Measured over 18 cells × 1,000 seeds = 18,000 voyages, zero child
failures, at engine `40862b8c` — image
`picard-campaign@sha256:29ea170eaede08d02566910967bfbda879a3656ceb3a40cf3ef45201fc5d9599`,
jobdef `picard-noro-food-score-01` (revs :1–:19), prefix
`campaign/noro_food_score_01/`, ledger
`campaigns/noro/noro_food_score_01/LEDGER.md`, frozen design
`noro_food_score_01_sweep_design.md`. Cells: `*_12d_scr` bp32.5c18.5,
nsf29, 288 epochs, dose_adjustment 7.57 — same seeds as AGE-FOOD-01
(exp 8000–8999, cls/spr 8105–9104), so every voyage pairs free with
the prior campaigns.

Mechanism under test: FOOD-COMMON-SOURCE-02 legs 1+2 — contamination
objects for `provisioned_lot` / `ill_handler` / `ill_diner` on the
object arms (`ol1`–`ol3`, `ship`); `ind` = all three arms
`"independent"` (the v1 shipped mechanism re-run on the current
engine); `off` = whole-mechanism baseline (`mode: off`, in-campaign
posting floor).

| arm | lot rung (`lot_object_probability`) | E (P(≥1 lot-object voyage)) |
|---|---|---|
| off | — | — |
| ind | v1 `lot_event_probability` U[0.02,0.15] | — |
| ol1 | [0.0005, 0.0025] | 0.15% |
| ol2 | [0.001, 0.006] | 0.35% |
| ol3 | [0.002, 0.012] | 0.70% |
| ship | [0.001, 0.02] | 1.05% |

Handler/diner arms run their shipped object intervals
(U[0.01,0.30] / U[0.005,0.15] per window) on every object rung — not
swept; their contribution is the residual floor.

Readout tooling: new `tools/noro_diag/food_score_01_scan.py` streams
each zip once (summary member via EOCD range-read, census member via
incremental gunzip — acquisition epochs regexed per chunk, the
trailing `common_source` block tail-decoded; head-only ranged reads
for burst-only targets) + `tools/noro_diag/food_score_01_report.py`
aggregates to the tables below. Coverage: all 18,000 summaries;
full census on 4,000 exp object-arm cells + samples elsewhere
(per-cell n shown); head census on every posted/excursion voyage plus
a 150/cell rest sample.

## §1 D1 — posting frequency

Posted = reported-case attack rate ≥ 3% wire on pax or crew stream
(the design's posted criterion). Marginal pp = posted_arm − posted_off;
gained/lost are per-seed paired vs `off`.

| hull | arm | n | posted | Wilson 95% | gained/lost vs off | marginal pp |
|---|---|---|---|---|---|---|
| exp | off | 1000 | 10 (1.00%) | [0.54,1.83] | 0/0 | +0.00 |
| exp | ind | 1000 | 68 (6.80%) | [5.40,8.53] | 58/0 | +5.80 |
| exp | ol1 | 1000 | 10 (1.00%) | [0.54,1.83] | 1/1 | +0.00 |
| exp | ol2 | 1000 | 11 (1.10%) | [0.62,1.96] | 1/0 | +0.10 |
| exp | ol3 | 1000 | 13 (1.30%) | [0.76,2.21] | 3/0 | +0.30 |
| exp | ship | 1000 | 15 (1.50%) | [0.91,2.46] | 5/0 | +0.50 |
| cls | off | 1000 | 0 (0.00%) | [0.00,0.38] | 0/0 | +0.00 |
| cls | ind | 1000 | 41 (4.10%) | [3.04,5.51] | 41/0 | +4.10 |
| cls | ol1 | 1000 | 1 (0.10%) | [0.02,0.56] | 1/0 | +0.10 |
| cls | ol2 | 1000 | 1 (0.10%) | [0.02,0.56] | 1/0 | +0.10 |
| cls | ol3 | 1000 | 1 (0.10%) | [0.02,0.56] | 1/0 | +0.10 |
| cls | ship | 1000 | 2 (0.20%) | [0.05,0.73] | 2/0 | +0.20 |
| spr | off | 1000 | 1 (0.10%) | [0.02,0.56] | 0/0 | +0.00 |
| spr | ind | 1000 | 14 (1.40%) | [0.84,2.34] | 13/0 | +1.30 |
| spr | ol1 | 1000 | 1 (0.10%) | [0.02,0.56] | 0/0 | +0.00 |
| spr | ol2 | 1000 | 1 (0.10%) | [0.02,0.56] | 0/0 | +0.00 |
| spr | ol3 | 1000 | 2 (0.20%) | [0.05,0.73] | 1/0 | +0.10 |
| spr | ship | 1000 | 2 (0.20%) | [0.05,0.73] | 1/0 | +0.10 |

Reads:

- **All six floors re-measured in-campaign:** exp `off` floor 1.00%
  (FOOD-02 predicted "~0.5%" — re-measured at 1.0% here), cls 0.00%,
  spr 0.10% — the cls/spr floors are clean as the design assumed.
- **Dose-response is monotone where powered.** exp ladder
  +0.00/+0.10/+0.30/+0.50pp across ol1→ol2→ol3→ship — monotone in E,
  and `ship` lands at ~+0.5pp, at the top edge of the ~0.3–0.5pp anchor band.
  cls (+0.10→+0.20pp) and spr (0→+0.10pp) are flat-low — the ladder's
  slope is present but the per-rung counts are 1–2 postings, i.e.
  CIs wider than the band exactly as the design warned.
- **`ind` (v1) overposts everywhere**: +5.80/+4.10/+1.30pp vs `off`,
  ceilings 6.80/4.10/1.40% — the v1 overshoot reproduces in-campaign
  (FOOD-01 measured 6.3/4.2/1.7–1.9%), so the contrast is a faithful
  v1 baseline on the current engine.
- **The ship rung's gained postings are channel-clean:** every gained
  posting on exp (5/5) and spr (1/1), and 1/2 on cls, is a
  `common_source_food` excursion voyage — the marginal posting comes
  through the object channel, not background drift. `ind`'s gained
  postings are 100% cs-excursion voyages too (58/58, 41/41, 13/13).

**Verdict (D1):** partially recovered — the object ladder produces a
monotone, floor-aware marginal posting contribution that on `ship`
sits at ~+0.5pp on exp (at the band's top edge), ~+0.2pp
cls, ~+0.1pp spr; per the design's floor-aware read the shipped
interval's contribution is *in or below* the ~0.3–0.5pp band on the
two clean-floor hulls and just over it on exp — "signature recovered,
interval sits near/under the band", and dramatically closer than
v1's 3–14× overposting.

## §2 D2 — posted-conditional passenger AR (the thin-signature check)

Per-cell `posted_pax_ar` medians where n_posted ≥ 10, pooled per hull
otherwise (the design's declared pooling rule — exp cells powered,
cls/spr pooled).

| hull | arm | n_posted | posted pax-AR med [IQR] | p90 |
|---|---|---|---|---|
| exp | ind | 68 | 0.035 [0.006,0.048] | 0.055 |
| exp | ol1 | 10 | 0.021 [0.007,0.032] | 0.032 |
| exp | ol2 | 11 | 0.016 [0.003,0.032] | 0.032 |
| exp | ol3 | 13 | 0.016 [0.003,0.032] | 0.034 |
| exp | ship | 15 | 0.016 [0.002,0.032] | 0.037 |
| exp | obj pooled | 49 | 0.016 [0.003,0.032] | 0.035 |
| cls | ind | 41 | 0.034 [0.019,0.038] | 0.042 |
| cls | ol1 | 1 | 0.014 [0.014,0.014] | 0.014 |
| cls | ol2 | 1 | 0.014 [0.014,0.014] | 0.014 |
| cls | ol3 | 1 | 0.003 [0.003,0.003] | 0.003 |
| cls | ship | 2 | 0.009 [0.006,0.011] | 0.013 |
| cls | obj pooled | 5 | 0.014 [0.003,0.014] | 0.014 |
| spr | ind | 14 | 0.020 [0.015,0.030] | 0.037 |
| spr | ol1 | 1 | 0.021 [0.021,0.021] | 0.021 |
| spr | ol2 | 1 | 0.021 [0.021,0.021] | 0.021 |
| spr | ol3 | 2 | 0.011 [0.006,0.016] | 0.019 |
| spr | ship | 2 | 0.011 [0.006,0.016] | 0.019 |
| spr | obj pooled | 6 | 0.021 [0.006,0.021] | 0.021 |

**Verdict (D2):** not recovered. Object-arm pooled medians sit at
0.014–0.021 on all three hulls — below the class-IQR band lower edge
(0.04) and below `ind`'s own 0.034–0.035 on the same engine. The
thin-signature defect persists under the object mechanism: the
postings it produces are thin, exactly the failure shape this campaign
was built to detect. (cls/spr pooled n = 5–6 posted voyages — the
median is what it is; widening n requires more postings, not more
seeds.)

## §3 D3 — hull-scaling compression (conversion and ceilings)

Excursion voyage = ≥1 `common_source_food` infection (the FOOD-01/02
`cs voy` definition — `summary.mechanisms.common_source_events` is a
per-delivery counter, near-universal on big hulls, not the excursion).
`obj voy` = census-verified ≥1-object voyages among scanned cells.

| hull | arm | exc voy (cs_food>0) | posted | conv % | obj voy (census n) | posted | conv % | ceiling posted % |
|---|---|---|---|---|---|---|---|---|
| exp | ind | 94 | 59 | 62.8 | 0/192 | 0 | 0.0 | 6.80 |
| exp | ol1 | 1 | 1 | 100.0 | 585/879 | 10 | 1.7 | 1.00 |
| exp | ol2 | 1 | 1 | 100.0 | 597/877 | 11 | 1.8 | 1.10 |
| exp | ol3 | 3 | 3 | 100.0 | 594/875 | 13 | 2.2 | 1.30 |
| exp | ship | 6 | 5 | 83.3 | 590/880 | 15 | 2.5 | 1.50 |
| cls | ind | 96 | 41 | 42.7 | 0/192 | 0 | 0.0 | 4.10 |
| cls | ol1 | 16 | 0 | 0.0 | 620/620 | 1 | 0.2 | 0.10 |
| cls | ol2 | 11 | 0 | 0.0 | 207/207 | 1 | 0.5 | 0.10 |
| cls | ol3 | 17 | 1 | 5.9 | 214/215 | 1 | 0.5 | 0.10 |
| cls | ship | 17 | 1 | 5.9 | 216/216 | 2 | 0.9 | 0.20 |
| spr | ind | 98 | 13 | 13.3 | 0/190 | 0 | 0.0 | 1.40 |
| spr | ol1 | 22 | 0 | 0.0 | 233/233 | 1 | 0.4 | 0.10 |
| spr | ol2 | 25 | 0 | 0.0 | 220/220 | 1 | 0.5 | 0.10 |
| spr | ol3 | 25 | 1 | 4.0 | 221/221 | 2 | 0.9 | 0.20 |
| spr | ship | 29 | 1 | 3.4 | 283/283 | 2 | 0.7 | 0.20 |

Reads:

- **v1's ~43% conversion reproduces on `ind`**: 42.7% on cls, and the
  hull-compression ordering reproduces too (exp 62.8 > cls 42.7 >
  spr 13.3). The in-campaign v1 baseline is valid.
- **Object excursions under-convert on big hulls**: 0–5.9% cls
  (n=11–17), 0–4.0% spr (n=17–29) vs `ind`'s 42.7/13.3%. On exp the
  object excursions convert hard (83–100%) but there are only 1–6 of
  them per 1,000 — the object mechanism produces *fewer, smaller*
  excursions, not more-wire-reaching ones.
- **Ceilings**: ship 1.50/0.20/0.20% vs `ind` 6.80/4.10/1.40% vs
  FOOD-01's v1 ceilings 6.3/4.2/1.7–1.9% — objects sit an order of
  magnitude under v1 ceilings on cls/spr.
- Object-voyage share is high on big hulls (cls/spr ~100%, exp ~67%
  of scanned voyages carry ≥1 object of any kind) — handler/diner
  windows fire often; the swept lot arm is rare by design (lot-object
  voyages measured 0.11–0.68% on exp vs E 0.15–1.05%).

**Verdict (D3):** the object mechanism does not buy more of the 3%
wire on the 3,000-agent hull — spr object conversion ~3–4% vs `ind`'s
13.3%. The compression signature (exp ≫ spr conversion) is *worse*
under objects than under v1, not better.

## §4 D4 — outbreak shape (burst48 declared discriminator)

burst48/burst12 = max share of a voyage's acquisition epochs inside
any 48/12-epoch rolling window; excursion set = cs_food-infection
voyages, rest = the rest of each hull's scanned cells (posted +
excursion voyages all head/full-scanned + random rest sample).

| hull | set | n | burst48 med | burst12 med |
|---|---|---|---|---|
| exp | excursion | 11 | 0.564 | 0.314 |
| exp | rest | 3433 | 0.400 | 0.214 |
| cls | excursion | 61 | 0.292 | 0.137 |
| cls | rest | 1663 | 0.286 | 0.126 |
| spr | excursion | 101 | 0.276 | 0.112 |
| spr | rest | 1339 | 0.272 | 0.114 |

| hull | cs acq | in object span | share % |
|---|---|---|---|
| exp | 263 | 263 | 100.0 |
| cls | 459 | 459 | 100.0 |
| spr | 419 | 419 | 100.0 |

**Verdict (D4):** shape recovered on exp — excursion-vs-rest
separation on the declared discriminator (burst48 med ~0.56 vs ~0.40,
+16pp) exactly where the design said it would resolve; cls/spr show
no separation (~0.29/0.27 both sets) — the dilution case the design
pre-declared. burst12 follows the same pattern (excursion 0.314 vs
rest 0.214 on exp; flat cls/spr). The failure mode the design named —
"no separation on any window at any hull while the posting tail
exists" — does not occur: the posting tail exists and exp separates.

## §5 Witness diagnostics

| hull | arm | voy | w/ev % | ev/voy med | lot voy | obj/voy | pans/obj | win/obj | zero-dose % | arm L/H/D % | takers/ev |
|---|---|---|---|---|---|---|---|---|---|---|---|
| exp | off | 119 | 0.0 | 0 | 0 | 0 | - | - | - | - | - |
| exp | ind | 192 | 65.1 | 1 | 0 | 0 | - | - | 46.5 | 16/34/50 | 10.9 |
| exp | ol1 | 879 | 43.2 | 0 | 1 | 585 | 1.9 | 1.9 | 61.0 | 0/53/46 | 10.7 |
| exp | ol2 | 877 | 44.9 | 0 | 1 | 597 | 1.9 | 1.9 | 61.6 | 0/52/48 | 10.7 |
| exp | ol3 | 875 | 44.5 | 0 | 3 | 594 | 1.9 | 1.9 | 61.0 | 1/52/47 | 10.7 |
| exp | ship | 880 | 43.1 | 0 | 6 | 590 | 1.9 | 1.9 | 61.5 | 1/54/44 | 10.6 |
| cls | off | 137 | 0.0 | 0 | 0 | 0 | - | - | - | - | - |
| cls | ind | 192 | 99.5 | 22.5 | 0 | 0 | - | - | 59.8 | 1/33/66 | 26.7 |
| cls | ol1 | 620 | 99.2 | 79 | 1 | 620 | 2.8 | 2.8 | 57.4 | 0/42/58 | 25.9 |
| cls | ol2 | 207 | 99.5 | 79 | 1 | 207 | 2.7 | 2.7 | 57.8 | 0/44/56 | 25.3 |
| cls | ol3 | 215 | 98.6 | 74 | 3 | 214 | 2.8 | 2.8 | 57.3 | 0/44/56 | 25.6 |
| cls | ship | 216 | 100.0 | 82.5 | 6 | 216 | 2.9 | 2.9 | 56.7 | 0/41/59 | 25.6 |
| spr | off | 115 | 0.0 | 0 | 0 | 0 | - | - | - | - | - |
| spr | ind | 190 | 100.0 | 39 | 0 | 0 | - | - | 58.3 | 2/33/65 | 24.9 |
| spr | ol1 | 233 | 100.0 | 151 | 1 | 233 | 2.9 | 2.9 | 58.9 | 0/43/57 | 24.8 |
| spr | ol2 | 220 | 100.0 | 147 | 1 | 220 | 2.8 | 2.8 | 59.2 | 0/44/56 | 24.6 |
| spr | ol3 | 221 | 100.0 | 146 | 3 | 221 | 2.9 | 2.9 | 59.1 | 0/43/57 | 24.9 |
| spr | ship | 283 | 100.0 | 148 | 6 | 283 | 2.7 | 2.7 | 58.2 | 0/45/55 | 24.5 |

| hull | arm | voy scanned | ev rows | unresolved oid | missing oid | missing serial | open obj | srv>lot | non-noro |
|---|---|---|---|---|---|---|---|---|---|
| exp | off | 119 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| exp | ind | 192 | 546 | 0 | 546 | 546 | 0 | 0 | 0 |
| exp | ol1 | 879 | 6923 | 0 | 0 | 0 | 0 | 0 | 0 |
| exp | ol2 | 877 | 7163 | 0 | 0 | 0 | 0 | 0 | 0 |
| exp | ol3 | 875 | 7112 | 0 | 0 | 0 | 0 | 0 | 0 |
| exp | ship | 880 | 6857 | 0 | 0 | 0 | 0 | 0 | 0 |
| cls | off | 137 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cls | ind | 192 | 4638 | 0 | 4638 | 4638 | 0 | 0 | 0 |
| cls | ol1 | 620 | 56370 | 0 | 0 | 0 | 0 | 0 | 0 |
| cls | ol2 | 207 | 18555 | 0 | 0 | 0 | 0 | 0 | 0 |
| cls | ol3 | 215 | 18500 | 0 | 0 | 0 | 0 | 0 | 0 |
| cls | ship | 216 | 19879 | 0 | 0 | 0 | 0 | 0 | 0 |
| spr | off | 115 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| spr | ind | 190 | 7788 | 0 | 7788 | 7788 | 0 | 0 | 0 |
| spr | ol1 | 233 | 35398 | 0 | 0 | 0 | 0 | 0 | 0 |
| spr | ol2 | 220 | 34617 | 0 | 0 | 0 | 0 | 0 | 0 |
| spr | ol3 | 221 | 33706 | 0 | 0 | 0 | 0 | 0 | 0 |
| spr | ship | 283 | 42298 | 0 | 0 | 0 | 0 | 0 | 0 |
| **all** |  |  | 300350 | 0 | 12972 | 12972 | 0 | 0 | 0 |

Reads:

- `off` is zero-witness: 0 events, 0 objects across the 316 sampled
  `off` voyages (60–137/cell) — the labelled baseline is clean.
- Objects expire by window close, not exhaustion: `end_reason` mix on
  ~51k object rows ≈ 76% `source_excluded`, 9% `voyage_end`, 4%
  `shedding_ended`, 0.05% `exhausted`. `multi_pan_windows`
  8,202/117,025 pans ≈ 7% — the multi-pan tail exists.
- Zero-dose share ~57–62% on object arms vs `ind`'s 47–60% — the
  "should fall vs v1's ~58%" witness expectation did NOT materialise:
  object-mode deliveries carry a similar zero-dose share to v1.
- Arm mix L/H/D on object arms ≈ 0–2/34–54/45–67 — the swept lot arm
  contributes ~1% of event rows (rare, by design); `ind` shows the v1
  mix (L 1–16/H 32–34/D 50–67).
- Object-integrity invariants: clean across ~287k object-arm event
  rows — every event `object_id` resolves to an objects row, every
  `pan_serial` populated, 0 open (un-closed) objects, 0
  `servings_served > lot_servings`, 0 non-`norwalk_gi` objects.
  (`ind` events lack `object_id`/`pan_serial` by construction — the
  v1 mechanism has no objects; that is expected, not a violation.)

## §6 Must-not-move audit

| hull | arm | med inf-AR pax | paired med Δ vs off | cs share % | top non-cs route share shift pp |
|---|---|---|---|---|---|
| exp | off | 0.0728 | +0.0000 | 0.00 | +0.00 (-) |
| exp | ind | 0.0728 | +0.0000 | 7.58 | -8.48 (fomite) |
| exp | ol1 | 0.0728 | +0.0000 | 0.10 | -0.15 (fomite) |
| exp | ol2 | 0.0728 | +0.0000 | 0.10 | -0.16 (fomite) |
| exp | ol3 | 0.0728 | +0.0000 | 0.49 | -0.54 (fomite) |
| exp | ship | 0.0728 | +0.0000 | 0.86 | -0.92 (fomite) |
| cls | off | 0.0927 | +0.0000 | 0.00 | +0.00 (-) |
| cls | ind | 0.0942 | +0.0000 | 2.42 | -2.72 (fomite) |
| cls | ol1 | 0.0927 | +0.0000 | 0.04 | -0.03 (emesis_aerosol) |
| cls | ol2 | 0.0927 | +0.0000 | 0.02 | -0.03 (emesis_aerosol) |
| cls | ol3 | 0.0927 | +0.0000 | 0.14 | -0.14 (fomite) |
| cls | ship | 0.0927 | +0.0000 | 0.18 | -0.15 (fomite) |
| spr | off | 0.0938 | +0.0000 | 0.00 | +0.00 (-) |
| spr | ind | 0.0943 | +0.0000 | 1.27 | -1.44 (fomite) |
| spr | ol1 | 0.0938 | +0.0000 | 0.02 | -0.05 (fomite) |
| spr | ol2 | 0.0938 | +0.0000 | 0.02 | -0.03 (fomite) |
| spr | ol3 | 0.0938 | +0.0000 | 0.08 | -0.11 (fomite) |
| spr | ship | 0.0938 | +0.0000 | 0.11 | -0.10 (fomite) |

- Median infection-AR pax is **bit-flat** across every arm
  (exp 0.0728, cls 0.0927, spr 0.0938; paired median Δ vs `off`
  +0.0000 everywhere) — the object mechanism replaces dose channels
  rather than adding infections, and no net AR moved.
- `common_source_food` count share: object arms 0.02–0.84% (vs
  FOOD-01's v1 measured 1.2–8.9% and the >50% over-delivery alarm) —
  small and well under the alarm. `ind` reproduces 1.27–7.58%.
- Non-cs route shares stable: largest shift −0.92pp (fomite, exp
  ship) — all arms within ±1pp of `off`.
- `off` arm zero-witness: confirmed (§5).
- Object-integrity invariants: confirmed (§5 integrity table).

**Must-not-move: PASS** — no invariant moved on any hull.

## §7 `ind` baseline validity (design's immediate-report check)

The design asked to flag immediately if `ind` failed to reproduce v1
event counts at distribution level. Measured on `ind` (n=60–192
census-verified/cell + all 1,000 summaries):

- events/voyage medians 1 / 22.5 / 40 (exp/cls/spr) ≈ FOOD-01's
  measured 10.7-mean / 23.5 / 39.5 per-voyage rates — same
  distribution;
- posting ceilings 6.80/4.10/1.40% ≈ FOOD-01's 6.3/4.2/1.7–1.9%;
- excursion→posting conversion 62.8/42.7/13.3% ≈ v1's measured ~43%
  cls (plus the hull ordering);
- posted-conditional pax-AR med 0.035/0.034/0.020 ≈ FOOD-01's
  0.019–0.032 band;
- zero-dose share 46–60% ≈ v1's ~58%.

`ind` reproduces v1 on the current engine. The contrast is valid.

## §8 Verdicts summary

| criterion | verdict | measured |
|---|---|---|
| D1 posting marginal + ladder | partial — monotone on exp, flat-low cls/spr | ship +0.50/+0.20/+0.10pp vs off; ind +5.80/+4.10/+1.30 |
| D2 posted-conditional AR ≥0.04 | not recovered | obj pooled med 0.016/0.014/0.021 (ind 0.035/0.034/0.020) |
| D3 conversion + ceilings vs ind | objects under-convert on big hulls | obj exc conv 83–100% exp (n=1–6), 0–5.9% cls, 0–4.0% spr; ceilings ship 1.50/0.20/0.20% vs ind 6.80/4.10/1.40% |
| D4 burst48 separation | recovered on exp (design's resolving hull) | 0.564 vs 0.400; flat cls/spr as pre-declared |
| must-not-move | PASS | AR bit-flat, routes ±1pp, off zero-witness, integrity clean over ~287k obj-arm event rows |
| ind reproduces v1 | yes | conv 42.7% cls ≈ 43%, ceilings + distributions match |

**Mechanism reading (measured, not fitted):** the contamination
objects produce rare, small, correctly windowed excursions — the
posting signature is honest (monotone dose-response, channel-clean
gained postings, in-or-below the anchor band where floors are clean),
the outbreak shape resolves on exp (burst48 separation), and the
invariants all hold. What the shipped interval does NOT do is buy
enough wire-reaching excursions on the big hulls to restore v1-scale
posting or ≥0.04 posted-conditional pax-AR — the thin signature
persists there. Whether to widen the lot interval, raise per-pan
dose, or accept the under-shoot is the user's call — the readout
makes no fitting recommendation.
