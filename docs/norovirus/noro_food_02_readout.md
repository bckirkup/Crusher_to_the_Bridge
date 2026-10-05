# NORO-FOOD-02 readout — `lot_event_probability` sweep, where does the real posting anchor sit?

> **Status:** Measured — 12/12 cells complete

Measured over 12 cells × 1,000 seeds = 12,000 voyages, zero child
failures, at engine
`8e8ebc79` — config-only sweep on the NORO-FOOD-01 image
`picard-campaign@sha256:75931b1d…`, jobdef `picard-noro-food-02:2`,
prefix `campaign/noro_food_02/`, manifest
`noro_food_02_manifest.json`, design `noro_food_02_sweep_design.md`.
Cells: the mid-diagonal only (`*_12d_scr` bp32.5c18.5, nsf29, 288
epochs, dose_adjustment 7.57), 1,000 seeds per cell — same seeds as
FOOD-01 (exp 8000–8999, cls/spr 8105–9104) so every voyage pairs free
with FOOD-01 and the 02/03/04 baselines.

Sweep axis: `transmission.common_source.lot_event_probability` —
one Bernoulli draw per voyage → at most one scheduled lot per voyage →
P(excursion voyage) ≈ interval mean E. `food_safety_posture` 1.0 and
`lot_posture_coupling` false throughout (posture multiplies only the
handler/diner per-window rates; the lot arm is decoupled by design).

| rung | interval | E |
|---|---|---|
| L1 | [0.001, 0.0075] | 0.425% |
| L2 | [0.002, 0.015] | 0.85% |
| L3 | [0.004, 0.030] | 1.70% |
| L4 | [0.010, 0.075] | 4.25% |
| FOOD-01 | [0.02, 0.15] (shipped) | 8.5% |

## 1. Dose-response — excursion share vs interval mean E

Full census reads (`tools/noro_diag/common_source_readout.py`).
`lot voy` = voyages with ≥1 provisioned-lot event row; `cs voy` =
voyages with ≥1 `common_source_food` infection (excursion voyages);
`no-lot` = excursion voyages whose cs infections all came through the
unswept handler/diner arms; `cs_food share` = share of all infections
dominant-route-attributed `common_source_food` (FOOD-01-comparable
count share; dose-credit share is smaller and also linear in E).

| hull | rung | E | lot voy /1000 | cs voy /1000 | no-lot | events | arm L/H/D % | takers/ev | zero-dose | cs_food share |
|---|---|---|---|---|---|---|---|---|---|---|
| exp | L1 | 0.43% | 8 | 9 | 1 | 2,282 | 1.6/43.5/54.9 | 10.7 | 1,331 | 0.73% |
| exp | L2 | 0.85% | 9 | 10 | 1 | 2,283 | 1.8/42.9/55.3 | 10.7 | 1,324 | 0.81% |
| exp | L3 | 1.70% | 18 | 19 | 1 | 2,347 | 3.7/42.6/53.8 | 10.6 | 1,332 | 1.68% |
| exp | L4 | 4.25% | 41 | 42 | 1 | 2,504 | 7.9/40.1/52.0 | 10.6 | 1,368 | 3.73% |
| exp | F01 | 8.5% | ~87 | 94 | ~7 | — | — | 10.7 | — | 6.6–8.9% |
| cls | L1 | 0.43% | 8 | 12 | 4 | 23,549 | 0.2/32.0/67.8 | 26.5 | 14,023 | 0.20% |
| cls | L2 | 0.85% | 9 | 11 | 2 | 23,677 | 0.2/32.0/67.8 | 26.5 | 14,030 | 0.23% |
| cls | L3 | 1.70% | 19 | 22 | 3 | 23,817 | 0.4/31.6/68.0 | 26.5 | 14,126 | 0.49% |
| cls | L4 | 4.25% | 41 | 45 | 4 | 23,829 | 0.9/31.9/67.3 | 26.4 | 14,090 | 1.12% |
| cls | F01 | 8.5% | ~87 | 97 | ~10 | — | — | 26.4 | — | 1.2–2.5% |
| spr | L1 | 0.43% | 8 | 19 | 11 | 39,172 | 0.1/33.8/66.1 | 25.3 | 23,491 | 0.12% |
| spr | L2 | 0.85% | 9 | 15 | 6 | 39,133 | 0.1/34.0/65.9 | 25.3 | 23,526 | 0.14% |
| spr | L3 | 1.70% | 19 | 28 | 9 | 39,415 | 0.2/33.8/65.9 | 25.2 | 23,541 | 0.26% |
| spr | L4 | 4.25% | 41 | 47 | 6 | 39,512 | 0.5/33.8/65.7 | 25.3 | 23,652 | 0.59% |
| spr | F01 | 8.5% | ~87 | 102 | ~15 | — | — | 25.2 | — | 1.2–2.5% |

Reads:

- **Lot-voyage share tracks E almost exactly** (L1–L4 ≈ 0.8/0.9/1.9/4.1%
  vs 0.43/0.85/1.70/4.25 — the small-sample upward drift at L1/L2 is
  binomial noise on ~10 draws; identical counts across hulls at the
  same rung confirm the same-seed Bernoulli stream). No rung's
  excursion share ≫ its E — the override is applied at the swept
  interval on every cell.
- **Every lot voyage converts to ≥1 cs infection** at every rung
  (cs_voy − lot_voy ≈ the no-lot residual). The excursion machinery is
  unchanged in kind; only its frequency moved.
- **Handler/diner arms are untouched and still fire**: arm mix is
  H/D-dominant on every rung; lot rows rise as a share of events only
  because lot count scales with E (L 0.2–8% of event rows).
- **cs_food count share is linear in E** (exp 0.73→3.73%, cls
  0.20→1.12%, spr 0.12→0.59% at L1–L4, vs FOOD-01's 6.6–8.9% /
  1.2–2.5% at E=8.5%) —
  the rung moves how often the excursion happens, not how big it is
  when it does (per-excursion share is E-independent: ~14–31% of an
  excursion voyage's infections).

## 2. Posting rate — paired vs NORO-OUTBREAK-02/03/04 (THE anchor readout)

`tools/noro_diag/outbreak_anchor_readout.py`, `--import-root` per
baseline campaign, same-seed pairing (1,000 pairs per cell). Real
posting anchor: ~0.3–0.5% per voyage.

| hull | rung | E | baseline posted | rung posted (Wilson 95%) | Δpp | gained/lost |
|---|---|---|---|---|---|---|
| exp | L1 | 0.43% | 0.70% | 1.30% [0.76, 2.21] | +0.6 | 6/0 |
| exp | L2 | 0.85% | 0.70% | 1.40% [0.84, 2.34] | +0.7 | 7/0 |
| exp | L3 | 1.70% | 0.70% | 2.00% [1.30, 3.07] | +1.3 | 13/0 |
| exp | L4 | 4.25% | 0.70% | 3.80% [2.78, 5.17] | +3.1 | 31/0 |
| exp | F01 | 8.5% | 0.70% | 6.8% [5.4, 8.5] | +6.1 | 61/0 |
| cls | L1 | 0.43% | 0.50% | 0.70% [0.34, 1.44] | +0.2 | 3/1 |
| cls | L2 | 0.85% | 0.50% | 0.90% [0.47, 1.70] | +0.4 | 5/1 |
| cls | L3 | 1.70% | 0.50% | 1.10% [0.62, 1.96] | +0.6 | 8/2 |
| cls | L4 | 4.25% | 0.50% | 2.50% [1.70, 3.66] | +2.0 | 22/2 |
| cls | F01 | 8.5% | 0.50% | 5.0% [3.8, 6.5] | +4.5 | 47/2 |
| spr | L1 | 0.43% | 0.00% | 0.30% [0.10, 0.88] | +0.3 | 3/0 |
| spr | L2 | 0.85% | 0.00% | 0.30% [0.10, 0.88] | +0.3 | 3/0 |
| spr | L3 | 1.70% | 0.00% | 0.60% [0.28, 1.30] | +0.6 | 6/0 |
| spr | L4 | 4.25% | 0.00% | 1.20% [0.69, 2.09] | +1.2 | 12/0 |
| spr | F01 | 8.5% | 0.00% | 2.0% [1.3, 3.1] | +2.0 | 20/0 |

Posting gain is ≈linear in E through the ~43% excursion→posting
conversion measured in FOOD-01 (predicted +0.2/0.4/0.7/1.8pp at the
mid diagonal; observed exp +0.6/+0.7/+1.3/+3.1, cls +0.2/+0.4/+0.6/+2.0,
spr +0.3/+0.3/+0.6/+1.2 — spr tracks prediction almost exactly; exp
rides higher because the same excursion is a bigger share of a
450-agent complement).

## 3. Onset re-check — burst12 on the anchor-nearest rung (L1)

`tools/noro_diag/onset_curve_readout.py`, stride-200 sample per cell
plus every excursion voyage forced into the read set
(`--also-seeds`). FOOD-01 baseline for comparison: burst12 med
~0.13–0.24, share >0.5 ≈ 0% of ordinary voyages; excursion subset med
0.36–0.45 on exp.

| cell | excursion n | burst12 med | >0.5 | rest n | burst12 med | >0.5 |
|---|---|---|---|---|---|---|
| exp L1 | 9 | 0.43 | 3/9 | 170 | 0.22 | 0/170 |
| cls L1 | 12 | 0.16 | 1/12 | 198 | 0.12 | 0/198 |
| spr L1 | 8 | 0.115 | 0/8 | 202 | 0.115 | 0/202 |

The point-source onset signature survives at the lowest rung: on exp,
a single scheduled lot still concentrates ~43% of a voyage's
acquisitions into the densest 12-epoch window (3/9 over the >0.5
point-source bar vs 0/170 ordinary). On cls the excursion elevates
burst12 (0.16 vs 0.12) without crossing the bar — hull-scale dilution,
same as FOOD-01. On spr the excursion is invisible in burst12 (0.115
≈ background), as FOOD-01 measured at E=8.5% — excursion voyages
still post (1 of the 3 L1 postings is a lot voyage).

## 4. Residual floor — what the unswept handler/diner arms leave at L1

The handler/diner arms are NOT swept (still at declared
U[0.005,0.10]/U[0.001,0.05] per window). At L1 they account for:

| hull | no-lot cs excursions /1000 | of which posted | lot voy posted | background posted (baseline) |
|---|---|---|---|---|
| exp | 1 | 0 | 5/8 | ~0.7% |
| cls | 4 | 0 | 3/8 | ~0.5% |
| spr | 11 | 0 | 1/8 | ~0.0% |

Handler/diner-only excursions persist at ~1–4 per 1,000 voyages but
none converted to a posting at L1 — the posting floor under a zeroed
lot arm is the baseline itself (0.5–0.7% on the mid diagonal), not a
mechanism contribution.

## 5. Verdict — where the real anchor sits

- On **spr** — the cleanest read, since its baseline posts 0.0% —
  L1 and L2 both land **0.30% [0.10, 0.88]**, inside the 0.3–0.5%
  band; L3 (0.60% [0.28, 1.30]) grazes the band's top edge; L4
  overposts at 1.20%.
- On **cls**, L1 (E≈0.43%) lands 0.70% [0.34, 1.44] — nearest
  above the band; its CI overlaps the band's top edge and its 0.50%
  baseline is already at the band's upper edge.
- On **exp**, even L1 sits at 1.30% [0.76, 2.21] — but the exp
  mid-diagonal *baseline* is already 0.70%, at/above the band, so no
  non-negative lot probability lands exp inside the band; the
  excess over the band on exp is dominated by the baseline, not the
  mechanism.
- **Answer**: the real ~0.3–0.5% posting anchor is consistent with a
  provisioned-lot event probability of **E ≲ 0.4–0.9% per voyage
  (L1–L2)** — roughly 10–20× lower than the shipped U[0.02,0.15]
  mean. The shipped interval remains a declared (unfitted) range;
  this is the measured location of the anchor on its ladder, not a
  defect. A posture sweep could not have reached this: the lot arm
  is decoupled from `food_safety_posture` by construction.
