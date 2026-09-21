# NORO-TRANSFER-PRODUCT-01
**Date:** 2026-09-21
**Commit:** a9b4f1f (declared), `bd462c5` (instrument merged)
**Measured at:** `bd462c5`
**Pathogens:** norwalk_gi
**Status:** measured

`NORO-DOSE-BLOCK-01` (measured at `5870c74`) reported whole-voyage "transfer
terms": a surface->hand loss of
`log10(sum(surface_mass_offered_gec) / sum(mass_delivered_to_hands_gec))` with
median 0.840 log10 and range 7e-7..2.673 log10 across the 22-cell block, and a
hand->mouth loss of `log10(sum(hand_load_seen_gec) / sum(hand_to_mouth_dose_gec))`
with median 1.960 log10. The committed per-seed dumps under
`docs/norovirus/noro_dose_block_01/classic_cruise_1900/` show those ratios are
**not** transfer efficiencies and are not commensurable with any published
transfer measurement: `sum(requested) / sum(offered)` spans 0.0021 (seed 8002)
to 2.13 (seed 8000) across the block; seed 8000's ~0-loss cell is
`_delivery_scale` saturation, not efficient transfer; and the denominator sums
per-epoch `_deliver_fomite_requests` calls against a surface pool that persists
across epochs, so the same mass is counted as offered once per epoch it
survives — cross-epoch double counting by construction.

## Question

Is the hull's implemented fomite transfer chain defensible against independent
literature, and at what layer is it even commensurable?

## Declared position

The whole-voyage `sum(offered) / sum(delivered)` ratio `NORO-DOSE-BLOCK-01`
reported is a bookkeeping ratio over per-epoch deliver calls against a
persisting pool, inflated by cross-epoch double counting and collapsed by
`_delivery_scale` saturation. It is **not** comparable to any published
transfer efficiency. The literature-commensurable quantity is the per-touch
chain: per surface contact the engine implements

    f_touch = used_fraction * (hand_area_m2 / surface_area_m2)
              * eff_surface_to_hand

(`engines/transmission_core.py` `_fomite_pickup_request_for_area`), and per
mouth contact

    g_touch = used_fraction_mouth * eff_hand_to_mouth

(`_hand_to_mouth_dose`). Only these per-touch factors and their product can be
set against published measurements.

## Layers, declared in advance as comparable vs not

| Layer | Term | Comparable to literature? |
| --- | --- | --- |
| (a) per-touch surface->hand efficiency | `SURFACE_TO_HAND_LOGNORMAL` draw | Yes — published fingerpad/hand transfer efficiencies |
| (b) per-touch hand->mouth efficiency | `HAND_TO_MOUTH_NORMAL` draw | Yes — published hand-to-mouth transfer efficiencies |
| (c) product | `f_touch * g_touch` per touch | Yes — published per-touch surface->hand->mouth QMRA chain factors |
| (d) areal dilution and contact frequency | `used_fraction * hand_area / HIGH_TOUCH_AREA_M2[zone]`, contacts/epoch | No — a geometry/behaviour declaration, not a transfer measurement; `HIGH_TOUCH_AREA_M2` is already flagged in-code as a declared assumption |
| (e) cap/saturation path | `min(surface_mass, ...)` and `_delivery_scale` | No — a model artifact with no literature counterpart |

A conclusion is recorded per layer as measured, inferred, null, or unresolved.
No engine constant is changed to close a gap with literature.

## Instrument

`tools/noro_diag/per_host_dose_challenge.py` is extended (this change) with a
`transfer_product_witness` summary block: a wrapper on
`_fomite_pickup_request_for_area` that calls the original exactly once,
re-calls only RNG-free helpers (`_fomite_surface_contacts`,
`_fomite_zone_class`), tags each call `pool` or `patch` via a depth counter
the `_emesis_patch_pickup_one` wrapper holds while its original is on the
stack, classifies it `confined` / `zero_mass` / `capped` / `clean`, and for
clean calls accumulates `log10(f_touch)` statistics and a fixed-bin histogram
(bin width 0.25 over [-12, +1), edges emitted in the summary). The existing
`hand_to_mouth` wrapper accumulates `log10(dose / hand_load)` split
eating/non-eating on the same bin spec, and a `delivery_scale_witness` counts
scaled deliver calls and the log10 scale applied. All existing
`fomite_witness` keys keep their names and semantics; the instrument consumes
no draw from `self.rng`. Readout by a new
`tools/noro_diag/transfer_product_readout.py` — not part of this declaration.

## Cells, frozen before any cell runs

| Hull | Seeds | Agents | Epochs | Cells |
| --- | --- | --- | --- | --- |
| `classic_cruise_1900` | 8000-8019 | 1,910 | 288 | 20 |
| `classic_cruise_1900` | 8105, 8106 | 1,910 | 288 | 2 |

Shipped default `active_profiles` bundle at its declared complement, no
override — the same 22 cells as `NORO-DOSE-BLOCK-01`, so the per-touch chain
is measured on exactly the voyages whose bookkeeping ratios it reinterprets.

## Criteria, declared before any cell runs

**RNG-neutrality gate.** The engine is unchanged between `5870c74` and the
run commit, so the re-run must reproduce every existing per-seed
`fomite_witness` aggregate total in
`docs/norovirus/noro_dose_block_01/classic_cruise_1900/` exactly. Any
deviation means the extended instrument consumed a draw, the instrument is
not RNG-neutral, and the cells it produced are **void**.

**Per-layer verdict.** Each of the five layers above is recorded as measured,
inferred, null, or unresolved against its declared comparability, with the
censored fractions (`calls_capped`, `calls_confined`, `calls_zero_mass`,
`scaled_calls`) reported alongside so an efficiency estimate is never quoted
without the share of calls it does not describe.

**Report immediately if:** the RNG-neutrality gate fails on any cell; or any
cell raises.

## Non-goals

No engine constant, engine formula, profile, platform, or test is changed.
The readout script and the literature comparison itself are the follow-on
entry, not this one. No `--alpha` arm.

## Stop condition

One measured ledger entry recording a per-layer verdict for layers (a)-(e)
over the 22 cells, with the RNG-neutrality gate passed.

# Readout

Measured at `bd462c5`, 22/22 cells admissible, 0 void, no cell raised. Cells in
`docs/norovirus/noro_transfer_product_01/classic_cruise_1900/`; aggregation by
`tools/noro_diag/transfer_product_readout.py` into
`docs/norovirus/noro_transfer_product_01/transfer_product_cells.json`. 1 h 56 m
wall clock for the 22 cells, two concurrent.

## 0. Gates

**RNG-neutrality: PASS.** All 22 cells reproduce all 7 pre-existing
`fomite_witness` aggregates from the `5870c74` cells exactly (`mismatches: []`,
no seed absent from the baseline). The extended instrument consumes no draw, so
the per-touch witness describes the same voyages `NORO-DOSE-BLOCK-01` measured
rather than a perturbed engine.

**Three-sum reconciliation at 1e-9: FAILS, and is not this entry's finding.**
Worst 8.400e-3 at seed 8019 — the same cells, the same value, and the same
one-sided `sum_effective_dose_evaluated_gec` shortfall that
`NORO-DOSE-BLOCK-01` §0 already attributed to the `REINFECT-01` protection
short-circuit. The readout's exit code 1 is that inherited gate, not a transfer
result.

## 1. Layer (a), per-touch surface->hand efficiency — **measured**

Per clean pickup call the witness records
`f_touch = (request / surface_mass) / contacts`. Dividing the areal geometry
back out with the geometric means of the two uniform draws (0.10305 for
`used_fraction`, 0.048931 m² for hand area) gives the implied efficiency:

| source / zone class | calls | clean | f_touch geomean | sd log10 | implied efficiency |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pool/public` | 132,046 | 132,046 | 9.87e-5 | 0.664 | 0.1174 |
| `pool/dining` | 8,474 | 8,474 | 7.53e-5 | 0.668 | 0.1195 |
| `pool/cabin` | 24,840 | 3,365 | 3.87e-4 | 0.674 | 0.1151 |
| `pool/crew_mess` | 2,609 | 2,603 | 1.55e-4 | 0.651 | 0.1231 |
| `pool/galley` | 640 | 640 | 6.14e-5 | 0.683 | 0.1217 |
| `patch/cabin` | 1,412 | 30 | 7.47e-4 | 0.667 | 0.1265 |
| `patch/galley` | 2 | 0 | — | — | — |

The closed form over the shipped constants — geometric mean of
`min(1, lognormal(-2.1, 1.4))`, 8e6 draws — is **0.1176**, and the measured
sd log10 (0.65-0.68) is what the efficiency draw (0.573) composed with the
`used_fraction` uniform gives. The implemented path therefore applies the
declared efficiency draw and nothing else: no hidden multiplier, no per-zone
efficiency, and the 1.6% spread across buckets is sampling noise on n from 30
to 132,046.

**Verdict: measured, and defensible.** 0.118 geometric mean sits inside the
norovirus/surrogate infectivity band on non-porous donors (~2-24%, tranche 44
§2). The upper tail is not: 6.7% of draws clip at 1.0, which only analogue
evidence supports (Wilson 2020 reports recoverable fingertip transfer up to
9.98e-1), and that is recorded as the layer's residual weakness, not as
agreement.

**Censoring, reported with the estimate.** Cabin pickups are dominated by
confinement, not by transfer: 86.5% of `pool/cabin` and 97.9% of `patch/cabin`
calls return 0 because the occupant is confined, so the cabin efficiency
describes 13.5% and 2.1% of calls respectively. No call anywhere hit
`zero_mass`.

## 2. Layer (b), per-touch hand->mouth efficiency — **inferred, composition measured**

The witness records `dose / hand_load` per epoch, which is
`contacts * used_fraction * efficiency` — and `contacts` is an RNG draw the
instrument may not re-take, so the per-contact efficiency is not directly
observable here:

| | calls | logged | zero-contact share | ratio geomean | mean log10 | sd log10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| eating | 10,700 | 10,317 | 3.58% | 2.08e-2 | -1.6818 | 0.377 |
| non-eating | 139,845 | 122,098 | 12.69% | 8.17e-3 | -2.0876 | 0.450 |

Recomposing the declared constants at `epoch_duration_hours = 1`
(`EATING_MOUTH_CONTACTS_PER_HOUR`, `NON_EATING_MOUTH_CONTACTS_PER_HOUR`,
`MOUTH_CONTACT_FRACTION_RANGE`, `HAND_TO_MOUTH_NORMAL`) gives mean log10
-1.682 / -2.086, sd 0.377 / 0.449, and zero-contact shares 3.50% / 12.81%.
The witness matches the composition in mean, spread **and** truncated-tail
mass in both meal states, so the per-contact factor is the declared draw:
geometric mean 0.309, median 0.339.

**Verdict: inferred (from constants, composition measured), defensible but
surrogate-only.** 0.339 sits inside Rusin 2002's fingertip-to-lip range
(33.90% PRD-1 phage, 33.97-40.99% bacteria) and Abney 2022's MS2 range
(23.15-52.53%, matrix-dependent). No human-norovirus finger-to-lip measurement
was retrieved in two differently phrased searches, and the 0.132 standard
deviation has no source at all (§5).

## 3. Layer (c), the per-touch product — **inside the composed envelope**

Geometric mean 0.1176 x 0.309 = **0.0364** per touch-and-mouth pair (median of
the product distribution 0.0381), against the composed literature envelope of
0.007-0.22 from the two-step low/high combinations in tranche 44 §4. Inside,
with the same two caveats as its factors: the surface->hand upper tail is
analogue-supported only, and the hand->mouth factor is surrogate-only.

## 4. Layers (d) and (e) — **null and artifact, as declared**

**(d) Areal dilution and contact frequency: unresolved, and dominant.** The
witnessed mean surface areas are exactly the declared constants (cabin 1.5,
crew_mess 4.0, public 6.0, dining 8.0, galley 10.0 m²; the 0.854 m² for
`patch/cabin` is the declared emesis footprint), so nothing measured enters
this layer. It is also the layer that sets the magnitude: `f_touch` is
6.1e-5-7.5e-4, three decades below the efficiency it contains, and that gap is
almost entirely `hand_area / HIGH_TOUCH_AREA_M2`. **The hull's fomite dose is
more sensitive to an unmeasured geometry declaration than to either
microbiological efficiency.**

**(e) Cap and saturation: a model artifact, and not what moved the
whole-voyage ratio.** Per-touch truncation is negligible — 8 capped calls in
170,023 surface pickups (6 `pool/crew_mess`, 2 `patch/galley`) and **zero**
capped calls in 150,545 hand->mouth calls. `_delivery_scale` scales 0-4.6% of
deliver calls per cell, geometric mean scale 0.151-0.935 where it applies, and
only 3 cells (8000, 8003, 8004) request more than they are offered over the
whole voyage. So the 0.840-log10 median "surface->hand loss" of
`NORO-DOSE-BLOCK-01` is neither a transfer efficiency nor per-touch
truncation: it is a persisting pool re-offered once per surviving epoch, with a
few-percent saturation correction on top. The decade-scale move between blocks
is a move in that bookkeeping, and the transfer efficiencies did not move.

## 5. Findings carried forward, not repaired here

- **F44-1 `HAND_TO_MOUTH_NORMAL` has no provenance row.** The mean 0.339 is
  traceable to Rusin 2002's PRD-1 figure; the sd 0.132 is untraced. Layer (b)
  rests on it.
- **F44-2 `MOUTH_CONTACT_FRACTION_RANGE = (0.008, 0.012)`** is ~10x below the
  only retrieved measured mouthed-area fraction (AuYeung 2006, children,
  median ~0.11 per contact) and has no adult-fingertip source of its own.
- **F44-3 `HAND_AREA_CM2_RANGE = (445, 535)`** is a male-only upper band
  against Lee 2007 (male mean 448, female mean 392 cm²).
- **F44-4 `HIGH_TOUCH_AREA_M2` is the dominant unmeasured factor** (layer (d)
  above), already flagged in-code as a declared assumption.
- **Aggregation defect, found and fixed before publication.** The first
  `transfer_product_readout.py` divided the pooled log sums by the call count
  rather than by the number of logged samples, so every geometric mean was
  pulled toward 1 by the zero-ratio share (non-eating 1.50e-2 instead of
  8.17e-3). The divisor is now read off the histogram the instrument files
  every logged sample into. No engine path and no cell is affected; the
  numbers above are the corrected ones.

No engine constant, formula, profile or test was changed by this entry.

## 6. Stop

The stop condition is met: layers (a)-(e) each carry a verdict over the frozen
22 cells with the RNG-neutrality gate passed. The open decision this hands to
the next session is which of F44-1..F44-4 to source or re-declare first — the
measurement above says **F44-4 (`HIGH_TOUCH_AREA_M2`) dominates the dose**,
while F44-1 is the largest pure provenance hole.
