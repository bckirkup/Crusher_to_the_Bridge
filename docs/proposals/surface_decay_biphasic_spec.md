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
* **It does not extend to the exterior.** The HVAC-pinned argument that the
  environmental covariates collapse is sound for the ship's *interior*; it does
  not hold for the open decks, pool decks and semi-open zones every cruise
  platform carries, which are neither temperature- nor humidity-pinned.
  [`exterior_zone_environment_spec.md`](exterior_zone_environment_spec.md)
  records what the tree asserts about those zones today, and its §3(c) is the
  connection back to this document: a permanently wet poolside surface may never
  complete the drying transition, so it would sit in one regime rather than
  passing through both. Nothing there is adopted either.

## 6. Open questions

1. **Drying time is volume-dependent.** Greatorex applied 10 µL and observed
   drying by 7 h; Qian applied 1 µL. A ship deposit from a cough, a hand, or an
   emesis bolus differ by orders of magnitude in volume. If `t_dry` is a
   constant it is wrong for at least one of them, and the model does have a
   deposit-volume distinction available.
2. **Between-host matrix variability** (§4) has no representation, and would
   need per-host or per-deposit structure the pool cannot carry.
3. **`k_wet` and `k_dry` are separately sourced, in systems that do not match
   this field.** §1 and §2 of this spec establish only that two regimes exist.
   §8 now reports two studies that measure both rates on an infectivity
   endpoint — Rockey 2024 in human saliva, French 2023 in cell-culture medium —
   so the question is no longer whether the rates exist but whether any measured
   pair is commensurable with a per-day fomite-pool law. Neither is: both are
   single-droplet experiments over one to eight hours. Reading rates off this
   spec's own short-window and long-window rows remains refused as a fit to our
   own stratification.
4. **Is `t_dry` observable in the same studies that report the rates?** Yes, and
   this is resolved: Rockey 2024 measures drying time gravimetrically at three
   humidities with replicate ranges (0.26 h at 20% RH, 0.54 h at 50%, 1.29 h at
   80%), and French 2023 measures quasi-equilibrium time per droplet volume and
   RH. **The open question is now the opposite one** — Rockey finds inactivation
   *not* associated with drying time, so a measured `t_dry` exists while its
   status as the causal phase boundary is weaker than §3 assumes.
5. **Deposit volume is now the sharpest open question, not a footnote to it.**
   Both sourced triplets are 1–50 µL single droplets; §6.1's volume dependence
   is the axis along which their rates would have to be extrapolated to a pool.

## 7. What should happen next, in order

1. **Do not implement anything in this document yet.** The refusal stands, but
   §8 has changed its grounds: all three quantities (`k_wet`, `k_dry`, `t_dry`)
   are now sourced on an infectivity endpoint, and none of the sourced sets is
   commensurable with a per-day fomite-pool law — they are single-droplet
   experiments over one to eight hours, they disagree on which phase is faster,
   and the respiratory matrix shows no phase split at all. Adopting one would
   still replace one scalar with three quantities plus a choice of matrix,
   volume, RH and window — the trade the project exists to stop making. It is a
   selection problem now, not an absence.
2. **#36 still runs first**, and this document sharpens what it must answer. A
   rate screen over `[0.067, 0.79]` cannot bound a shape change; the screen
   needs a factor that varies the *split* between early and late availability,
   not only the aggregate rate. If the split moves nothing, both this proposal
   and Weibull are moot and #60 closes cheaply.
3. **Re-scope the sourcing unit** if the screen says the split is live. The
   original question — find the two rates and the boundary — is answered by §8.
   What is unanswered, and what a unit should now ask, is whether a
   single-droplet rate pair can be carried to a pool at all: that turns on
   deposit volume (§6.1, §6.5) and on whether the split is a matrix effect
   rather than a time effect, given that airway surface liquid shows one rate
   and saliva two.
4. **#60 should be re-scoped** from "Weibull or exponential-with-covariates" to
   "biphasic-by-drying, or exponential", per arm rather than once for both.
   Weibull was the wrong pair of alternatives: it is the phenomenological
   description of the thing §3 gives a mechanism for.

## 8. Sourcing note: the search for the two rates, and the assay endpoint (R2)

This section closes R2's remaining live question. It **adopts nothing**: no
value, grade, interval, schema or engine change follows from it, and `k_wet`,
`k_dry` and `t_dry` are still refused per §7.1.

The full query log, including the filters used and what each of the eleven
searches returned, is
[`../literature/consensus_tranche_19_influenza_biphasic_surface.md`](../literature/consensus_tranche_19_influenza_biphasic_surface.md).

**What was searched for.** One influenza surface experiment reporting *infectious*
virus at enough time points to identify a wet-phase rate, a dry-phase rate and
the drying boundary, preferably in a respiratory matrix — i.e. the sourcing unit
§7.3 asks for.

**What came back.** Two studies report all three quantities on an infectivity
endpoint, which is more than this section originally recorded: the first pass
read abstracts only, and the abstracts do not contain the Results tables. The
values are reported in full in
[`../literature/consensus_tranche_19_influenza_biphasic_surface.md`](../literature/consensus_tranche_19_influenza_biphasic_surface.md)
§2 and are **not adopted here**:

* **French 2023** (*mBio*, DOI `10.1128/mbio.03452-22`) deposits
  influenza A in 1–50 µL droplets across three humidities, tracks evaporation to
  quasi-equilibrium as the phase breakpoint, and reports **both phase rate
  constants for H1N1pdm09 in all nine conditions** (Table 1, h⁻¹). The phase
  boundary is measured as a mass plateau, which is §3's mechanism observed
  directly rather than inferred from window ordering. Two things disqualify it as
  a parameter source: its matrix is cell-culture medium, which §4's selection
  criterion excludes, and the wet/dry ordering for influenza is **not
  consistent** across conditions — in 50 µL droplets at 40% RH the dry phase is
  the faster one.
* **Rockey 2024** (*Appl Environ Microbiol*, DOI `10.1128/aem.02010-23`) is the
  closest matrix match and supplies the whole triplet in a respiratory matrix:
  H1N1pdm09 in 1 µL saliva droplets at 50% RH decays at **0.010 ± 0.012 log10
  min⁻¹ wet** (indistinguishable from zero) and **0.036 ± 0.020 log10 min⁻¹
  dry**, with drying time measured at three humidities. Decisively for this
  spec, **airway surface liquid shows no wet/dry difference at all** — one rate,
  0.010 ± 0.0030 log10 min⁻¹ — so in the matrix §4 prefers, the biphasic form is
  unsupported.
* **Wei 2026** (*J Hazard Mater*, DOI `10.1016/j.jhazmat.2026.141707`) quantifies
  evaporation-phase inactivation rate constants two orders of magnitude above
  suspension-phase constants. It is an airborne system, not a deposited pool, so
  it bears on the air reservoir rather than on this field.
* **Qian 2023** (`10.1128/aem.00633-23`) gives respiratory-matrix half-lives of
  4.5–5.9 h on non-copper surfaces at 23% RH, with donor identity dominating
  surface material — §4's between-host variability, measured.

**Why §7.1's refusal survives being sourced.** The two triplets are
incommensurable with the field they would fill and with each other. They disagree
on which phase is faster; they are single-droplet experiments over one to eight
hours, while `surface_decay_log10_per_day` is a per-day pool law; the matrix the
ship setting favours shows no phase split; and Rockey's own analysis attributes
the dry-phase rate to residue morphology rather than to drying, having found
inactivation associated with neither protein content, salt content nor drying
time. Adopting either set would mean choosing a matrix, a droplet volume, an RH
and a time window — four freedoms in exchange for one scalar, which is the trade
§7.1 exists to refuse. **The values are therefore reported and the unit stops;
adoption is a separate decision, and not this unit's.**

**The complication to carry forward.** That airway surface liquid retains
infectivity with decay unassociated with drying time means the phase boundary may
not be drying in the matrix this model needs, and the wet/dry split may be partly
a matrix effect for which §4's selection criterion, not a time axis, is the right
instrument. §7.3's sourcing unit should be rewritten around deposit volume and
matrix rather than around finding the two rates, which now exist.

### 8.1 Assay endpoint: infectivity, not RNA

R2's assay-endpoint question is resolved here and is **unaffected** by the scope
supersession. Greatorex 2011 measures, on the same coupons, 0.06 log10 RNA loss
against >4.2 log10 infectivity loss at 24 h; Thompson 2017
(`10.1016/j.jhin.2016.12.003`) recovers viable virus for up to two weeks on
stainless steel while PCR stays positive for seven. Our pools are denominated in
genome copies and the dose-response consumes copies, so decaying a pool at an RNA
rate is dimensionally consistent and epidemiologically wrong by up to four orders:
it keeps material epidemiologically available long after no infectious virus
remains.

Tranche 5 §1 resolved this for norovirus in favour of the **infectivity** rate.
**The influenza row inherits that resolution**: whatever rate or rates eventually
land in `surface_decay_log10_per_day` for `influenza_a` must be measured on an
infectivity endpoint, and a genome-copy pool decayed at an infectivity rate is
carrying an infectivity-equivalent availability state whose conversion is itself
an open item — not a licence to substitute the RNA rate because the units match.
