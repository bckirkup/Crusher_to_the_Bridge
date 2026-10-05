# NORO-FOOD-02
**Date:** 2026-10-05
**Commit:** 8e8ebc79
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 8e8ebc79

Where the real posting anchor sits on the
`lot_event_probability` ladder — config-only rescale of the declared
provisioned-lot interval on the NORO-FOOD-01 image
(`picard-campaign@sha256:75931b1d`, engine `8e8ebc79`), 12 cells =
3 hulls × 4 rungs on the mid diagonal (`*_12d_scr` bp32.5c18.5,
nsf29, 288 epochs, dose_adjustment 7.57), 1,000 seeds per cell,
same seeds as FOOD-01 (exp 8000–8999, cls/spr 8105–9104) so every
voyage pairs free with FOOD-01 and the 02/03/04 baselines.
Prefix `campaign/noro_food_02/`, jobdef `picard-noro-food-02:2`,
manifest `noro_food_02_manifest.json`, design
`docs/norovirus/noro_food_02_sweep_design.md`. Readout of record:
`docs/norovirus/noro_food_02_readout.md`.

Measured:

- **Excursion share tracks E.** Lot-voyage counts 8/9/18–19/41 per
  1,000 at L1–L4 (E = 0.43/0.85/1.70/4.25%) — identical counts across
  hulls at the same rung (same-seed Bernoulli stream); every lot
  voyage converts to ≥1 `common_source_food` infection; no rung's
  excursion share ≫ its E. Handler/diner arms untouched and firing;
  handler/diner-only excursions persist at 1–11 per 1,000 at L1.
- **Anchor located at L1–L2.** Posted share (Wilson 95%), paired vs
  the matching 02/03/04 baseline (1,000 pairs/cell):
  exp L1 1.30% [0.76,2.21] → L4 3.80% [2.78,5.17] (baseline 0.70%);
  cls L1 0.70% [0.34,1.44] → L4 2.50% [1.70,3.66] (baseline 0.50%);
  spr L1/L2 both 0.30% [0.10,0.88], L3 0.60% [0.28,1.30],
  L4 1.20% [0.69,2.09] (baseline 0.00%). The real ~0.3–0.5% band
  sits at E ≲ 0.4–0.9% per voyage — roughly 10–20× below the
  shipped U[0.02,0.15] mean. exp's mid-diagonal baseline (0.70%)
  already overtops the band; on cls, L1's CI touches it; on spr —
  the cleanest read, baseline 0.0% — L1–L2 land inside it. The
  shipped interval remains declared (unfitted) — this is the
  measured location of the anchor on its ladder, not a defect.
- **Posting gain ≈ linear in E** through FOOD-01's ~43%
  excursion→posting conversion: predicted +0.2/0.4/0.7/1.8pp at the
  mid diagonal; observed exp +0.6/+0.7/+1.3/+3.1pp, cls
  +0.2/+0.4/+0.6/+2.0pp, spr +0.3/+0.3/+0.6/+1.2pp (gained/lost
  exp 6/0…31/0, cls 3/1…22/2, spr 3/0…12/0).
- **Onset signature survives at L1**: exp excursion burst12 med 0.43
  (3/9 >0.5 vs 0/170 ordinary); cls 0.16 vs 0.12 (1/12 over the bar);
  spr 0.115 ≈ background (invisible, consistent with FOOD-01).
- **cs_food count share linear in E**: exp 0.73→3.73%, cls
  0.20→1.12%, spr 0.12→0.59% at L1–L4 (FOOD-01: 6.6–8.9% /
  1.2–2.5% at E=8.5%). Per-excursion share E-independent.
- **Residual floor ≈ baseline**: handler/diner-only excursions at L1
  (exp 1, cls 4, spr 11 per 1,000) produced zero postings — a zeroed
  lot arm leaves the baseline floor, not a mechanism contribution.

No engine or constant changes; the sweep is pure
`config_overrides` on the same image and seed sets.
