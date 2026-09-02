# Provenance request to Edison Science

**Status:** Sent as a query; no answer incorporated. Nothing here changes a model
constant. Companion to
[`parameter_sourcing_bundle.md`](parameter_sourcing_bundle.md), which holds the
independent literature side of the same exercise.

This document is written to be readable outside the repository: an external
collaborator should be able to answer it without a checkout.

---

## 0. Why we are asking

Crusher's pathogen profiles carry roughly 85 non-structural scalars across the
three arms we intend to score (`norwalk_gi`, `sars_cov2_resp`, `influenza_a`).
Sixteen of them carry an external citation. Of the rest, a block was inherited
verbatim from the upstream Java ABM (`Person.java`, `ViralParticle.java`) and
the remainder are blank. An independent literature search can tell us whether a
measurement of a quantity *exists*; it cannot tell us **what the shipped number
was originally derived from, in what units, and against what data it was
tuned**. Only the authors of the upstream model can.

The reason this matters now, rather than as bookkeeping: we are moving every
parameter from a point value to a sourced *interval*, screening which intervals
the outputs are actually sensitive to, and then asking whether any point in the
resulting box reproduces the observed outcomes simultaneously. A number with
unknown provenance cannot be given an interval, and a number that was
originally *fitted* to an outcome must not be re-scored against that same
outcome. So each question below blocks either an interval or a scoring
decision.

Counts, per arm, on one grouping (non-structural profile scalars):

| Arm | Scalars | External citation | Inherited from the Java ABM | In-repo spec | Derived | Blank |
|---|---:|---:|---:|---:|---:|---:|
| `sars_cov2_resp` | 25 | 8 | 1 | 2 | 1 | 13 |
| `norwalk_gi` | 35 | 6 | 6 | 2 | 1 | 20 |
| `influenza_a` | ~25 | 2 | — | 2 | 1 | rest |

---

## 1. What we would like for each value

For any value you recognise, whatever subset you can give:

1. **Origin** — Korkin ABM, a paper, a fit, an engineering default, or a
   placeholder.
2. If a fit: **what data**, and **what quantity was being matched**.
3. **Units**, explicitly, including the unit of the dose axis.
4. Whether it was **adapted from another pathogen**, and by what argument.
5. A **defensible interval**, which is more useful to us than a better central
   estimate.
6. Whether it is a **construction parameter** (a modelling convention with no
   external referent) rather than a physical quantity.
7. Whether the value was **chosen to reproduce a target** — this one is not a
   criticism, it is the single fact we most need, because such a value cannot be
   scored against that target again.

"Placeholder, by intent" is a complete and welcome answer. We would rather
record a declared placeholder than manufacture a citation for it.

---

## 2. Norovirus (`norwalk_gi`)

**Q1. `Person.java` dose-response $\alpha = 0.111$, $\beta = 32.81$.**
What data were these fitted to, and **in what dose unit is the dose axis
expressed** — genome copies, RT-PCR units, infectious units? Our profile cites
Teunis et al. 2008 for the functional *form* only. The dose unit is the
load-bearing question: the model draws a per-host susceptibility
$r \sim \mathrm{Beta}(\alpha,\beta)$ once and then evaluates
$P(\text{establish}) = 1 - \exp(-r\,D)$ per epoch, so $r$ and $D$ enter **only
as a product**. Any rescaling of the emission side can be absorbed exactly by
rescaling the Beta mean. Without an externally fixed dose unit, emission scale
and dose-response are one parameter, not two.

**Q2. `illness_probability` $\eta = 0.508$, $\gamma = 0.095$.**
Measured, fitted, or chosen? They enter
$P(\text{symptomatic}) = 1 - (1 + \eta D_{\text{acq}})^{-\gamma}$, which is
dose-conditioned, so they inherit the same unit question as Q1. Note that the
COVID profile carries 0.4 / 0.12 — unattributed near-neighbours of these — which
is what makes us suspect a shared origin rather than two independent sources.

**Q3. `recovery_day = 3`, `presymptomatic_shedding_days = 0.5`.**
Recovery is a fixed duration, not a draw. Was 3 a median of something, or a
convention?

**Q4. `surface_deposition_fraction = 1e-4` (`ViralParticle.java`), and why is
the SARS-CoV-2 value exactly half of it (5e-5)?**
We can find no argument for the factor of two.

**Q5. `innate_nonsusceptible_fraction` — was 0.2 meant as full resistance or as
a prevalence?** The Edison bundle carries 0.2 with `nonsusceptible_mechanism =
FUT2_nonsecretor`; the active profile carries 0.0. The arm is GII — that part we
have now answered ourselves, from the profile's `name`, `genotypes` and
`incubation.notes` — and for GII, Teunis 2020 gives Se− infection risk at one
genomic copy of 0.015 against Se+ 0.076, with non-secretors only partially
resistant (Rouphael's GII.2: 4 of 8 Se− ill at top dose; Frenck's GII.4: 1 of
17). A **fully removed** fraction is therefore the wrong shape, whatever its
size, and its ceiling is ≈0.16. For GI the picture is entirely different — Se−
0.00007 against Se+ 0.28, and Lindesmith 2003 found the FUT2 null allele fully
penetrant in GI.1 challenge — so **was the 0.2 taken from GI evidence, or from a
non-secretor prevalence figure applied as though it were full resistance?** In a
Morris screen over the sourced box this factor ranks **first** on every passenger
channel, so its mechanism matters more than its value.

This raises Q1 rather than settling it: the arm simulates GII.4 / GII.17 / GII.2
but its dose-response is recorded as fitted to oral **Norwalk GI.1** inoculum,
and GI is 3.7× more infectious per genome copy than GII in secretor-positive
hosts. If that provenance is right, the arm has a genogroup mismatch at its most
sensitive point.

**Q6. `airborne_half_life_hours = 1.1`, cited in our tables to van Doremalen et
al. 2020.** That is the SARS-CoV-2 aerosol measurement, and it is the identical
value carried by the COVID profile. We can find no measurement of airborne
norovirus decay in the literature at all (recorded as a null result). Was this a
deliberate cross-pathogen borrow, or has a norovirus source been lost?

**Q7. `surface_decay_per_day = 0.25`.** Blank in our tables. It implies 0.125
log10/day, slower than the closest surrogate measurement we can find (MNV-1 on
stainless steel, ≥0.29 log10/day, Leblanc et al. 2019), and the difference
inflates the fomite reservoir. Origin?

---

## 3. SARS-CoV-2 (`sars_cov2_resp`)

**Q8. `shedding_curve_log10` — what is the unit, and what is the referent
medium?** The v3 spec states $\log_{10}$(copies/g), and `dose_adjustment` is
documented on the norovirus side as $-\log_{10}$ of the **grams of stool**
released per epoch (we have since renamed that key
`environmental_faecal_release_log10_g_per_epoch`). On a respiratory profile,
what is the gram of? The COVID profile pays `dose_adjustment = 3.0` and
influenza 1.5, i.e. the respiratory arms are dividing an emission by a
stool-mass term. If the intended reading is "copies per gram of respiratory
fluid × grams of respiratory fluid emitted per epoch", say so and we will source
the second factor against measured exhaled aerosol volume; if the term is doing
something else, we need to know before we re-derive it.

**Q9. `dose_response` $\alpha = 0.18$, $\beta = 58.0$.** This was attributed in
our notes to "Watanabe 2020 derived models for SARS-CoV-1, adapted for CoV-2".
We checked and withdrew that attribution: the paper is Watanabe et al. **2010**,
*Risk Analysis* 30(7); it reports an **exponential** model
($k = 4.1\times10^{2}$ PFU) and states that beta-Poisson gave no statistically
significant improvement; and its data are **murine**, with doses in PFU. So the
shipped $\alpha$/$\beta$ are, as far as we can establish, unsourced. Do you have
their real origin — and if they were adapted from SARS-CoV-1, what was the
adaptation argument and what happened to the dose units?

**Q10. Unsourced remainder:** `recovery_day = 7`,
`shedding_variance_log10 = 1.2`, `base_susceptibility = 1.0`, the six
`transmission_route_weights`, `surface_decay_per_day = 0.95`. Of these, 0.95
turns out to match van Doremalen's 5.6 h surface half-life almost exactly
(5.55 h) — was that intentional, or a coincidence we should not read as a
source? The others we would like graded.

**Q11. `severity_model` and `observation_model` are both absent on this
profile** while norovirus has both. Was that a deliberate scope decision? We
intend to add them; if upstream already has a five-state severity vector for
SARS-CoV-2, we would rather adopt it than invent one.

---

## 4. Influenza (`influenza_a`, inactive)

**Q12. Exponential `k = 0.18`.** Source, and in what unit — TCID50, EID50,
genome copies? Influenza is the one respiratory arm where emission and
dose-response could be sourced in a *single* unit system (Yan et al. 2017
measured exhaled viable virus; human challenge studies give dose-response in
TCID50), so the unit answer decides whether that is possible.

**Q13. `base_susceptibility = 0.65`.** Which season, which population, and which
route of immunity (prior infection, vaccination, or both)? Our reading is that
this is a scenario input rather than a pathogen constant, and that leaving it in
the profile makes it the one place an influenza arm could quietly overfit.

**Q14. Which values in the ten-pathogen bundle are placeholders by intent** —
specifically reassortment, `superinfection_susceptibility`, immune waning, the
transmissibility/shedding ranges [0.8, 1.25] and the immune-escape range
[0.01, 0.3]? We do not want to audit a declared placeholder as if it were a
claim.

---

## 5. Cross-cutting

**Q15. Are `transmission_route_weights` intended as shares or as independent
multipliers?** They sum to 1.0, which reads as shares, but they act
multiplicatively. In our instrumented runs the realised fomite share measured
100% against a nominal 0.30.

**Q16. What was the upstream model trained or calibrated against?** If any of
the values above were tuned so that a simulated outbreak reproduced an observed
one, we need to know which observation, because we cannot then use that
observation to validate them.

**Q17. Is there an Edison-side derivation for the four VSP class attack-rate
IQRs** we were scoring against? We withdrew them: they have no derivation
anywhere in this repository and do not reproduce from the VSP outbreak series
under any binning we tried.

---

## 6. What we are not asking for

Point estimates to fill blank fields. A supplied number with no provenance
converts a known gap into an unknown one, which is worse for us than the gap. An
interval with a stated basis, or an honest "placeholder", is more useful than a
central value.
