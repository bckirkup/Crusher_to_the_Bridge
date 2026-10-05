# NORO-MEGA-IMPACT-01
**Date:** 2026-10-05
**Commit:** 7e1b54bc
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 7e1b54bc (fleet arms A1/A2/A3/a1_bp40c30); A0 baseline at `1e158d47` (existing NORO-MEGA-01 zips re-read)

Fleet readout of the 2×2 caregiver×food mechanism-attribution
factorial on `fl_mega_12d_scr` (posting wires: 147 pax / 63 crew at
3% of complement). 618/618 cells SUCCEEDED on
`picard-campaign-queue`, image `campaign-7e1b54bc`
(sha256:60793dd3…, `--payload lean`, 6144 MB/child), jobdef
`picard-noro-mega-impact-01:6`; 926 zips read via
`tools/noro_diag/mega_impact_fleet_readout.py`. Readout of record:
`docs/norovirus/noro_mega_impact_01_readout.md`.

Measured:

- **0/926 voyages post to VSP** on every mechanism combination.
  Food lifts only the tail: paired A1-vs-A0 medians are identical
  (56 pax / 18 crew reports), p90 deltas +9/+5, max reach
  0.746→**0.810** of the crew wire — the first ≥80% voyage on mega
  (seed 8119, a `common_source_food` excursion). Posting
  transitions: +0/−0.
- **Caregiver is the mega report channel**: 87.9% of A1 reports via
  the caregiver stamp (92.3% on bp40c30); removing it costs ~25%
  pax / ~39% crew reports and collapses detection 15/150→5/150.
  Caregiver share of aboard acquisitions stays 3.4–3.7% (under the
  design's >10% trigger) — it is a report channel, not a
  transmission route.
- **The infected→ill rung is hull-invariant**: pooled ill/inf
  0.173–0.187 on all five arms reproduces CHANNEL-03's
  symptomatic-course gap (0.17–0.41) at 7,000-agent scale. rep/ill
  0.67–0.72 caregiver-on vs 0.50–0.52 off.
- **Excursion tail fires at the same ~9.7% voyage rate as FOOD-01**
  (28/288 on A1, 643 cs_food infections) but is diluted at mega
  scale: excursion-voyage burst12 med 0.185 = background; the
  point-source signature resolves only on the expedition hull
  (FOOD-01). Every arm is a ramp clipped at epoch 287 (~94% still
  climbing).
- **bp40c30 lifts the curve, not the shape**: med ratios +3–4pp,
  detection 36%, max 0.857 — still 0 posts.
- **Lean payload memory quote held at fleet scale**: peak RSS med
  ~4.2 GB, max 4,355 MB (a1_bp40c30) vs the 6144 MB quote.

Hypothesis (not measured): lifting the infected→ill draw into its
declared band plausibly posts the median mega voyage (~3–4×
reports); the excursion-generator ceiling on mega is event
magnitude (≤65 inf/event vs a 63/147 wire), not event rate.

No constants fitted; no engine changes in this stage.
