# Norovirus observation model: subclinical infection, symptom severity, reporting

Status: design, no code changed yet.

## Why this exists

VSP/MIDRS is a syndromic register: it counts passengers and crew who *reported*
gastrointestinal symptoms to the ship's medical centre. There is no serology and
no denominator of infection anywhere in the record — specimens, when collected,
come from already-ill passengers and establish aetiology, not attack rate. So
the VSP attack rate is

    reported clinical AGE / complement

and it is three links away from the quantity our engine natively produces
(infection attack rate). The public health response is part of the observation
process, not merely a modifier of the epidemic.

Fitting a single delivered-dose parameter against the VSP distribution while
the two intervening links are wrong is what we have been doing, and it can
match the target for the wrong reasons.

## The chain, with independent anchors

| Link | Quantity | Literature anchor | Source |
|---|---|---|---|
| exposure → infection | P(inf \| dose) | beta-Poisson α=0.111, β=32.81 | Teunis 2008 |
| infection → illness | P(ill \| inf) = 1 − asymptomatic ratio | **0.68–0.81** overall; **≈0.59** for GII.4 | Miura 2018 (32.1% overall, 40.7% GII.4); Misumi & Nishiura 2021 (18.6% overall, 25.8% GII.4) |
| illness → reported | infirmary capture | **0.60** (reporting multiplier 1.67) | Wikswo 2011 (95/236 cases did not report) |
| illness attack rate | whole-ship cohort | **15.4% ill** | Wikswo 2011 retrospective cohort |
| infection → lab positive | P(test +) | ≈0.63 | Misumi & Nishiura 2021 |
| cross-sectional screen | PCR+ asymptomatic prevalence among exposed | 0.18–0.22 | Wang 2023 (21.8% global), Wang 2024 (17.6% China) |

Two of these are anchors we have never used, and both are independent of VSP:
the asymptomatic ratio pins `P(ill | inf)`, and the cohort study pins the
illness attack rate. That converts the fit from one free parameter against one
target into an over-determined system, which is the only way to know the fit is
right rather than merely coincident.

Note PCR+ asymptomatic *prevalence* among exposed cohorts is not the
asymptomatic *ratio*: it mixes true silent infection with post-symptomatic
shedding (Bucardo 2018, Qi 2018). Only the ratio belongs on the illness link.

## What the current model does

Measured on the σ pilot (10 seeds/cell, one index case, hourly clock, post-#340):

| hull | σ | dose_adj | infection AR | ever-ill | reported | ill/inf | rep/ill |
|---|---|---|---|---|---|---|---|
| classic | 1.0 | 2.5 | 0.800 | 0.336 | 0.059 | **0.419** | **0.176** |
| classic | 1.0 | 3.0 | 0.790 | 0.187 | 0.029 | 0.236 | 0.154 |
| expedition | 1.0 | 2.5 | 0.663 | 0.122 | 0.013 | 0.184 | 0.104 |
| expedition | 1.0 | 3.0 | 0.402 | 0.049 | 0.006 | 0.122 | 0.129 |

Across all 16 σ×dose cells: `ill/inf` ∈ 0.12–0.59 against a target of 0.68–0.81,
and `rep/ill` ∈ 0.09–0.22 against a target of 0.60. Both links are low, in the
same direction, and their product (0.02–0.13 versus a literature ≈0.42) is
compensated by an infection attack rate of 0.55–0.80 where the cohort data
implies ≈0.22. The reported rate lands in the VSP range as the product of three
errors that cancel.

### Link 3 has a specific, identified cause

Sick-call is driven by `severity_belief`, an *information-state* variable
(`decision_engine/information/diffusion.py`) initialised to 0.1 and raised only
when the outbreak is declared ship-wide. Through
`effective_sick_call_probability`, that multiplies the documented 0.70/day
sick-call rate down to ≈0.06/day before the response fires. A host's decision to
visit the infirmary is therefore a function of the ship's alert status rather
than of how sick that host is — which also makes our fit target depend on the
response branch. The severity of a host's own illness is not represented at all.

### Link 2 is a dose-magnitude statement

`P(ill | inf)` is already dose-conditioned per host (Teunis η=0.508, γ=0.095, on
`acquired_particles` at the moment of infection), so the asymptomatic ratio is
not a free parameter we may set — it is a *prediction*, and it constrains the
per-exposure dose:

| target P(ill \| inf) | required dose at infection | implied P(inf \| that exposure) |
|---|---|---|
| 0.59 (GII.4) | 2.3 × 10⁴ | 0.52 |
| 0.68 | 3.2 × 10⁵ | 0.64 |
| 0.75 | 4.3 × 10⁶ | 0.73 |

Our cells sit far below that. The engine is producing a *diffuse, low-dose*
epidemic: nearly everybody is exposed to a little virus, most infections are
therefore subclinical, and the ship-wide infection attack rate runs to 80%.

The literature describes the opposite shape — a *concentrated, high-dose*
epidemic: a minority of the complement receives a large inoculum (vomiting
events, shared cabins, point-source food and ice), most of those become ill, and
the illness attack rate is ~15%. Both constraints can be satisfied at once, but
only by making exposure rarer and larger, not by raising mean dose. That is a
statement about exposure *concentration* — the variance of delivered dose — and
it is testable against the same three anchors.

## Corroboration: severity and reporting are coupled in the data

The second literature synthesis supplies the mechanism-level check this design
most needed, and it is a correlation rather than a level:

- In a norovirus outbreak reconstruction, **10% of infected hosts caused 57% of
  secondary cases**, and those superspreaders had **half the symptom frequency**
  of other infectors and a **diagnostic delay of 83 h against 47 h**. Mild cases
  are the dangerous ones because they stay in circulation.
- **88% of norovirus infections occurred in public spaces**, with limited
  within-cabin transmission — which both supports concentrated public-space
  exposure and retrospectively justifies leaving cabin-mate dose unattenuated in
  #340 as a minor term rather than a dominant one.
- Passenger attack rate averages **7% against 2% for crew**, a second
  population-split observable we already emit separately.
- A **72 h isolation protocol averted 71%** of potential cases, and movement
  restriction on Diamond Princess cut R0 from 14.8 to 1.78 — containment should
  bite hard, which is the direction #340 moved it.
- Surface-to-surface **transfer rate ≈0.25** minimised infection risk in a
  contact model; our direct-contact transfer fraction is presently an implicit
  1.0, which is a separate open item.

This matters because severity → own sick-call hazard *generates* the
superspreader correlation endogenously instead of requiring a superspreader
parameter: a mild host has a low reporting hazard, is therefore detected late,
and therefore transmits more. So the design gains a fourth validation target —
top-decile transmitters should show roughly half the symptomatic fraction and
~1.8× the detection delay of other infectors.

## Per-pathogen asymptomatic fractions, and a definition trap

| Pathogen | Asymptomatic fraction | Note |
|---|---|---|
| Norovirus | 0.19–0.32 (GII.4 to 0.41) | Miura 2018, Misumi & Nishiura 2021 |
| SARS-CoV-2 | 0.179 (95% CrI 0.155–0.202) *never* symptomatic; 0.32 through full observation; up to 0.74 if pre-symptomatic states are pooled | Mizumoto 2020, Diamond Princess clinical series, Emery 2020 |
| Influenza | ≈0.75 | ship-based estimate |

The SARS-CoV-2 spread is a definitional artefact, not a real disagreement:
Emery's 0.74 pools pre-symptomatic with asymptomatic, Mizumoto's 0.179 counts
only hosts never developing symptoms. Our engine models those as *distinct*
states (`presymptomatic_shedding_days` versus a failed illness draw), so the
validation target for `1 − P(ill|inf)` is the never-symptomatic figure, and
comparing it against the pooled one would be a unit error of the same species as
the ones we spent this week removing.

## Design

Three separately-grounded quantities, none of them fitted to VSP:

1. **Subclinical infection.** Keep the dose-conditioned Teunis illness draw as
   the mechanism; treat the resulting voyage-level asymptomatic ratio as a
   *validation target* (0.19–0.32, GII.4-weighted toward 0.32–0.41), never as a
   parameter. Asymptomatic hosts already shed off `asymptomatic_shedding_log10`
   (peak 10^10.5 against 10^11 symptomatic), consistent with the stool-load data
   showing similar detectability under sensitive PCR; they contribute to the
   infection attack rate and to transmission, and never to the reported rate.
2. **Symptom severity, per pathogen.** A host-level severity draw at onset,
   conditioned on dose where the literature supports it, mapped to a symptom
   burden. Severity drives that host's *own* sick-call hazard; it must not be
   conflated with `severity_belief`, which stays what it is (a behavioural,
   information-diffusion construct). Norovirus severity is graded, not binary —
   modified Vesikari scoring in challenge studies gives mild/moderate/severe
   strata to anchor against.
3. **Reporting.** Calibrate the severity → sick-call mapping so that
   voyage-level capture of symptomatic cases is ≈0.60, with the time-varying
   component (post-declaration behaviour change) explicit rather than implicit.

## Acceptance criteria for the fit

A candidate common dose is accepted only if, conditional on take-off:

- reported passenger rate median inside the VSP class IQR on all four hulls;
- `ill/inf` ∈ 0.68–0.81 (0.59–0.81 if GII.4-weighted);
- `rep/ill` ≈ 0.60 ± 0.05;
- ever-ill passenger rate of order 0.15 (Wikswo cohort), not 0.35–0.47;
- one pathogen profile and one dose-response on every hull;
- passenger:crew reported-rate ratio of order 7:2;
- top-decile transmitters roughly half as often symptomatic, and detected roughly
  1.8× later, than other infectors.

Failing any of the middle three while passing the first is the failure mode this
document exists to prevent.

## References

Wikswo et al. 2011 CID 52(9):1116-22. Miura et al. 2018 J Epidemiol 28:382-387.
Misumi & Nishiura 2021 PeerJ 9:e11769. Wang et al. 2023 BMC Infect Dis 23.
Wang et al. 2024 J Med Virol 96. Qi et al. 2018 EClinicalMedicine 2-3:50-58.
Bucardo 2018 EClinicalMedicine 2-3:7-8. Khan et al. 1994 J Clin Microbiol
32:318-322. O'Reilly et al. 2026 (English GII.4 serology). Teunis et al. 2008
J Med Virol 80:1468-1476. Teunis et al. 2014 Epidemics 8:1-8.
