# NORO-TRANSFER-PRODUCT-01
**Date:** 2026-09-20
**Commit:** a9b4f1f
**Pathogens:** norwalk_gi
**Status:** declared

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
