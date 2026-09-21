# NORO-HIGH-TOUCH-AREA-01
**Date:** 2026-09-21
**Commit:** 28441bd
**Pathogens:** norwalk_gi
**Status:** declared

`NORO-TRANSFER-PRODUCT-01` (measured at `bd462c5`) found the hull's per-touch
fomite chain defensible against the literature that measures it — surface→hand
implied efficiency 0.115–0.127 across six source/zone buckets against a 0.1176
closed form, hand→mouth recomposing the constants to the tail — and essentially
uncapped: **8 truncations in 170,023 surface pickups**. Because the pool enters
a touch only as `mass / A`, that leaves the areal denominator
`HIGH_TOUCH_AREA_M2` as the factor that sets the fomite dose, and it is a
declared assumption carrying no measurement.

Tranche 45 (`docs/literature/consensus_tranche_45_high_touch_area.md`) retires
the in-code "never measured by anybody" claim and replaces it with a **derived
envelope**: enumerated high-touch item sets × per-item areas, evaluated against
the actual `classic_cruise_1900` zone occupancies, with the measured total
room-surface inventories as an impossibility ceiling. This entry freezes the
sweep over that envelope. **It carries no results.**

## 1. Question

Across the literature-bounded envelope for `A`, does the hull's fomite pathway
stay in the regime `NORO-TRANSFER-PRODUCT-01` measured — dose exactly `∝ 1/A`,
uncapped, epidemiologically inert — or does some admissible corner of the
envelope put it into saturation, or make it produce secondary infections?
Equivalently: **is the unmeasured denominator a free parameter that changes the
conclusion, or a scale factor on a route that is dead either way?**

## 2. What is not being done

* No constant is changed. `HIGH_TOUCH_AREA_M2` and
  `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` are untouched on every arm; the arms are
  the sweep knobs `transmission.high_touch_area_scale` (global) and
  `transmission.high_touch_area_scale_by_zone_class` (per class), both of which
  are absent-by-default and bit-identical to the shipped tree when unset.
* **No arm is a candidate for adoption.** An arm that reproduces VSP attack
  rates, or any other outcome anchor, is not thereby evidence for its value of
  `A`; per `.agents/skills/model-parameter-provenance/SKILL.md`, geometry may
  not be fitted to an epidemiological anchor. If the readout finds such a
  coincidence it is reported as a coincidence.
* Nothing declares the envelope to *contain* the true value. Seven of the
  seventeen item areas behind it are this repository's own declared geometry.

## 3. Arms (frozen)

Scale is a multiplier on the declared area, so **dose moves as `1/scale`** while
the chain stays uncapped. The per-class arms come from tranche 45 §4.

| arm id | knob | value | provenance of the value |
|---|---|---|---|
| `shipped` | — (absent) | — | the shipped declaration; the paired baseline |
| `g0.10` | `high_touch_area_scale` | 0.10 | order-of-magnitude low corner |
| `g0.25` | `high_touch_area_scale` | 0.25 | **canary arm** |
| `g0.50` | `high_touch_area_scale` | 0.50 | |
| `g2.0` | `high_touch_area_scale` | 2.0 | |
| `g4.0` | `high_touch_area_scale` | 4.0 | |
| `g10.0` | `high_touch_area_scale` | 10.0 | order-of-magnitude high corner |
| `hardware` | `high_touch_area_scale_by_zone_class` | cabin 0.12, sanitary 0.29, dining 0.93, crew_mess 1.03, public 0.56, galley 0.05 | tranche 45 §4, hand-contact-hardware reading |
| `broad` | `high_touch_area_scale_by_zone_class` | cabin 1.28, sanitary 0.92, dining 13.25, crew_mess 14.53, public 11.65, galley 1.93 | tranche 45 §4, touched-planes reading |

Cells: `classic_cruise_1900`, `norwalk_gi`, 1,910 agents, 288 epochs, seeds
**8000–8019** (20 per arm) — the same seeds as the `NORO-TRANSFER-PRODUCT-01`
block, so `shipped` is the already-measured 20-cell baseline and is **not
re-run**. Instrument: `tools/noro_diag/per_host_dose_challenge.py`, unchanged.

## 4. Admissibility criteria (frozen before any cell runs)

Declared now so the readout cannot choose them afterwards. Per arm, over its 20
seeds:

1. **Neutrality gate.** The `shipped` arm re-run at the sweep commit with the
   knobs absent must reproduce the committed `NORO-TRANSFER-PRODUCT-01`
   `fomite_witness` aggregates **exactly**. Any deviation voids the whole
   sweep: the knobs took a draw.
2. **Scaling prediction (the falsifiable one).** With pickups uncapped, dose is
   analytically `∝ 1/scale`. The arm **conforms** if the median over seeds of
   `hand_to_mouth_dose_gec × scale` is within **±10 %** of the `shipped`
   median, and **departs** otherwise. A departure is the interesting outcome
   and must be attributed to a named mechanism (cap truncation, pool
   exhaustion, emesis `touchable_fraction`, or a changed infection trajectory),
   not reported as a bare number.
3. **Saturation witness.** `capped_calls / surface_pickup_calls` and
   `Σ requested / Σ offered` are reported on every arm. An arm with
   `capped_calls / calls > 0.01` is **out of the linear regime** and its dose
   figures may not be quoted as a `1/A` scaling.
4. **Epidemiological endpoint.** `transmission.secondaries` summed over seeds.
   The baseline is **3 secondaries in 22 cells**, so this endpoint is
   underpowered by construction: an arm is only declared to have *changed* the
   endpoint at **≥ 20 secondaries over its 20 seeds**, and any smaller
   difference is reported as **not resolvable at n = 20** rather than as an
   effect.
5. **Reporting floor.** Every quoted dose figure carries its censored share
   (confined / zero-mass / capped calls), per the tranche 44 convention.

## 5. Canary (the only cells this session runs)

One arm, `g0.25`, 20 seeds, 288 epochs, read out against the four criteria
above. `g0.25` is chosen because it is the smallest area change that is
expected to leave the chain uncapped (a 4× dose rise against a baseline with
8/170,023 truncations), so it tests criterion 2 where the prediction is
sharpest and criterion 3 where a departure would first appear. **Nothing else
runs until the canary is read out and reported.**

Prior (recorded so the readout can disagree with it): the canary conforms —
`hand_to_mouth_dose_gec` median rises ~4×, capped share stays ≪ 1 %, and
secondaries stay unresolvable. Cost is the reason the rest waits: a 20-seed
288-epoch arm is ~3 h on two local cores, so the full nine-arm grid is a
~24 h local run or an AWS Batch array, and that is a decision for after the
canary, not before it.

## 6. Status

`declared`. No cell of this entry has been read out. This entry moves to
`measured` when the canary readout is committed; the remaining arms require an
explicit decision to run.
