# Consensus tranche 2 — the high-sensitivity factors, and a genogroup error in our own interval

**Status:** Reference. Search output and its reading. **One correction to a
previously-published interval**, recorded below and carried into the open ledger.
No profile JSON, constant or code changed.

Search order was the Morris ranking in
[`../norovirus/bounded_screen_results.md`](../norovirus/bounded_screen_results.md),
not ease of search: the top-ranked factor first. Nine Consensus searches,
peer-reviewed filter on.

---

## 1. The correction: our non-secretor interval was built from the wrong genogroup

**What we published.** PR #367 withdrew the standing plan to set
`innate_nonsusceptible_fraction = 0.2` and replaced it with a sourced interval
of **0.00 – 0.16**, on the argument that "non-secretors are partially
susceptible, not protected, so the removed-fraction *mechanism* is the defect."
The derivation used Teunis et al. 2020's Se−/Se+ infection-risk ratio, and
Rouphael et al. 2022's GII.2 challenge in which 4 of 8 secretor-negative
subjects fell ill at the top dose.

**What the full evidence says.** Teunis et al. 2020, *Epidemics* 32:100401
reports mean infection risk at a dose of **one genomic copy**, stratified both
ways — and the two genogroups are not remotely alike:

| | Se+ | Se− | Se− / Se+ |
|---|---:|---:|---:|
| **GI** | 0.28 | **0.00007** | **0.00025** |
| GII | 0.076 | 0.015 | 0.197 |

We read the GII row. **Our profile is `norwalk_gi` — GI.1.** For GI, secretor
negativity is not a five-fold reduction; it is a factor of four thousand. It is
corroborated by the strongest study in this literature: Lindesmith et al. 2003,
*Nature Medicine* (1,131 citations), a GI.1 human challenge in which the FUT2
null allele was **"fully penetrant against Norwalk virus infection — none of
these individuals developed an infection after challenge, regardless of dose."**

So for the profile we actually ship and screen, the removed-fraction mechanism is
**correct**, and the ceiling is the non-secretor prevalence itself rather than a
partial-susceptibility discount:

```
0.2 × (1 − 0.00025) ≈ 0.1999
```

Edison's 0.2 is defensible for `norwalk_gi`. Our 0.00 – 0.16 interval is not: its
upper end is a GII discount applied to a GI profile, and it excludes the
defensible value. **The withdrawal was wrong, for the profile we run.** Task #21
comes back off the shelf.

The genogroup-stratified evidence, for whichever arm is being parameterised:

| Genotype | Challenge | Se+ | Se− | Reading |
|---|---|---|---|---|
| GI.1 | Lindesmith 2003, *Nat Med* | infected | **0 / all, any dose** | Full removal correct |
| GII.4 | Frenck 2012, *JID* (23 Se+, 17 Se−, 5×10⁴ RT-PCR U) | 13/23 ill (57%) | **1/17 ill (5.9%)** | ~0.10 relative; strong, not complete |
| GII.2 | Rouphael 2022, *JID* (top dose) | 10/12 ill (83%) | **4/8 ill (50%)** | ~0.6 relative; barely restricted |

## 2. The deeper problem this exposes: the profile's genotype is inconsistent

Correcting the interval surfaces something worse than the interval. The
`norwalk_gi` profile is GI.1 by name, and its dose-response is Teunis 2008 fitted
to GI.1 Norwalk challenge data — but **it is scored against VSP cruise
outbreaks, which are predominantly GII.4**, and the ledger's own reasoning refers
to "the mixed GII.4/GII.17/GII.2 profile the campaign runs". The arm is
GI-parameterised and GII-validated.

That is not fixable by choosing a number, and it should not be papered over by
choosing the genogroup whose interval is most convenient. Either:

- **the arm is GI.1** — then the non-secretor fraction is ≈ the prevalence, the
  Teunis 2008 α/β are the right dose-response, and we must say plainly that we
  are scoring a GI.1 model against GII.4-dominated observations; or
- **the arm is meant to be cruise-realistic GII.4** — then the removed fraction
  drops to ≈0.16 or below, *and the shipped α/β are the wrong genogroup's
  dose-response*, which is a far larger change than the susceptibility term.

Note the asymmetry the Teunis table forces: GI is **3.7× more infectious per
genome copy** in Se+ hosts than GII (0.28 vs 0.076). A genogroup switch moves
infectivity and susceptibility in *opposite* directions, so the two errors
partially cancel in the aggregate attack rate — the configuration in which a fit
looks best and means least. This is the same structure as the COVID emission/β
finding in #366, arrived at from the norovirus side.

Recorded as an open question, not decided here. It is a modelling-scope decision
and it belongs to the user.

## 3. Emesis titre — sourced, with a genome-to-infectious caveat

`emesis_titre_log10` ranked second in the screen. The shipped source is right and
now has a bound around it:

- **Kirby et al. 2016, *PLoS ONE* 11(4)** (already Grade B in-repo): mean emesis
  titre **8.0 × 10⁵ GEC/mL for GI**, **3.9 × 10⁴ GEC/mL for GII** (p = 0.02);
  mean **1.7 × 10⁸ GEC shed per vomiting subject**; 40–100% of infected subjects
  vomited at least once, and only 45% of vomiters also had diarrhoea.
- The GI/GII gap is **20×**, and it points the same way as §2: the value we use
  depends on a genogroup decision we have not made.
- **New, and it bears on the dose axis:** Hagbom et al. 2021, *EID* 27(8)
  recovered **replication-competent** norovirus from **25% of vomit samples**.
  Our emesis pathway emits genome copies into a dose axis whose infectious-unit
  interpretation is unresolved; a measured genome→infectious success fraction of
  0.25 on this route is the first empirical handle on that conversion. It is
  *not* a licence to multiply anything yet — it is a detection frequency in a
  small sample, not a titre ratio.

## 4. Influenza — the one arm where emission and dose can share a unit system

Confirmed, and now with an interval rather than a point:

- **Yan et al. 2017, *PNAS*** (142 confirmed cases, days 1–3): geometric mean
  **3.8 × 10⁴ RNA copies / 30-min fine** (≤5 µm) and **1.2 × 10⁴ coarse**;
  infectious virus cultured from **39%** of fine aerosols; NP swab load
  8.2 × 10⁸/swab **not** associated with fine-aerosol RNA — upper and lower
  airway shedding compartmentalised and independent.
- **Chow et al. 2023, *Viruses* 15:2033** gives the *range* directly:
  **9 – 1.67 × 10⁵ copies/min fine**, **10 – 1.24 × 10⁴ coarse**, n = 31,
  culturable from 29% of fine fractions. Five orders of magnitude wide — which is
  the honest width of a respiratory emission interval, and exactly the kind of
  bound the admissible-region test is built to consume.
- **Fabian et al. 2008, *PLoS ONE*** is the third independent measurement.

Dose side, human, in TCID50:

- **Han et al. 2019, *CID*** — A/Bethesda/MM1/H3N2 dose escalation, **10⁴ to 10⁷
  TCID50** intranasal, 37 participants: mild-to-moderate influenza disease
  **only** at 10⁶ (44%) and 10⁷ (40%).
- **Caveat that must travel with it:** intranasal instillation of a liquid
  inoculum is not aerosol inhalation, the deposition site differs, and the
  response is flat between 10⁶ and 10⁷. A `k` fitted to this is weakly
  identified and its unit is a *challenge* TCID50, not an inhaled one. It is a
  bound on the ID50's order of magnitude, not a dose-response curve.

So influenza can source emission and dose in one unit system, but the bridge
between "copies/min exhaled" and "TCID50 instilled" is still a conversion we
would have to declare. That is a smaller gap than COVID's, not an absent one.

## 5. Conditional illness probability — the shipped η, γ have a shape problem

`illness_probability` (η = 0.508, γ = 0.095, inherited from `Person.java`) is a
dose-dependent conditional-illness function. Two sources bear on it:

- **Liu et al. 2026, *Water Research*** (the meta-analysis already cited in
  #369): conditional illness probability is **best represented by a one-inflated
  beta distribution** for both GI and GII, "with GII showing a stronger
  concentration near 1". A one-inflated beta is not a dose-dependent function at
  all — it says a substantial point mass of infected hosts become ill with
  probability one, and the rest are spread. That is a different functional form
  from ours, and the same paper concludes aggregation parameters "function as an
  effective fitting parameter rather than a directly measured property".
- **Frenck 2012** gives a clean conditional rate for GII.4: 13 ill of 16
  infected = **81%**, at a single dose — consistent with A2's 0.68–0.81 band.

Reading: our η/γ are not obviously wrong in magnitude, but the *family* is
questionable and the evidence favours a form with a mass at 1. Filed for the
dose-response family question, not corrected here.

## 6. Null and weak results, recorded so they are not re-searched

- **Diarrhoeal stool mass per day** — no usable distribution found. What the
  literature offers is the *diagnostic definition* (">250 g of unformed stool per
  day", three or more unformed stools per day; Archuleta 2021 and others), which
  is a threshold for calling something diarrhoea, not a measured mass
  distribution for norovirus cases. The paediatric racecadotril trials (Salazar-
  Lindo 2000, *NEJM*) measure 48-hour stool output in grams but in children under
  3 with watery diarrhoea of mixed aetiology. `environmental_faecal_release_log10_g_per_epoch`
  therefore still has no direct source, and this search does not close it.
- **COVID severity proportions** — the top hits are single-centre asymptomatic-
  fraction retrospectives, several of them preprints despite the filter. Nothing
  here is yet a five-state severity vector for task #31; that needs a targeted
  search against a large stratified cohort, not this query.

## 7. What changed in the repository from this tranche

- The open ledger's non-secretor entry is corrected: the withdrawal is itself
  withdrawn for `norwalk_gi`, and the genogroup inconsistency is recorded as the
  open question behind it.
- The interval table in
  [`../proposals/bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md)
  §3.3 carries the genogroup-conditional interval instead of a single 0.00–0.16.
- Edison Q5 is re-asked: the question is no longer "was 0.2 the prevalence" but
  "which genogroup is this profile supposed to be".

Nothing else. No constant moved; the screen's ranking is unaffected, since
`innate_nonsusceptible_fraction` was screened over 0.00–0.16 and its top-ranked
position can only strengthen if the defensible range extends to 0.20.
