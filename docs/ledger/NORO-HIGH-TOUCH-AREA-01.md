# NORO-HIGH-TOUCH-AREA-01
**Date:** 2026-09-21
**Commit:** 28441bd
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 25eaa17

Measured on the canary arm `g0.25` only; eight arms not run.

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
sweep over that envelope; §6 carries the canary readout and nothing else.

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

## 6. Canary readout (measured)

Criterion 1 was checked by the per-commit smoke only (seed 9000, 24 epochs,
knobs absent, whole summary byte-identical pre/post change); the 20-seed
288-epoch `shipped` re-run it calls for was not done and is charged to the full
sweep.

Cells: `g0.25`, `classic_cruise_1900`, `norwalk_gi`, 1,910 agents, 288
epochs, seeds 8000–8019, engine at `25eaa17`; per-seed dumps under
`docs/norovirus/noro_high_touch_area_01/classic_cruise_1900/`, readout by
`tools/noro_diag/high_touch_area_readout.py` in
`docs/norovirus/noro_high_touch_area_01/high_touch_area_readout_g0p25.{json,txt}`.
Baseline is the 20 matching seeds of `NORO-TRANSFER-PRODUCT-01` (same engine
behaviour; the sweep key was absent).

| criterion | result | verdict |
|---|---|---|
| 2 per touch — area per pool pickup | ×0.250000 in all five classes (cabin, crew_mess, dining, galley, public) | conforms, exact |
| 2 per touch — mean log10 f_touch shift (expected +0.602) | cabin +0.605±0.017, public +0.604±0.004, dining +0.578±0.011, crew_mess +0.576±0.021, galley +0.426±0.052 | 4/5 conform at 3 SE; galley departs |
| 2 whole voyage — median(dose×0.25)/median(base dose) | 7.7 (tolerance ±10 %) | **departs** |
| 3 saturation, pooled | capped 154/64,132 = 2.4e-3 (base 8/153,517 = 5.2e-5); Σreq/Σoff 0.082 (base 0.007) | linear regime by the frozen pooled test |
| 3 saturation, per class (not frozen; reported) | galley 19/226 = 8.4 %, crew_mess 40/1,514 = 2.6 %, dining 91/7,705 = 1.2 %, cabin 0, public 0 | three classes above the 1 % line |
| 4 secondaries | 4 vs 3 over 20 seeds (seed 8008 gained one) | not resolvable at n=20 |

Reading, measured vs inferred:

- **Measured:** the sweep key reaches the pickup denominator exactly and only
  there — every pool pickup in every class divides by 0.25× the shipped area;
  the emesis-patch footprint scales with it (cabin patch 0.814 → 0.298 m²,
  galley 0.243 → 0.061 m²) as designed. Per touch, the 1/A prediction holds
  where the chain is uncapped.
- **Measured:** at 0.25× the chain is *not* uncapped in the shared zones.
  The galley departure on `f_touch` is a censoring artefact of that: capped
  calls are excluded from the logged `f_touch`, and 8.4 % of galley pickups
  capped, so the surviving draws are the low tail. The prior in §5 ("expected
  to leave the chain uncapped") was wrong for galley/crew_mess/dining.
- **Measured:** whole-voyage `hand_to_mouth_dose_gec` does not follow
  1/A. Per seed the arm/base ratio spans 0.01–7×10⁵ (20 pairs in the JSON);
  the dose is set by which hosts vomit where, and a 4× change in per-touch
  pickup re-routes the trajectory rather than scaling it. Criterion 2b
  therefore fails as frozen, and the failure is attributable: the criterion
  assumed a fixed deposition history, and this model does not have one across
  a config change (the RNG streams stay aligned only until the first
  area-dependent branch).
- **Inferred (not measured):** Σreq/Σoff rising 12× rather than 4× is
  consistent with the deposition coupling — a smaller high-touch area also
  shrinks `touchable_fraction`, so less bolus mass enters the pool the hands
  then demand more from. Confirming this needs the deposition witness split by
  arm; not done here.
- **Null:** secondaries are unchanged within resolution. Nothing here is a
  dose figure fit for quotation; all dose figures remain withdrawn per the
  open ledger.

What this means for the remaining arms: the frozen design is sound for the
per-touch and saturation questions, but criterion 2b cannot be met by any arm
and should be read as a *distribution* comparison (paired per-seed ratios,
censored shares) rather than a median tolerance. Any arm at ≤0.25× on the
shared zones is in the capped regime, so `g0.10` and the `hardware` arm (galley
×0.05) will be measuring the conservation cap, not the transfer chain.

## 7. Status

`measured`, canary arm only. One arm of nine has been read out. The remaining
arms require an explicit decision to run; the design question on criterion 2b
(§6) should be settled before they do. No constant has been changed and
nothing from tranche 45 has been adopted.
