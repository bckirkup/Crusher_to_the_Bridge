# NORO-HIGH-TOUCH-SWEEP-01
**Date:** 2026-09-22
**Commit:** 6c9a564
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 06b3239

A campaign design frozen before any of its cells ran (§§1–6 are the frozen
design, unaltered since). **Measured for the `hardware` canary only** (§7);
`shared` and `broad` have not run. Every dose figure here is a ratio against a
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

## 7. Canary readout — `hardware` (measured)

**Measured at `06b3239`**, seeds 8000–8019 (20 paired cells, 0 lost), 288
epochs, `classic_cruise_1900`, `norwalk_gi`, 1,910 agents, run locally in
3 h 01 min against the unaltered `shipped` baseline of
`NORO-TRANSFER-PRODUCT-01`. Cells:
`../norovirus/noro_high_touch_sweep_01/classic_cruise_1900/per_host_dose_challenge_hardware_seed<N>.json.gz`.
Readout: `../norovirus/noro_high_touch_sweep_01/high_touch_area_readout_hardware.json`
and `.txt`, produced by `tools/noro_diag/high_touch_area_readout.py
--scale-by-zone-class <§3 hardware row> --predicted-direction up`.

### 7.1 Criterion 1 — neutrality gate: **passed**, both halves

Seed 9000 / 24 epochs. With the knob absent the challenge output is
byte-identical on re-run and the summary carries no `high_touch_area_scale*`
key, so the default path is untouched. With the `hardware` map set, every
zone class with pool pickups shows its mean `sum_surface_area_m2 / calls` at
exactly its multiplier times the baseline's: cabin 1.500 → 0.1738 (×0.115867),
dining 8.000 → 7.4556 (×0.931948), public 6.000 → 3.3713 (×0.561882), all to
`rel_tol 1e-9`. `crew_mess` had no pool calls in the 24-epoch unscaled leg, so
it was cross-checked against the 20 pooled baseline cells (4.000 m²/call) and
matches at 4.1198 = 4.000 × 1.02995 exactly. The per-class override therefore
reaches `_fomite_surface_area` per class, and the sweep is not voided.

### 7.2 Criterion 2a — per-touch scaling, per class

| zone class | area ratio (expected) | log10 `f_touch` shift ± SE (expected) | capped share | pool calls arm/base | verdict |
|---|---|---|---:|---|---|
| cabin | 0.115867 (0.115867) | +0.917 ± 0.019 (+0.936) | 3.39e-03 | 11,490 / 22,677 | `conforms` |
| crew_mess | 1.029950 (1.029950) | −0.018 ± 0.020 (−0.013) | 4.35e-03 | 1,838 / 2,502 | `conforms` |
| dining | 0.931948 (0.931948) | +0.028 ± 0.010 (+0.031) | 0.00e+00 | 11,988 / 7,820 | `conforms` |
| public | 0.561882 (0.561882) | +0.250 ± 0.003 (+0.250) | 0.00e+00 | 62,938 / 118,650 | `conforms` |
| galley | 0.050420 (0.050420) | +0.822 ± 0.051 (+1.297) | **3.63e-01** | 226 / 640 | **`censored`** (area_match=True, shift_match=False) |

`sanitary` had no pool pickups in either arm at this cell, so it is not
scored; its multiplier is exercised but unobserved here. **In every class that
is not saturated the per-touch chain scales exactly as `1/A`** — the fourth
independent confirmation of `NORO-TRANSFER-PRODUCT-01`, now per class rather
than under a single global factor.

Galley is the one departure and it is a *censoring* artefact, not a mechanism
failure: `f_touch` is logged only on uncapped calls, so at ×0.05042 the
surviving 144 of 226 draws are the low tail and the pooled shift is pulled
short of `−log10(0.05042)`. The area ratio is still exact. This is the galley
mechanism the `g0.25` canary predicted, arriving at the endpoint where §5
said it would bite first.

### 7.3 Criterion 2b — paired per-seed dose distribution: **not resolvable at n = 20**

Predicted direction **up** (§3). All 20 pairs defined, 0 undefined (no seed
had a zero dose on either side).

| statistic | value |
|---|---|
| `k` matching predicted sign `up` | **8 / 20** |
| threshold for `shifted` at α = 0.05 | `k ≥ 15` (or `k ≤ 5` against) |
| exact two-sided binomial p | **0.5034** |
| median `r_s` (decades, unscored) | −0.205 |
| IQR `r_s` | [−0.560, +1.012] |
| min, max `r_s` | −1.577, +5.301 |
| `legacy_median_ratio_unscaled` (retired, no verdict) | 18.81 |

**Verdict: `not resolvable at n = 20` — design-limited, not a null.** The
smallest admissible area endpoint, which raises per-touch dose by a
calls-weighted +0.34 decades and does so exactly (§7.2), does not produce a
resolvable directional shift in whole-voyage fomite dose: the signs split
8 up / 12 down, and the per-seed spread (−1.58 to +5.30 decades, IQR 1.6
decades wide) swamps the predicted move. Seed 8008 alone moves +5.30 decades
and seed 8001 −1.58. This is `NORO-HIGH-TOUCH-AREA-01`'s finding reproduced
under the rescored statistic and at a per-class endpoint rather than a global
factor: **the per-touch relation is exact and the whole-voyage relation is
not a scale law at all.** The magnitude figures above are reported and not
scored, per §4.3; all are ratios against a withdrawn baseline.

### 7.4 Criterion 3 — saturation, and the headline

> **HEADLINE: for `galley` this arm measures the conservation cap, not the
> transfer chain.** Galley pool pickups are capped on 82 of 226 calls
> (**36.3 %**), far above the 20 % line frozen in §4.3(b).

Arm pooled: 134 / 89,606 capped = 1.50e-03, `Σ requested / Σ offered` 0.027 →
`linear regime` overall. Baseline pooled: 8 / 153,517 = 5.21e-05, 0.007 →
`linear regime`.

| zone class | arm capped / calls | arm share | regime | confined share | zero-mass share | base capped / calls |
|---|---|---:|---|---:|---:|---|
| cabin | 39 / 11,490 | 3.39e-03 | linear | 0.828 | 0.000 | 0 / 22,677 |
| crew_mess | 8 / 1,838 | 4.35e-03 | linear | 0.000 | 0.000 | 6 / 2,502 |
| dining | 0 / 11,988 | 0.00e+00 | linear | 0.000 | 0.000 | 0 / 7,820 |
| public | 0 / 62,938 | 0.00e+00 | linear | 0.000 | 0.000 | 0 / 118,650 |
| galley | 82 / 226 | **3.63e-01** | **measures the cap** | 0.000 | 0.000 | 0 / 640 |

What this does and does not invalidate. Galley carries 226 of 89,606 arm pool
pickups (0.25 %), so the arm's §7.3 dose distribution is not a galley result
and is not withdrawn; but **no galley per-touch or per-class dose number from
this arm is quotable as a transfer-chain result**, and any later arm that
shrinks galley further measures the cap harder, not the chain. Cabin's 0.828
confined share is the cabin-compartment localisation, not saturation — it is
reported because §4.6 requires the censored shares beside every ratio.

### 7.5 Criterion 4 — epidemiological endpoint: **not resolvable at n = 20**

Arm 3 secondaries over 20 seeds; baseline 3 over the same 20 seeds. The §4.5
floor for *changed* is ≥ 20. Identical counts here, and even a difference
would not have been called: this design cannot resolve the endpoint, and no
smaller difference is an effect in either direction.

### 7.6 What is measured, inferred, and hypothesis

- **Measured** (at `06b3239`, seeds 8000–8019): criterion 1 both halves;
  per-class `1/A` per-touch scaling in cabin, crew_mess, dining, public;
  galley censored at 36.3 % capped; `k = 8/20`, p = 0.5034 on the paired dose
  signs; secondaries 3 vs 3.
- **Inferred:** the galley shift shortfall is censoring rather than a
  mechanism departure (its area ratio is exact and only uncapped calls are
  logged). The whole-voyage dose distribution is dominated by touch-history
  divergence rather than by the areal denominator.
- **Hypothesis, not measured:** that `shared` and `broad` — whose predicted
  direction is *down* and which move most classes by ×12–14 rather than
  ×0.05–1 — would also be unresolvable. The endpoint measured here is the one
  with the smaller predicted move (+0.34 decades vs ≈ −0.9), so this canary
  does **not** settle the other two arms.
- **Not contradicted:** nothing in this canary bears on the `∅nr` / `∅lit`
  null on summed high-touch area; no literature was retrieved.

### 7.7 Open decision (Benjamin's)

Whether `shared` and `broad` run. They are frozen and ready (§§2–4); if they
run they run on AWS Batch, not the local VM. The case for running them is
that their predicted move is ≈ 2.6× larger than the canary's and in the
opposite direction, so the canary does not answer them. The case against is
that criterion 2b is design-limited at n = 20 for a per-seed spread of ~7
decades, so two more 20-seed arms would most likely return
`not resolvable at n = 20` again; resolving the coordinate at all plausibly
needs either many more seeds per arm or the per-surface disaggregation
(`../proposals/fomite_surface_disaggregation_spec.md`), which is a separate
session. **No arm beyond this canary was run in this session, and nothing is
adopted.**
