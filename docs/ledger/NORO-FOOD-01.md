# NORO-FOOD-01
**Date:** 2026-10-05
**Commit:** 8e8ebc79
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 8e8ebc79

First fleet measurement of the FOOD-COMMON-SOURCE-01 mechanism
(synchronized common-source foodborne events; engine SHA `8e8ebc79`,
census-witness harvest shipped on main as #893's `common_source`
payload block), 9 cells × 1,000 seeds,
zero failures, prefix `campaign/noro_food_01/`, jobdef
`picard-noro-food-01:2` (image `campaign-8e8ebc79-food01`
@sha256:75931b1d — overlay on the prompt-pinned base digest, which
lacked the campaign entrypoint). Readout of record:
`docs/norovirus/noro_food_01_readout.md`.

Measured:

- **Excursion tail exists.** 873/9,000 voyages (9.4–10.3%, flat across
  all nine cells) carry `common_source_food` infections — essentially
  every voyage that schedules a provisioned lot converts (lot draw
  ~8.5%/voyage at the declared interval). Handler/diner arms convert a
  further ~10–12 voyages per cell without a lot.
- **Posting rate moves ~7–20× upward**, paired same-seed: 374 gained /
  8 lost postings across the 9 cells; posted share 0–0.8% → 1.8–6.9%
  (exp +5.8–6.1pp, cls +3.6–5.0pp, spr +1.7–2.0pp — gain shrinks with
  hull size as the excursion dilutes into a bigger complement).
- **Onset falsifier: signature produced, resolvable on the small
  hull.** exp excursion voyages carry burst12 med 0.36–0.45 with 16/57
  sampled over the >0.5 point-source bar (ordinary voyages 1/543); cls
  excursions elevate burst12 to 0.18–0.22 (rarely crossing 0.5); spr
  excursions are invisible in burst12 (~0.13 ≈ background) yet still
  post. Baseline had 0% over 0.5 everywhere.
- **`common_source_food` dose share** of all infections: 1.2–2.5%
  (cls/spr), 6.6–8.9% (exp) — far under the spec's >50% over-delivery
  alarm.
- **Event rows are per-epoch slices of a pan window** (~5–6 rows per
  scheduled lot); ~58% of rows are zero-dose. Realized arm mix is
  diner-dominant (62–69% on big hulls), reversed vs the Clough prior —
  consistent with duty-exclusion suppressing symptomatic handlers;
  flagged for the design owner.
- **Incidence overcorrects the real anchor** (~0.3–0.5% real posting
  incidence vs measured 1.8–6.9%): `lot_event_probability`'s declared
  interval fires ~9.5% of voyages where nearly all convert — a declared
  (unfitted) sweep axis, candidate for a next-stage posture/probability
  sweep. Not a defect.

Bit-identical baseline behavior preserved on unarmed profiles by
construction; no engine or constant changes shipped in this stage
(the census witness harvest converged with the sibling's #893
`_cs_event_log` capture of the same fields).
