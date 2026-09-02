# Parameter Sourcing Bundle: the count, the first search tranche, and what only Edison can answer

> **Status:** Reference. This records a provenance count, a Consensus search
> tranche, and an open question list. **No constant is changed by this document
> and no interval here is adopted.** Adoption goes through
> `.agents/skills/model-parameter-provenance/SKILL.md` and the interval ledger in
> [`../proposals/bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md).

## 1. How many profile scalars carry a citation

Counted from the `Source` column of `formal_spec_v2.md` Appendix A, excluding the
four structural rows (`pathogen_id`, `name`, `category`, `transmission_routes`)
and using the grouping of the
[COVID audit](../covid/covid_parameter_provenance_audit.md) so the arms are
comparable.

| Arm | Non-structural profile scalars | External citation | Inherited from the Java ABM | In-repo spec | Derived | Blank |
|---|---:|---:|---:|---:|---:|---:|
| `sars_cov2_resp` | 25 | 8 | 1 | 2 | 1 | 13 |
| `norwalk_gi` | 35 | 6 | 6 | 2 | 1 | 20 |
| `influenza_a` | ~25 (no Appendix entry) | 2 | — | 2 | 1 | rest |

Norovirus's six: Lee et al. 2013 (incubation distribution, median, dispersion),
Atmar et al. 2008 (presymptomatic window), Teunis et al. 2008 (the dose-response
*functional form* only — its $\alpha$ and $\beta$ are `Person.java`), and van
Doremalen et al. 2020 (`airborne_half_life_hours`). Influenza's two are Lessler
et al. 2009 (incubation) and Ip et al. 2017 (presymptomatic window).

Two findings the count itself produced:

1. **`norwalk_gi.airborne_half_life_hours = 1.1` is cited to van Doremalen et al.
   2020, which is the SARS-CoV-2 aerosol measurement** — the identical value in
   `sars_cov2_resp`. It is a cross-pathogen borrow presented as a citation, and
   it is the only source in the norovirus environmental block.
2. **`surface_decay_per_day` is sourced on the COVID arm and blank on the
   norovirus arm.** The audit that sourced COVID's 0.95 to a 5.55 h half-life did
   not touch norovirus's 0.25, which is the arm the campaigns fit.

The count understates norovirus in one direction that must be stated with it: the
sourcing of the last several changes went into engine-level constants Appendix A
does not list — emesis titre, volume, aerosol fraction and deposition footprint
(Grade B), shared-surface contact rates by zone class, POLYMOD contact rate,
routine cleaning coverage 0.37 (Grade A for cruise public restrooms) and the
hypochlorite log-reductions (Grade B). Norovirus is the best-sourced arm
mechanistically and among the worst inside its own profile. The
[Morris screen](../norovirus/bounded_screen_results.md) then ranked two profile
scalars into its top three.

## 2. Consensus tranche 1

Queries were fixed from the definition of each quantity before the model's
current value was consulted, per
[`searching-literature-evidence`](../../.agents/skills/searching-literature-evidence/SKILL.md).
Grades below are the grade the value *would* carry if adopted, not a grade now in
force.

### 2.1 `shedding_variance_log10` (blank; clears the noise floor on whole-ship attack rate)

[Teunis et al. 2014, *Epidemiol Infect*](https://doi.org/10.1017/S095026881400274X)
fits a multilevel Bayesian longitudinal shedding model to 102 subjects
(symptomatic and asymptomatic, patients and staff) and reports peak levels
averaging $10^5$–$10^9$ per gram of faeces and shedding durations averaging
8–60 days. That is the first empirical basis this parameter has had: a roughly
4-log10 spread in individual peaks. It is *not* yet the value — the between-subject
standard deviation on the log10 scale has to be read off the paper's fitted
variance components, not inferred from the range in the abstract, and the
model's $\sigma$ multiplies a curve whose own units are unresolved (§5, Q2).
Would be Grade B (hospital outbreaks and volunteers, not cruise).

### 2.2 `surface_decay_per_day` (blank on the norovirus arm)

No paper measures human norovirus infectivity decay on a dry hard surface over
days; the human virus was unculturable until the enteroid system and the
surrogate work is what exists.

- [Leblanc et al. 2019, *Food Microbiol*](https://doi.org/10.1016/j.fm.2019.103257):
  MNV-1 on stainless steel at 21 °C lost >4 log of viability in 14 days
  ($\geq$ 0.29 log10/day, i.e. a proportional loss $\geq$ ~0.49/day). Grade B,
  surrogate virus on a food-contact surface.
- [Kim et al. 2014, *Food Environ Virol*](https://doi.org/10.1007/s12560-014-9154-4):
  MNV survival across six food-contact surfaces, including stainless steel.
- Kennedy et al. 2023: human GII.4 in filter-sterilised surface water at
  15–20 °C, infectivity measured in the enteroid system, spans *no significant
  decay* to $k = 2.2$ day$^{-1}$ — a different medium, useful only as an outer
  bracket.

The shipped 0.25/day is 0.125 log10/day, i.e. **slower than the surrogate
measurement on the same surface material**, and the direction of that gap
inflates the fomite pool. Any adopted interval must be wide and must say which
medium it came from.

### 2.3 `norwalk_gi.airborne_half_life_hours` — null result

No measurement of airborne norovirus decay or half-life was found.
Alsved et al. 2019 (*Clin Infect Dis*) detects airborne norovirus in hospital
outbreaks, Bonifait et al. 2015 quantifies it in healthcare facilities, and
[Tung-Thompson et al. 2015, *PLoS ONE*](https://doi.org/10.1371/journal.pone.0134277)
quantifies aerosolisation of the MS2 surrogate during simulated vomiting, but
none of them gives a decay rate. **Recorded as a null result so the search is not
repeated.** The honest options are to declare the parameter Grade C or to bound
it by deposition physics for the vomitus particle-size distribution; continuing
to cite a SARS-CoV-2 paper for it is not one of them.

### 2.4 An unexpected observable: cruise-ship environmental swabs

[Park et al. 2015, *Appl Environ Microbiol*](https://doi.org/10.1128/aem.01657-15)
swabbed case cabins and common areas on a cruise ship during a gastroenteritis
outbreak: 17 of 92 samples (18.5%) positive for GII, with **case-cabin loads of
80–31,217 RNA copies per swab against 16–113 in public spaces**, on a validated
recovery protocol (macrofoam swabs, 2.2–36.0% recovery on stainless steel).
[Park et al. 2017, *JoVE*](https://doi.org/10.3791/55205) reports 127 of 217
(58.5%) positive across cruise ships and long-term-care facilities.

This is a measurement of the quantity the model's fomite pool *is*, in the
setting the model simulates, with a stated recovery efficiency — and the
cabin-versus-public ratio bears directly on the cabin-localization fraction $f$
(open task: measure or externally bound $f$), which the Park surface work
identified as its binding uncertainty. It is a candidate anchor rather than a
parameter, and it would be an anchor on a channel nothing currently scores.

### 2.5 SARS-CoV-2 emission as a rate (blocks the #30 re-source)

The audit's finding was dimensional: the profile's emission term is a nasal
concentration where the model needs a rate. Rate measurements exist.

- [Ma et al. 2020, *Clin Infect Dis*](https://doi.org/10.1093/cid/ciaa1283):
  patients exhaled **millions of RNA copies per hour**; exhaled breath was
  positive in 26.9% (n = 52) against 5.4% of surfaces and 3.8% of air samples.
- [Coleman et al. 2021, *Clin Infect Dis*](https://doi.org/10.1093/cid/ciab691):
  viral load in coarse (>5 µm) and fine ($\leq$ 5 µm) aerosols while breathing,
  talking and singing — the same fine/coarse split as the influenza EMIT work.
- Malik et al. (case series): 8.6 × 10³–4.1 × 10⁴ copies/h in a mild case, up to
  2 × 10⁵ copies/h in an asymptomatic one. Small-n, but the asymptomatic figure
  being the higher one bears on the profile's unsourced 1.5-log10 symptomatic /
  asymptomatic offset.
- Lane et al. 2023 reports copies exhaled per minute across the course of
  infection — the shape as well as the scale. Preprint (medRxiv); grade
  accordingly.

### 2.6 The dose-response denominator, and a family problem

The candidates found are quanta-based, not beta-Poisson:
[Aganovic et al. 2022, *Build Environ*](https://doi.org/10.1016/j.buildenv.2022.109924)
derives a quanta–RNA relationship and average emission of **0.13 quanta/h
breathing and 3.8 quanta/h speaking** for the original strain, and
[Buonanno et al. 2020](https://doi.org/10.1016/j.envint.2020.105794) estimates
quanta emission from mouth viral load and activity level.

A quantum is *defined* by $P = 1 - e^{-\text{dose}}$. Adopting a quanta-based
denominator therefore changes the COVID dose-response **family** from
beta-Poisson to exponential — a design decision, not a parameter substitution,
and the screen's rule is that families are separate runs and never interpolated.
It would however fix the denominator in a unit system that the copies-per-hour
emission measurements above can be expressed in, which is what #30 needs.

### 2.7 `influenza_a.base_susceptibility = 0.65` — a scenario input, not a constant

Seroprevalence studies exist in quantity, and that is the problem: pre-existing
immunity is specific to season, subtype, age structure and vaccination coverage,
so no literature value is a property of the pathogen. The honest treatment is to
move it out of the profile and into the scenario, sourced per outbreak — for the
2009 Sydney co-circulation voyage, from that season's serology and coverage.
Otherwise it is the free knob the influenza arm would overfit through.

## 3. Query list not yet run

Ranked by the Morris ranking first, then by what blocks a task.

| # | Quantity | Query |
|---|---|---|
| 1 | Norovirus secretor-negative *reduced susceptibility* multiplier (top-ranked factor; mechanism known wrong) | `norovirus secretor-negative infection risk relative susceptibility GII.2 GII.17 challenge dose` |
| 2 | Emesis titre distribution, not central value (2nd-ranked factor) | `norovirus vomitus viral load genome copies per mL range emesis` |
| 3 | Faecal mass released to the environment per epoch (construction parameter, 3rd-ranked) | `diarrhoeal stool mass per episode grams adults gastroenteritis` |
| 4 | `illness_probability` $\eta$, $\gamma$ (inherited from `Person.java`, both arms) | `norovirus probability of illness given infection dose-dependent volunteer challenge` |
| 5 | `recovery_day` = 3 (inherited) | `norovirus symptom duration hours adults outbreak median` |
| 6 | `surface_deposition_fraction` (inherited; COVID's is norovirus's halved) | `virus deposition fraction from hand to surface per contact transfer efficiency` |
| 7 | Influenza exhaled emission (already partly held: Yan 2018 / Milton 2013) | `influenza exhaled aerosol infectious virus per 30 minutes fine coarse` |
| 8 | COVID severity distribution for the five-state model (#31) | `SARS-CoV-2 asymptomatic mild moderate severe proportion 2020 ancestral cohort` |

## 4. What the literature cannot answer — questions for Edison Science

These are provenance questions about the upstream model, not about the world. No
paper can settle them, and each one currently blocks a grade.

1. **`Person.java` $\alpha = 0.111$, $\beta = 32.81$:** what data were these
   fitted to, and in what dose unit is $\beta$ expressed? The repo cites Teunis
   2008 for the *form* only, and the dose axis is the reason the COVID emission
   scale is not identifiable.
2. **What is the unit of `shedding_curve_log10`?** Per gram of faeces, per epoch,
   or per infected host per day? The same key drives the respiratory arms, where
   its peak of $10^9$ is 2–4 orders above measured exhaled emission.
3. **Why is `sars_cov2_resp.surface_deposition_fraction` exactly half
   norovirus's $10^{-4}$?** The audit found the value is norovirus's halved with
   no stated reason.
4. **`illness_probability` 0.508 / 0.095 (norovirus) and 0.4 / 0.12 (COVID):**
   measured, fitted, or chosen? COVID's are unattributed near-neighbours of
   norovirus's.
5. **Are `transmission_route_weights` intended as shares or as independent
   multipliers?** They sum to 1.0 while acting multiplicatively, so the realised
   fomite share measured 100% against a nominal 0.30.
6. **`dose_adjustment`** is documented as $-\log_{10}$ grams of stool released per
   epoch. What is it supposed to mean on the respiratory profiles, which pay 3.0
   (COVID) and 1.5 (influenza) of it?
7. **`influenza_a`: exponential $k = 0.18$ and `base_susceptibility = 0.65`** —
   source, and which season's immunity is 0.65 meant to represent?
8. **Which Edison-bundle values are placeholders by intent** (reassortment,
   `superinfection_susceptibility`, immune waning) versus measured, so they are
   not audited as if they were claims?
9. **Is there an Edison-side derivation for the four VSP class IQRs** that #360
   withdrew for having no provenance in this repo?

## 5. Rules this document is held to

- A search result is not a parameter, and nothing here is adopted.
- Queries were fixed from the definition of the quantity before the model's value
  was consulted; no query was chosen because its answer would help an anchor.
- Null results are recorded as results (§2.3).
- Where only surrogate or cross-medium evidence exists, the interval says so and
  the grade drops accordingly.
