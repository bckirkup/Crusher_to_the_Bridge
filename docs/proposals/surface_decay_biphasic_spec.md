# Surface decay is biphasic, and the phase boundary is drying

> **Status:** Proposed. **Nothing here is implemented.** No profile constant,
> engine constant, schema, config or interval changes in this document, and
> none is recommended yet. It changes no register value, grade, interval or
> adoption count. It is a finding about the *shape* of surface inactivation and
> a proposed representation for it; the value that would go into any such
> representation is not proposed here.

**Scope:** R2 of [`field_repair_sequence.md`](field_repair_sequence.md)
(item #44, influenza surface decay), and item #60, the deferred
Weibull-versus-exponential decision for both pathogen arms.

**What changed my mind:** R2 was sequenced as "make the scalar a
covariate-indexed rate", on the strength of tranche 14's finding that every
influenza measurement is conditioned on material, matrix, humidity, temperature
and assay. That framing is wrong in both directions, and this document argues
both halves:

* the **environmental covariates largely collapse** for a climate-controlled
  ship, so indexing on them is not the repair; and
* the axis that does not collapse is **time since deposition**, which the field
  cannot express at all — so R2 and #60 are one question, not two.

---

## 1. The rate is a function of how long the study watched

Every influenza surface measurement in
[`../literature/consensus_tranche_14_influenza_surface.md`](../literature/consensus_tranche_14_influenza_surface.md)
§2, converted to `log10` reduction per day. Non-porous surfaces, infectivity
assays only. The `window` column is the observation interval the rate is
derived from, **not** the study's total duration where those differ.

| Study | Matrix | T (°C) | Window | log10/day | implied t½ |
|---|---|---|---|---|---|
| Greatorex 2011, steel, 0→4 h | 1% BSA/DMEM | 17–21 | 4 h | **9.00** | 0.80 h |
| Qian 2023, steel | human airway surface liquid | 22–24 | half-life fit, ~h | 1.60 | 4.52 h |
| Qian 2023, PS / glass | human airway surface liquid | 22–24 | half-life fit, ~h | 1.22 | 5.91 h |
| Greatorex 2011, steel, 4→9 h | 1% BSA/DMEM | 17–21 | 5 h | **3.36** | 2.15 h |
| Greatorex 2011, plastic control, fitted | 1% BSA/DMEM | 17–21 | 0–9 h | 4.82 | 1.50 h |
| Noyce 2007, steel | lab suspension | 22 | 24 h | 0.60 | 12.0 h |
| Bean 1982, steel | lab suspension | 28 | 48 h | 1.75 | 4.13 h |
| Perry 2016, steel | mucin / 2% FBS | 18–25 | 168 h | 0.21–0.29 | ~29 h |
| Thompson 2017, steel | 0.3% BSA | ~21 | 175 h | 0.27 | 26.4 h |

**Spearman ρ(window, rate) = −0.67**, 26 of 34 orderable pairs discordant.
The single clear exception is Bean at 28 °C, the warmest condition in the
table, which is the direction temperature predicts.

Two things make this more than a scatter plot.

**Matrix does not explain it.** Greatorex (1% BSA) and Thompson (0.3% BSA) are
the same matrix class and sit at the two extremes of the table — **33× apart**,
ordered by window. Matrix is the axis tranche 14 called dominant, and holding it
fixed does not remove the spread.

**It is the opposite of what the norovirus table shows.** I checked this
identical hypothesis on the norovirus interval and it failed: Fallahi is the
slowest at 15 days and Leblanc among the fastest at 14 days, same window, 4×
apart, so that width is real between-study variation. Influenza is the arm where
the window artifact is present. The two arms should not inherit one decision by
default — which is what #60 currently assumes.

## 2. It is visible inside one experiment, on one coupon

Cross-study ordering is confounded by everything. So the load-bearing evidence
is within a single study, and it was read from the primary text
(Europe PMC `PMC3222642`, Table 4) rather than from a transcription:

Influenza PR8, stainless steel, log10 reduction in plaque titre:

| contact time | 0 h | 4 h | 9 h | 24 h |
|---|---|---|---|---|
| reduction | 1.7 | 3.2 | 3.9 | >4.2 |

The `1.7` at 0 h is **not decay** — Greatorex reports "initial losses of
infectivity ranging between 20-fold … to nearly 4000-fold" as a contact effect
at deposition, confounded with swab recovery efficiency. It is excluded from the
rates below and is *not* proposed as a model quantity.

Decay after deposition, on one material, one matrix, one strain, one run:

* 0 → 4 h: 1.5 log10 in 4 h = **9.00 log10/day**
* 4 → 9 h: 0.7 log10 in 5 h = **3.36 log10/day**
* 9 → 24 h: censored — `>4.2` is below the limit of detection, so the apparent
  0.48 log10/day is a **lower bound only** and carries no weight here.

The hazard falls **2.7×** between the first four hours and the next five, in
uncensored data. The plastic control in the same table (0.6 / 3.4 / 4.2 / >4.2)
falls **4.4×** over the same intervals.

**And the paper's own fitted constant is refuted by its own table.** Greatorex
fits "one-phase exponential decay" and reports t½ ≈ 1.5 h. A one-phase
exponential has constant hazard by construction; the table it was fitted to has
the hazard dropping four-fold inside the fitted window. The 1.5 h is a
window-averaged summary of a decelerating process, not a rate. Any of these
published half-lives, ours included, is that same kind of object.

## 3. The mechanism is drying, not a shape exponent

Greatorex, Results, first paragraph:

> "the liquid was absorbed by the wooden surfaces within 5 minutes whereas a
> droplet could be seen on non-porous surfaces for considerably longer,
> although **in all cases, surfaces had dried by 7 hours**."

The deceleration happens across that boundary. Rockey 2024 distinguishes wet and
dry phase explicitly and finds infectious decay dominated by the phase and the
matrix rather than the material; Kormuth 2018 finds mucus-borne virus infectious
at 1 h across all RH where saline is gone in minutes. The evaporating droplet
concentrates solutes to the point of efflorescence and then stops changing; the
physical process genuinely has two regimes, and the transition is an observable
event rather than a fitted exponent.

**This is the better repair than Weibull, and it is cheaper.** A Weibull shape
parameter `p < 1` is a phenomenological description of the same tailing: it fits
the curve without naming why, and — as I described earlier — expressing `p ≠ 1`
faithfully requires an age-indexed deposition cohort, because a memoryless pool
has nothing in it to be old. A wet/dry split needs **two pools and one transfer
rate**, no age index:

```
deposit → [wet pool] --(1/t_dry)--> [dry pool] → contact / cleaning
             k_wet                     k_dry
```

An exponential dwell in the wet compartment is a two-box approximation to a
fixed drying time, and it produces biphasic aggregate decay — fast early, long
tail — with no memory in either box. The repository already carries a
two-compartment surface pool (cleaned/missed, #355), so the pattern exists.

It also has the property Weibull lacks: **each rate is separately measurable**,
and the phase boundary is a physical time that studies report. A shape exponent
is only ever recoverable by fitting our own data, which is the class of quantity
this project has been removing.

### 3.1 It is the recurring archetype, in a new dimension

`model-parameter-provenance` names it: *a well-mixed pool standing in for a
small number of concentrated events*, five instances so far. This is a sixth,
and it varies the dimension rather than the mechanism — the surface pool is well
mixed **in age**, so a mixture of fresh wet deposits and old dry residue is
represented by its mean. The consequence is the same shape as the others: the
aggregate can be made right while both ends are wrong, and no value of a single
rate recovers the distribution.

The two ends are the two things fomite transmission on a ship actually depends
on: the dose a hand picks up minutes after deposition, and the residue that
survives between cleanings to seed a zone with no shedder in it.

## 4. The environmental covariates mostly collapse — this is a correction

R2 was scoped as a covariate-indexed rate over material, RH and temperature.
Grounded against the tree and the ship, three of those largely go away:

* **Temperature and humidity are not model state.** No zone in
  `data/platforms/*` carries humidity or temperature, and nothing in `engines/`
  reads either (`py_contam_bridge` carries zone T in Kelvin for airflow, not for
  inactivation). More to the point, a cruise-ship interior is HVAC-pinned near
  22 °C and mid-range RH — which is Qian's condition, not a range to sweep. The
  literature conditions on these axes because a laboratory can vary them; the
  ship does not visit their extremes.
* **Material spread is smaller than the noise it sits in.** Qian's four
  non-porous materials span 4.52–5.91 h (1.3×) while its four human donor
  cultures span 3.21–8.13 h (2.5×). Between-material variation is inside
  between-host variation. A material index would be a covariate on the smaller
  effect.
* **Matrix is fixed by the route, not swept.** Influenza deposited from
  respiratory shedding arrives in airway surface liquid or saliva. That selects
  the Qian/Rockey/Kormuth rows and deselects the BSA-buffer rows; it is a
  **selection criterion for sourcing**, not a model covariate.

So the honest statement is narrower than #392 §1 claimed, and I should correct
it: influenza surface decay is not "the one row that is genuinely curve-shaped
in its covariates". It is a row whose *environmental* covariates are pinned by
the setting, and whose *time* axis is a curve the field cannot express. The
curve-not-scalar finding survives; the axis it lives on is different.

**What does not collapse is the donor spread.** Qian's 2.5× is between-host
variation in the matrix a host deposits, and it is the largest measured axis in
the table. The model has a mechanism of exactly that shape —
`shedding_variance_log10` draws a persistent per-agent multiplier at infection —
but a well-mixed zone pool cannot carry a per-host decay rate for the same
reason it cannot carry an age. Recorded as an open question in §6, not proposed.

## 5. What this does not say

* **It does not adopt a value.** No number here is proposed for
  `surface_decay_log10_per_day`, for either arm. `influenza_a`'s current
  1.221849 remains what R1 made it: a unit conversion of an unfounded 0.94,
  equal to a 5.91 h half-life by arithmetic coincidence rather than by
  provenance. Nothing in this document makes it better sourced.
* **It does not settle the norovirus arm.** §1 shows the window ordering is
  absent there. Whether norovirus is biphasic is a separate question with
  separate evidence — Kim 2012 reports Weibull beating linear from its abstract,
  with its rate constants still unverified, which is a claim about shape from a
  source we have not read.
* **It does not claim the effect is large.** The pre-rebuild Morris screen put
  surface decay marginally over the noise floor on whole-ship attack rate
  (ratio 1.09) and below it on both passenger channels, non-monotonically. That
  screen used the deprecated fractional box and predates the Wave 1 rebuild, so
  it settles nothing — but it is the only sensitivity evidence there is, and it
  does not point at a dominant factor.
* **It is not a licence to skip #36.** See §7.

## 6. Open questions

1. **Drying time is volume-dependent.** Greatorex applied 10 µL and observed
   drying by 7 h; Qian applied 1 µL. A ship deposit from a cough, a hand, or an
   emesis bolus differ by orders of magnitude in volume. If `t_dry` is a
   constant it is wrong for at least one of them, and the model does have a
   deposit-volume distinction available.
2. **Between-host matrix variability** (§4) has no representation, and would
   need per-host or per-deposit structure the pool cannot carry.
3. **`k_wet` and `k_dry` are not separately sourced yet.** §1 and §2 establish
   that two regimes exist; they do not supply two rates. Reading them off the
   table's short-window and long-window rows would be a fit to our own
   stratification, not a measurement, and is refused here.
4. **Is `t_dry` observable in the same studies that report the rates?** Only
   Greatorex states a drying time at all, and it is an incidental observation in
   a Results paragraph, not a measurement with dispersion.

## 7. What should happen next, in order

1. **Do not implement anything in this document yet.** Two of its three
   quantities (`k_wet`, `k_dry`, `t_dry`) have no source, and adopting a
   biphasic form with fitted rates would replace one unfounded scalar with three
   unfounded ones — a strictly worse position, and the exact trade the project
   exists to stop making.
2. **#36 still runs first**, and this document sharpens what it must answer. A
   rate screen over `[0.067, 0.79]` cannot bound a shape change; the screen
   needs a factor that varies the *split* between early and late availability,
   not only the aggregate rate. If the split moves nothing, both this proposal
   and Weibull are moot and #60 closes cheaply.
3. **Source `t_dry` and the two regime rates properly** if the screen says the
   split is live — as a sourcing unit with the matrix-selection criterion of §4
   applied, since the wet-phase rate in particular is where the buffer-matrix
   studies and the airway-surface-liquid studies most disagree.
4. **#60 should be re-scoped** from "Weibull or exponential-with-covariates" to
   "biphasic-by-drying, or exponential", per arm rather than once for both.
   Weibull was the wrong pair of alternatives: it is the phenomenological
   description of the thing §3 gives a mechanism for.
