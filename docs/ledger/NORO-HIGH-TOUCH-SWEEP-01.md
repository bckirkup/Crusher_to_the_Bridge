# NORO-HIGH-TOUCH-SWEEP-01
**Date:** 2026-09-22
**Commit:** 6c9a564
**Pathogens:** norwalk_gi
**Status:** declared

A campaign design frozen before any of its cells ran. Nothing in this entry is
a result. Every dose figure it will eventually report is a ratio against a
withdrawn baseline (`../norovirus/norovirus_open_ledger.md` §1) and is
relative/derived, never a dose result.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TRANSFER-PRODUCT-01`** (measured at `bd462c5`): the per-touch fomite
  chain behaves as declared; the areal denominator `HIGH_TOUCH_AREA_M2` is the
  single unsourced term carrying the route's magnitude.
- **`NORO-HIGH-TOUCH-AREA-01`** and its `g0.25` canary (measured at `25eaa17`,
  seeds 8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`, 1,910
  agents): per-touch dose scales exactly as `1/A` (area ratio 0.250000, log10
  `f_touch` shift +0.60 vs +0.602); whole-voyage dose does **not** (median
  ratio 7.7; per-seed arm/base 0.01–7e5); galley, crew_mess and dining
  already hit the conservation cap at 0.25× (8.4 % / 2.6 % / 1.2 %).
- **`NORO-HIGH-TOUCH-DEFINITION-01`** (commit `97b6af7`): three derived
  readings `hardware` / `shared` / `broad` in
  `tools/noro_diag/high_touch_area_envelope.py`. The definition of "high
  touch" is an axis of the uncertainty, not a choice. The `∅nr` / `∅lit` null
  on summed high-touch area is registered twice (tranches 45 and 46) and is
  not re-retrieved here.
- **The seam** `transmission.high_touch_area_scale_by_zone_class` is shipped,
  absent-by-default, banded `[0.01, 100.0]`, and consumes no RNG draw
  (`engines/transmission_core.py`, `_fomite_surface_area` /
  `_high_touch_area_effective_scale`); exposed as
  `--high-touch-area-scale-by-zone-class` / `--arm-tag` on
  `tools/noro_diag/per_host_dose_challenge.py`.
- **Baseline:** the 20 `shipped` cells of `NORO-TRANSFER-PRODUCT-01` at seeds
  8000–8019 under `docs/norovirus/noro_transfer_product_01/classic_cruise_1900/`.
  Not re-run.

## 1. Question

With `A` per zone class declared as a *ranged* coordinate whose interval is
the span of the three derived readings, does any admissible endpoint of that
range change what the fomite route does — or is the whole envelope a scale
factor on a route that stays uncapped, inert and unresolvable at n = 20? The
handoff (`../norovirus/high_touch_area_handoff_2026_09_22.md` §8 option (a))
frames this as one coordinate of the joint feasibility box; this entry
measures that coordinate's arms only, and adopts nothing.

## 2. The coordinate: `A` per zone class as a range (frozen)

Scale factors relative to the shipped table, read from the committed
`docs/norovirus/noro_high_touch_area_01/high_touch_area_envelope.json`
(`sweep_arms`, 3-decimal rounding as committed). The interval per class is
exactly `[min, max]` over the three readings. **These intervals are fixed now
and are never widened afterwards; they may only narrow on new evidence.**

| zone class | `hardware` | `shared` | `broad` | interval [min, max] | span (×) | inside `[0.01, 100.0]` |
|---|---:|---:|---:|---|---:|---|
| cabin | 0.116 | 0.879 | 1.279 | [0.116, 1.279] | 11.0 | yes |
| sanitary | 0.289 | 0.916 | 0.916 | [0.289, 0.916] | 3.2 | yes |
| dining | 0.932 | 12.337 | 13.249 | [0.932, 13.249] | 14.2 | yes |
| crew_mess | 1.030 | 13.530 | 14.530 | [1.030, 14.530] | 14.1 | yes |
| public | 0.562 | 11.651 | 11.651 | [0.562, 11.651] | 20.7 | yes |
| galley | 0.050 | 1.931 | 1.931 | [0.050, 1.931] | 38.6 | yes |

Every endpoint lies inside the seam's band, so the band is untouched. In
every class `hardware` is the minimum and `broad` the maximum; in galley,
public and sanitary the `shared` reading coincides with `broad`, so the
"mid" arm sits at the upper endpoint for those three classes and interior
only for cabin, dining and crew_mess. That is a property of the readings, not
a choice made here, and it is recorded so the `shared` arm is not read as a
midpoint.

## 3. Arms (frozen)

Per-class multipliers via `transmission.high_touch_area_scale_by_zone_class`;
global `high_touch_area_scale` absent (1.0). Cells: `classic_cruise_1900`,
`norwalk_gi`, 1,910 agents, 288 epochs, seeds **8000–8019** (20 per arm),
instrument `tools/noro_diag/per_host_dose_challenge.py` unchanged. Output per
arm under `docs/norovirus/noro_high_touch_sweep_01/classic_cruise_1900/` as
`per_host_dose_challenge_<arm>_seed<N>.json.gz`.

| arm id | role | cabin | sanitary | dining | crew_mess | public | galley |
|---|---|---:|---:|---:|---:|---:|---:|
| `shipped` | baseline (already measured, not re-run) | 1 | 1 | 1 | 1 | 1 | 1 |
| `hardware` | per-class **min** endpoint — **canary** | 0.116 | 0.289 | 0.932 | 1.030 | 0.562 | 0.050 |
| `shared` | mid arm | 0.879 | 0.916 | 12.337 | 13.530 | 11.651 | 1.931 |
| `broad` | per-class **max** endpoint | 1.279 | 0.916 | 13.249 | 14.530 | 11.651 | 1.931 |

**Predicted direction of the whole-voyage move, frozen from the baseline.**
The baseline's pool-pickup calls (152,289 over the 20 seeds) fall per class
as public 0.779, cabin 0.149, dining 0.051, crew_mess 0.016, galley 0.004.
The calls-weighted mean `log10 scale` an unchanged touch history would see is
therefore `hardware` −0.341, `shared` +0.898, `broad` +0.925, so the
per-touch relation predicts dose **up** on `hardware` (+0.34 decades if the
touch history were fixed) and **down** on `shared` and `broad` (≈ −0.9
decades). This is the reference direction for criterion 2b below. It is a
prediction about the *sign*, not a claim that the magnitude will hold —
`NORO-HIGH-TOUCH-AREA-01` already measured that it does not.

**Nothing is adopted.** An arm that happens to reproduce VSP, Park, an attack
rate or the passenger/crew ratio is reported as a coincidence
(`.agents/skills/model-parameter-provenance/SKILL.md`).

## 4. Admissibility criteria (frozen before any cell runs)

Criteria 1, 2a, 3 and 4 are carried over from `NORO-HIGH-TOUCH-AREA-01` §4
with the per-class generalisation noted; criterion 2b is **rescored** as that
entry's §6 required. Readout: `tools/noro_diag/high_touch_area_readout.py`
with `--scale-by-zone-class`.

1. **Neutrality gate.** The per-commit smoke (seed 9000, 24 epochs, knob
   absent) must reproduce the pre-change summary byte-for-byte, and the same
   smoke with the `hardware` map set must show every zone class's mean
   `sum_surface_area_m2 / calls` at exactly its multiplier times the
   baseline's. A deviation on the absent-knob smoke voids the sweep.
2. **(a) Per-touch scaling, per class.** For each zone class `c` with pool
   pickups in both arms: the mean area per pickup must equal `scale_c ×` the
   baseline's to `rel_tol 1e-9`, and the pooled mean `log10 f_touch` must
   shift by `−log10(scale_c)` within 3 pooled SE. Verdicts: `conforms`,
   `departs`, or — new — **`censored`** when the class's capped share
   (criterion 3) exceeds 1 %, because `f_touch` is logged only for uncapped
   calls and the surviving draws are the low tail (the galley mechanism of
   the `g0.25` canary). A `censored` class is not a departure and not a
   conformance; it is reported as such.
3. **(b) Whole-voyage dose, rescored — paired per-seed distribution.**
   Statistic, per seed `s` (20 pairs, same seed both arms):
   `r_s = log10(dose_arm_s) − log10(dose_base_s)` where `dose` is
   `fomite_witness.hand_to_mouth_dose_gec`. A pair with either dose exactly 0
   is `undefined` and excluded from the count (reported). Reported over the
   defined pairs: median, IQR, min, max of `r_s`, and `k` = number of pairs
   whose sign matches the frozen predicted direction of §3. **The only scored
   statistic is the sign:** with `n` defined pairs, the arm is
   - **`shifted`** if `k` reaches the exact two-sided binomial(`n`, ½)
     significance at α = 0.05 in the predicted direction (for `n = 20`,
     `k ≥ 15`);
   - **`shifted against prediction`** if the same holds in the opposite
     direction (`k ≤ 5` at `n = 20`) — a mechanism finding to be attributed,
     not hidden;
   - **`not resolvable at n = 20`** (design-limited) otherwise.
   The magnitude of `r_s` is **reported and never scored**: the prior entry
   measured per-seed ratios spanning 0.01–7e5, so no 20-seed design can
   bound the magnitude and none is claimed. The retired ±10 % median-ratio
   number is still printed, labelled `legacy_median_ratio`, for continuity
   with the `g0.25` readout; it carries no verdict.
   **Censored share per zone class** (the second half of the rescoring):
   for every class, `calls_capped / calls`, `calls_confined / calls` and
   `calls_zero_mass / calls` on pool pickups, arm and baseline side by side.
   The `r_s` distribution of an arm is quotable as a transfer-chain result
   only for classes whose capped share is ≤ 1 %; a class above 1 % is
   labelled **capped regime**; if **any class exceeds 20 % capped calls the
   arm is measuring the conservation cap, not the chain**, and that is
   reported immediately as the arm's headline.
4. **Saturation witness** (unchanged): pooled `capped_calls / calls` with the
   1 % line, `Σ requested / Σ offered`, both arms.
5. **Epidemiological endpoint** (unchanged): `transmission.secondaries`
   summed over seeds; baseline 3 over these 20 seeds; an arm is declared to
   have *changed* the endpoint only at ≥ 20 secondaries over its 20 seeds,
   otherwise **not resolvable at n = 20**. No smaller difference is called an
   effect, in either direction.
6. **Reporting floor:** every quoted dose ratio carries its censored shares.

## 5. Campaign gate

In order, per `.agents/skills/campaign-preflight/SKILL.md`:

1. Local smoke (seed 9000, 24 epochs) proving both halves of criterion 1 —
   the per-class map reaches `_fomite_surface_area` exactly, and the
   absent-knob output is byte-identical.
2. **One canary arm: `hardware`, 20 seeds 8000–8019, 288 epochs**, run
   locally (~3 h on two cores, as the `g0.25` canary was). Chosen because it
   is the endpoint the prior canary predicted would sit in the capped regime
   (galley ×0.05, cabin ×0.116): it tests criterion 3's 20 % stop rule and
   the `censored` verdict where they bite first, and it is the only arm whose
   predicted direction is *up*.
3. Read out, commit the readout under
   `docs/norovirus/noro_high_touch_sweep_01/`, set this entry to `measured`
   (canary only), and **stop**. Whether `shared` and `broad` run is
   Benjamin's decision; if they run, they run on AWS Batch, not the local VM.

## 6. What is not being done

No change to `HIGH_TOUCH_AREA_M2`, `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` or
any physical constant. No fitting to VSP, Park, attack rates or the
passenger/crew ratio. No adoption of any reading. No engine change — the
per-surface disaggregation (`../proposals/fomite_surface_disaggregation_spec.md`)
is a later, separate session. Out of scope and noted only: the post-era A4
anchor hole for two of four hulls and the `SURFACE_CONTACTS_PER_HOUR["cabin"]`
(Yuan 2024) numerator sourcing defect, both recorded in the handoff §4.

## 7. Canary readout

Not yet run. This section is filled when the `hardware` canary is read out
and the status moves to `measured`.
