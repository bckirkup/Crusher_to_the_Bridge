# Severity and Observation Priors for Cruise-Ship Pathogen Models

**Prepared for Benjamin Kirkup**  
**Scope:** the ten pathogen profiles in the cruise-ship model, plus construction rules for three synthetic Starfleet pathogens.

## Executive summary

Disease severity and clinical observation must be separate stochastic layers. Severity is a biological and functional property of an infected person: whether attributable symptoms occur, whether they limit normal activity, and what level of support the illness physiologically warrants. It is not defined by whether the person actually reports, attends the ship infirmary, is admitted ashore, or is entered in a surveillance line list. Those events occur later and depend on policy, access, recognition, incentives, and the observation system.

Use five mutually exclusive infection-conditioned states: `asymptomatic`, `subclinical`, `mild`, `moderate`, and `severe_critical`. Death is not a sixth instantaneous severity state. Fatality is a probability or transition hazard layered on a severity trajectory, usually concentrated in `severe_critical` but not created by assigning deaths to that state and then applying a second infection-fatality or case-fatality draw.

The Vessel Sanitation Program (VSP) acute-gastroenteritis system is directly relevant to norovirus and other enteric acute gastroenteritis (AGE) pathogens. It is not a universal observation system for severe acute respiratory syndrome coronavirus 2 (SARS-CoV-2), influenza, measles, Legionella pneumonia, hantavirus, or Ebola. The common model interface should therefore be called `clinical_surveillance_ascertainment`, with a pathogen-specific `observation_model.system`. VSP-linked calibration directly informs norovirus/AGE only.

Reporting and syndrome eligibility must be vectors over severity, not scalars. For severity probabilities \(\pi_s\), syndrome eligibility \(q_s\), and reporting probabilities \(r_s(t)\), the clinical observation probability is \(\sum_s \pi_s q_s r_s(t)\). Asymptomatic eligibility and voluntary symptom reporting are zero; active polymerase chain reaction (PCR) or serological screening is a separate channel. Reporting should usually increase with functional severity, although anticipated isolation can suppress reporting among subclinical or mild cases after outbreak recognition.

Three evidence labels are retained:

- **E — directly estimated:** a denominator-based empirical estimate or a simple arithmetic transformation of one.
- **M — modeled synthesis:** a distribution assembled across studies or evidence layers.
- **A — assumed prior:** a transparent modeling choice where suitable data are absent.

Most five-state vectors are **M/A priors**, not empirical multinomial distributions. The principal exceptions are individual components, such as the SARS-CoV-2 asymptomatic fraction and the coarse cholera split. Ebola household reconstruction identifies four observed/reconstructed outcome classes but not a five-way biological severity vector among survivors. Legionella and *Clostridioides difficile* infection (CDI) require special structures.

For norovirus, the cruise estimate near **0.60 [E]** is a weighted reporting fraction among people who met an AGE case definition, not among all symptomatic infections. The familiar multiplier of **2.1–2.5 [M]** is retained only as a simplified provisional calculation under the strong assumption that every symptomatic infection meets that definition. Because subclinical symptomatic infections may fail AGE criteria, it may be an optimistic lower multiplier. The wider **1.5–4.0 [A]** range is a scenario prior, not data, and its center must not be described as cruise-grounded.

**Primary synthesis provenance:** ten-pathogen severity review (`task:51cfaee6-d2dd-4a60-848f-9b6b62498d6f`) and cruise molecular/serological review (`task:9770d466-3daf-40ff-9ade-a425ce8cc69c`). The supplied source file also records the retrievable severity-review trajectory as `task:51cfaee6-57cb-4740-a841-c39566dfc521`; the requested provenance identifier is preserved above without treating the two identifiers as interchangeable.

## 1. Definitions: biological severity before observation

The states are ordered by biological and functional consequence, not realized care use:

1. **`asymptomatic`:** no symptoms attributable to the infection at any time during adequate follow-up.
2. **`subclinical`:** attributable symptoms are detectable by an active diary, structured interview, or repeated questioning, but cause no material limitation of ordinary activity.
3. **`mild`:** activity-limiting ambulatory disease, without a physiological need for hospital-level support.
4. **`moderate`:** clinically significant disease that warrants professional treatment or support, but not intensive care.
5. **`severe_critical`:** life-threatening disease requiring intensive intervention, such as invasive ventilation, vasopressors, extracorporeal support, urgent colectomy, or an equivalent intervention.

“Warrants” is deliberately counterfactual: it describes need under an appropriate standard of care whether or not care is sought or available. A person with physiologically moderate illness can conceal symptoms; a person with biologically mild illness can attend the infirmary because testing is free or mandatory. A hospital admission is therefore an imperfect empirical proxy. Admission may reflect isolation requirements, ship capability, evacuation thresholds, bed availability, age, or precaution rather than physiological severity. Preserve source-study admission outcomes, but map them to biological severity only with an explicit crosswalk and uncertainty.

Symptom duration, infectiousness, care location, isolation, and sequelae are separate dimensions. Prolonged shedding after norovirus recovery does not imply prolonged severity. Guillain–Barré syndrome after *Campylobacter* infection is a delayed outcome, not part of the acute `severe_critical` probability. `care_location` and `physiological_severity` should remain distinct fields.

Death is also separate. Implement `fatality_probability_by_severity` or time-varying transition hazards conditional on current trajectory, age, immunity, treatment, and time since onset. A coherent simulator samples severity once, evolves the trajectory, and permits death through that trajectory. It must not place observed death mass into `severe_critical` and then independently apply an infection-fatality rate (IFR) or case-fatality rate (CFR), which double counts fatality.

## 2. Observation-layer architecture

For pathogen \(p\), person \(i\), and time \(t\), the generic sequence is:

> infection → biological severity → symptom history → syndrome eligibility → reporting/presentation → clinical surveillance record → laboratory sampling → assay result

The observation system changes by pathogen:

- `VSP_AGE`: norovirus, cholera, *V. parahaemolyticus*, *Campylobacter*, and enteric CDI episodes when they satisfy the applicable AGE definition.
- `ship_medical_ARI_ILI`: routine acute respiratory infection/influenza-like illness observation for influenza and, where appropriate, SARS-CoV-2.
- `outbreak_specific_public_health_reporting`: measles, Ebola, Andes hantavirus, and respiratory/systemic outbreaks managed by case finding and public-health investigation.
- `environmental_exposure_plus_clinical_diagnosis`: Legionella, because aerosol exposure, environmental investigation, Pontiac fever, and Legionnaires’ disease form a different causal structure.
- `mandatory_screening_PCR`: an additional active channel where universal or near-universal molecular testing occurs. In this report it is used for COVID-19 cruise validation, not treated as routine VSP observation.

Use `clinical_surveillance_ascertainment` as the cross-pathogen concept. “VSP ascertainment” should be reserved for enteric AGE surveillance. VSP-linked behavior can directly calibrate norovirus and possibly other AGE observation assumptions; it does not calibrate respiratory or systemic pathogens.

Let \(S\) be severity, \(Q\) syndrome eligibility, \(R\) reporting, \(C\) clinical record creation, \(L\) laboratory sampling, and \(A\) assay positivity. A minimal clinical probability is

\[
P(C_{it}=1\mid I_i=1,p)=\sum_s \pi_{p,s}\,q_{p,s}\,r_{p,s}(t)\,c_{p,s}(t),
\]

where \(\pi_{p,s}=P(S=s\mid I,p)\), \(q_{p,s}=P(Q=1\mid S=s,p)\), and \(r_{p,s}(t)=P(R=1\mid Q=1,S=s,p,t)\). If a qualifying report is deterministically entered, \(c=1\). The probability of a positive clinical test additionally multiplies by severity- and campaign-specific sampling and time-varying assay sensitivity:

\[
P(A=1,L=1,C=1\mid I,p,t)=
\sum_s \pi_{p,s}q_{p,s}r_{p,s}(t)c_{p,s}(t)\ell_{p,s}(t)\alpha_p(\tau,\text{specimen}).
\]

A PCR-positive asymptomatic person detected by mandatory screening is an infection observation, not a symptom report or VSP AGE case. Model active screening independently:

\[
P(A^{screen}=1\mid I,p,t)=P(\text{selected for screening}\mid p,t)\,\alpha_p(\tau,\text{specimen}).
\]

All asymptomatic entries in `syndrome_case_eligibility_by_severity` and voluntary `reporting_probability_by_severity_*` are zero. Active PCR or serology may nevertheless detect asymptomatic infection through `active_screening`. This prevents molecular testing from being misrepresented as clinical care-seeking.

Recognition can change each severity-specific reporting probability. Announcements and interviews may increase awareness; cost, stigma, or anticipated cabin isolation may decrease voluntary presentation. The plausible post-recognition direction is therefore scenario-dependent. It is especially credible that isolation avoidance lowers reporting among `subclinical` and `mild` infections while `moderate` and `severe_critical` cases remain difficult to conceal.

> **WHAT THE DATA IDENTIFY**
>
> - **Infection denominator identified:** near-universal PCR on *Diamond Princess*; Ebola household reconstruction; and some controlled human challenge studies with protocol testing independent of symptoms.
> - **Symptomatic reporting identified:** one high-morbidity norovirus cruise outbreak estimated infirmary surveillance near **0.60 [E]** among people meeting an AGE case definition.
> - **Etiologic confirmation only:** most cruise norovirus and influenza PCR or sequencing studies test selected symptomatic people or contacts. They identify the pathogen among sampled persons, not the vessel-wide infection denominator or reporting fraction.
> - **Not identified:** the cruise norovirus infection/VSP ratio. No retrieved cruise study combined universal infection ascertainment with linked AGE eligibility and medical-report records.

## 3. Cross-pathogen defaults and evidentiary scope

Table 1 retains transparent default severity vectors where a generic infection-conditioned vector is defensible. Entries are ordered `[asymptomatic, subclinical, mild, moderate, severe_critical]`. They are M/A defaults even when one component is E. No scalar infection/VSP multiplier is shown for non-AGE pathogens; their observation systems and denominators differ.

**Table 1. Cross-pathogen severity and observation summary**

| Pathogen / reference population | Default biological severity prior | Observation system | Molecular infection denominator? | Grade |
|---|---|---|---|:---:|
| Norovirus GII.4, adults | `[.25,.55,.19,.009,.001]` | `VSP_AGE` | No on cruises; some challenge denominators | M, components E/M |
| SARS-CoV-2, pre-Omicron unvaccinated | `[.35,.42,.19,.03,.01]` | `ship_medical_ARI_ILI`; outbreak reporting; separate PCR screening | Yes, near-universal PCR on *Diamond Princess* | E/M/A |
| SARS-CoV-2, Omicron immune adults | `[.30,.52,.165,.013,.002]` | same, era-specific | Not from cited cruise evidence | E/M/A |
| Influenza A(H1N1)pdm09 | `[.20,.52,.27,.008,.002]` | `ship_medical_ARI_ILI` | No vessel-wide denominator in cited cruises | M/A |
| Influenza A(H3N2), cruise-aged | `[.15,.48,.35,.016,.004]` | `ship_medical_ARI_ILI` | No vessel-wide denominator in cited cruises | M/A |
| Measles, susceptible high-income population | `[.02,.43,.40,.12,.03]` | outbreak-specific public-health reporting | No | M/A |
| *V. cholerae* O1/O139 | `[.75,.15,.05,.035,.015]` | `VSP_AGE` if AGE-eligible | Not in cited cruises | E/M/A |
| *V. parahaemolyticus* | `[.20,.55,.22,.028,.002]` | `VSP_AGE` if AGE-eligible | No robust denominator | M/A |
| *Campylobacter jejuni*, adults | `[.10,.55,.315,.03,.005]` | `VSP_AGE` if AGE-eligible | Challenge denominators, not cruise-wide | M/A |
| Legionella | **Special structure:** exposure → no syndrome / Pontiac fever / Legionnaires’ disease → syndrome-conditional severity | `environmental_exposure_plus_clinical_diagnosis` | No ordinary infection denominator | M/A |
| Toxigenic *C. difficile* | **Special structure:** exposure/acquisition → colonization → toxigenic carriage → CDI → severity | `VSP_AGE` only for eligible enteric CDI | No ordinary acute-infection denominator | A, progression evidence limited |
| Andes hantavirus | No evidence-derived five-state vector; optional synthetic vector reported separately | outbreak-specific public-health reporting | No | A, very low confidence |
| Ebola virus | **Special reconstructed outcome system:** pauci/asymptomatic, unrecognized symptomatic, recognized survivor, fatal infection | outbreak-specific public-health reporting | Household reconstruction | E for reconstructed classes |

The vectors must not be swept component-by-component without a normalization model. Independent low/high bounds can produce negative residuals, sums other than one, or impossible combinations such as simultaneously high asymptomatic and severe fractions. Use Dirichlet, logistic-normal, or named scenario-set priors as described in Section 8.

## 4. Pathogen-specific recommendations

### 4.1 Norovirus GII, especially GII.4

Human challenge studies test volunteers regardless of symptoms and establish symptomatic and asymptomatic infection, but do not estimate natural care-seeking. Across older GI/GII challenges, illness occurred in **67–100% [E]** of infected volunteers; a GII.4 trial documented both symptomatic and asymptomatic infections. The vector `[.25,.55,.19,.009,.001] [M]` synthesizes challenge and community evidence. It should not be called an empirical five-way distribution. Use asymptomatic **0.19–0.35 [E/M]** and moderate **0.002–0.03 [M]** only through coherent scenario vectors or a simplex prior. [@Bernstein2015Norovirus; @Kirby2016Vomiting; `task:51cfaee6-d2dd-4a60-848f-9b6b62498d6f`]

A Yangtze cruise outbreak found **15/15 [E]** sampled symptomatic cases PCR-positive and **3/28 [E]** food handlers positive without symptoms. This demonstrates silent carriage but does not identify a vessel-wide asymptomatic fraction. One cruise investigation estimated that infirmary surveillance captured approximately **0.60 [E]** of AGE cases. That value constrains reporting among AGE-eligible symptomatic people, not all symptomatic infections and not all infections. [@Qi2018Chongqing; @Wikswo2011Norovirus; `task:9770d466-3daf-40ff-9ade-a425ce8cc69c`]

A transparent M/A decomposition is:

- `syndrome_case_eligibility_by_severity = [0, .55, .98, 1, 1] [A]`;
- post-recognition reporting `[0, .50, .76, .96, 1] [A]`.

With the default severity vector, the eligible symptomatic mass is about **0.50 [M/A]** and the reported eligible mass is about **0.30 [M/A]**. Their ratio is approximately **0.61 [M/A]**, close to the empirical 0.60 constraint. This decomposition is not identified by that study; many severity-specific vectors yield the same weighted fraction. A pre-recognition vector `[0,.45,.70,.94,1] [A]` gives lower weighted reporting. An isolation-avoidance post-recognition scenario `[0,.25,.55,.95,1] [A]` lowers subclinical and mild reporting while preserving high reporting for physiologically important disease.

Uncomplicated illness lasts **1–3 days [E]**. Shedding can continue for weeks and requires a separate infectiousness state. Age at least **65 years [M]**, frailty, renal disease, immunosuppression, and impaired hydration move probability toward moderate disease. For cruise-aged passengers, transfer **0.01–0.03 [A]** from leftward symptomatic states into moderate severity and renormalize. Immunocompromised hosts need a long-duration mixture, not only a severity odds multiplier.

### 4.2 SARS-CoV-2

A large pre-Omicron meta-analysis estimated truly asymptomatic infection at **0.351 [E]** (95% confidence interval **0.307–0.399 [E]**). A practical pre-Omicron vector is `[.35,.42,.19,.03,.01] [M]`. For Omicron in vaccinated or previously infected adults, `[.30,.52,.165,.013,.002] [M]` is a transparent prior; a pooled asymptomatic estimate was **0.255 [E]**, while nonsevere disease was **0.979 [E]**. Variant, vaccination, prior infection, and treatment era should define strata rather than be pooled into one ship-wide vector. [@Sah2021Asymptomatic; @Yu2022Omicron]

Near-complete testing on *Diamond Princess* identified **687 infections [E]** in the principal study: **544/2,666 passengers [E]** and **143/1,045 crew [E]**. At specimen collection, the infection-to-contemporaneously-symptomatic ratio was **2.12 overall [E]**, **2.37 in passengers [E]**, and **1.81 in crew [E]**. “Asymptomatic” at sampling included some presymptomatic infections, so this is not a final-ever-asymptomatic fraction. It belongs in the active-PCR validation channel, separate from VSP. [@ExpertTaskforce2020Diamond; `task:9770d466-3daf-40ff-9ade-a425ce8cc69c`]

Mild acute illness typically lasts **5–10 days [M]**; hospital trajectories often last **14–21 days [M]**. Pre-vaccine infection-fatality risk rose from about **0.4% at age 55 [M]** to **1.4% at 65 [M]**, **4.6% at 75 [M]**, and **15% at 85 [M]**. Use age-stratified severity vectors and `fatality_probability_by_severity`, not one pooled IFR. Vaccination, prior infection, boosting, and antiviral access shift mass leftward; transplantation and multimorbidity shift it rightward. [@Salje2020France]

### 4.3 Influenza A(H1N1)pdm09 and A(H3N2)

Virologically confirmed prospective studies support a lower truly asymptomatic fraction than many serologic studies. Use H1N1pdm09 `[.20,.52,.27,.008,.002] [M]` and cruise-aged H3N2 `[.15,.48,.35,.016,.004] [M]`. Appropriate simplex priors can place most H1N1 asymptomatic mass between **0.15 and 0.25 [M]** and H3N2 between **0.10 and 0.20 [M]** without treating those limits as independent component sweeps. [@Leung2015Influenza]

The Sydney–Noumea investigation found probable influenza in **310/836 respondents [E]**, far above initial clinic logs, but did not provide a vessel-wide infection denominator. A Pacific cruise with H1N1pdm09 and H3N2 used clinically triggered testing; its laboratory attack rates cannot calibrate asymptomatic infection. These studies support under-observation and etiologic attribution, not a universal reporting multiplier. [@Brotherton2003Influenza; @Ward2010Influenza; `task:9770d466-3daf-40ff-9ade-a425ce8cc69c`]

Uncomplicated symptoms last **3–7 days [E/M]**; cough and fatigue often last **7–14 days [M]**. Older age, cardiopulmonary disease, immunosuppression, and pregnancy increase severity. H3N2 places more severe burden on older adults; H1N1pdm09 places relatively more on younger adults and pregnancy. Vaccination and prior immunity should modify the full severity vector and fatality layer.

### 4.4 Measles virus

Wild-type measles in a susceptible person is usually clinically apparent. Use `[.02,.43,.40,.12,.03] [M]`, with uncertainty concentrated around asymptomatic **0–0.05 [M]** and combined moderate/severe **0.10–0.25 [M]**. The prodrome lasts **2–4 days [E/M]**, rash about **5–6 days [E/M]**, and uncomplicated illness about **7–10 days [M]**. [@Perry2004Measles]

Admission may reflect airborne-isolation policy rather than physiology. Reporting after a characteristic rash can be high, but modified measles after partial immunity may evade classic case definitions. Susceptible adults, infants, pregnancy, vitamin-A deficiency, cellular immunodeficiency, and poor supportive care shift severity rightward. A well-resourced case-fatality prior of **0.001–0.003 [M]** should be applied through severity-conditioned fatality, not by moving death probability into the severity simplex.

### 4.5 *Legionella pneumophila*: special syndrome structure

Do not force Legionella into one infection pyramid. Use `exposure → no recognized syndrome / Pontiac fever / Legionnaires_disease`, followed by severity conditional on syndrome.

For Pontiac-fever-type exposure, a provisional outcome prior is `no_illness=.10`, `pontiac_no_material_limitation=.20`, `pontiac_activity_limiting=.55`, and `pontiac_professional_support=.15 [all M]`. Reported attack rates can approach **0.90–0.95 [E/M]** after intense aerosol exposure. Illness lasts **2–5 days [E/M]**, and fatality is approximately zero. For Legionnaires’-disease-type exposure, use `no_recognized_ld=.96 [M]` and recognized LD **0.005–0.05 [M]**, then draw LD severity conditionally. A transparent conditional LD prior may place most recognized disease in `moderate`, with a smaller `severe_critical` mass; community-acquired LD case fatality is about **0.05–0.10 [M]**. These quantities do not form a common infection-denominator vector. [@Hamilton2018Legionella; @Diederen2008Legionella]

Age over **50 years [E/M]**, smoking, chronic obstructive pulmonary disease, diabetes, renal disease, malignancy, corticosteroids, and transplantation increase LD risk. Spa aerosol exposure may produce Pontiac fever; potable-water aerosols may produce sparse severe LD in older passengers. Environmental detection and exposure reconstruction must coexist with clinical diagnosis in the observation model.

### 4.6 *Vibrio cholerae* and *V. parahaemolyticus*

For toxigenic *V. cholerae* O1/O139, retain the denominator-based coarse split `asymptomatic=.75 [E]`, `nonsevere_symptomatic=.20 [E/M]`, and `severe=.05 [E/M]`. Expanding this to `[.75,.15,.05,.035,.015] [M]` is a modeled crosswalk, not a direct five-state estimate. Prompt rehydration can keep recognized-case fatality below **0.01 [M]**; without care, severe dehydration can be much more lethal. Symptoms usually last **3–6 days [M]**. Medical contact for oral rehydration does not itself imply moderate physiological severity. [@Kanungo2012Vibrio]

For *V. parahaemolyticus*, no robust infection denominator exists. Use `[.20,.55,.22,.028,.002] [M/A]`, with uncertainty represented by coherent scenarios rather than separate asymptomatic and hospitalization sliders. Illness usually lasts **1–3 days [M]**. Older age, liver disease, alcohol use disorder, iron overload, diabetes, and immunosuppression increase invasive Vibrio risk, although the strongest evidence concerns *V. vulnificus*. Cholera and seafood gastroenteritis should remain separate profiles.

### 4.7 *Campylobacter jejuni*

Use `[.10,.55,.315,.03,.005] [M]`. Controlled human infection confirms asymptomatic infection but depends on strain and inoculum; protocol observation is not hospitalization or realized care-seeking. Acute diarrhea lasts **3–7 days [E/M]**. [@Tribble2010Campylobacter; @Havelaar2009Campylobacter]

Infants, older adults, pregnancy, hypogammaglobulinemia, human immunodeficiency virus infection, malignancy, and other immunodeficiency increase prolonged, recurrent, bacteremic, or fatal disease. Delayed Guillain–Barré syndrome, reactive arthritis, and postinfectious bowel disorders need separate sequela transitions. An AGE eligibility vector should account for symptomatic infections that do not meet the operational diarrhea/vomiting definition.

### 4.8 *Clostridioides difficile*: acquisition and progression

The required chain is `spore_exposure → acquisition/colonization → toxigenic_carriage → CDI → biological_severity`. In an intensive-care cohort, toxigenic carriage was detected during **0.093 [E]** of admissions and carriers had **24-fold greater risk [E]** of healthcare-onset CDI, but most did not progress. Do not represent acquisition with a generic vector whose “asymptomatic” mass competes directly with acute CDI states. Instead, use an acquisition-to-colonization probability, a colonization-to-CDI hazard, and a CDI-conditional severity simplex. [@MilesJay2023Cdifficile; @McDonald2018CDI]

For a short voyage, provisional symptomatic progression after toxigenic acquisition can remain **0.01–0.10 [A]**, conditioned on antibiotics, age, healthcare exposure, and prior CDI. Treated diarrhea often improves in **3–5 days [M]**, while treatment generally lasts at least **10 days [E/M]**. Recurrence after an initial episode is about **0.15–0.25 [M]** and requires a post-recovery transition. Onboard disease may more often arise from pre-existing colonization than from a complete onboard acquisition-to-disease sequence. CDI enters `VSP_AGE` only when its illness meets the AGE case definition; colonization and positive tests without eligible diarrhea do not.

### 4.9 Andes hantavirus

Evidence confidence is **very low**. No Andes-specific cohort reconstructs all infections, symptoms, biological severity, observation, and outcomes. Therefore no five-state vector should be labeled evidence-derived. If the simulator requires an illustrative synthetic prior, use `[.40,.10,.10,.15,.25] [A]` solely as a named stress-test scenario. Alternative scenarios should jointly vary asymptomatic mass and the conditional severity among symptomatic infections. Recognized hantavirus cardiopulmonary syndrome has case fatality around **0.30–0.40 [M]**, but that does not identify an IFR or the unrecognized infection denominator. [@Tortosa2024Hantavirus; @Toledo2021Hantavirus]

The febrile prodrome lasts **3–6 days [M]** before possible rapid pulmonary edema and shock. The incubation median of **18 days [M]** and range **11–35 days [M]** imply that many voyage-acquired infections would present after disembarkation. Apply death as a transition among severe trajectories; do not encode the syndrome CFR as severe-state probability and then apply it again.

### 4.10 Ebola virus: reconstructed outcomes, not a generic pyramid

A Sierra Leone household study reconstructed **116 infections [E]**: pauci/asymptomatic **0.190 [E]**, unrecognized symptomatic **0.155 [E]**, recognized survivors **0.216 [E]**, and fatal infections **0.440 [E]**. Among reported cases, CFR was **0.671 [E]**; reconstructed IFR was **0.440 [E]**. These classes identify recognition and outcome, not the distribution of `subclinical`, `mild`, `moderate`, and `severe_critical` among survivors. Do not store `[.190,.155,0,.216,.440]` as a biological severity vector. [@Kelly2022Ebola]

Implement a special reconstructed outcome model that can reproduce those four observed classes while leaving survivor severity partially latent. One defensible factorization first draws pauci/asymptomatic versus symptomatic, then recognition conditional on symptomatic disease, then a severity trajectory and severity-conditioned fatality. Calibration targets the four reconstructed class probabilities and reported-case CFR without assigning all recognized survivors to `moderate` or all fatal infections directly to `severe_critical`.

Acute disease lasts about **7–14 days [M]**; fatal cases often die around days **7–10 [M]**, while survivors have prolonged convalescence. Higher exposure and viremia predict severity; children under **5 years [E/M]** and adults at least **45 years [E/M]** have higher CFR than those aged 15–44. Ebola is a stress-test scenario, not a routine cruise pathogen.

## 5. Norovirus observation model and multiplier

The full infection-to-VSP ratio is

\[
\frac{I}{VSP}=\frac{1}{\sum_s \pi_s q_{AGE,s} r_s},
\]

where \(q_{AGE,s}\) is the probability that severity state \(s\) meets the AGE definition and \(r_s\) is reporting conditional on eligibility. The denominator is the probability that an infection becomes a reported eligible AGE case. It is not `(1-asymptomatic)` multiplied by one universal reporting scalar unless strong simplifications are imposed.

If one assumes \(P(AGE\text{ definition}\mid symptomatic\ infection)=1\) and a common reporting probability \(r=0.60\), then

\[
I/VSP=\{(1-a)r\}^{-1}.
\]

Combining asymptomatic **0.19–0.32 [E]** with **0.60 [E]** gives approximately **2.1–2.5 [M]**. This simplified provisional range is valid only under the stated eligibility assumption. Subclinical symptoms can fail the AGE definition, making **2.1–2.5** an optimistic lower multiplier. It is not a cruise-measured ratio.

Using the illustrative vectors from Section 4.1 gives \(\sum_s\pi_s q_s r_s\approx0.30 [M/A]\), hence a multiplier near **3.3 [M/A]**. This value is still not empirically identified; it demonstrates how the 0.60 reporting constraint and imperfect syndrome eligibility interact. The broader **1.5–4.0 [A]** range is a scenario prior. It is not data, and neither **2.3** nor any other center should be described as cruise-grounded.

A reported VSP attack rate of 0.05 should remain an observation target. If a simulator explicitly draws severity, eligibility, and reporting, it should compare simulated VSP cases directly with that target. Applying an external multiplier to the target and then simulating under-reporting would double-correct. If a reduced model lacks an observation layer, any multiplier used to infer infections must be labeled scenario-dependent and tied to its \(\pi,q,r\) assumptions.

No retrieved cruise study used universal serial stool reverse-transcription PCR or paired pre/post-voyage anti-virus-like-particle immunoglobulin G linked to daily diaries and report records. Cruise PCR studies establish etiology or selected silent carriage; they do not identify the infection/VSP ratio.

## 6. COVID-19 cruise validation, separate from VSP

The *Diamond Princess* infection-to-contemporaneously-symptomatic ratio of **2.12 overall [E]** validates the architecture: latent infection, symptom history, clinical observation, and molecular detection are distinct. It does not validate norovirus values. The pathogen, specimen, testing schedule, symptom definition, and behavior differed. Contemporaneous asymptomatic status included presymptomatic infections, so the ratio is not equivalent to one divided by the final asymptomatic fraction.

Its correct model representation is `observation_model.active_screening` with near-universal PCR coverage and time-dependent sensitivity, alongside a separate clinical ARI/ILI or outbreak-reporting channel. It must not be coded as VSP capture. The USS *Theodore Roosevelt* experience similarly provides qualitative validation that symptom screening can miss infections, but the previously quoted **0.769** initial asymptomatic/presymptomatic classification is not used as a default because follow-up and selection differ.

## 7. Synthetic Starfleet pathogens

All values in this section are **synthetic [A]** and should carry `synthetic=true`. They are analog-based design choices, not clinical or canon-derived estimates. Their observation arrays follow the same semantic rules: zero asymptomatic reporting, severity-specific eligibility, and a separate active-screening channel if one exists.

### Rigelian Fever

Use `[.15,.40,.30,.10,.05] [A]`, anchored loosely to systemic febrile respiratory disease. Use lognormal incubation `mu=1.386`, `sigma=.500`, median **4.0 days**, dose shift `.15`, floor `.30`, and reference dose `50 model units [all A]`. Reporting may rise after recognition, for example `[0,.45,.70,.90,.98]` to `[0,.60,.85,.97,1] [A]`. Duration is **7 days [A]** as a central scenario.

### Psi-2000 Polywater

Do not use the biomedical severity states. Use `no_behavioral_effect=.05`, `subtle_disinhibition=.20`, `operational_impairment=.55`, `dangerous_behavior=.18`, and `critical_accident=.02 [all A]`. Traditional fatality is zero; injury or secondary operational death is a separate mechanism. Use lognormal incubation `mu=-.223`, `sigma=.600`, median **0.8 days**, dose shift `.20`, floor `.20`, and reference dose `10 model units [all A]`. Observation is behavior-dependent and can be paradoxically low before recognition.

### TNG Shipboard Influenza

Use `[.15,.48,.34,.025,.005] [A]`. Use lognormal incubation `mu=.405`, `sigma=.420`, median **1.5 days**, dose shift `.10`, floor `.40`, and reference dose `500 model units [all A]`. A severity-specific reporting scenario is `[0,.25,.50,.85,.98]` pre-recognition and `[0,.35,.68,.94,1]` post-recognition. Duration is **6 days [A]** centrally.

## 8. Uncertainty, age, and immunity

Severity probabilities live on a simplex. Independent scalar sweeps are incoherent because component choices can violate sum-to-one and distort correlations. Use one of three prior types:

- **Dirichlet:** specify a mean vector and concentration. Larger concentration produces tighter draws around the mean. Use cautiously when negative correlations induced by closure are acceptable.
- **Logistic-normal:** place a multivariate normal prior on log-ratios. This supports richer covariance, such as jointly moving mass from subclinical and mild states toward moderate and severe states in frail passengers.
- **Scenario set:** define named `low`, `base`, and `high` vectors, each summing exactly to one. This is easiest to audit when evidence is sparse.

Do not use “low” for every component simultaneously. A low-severity scenario means a complete left-shifted vector; a high-severity scenario is a complete right-shifted vector. Evidence ranges can inform marginal behavior, but the implemented prior must preserve normalization.

Age, immunity, vaccination, dose, and comorbidity should modify the simplex coherently. Preferred implementations are strata-specific vectors or additive odds shifts in an ordinal/log-ratio model followed by softmax renormalization. Fatality should be modified separately, conditional on severity. For example, age may increase both the probability of a severe trajectory and the fatality probability within that trajectory; these are distinct effects and should not be conflated.

## 9. Implementation contract

The current `illness_probability` must become a derived view, never an independent random draw. Depending on the compatibility requirement it can report `1 - base_probabilities[asymptomatic]` or a derived probability of any attributable symptoms for a given stratum. Sampling it independently after severity would permit contradictory states.

Table 2 gives illustrative observation-array defaults for implementation. Every numeric entry is **A** unless a weighted target is noted; the arrays are not empirical severity-by-severity estimates. They are ordered over the five standard states. Respiratory/systemic syndrome eligibility means eligibility for that profile’s clinical surveillance definition, not VSP AGE eligibility.

**Table 2. Illustrative severity-specific clinical observation arrays**

| Profile | System | Eligibility `q` | Reporting pre-recognition | Reporting post-recognition |
|---|---|---|---|---|
| Norovirus GII.4 | `VSP_AGE` | `[0,.55,.98,1,1]` | `[0,.45,.70,.94,1]` | `[0,.50,.76,.96,1]`; weighted eligible-case reporting ≈0.61 [M/A], constrained by 0.60 [E] |
| SARS-CoV-2 | `ship_medical_ARI_ILI` | `[0,.35,.90,1,1]` | `[0,.30,.65,.90,.98]` | `[0,.45,.78,.95,1]` |
| Influenza A | `ship_medical_ARI_ILI` | `[0,.40,.92,1,1]` | `[0,.25,.55,.88,.98]` | `[0,.40,.72,.94,1]` |
| Measles | outbreak public-health reporting | `[0,.25,.90,1,1]` | `[0,.40,.80,.95,1]` | `[0,.70,.95,.99,1]` |
| Cholera | `VSP_AGE` | `[0,.45,.95,1,1]` | `[0,.35,.65,.92,.99]` | `[0,.50,.80,.97,1]` |
| *V. parahaemolyticus* | `VSP_AGE` | `[0,.50,.95,1,1]` | `[0,.30,.60,.90,.99]` | `[0,.42,.72,.95,1]` |
| *Campylobacter* | `VSP_AGE` | `[0,.50,.95,1,1]` | `[0,.30,.58,.90,.99]` | `[0,.42,.72,.95,1]` |
| Andes hantavirus | outbreak public-health reporting | `[0,.20,.70,1,1]` | `[0,.25,.65,.93,1]` | `[0,.45,.82,.98,1]` |

For Legionella, CDI, and Ebola, these arrays belong inside their special branches: syndrome-conditional for Legionella, CDI-conditional after progression, and recognition/outcome calibration for Ebola. Active testing never changes the zero in the asymptomatic clinical-reporting position; it is represented in `active_screening`.

Required generic keys are:

```text
severity_model.states
severity_model.base_probabilities
severity_model.prior.type = dirichlet | logistic_normal | scenario_set
severity_model.prior.parameters
severity_model.fatality_probability_by_severity
observation_model.system
observation_model.syndrome_case_eligibility_by_severity
observation_model.reporting_probability_by_severity_pre_recognition
observation_model.reporting_probability_by_severity_post_recognition
observation_model.active_screening
observation_model.lab_sampling_probability_by_severity
observation_model.assay_sensitivity_by_time_since_infection
```

A norovirus example is:

```json
{
  "severity_model": {
    "states": ["asymptomatic", "subclinical", "mild", "moderate", "severe_critical"],
    "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
    "prior": {
      "type": "dirichlet",
      "parameters": {
        "mean": [0.25, 0.55, 0.19, 0.009, 0.001],
        "concentration": 80
      }
    },
    "fatality_probability_by_severity": null,
    "evidence_grade": "M/A"
  },
  "observation_model": {
    "system": "VSP_AGE",
    "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
    "reporting_probability_by_severity_pre_recognition": [0, 0.45, 0.70, 0.94, 1],
    "reporting_probability_by_severity_post_recognition": [0, 0.50, 0.76, 0.96, 1],
    "active_screening": {
      "enabled": false,
      "modality": null,
      "selection_probability_by_time": null
    },
    "lab_sampling_probability_by_severity": [0, 0.05, 0.20, 0.60, 0.90],
    "assay_sensitivity_by_time_since_infection": {
      "assay": "stool_RT_PCR",
      "specimen": "stool",
      "time_grid_days": [],
      "values": [],
      "status": "not_parameterized"
    },
    "evidence_grade": "A_except_weighted_reporting_target_E"
  }
}
```

The empty assay arrays and null fatality array are deliberate: the supplied evidence does not identify those parameters at the requested resolution. Production profiles must populate them from assay-, time-, specimen-, and severity-specific evidence or leave them explicitly unparameterized; they must not be silently replaced by universal constants.

For sparse evidence, a scenario-set representation is preferable:

```json
{
  "severity_model": {
    "prior": {
      "type": "scenario_set",
      "parameters": {
        "low":  [0.30, 0.55, 0.14, 0.009, 0.001],
        "base": [0.25, 0.55, 0.19, 0.009, 0.001],
        "high": [0.20, 0.50, 0.27, 0.025, 0.005],
        "weights": [0.25, 0.50, 0.25]
      }
    }
  }
}
```

Every vector must be validated as nonnegative, finite, length five, and summing to one within tolerance. Reporting, eligibility, sampling, and fatality arrays must match the state order and lie in `[0,1]`. The first entries of clinical eligibility and voluntary reporting arrays must be exactly zero. `active_screening` is evaluated independently and can detect asymptomatic infection.

Special profiles require schema discriminators rather than fake generic vectors:

- Legionella: `special_structure.type="legionella_syndrome_branch"`, with exposure outcome probabilities and severity models conditional on Pontiac fever or Legionnaires’ disease.
- CDI: `special_structure.type="cdi_colonization_progression"`, with acquisition, toxigenic carriage, progression hazard, recurrence, and CDI-conditional severity.
- Ebola: `special_structure.type="reconstructed_recognition_outcome"`, with calibration targets for the four reconstructed classes and a partially latent survivor severity model.
- Andes: `prior.type="scenario_set"` and `evidence_grade="A_very_low"`; the illustrative vector must be named `synthetic_stress_test`, not evidence-derived.

`lab_sampling_probability_by_severity` is an operational parameter, not pathogen biology. `assay_sensitivity_by_time_since_infection` must be indexed by assay, specimen, and infection time or symptom time as supported by the test. A universal scalar sensitivity is inadequate.

## 10. Limitations and decisive norovirus study designs

Most five-state priors are synthesized from studies that observe different layers. Challenge studies provide protocol-defined infection denominators but selected hosts and doses. Clinical cohorts characterize severe trajectories but truncate mild and unrecognized disease. Cruise laboratory studies frequently sample symptomatic presenters, contacts, or selected subgroups. Admission and evacuation are operational proxies. Passenger age, vaccination, prior immunity, frailty, access, cost, announcements, and isolation policy vary by voyage.

Environmental and wastewater PCR establishes pathogen presence but does not identify infected-person prevalence without a calibrated shedding model. Serology can expand denominators but depends on baseline immunity, timing, assay performance, and a validated seroconversion definition. These limitations should enter the observation model rather than be hidden in one multiplier.

Two designs would resolve the central norovirus gap:

1. A commercial-cruise pre/post-voyage anti-virus-like-particle immunoglobulin G cohort, linked to daily symptom diaries, activity limitation, AGE definition status, medical reports, and public-health measures.
2. Universal serial stool reverse-transcription PCR during an outbreak, independent of symptoms, linked to onset, functional severity, reporting, VSP eligibility, sampling time, and isolation policy.

No such design was identified in the supplied cruise review **[E, review finding]**. Ideally one protocol would combine molecular and serological ascertainment because PCR positivity is time-limited and serology has baseline-immunity constraints. Until then, the infection/VSP ratio must remain an explicit scenario calculation, not a fitted cruise constant.

## References

Primary citations are retained from the supplied reviews. DOI-bearing entries are reproduced only where the supplied metadata identified a matching work.

- Bernstein DI, Atmar RL, Lyon GM, et al. Norovirus vaccine against experimental human GII.4 virus illness. *J Infect Dis.* 2015. doi:10.1093/infdis/jiu497. `[@Bernstein2015Norovirus]`
- Kirby AE, Streby A, Moe CL. Vomiting as a symptom and transmission risk in norovirus illness. *PLoS One.* 2016. doi:10.1371/journal.pone.0143759. `[@Kirby2016Vomiting]`
- Wikswo ME, Cortes JE, Hall AJ, et al. Disease transmission and passenger behaviors during a high-morbidity norovirus outbreak. *Clin Infect Dis.* 2011. doi:10.1093/cid/cir144. `[@Wikswo2011Norovirus]`
- Qi L, Xiang X, Xiong Y, et al. Norovirus GII outbreak attributed to cold dishes on a cruise ship. *Int J Environ Res Public Health.* 2018. doi:10.3390/ijerph15122823. `[@Qi2018Chongqing]`
- Sah P, Fitzpatrick MC, Zimmer CF, et al. Asymptomatic SARS-CoV-2 infection: systematic review and meta-analysis. *PNAS.* 2021. doi:10.1073/pnas.2109229118. `[@Sah2021Asymptomatic]`
- Yu W, Guo Y, Zhang S, et al. Asymptomatic infection and nonsevere disease caused by Omicron. *J Med Virol.* 2022. doi:10.1002/jmv.28066. `[@Yu2022Omicron]`
- Salje H, Tran Kiem C, Lefrancq N, et al. Estimating the burden of SARS-CoV-2 in France. *Science.* 2020. doi:10.1126/science.abc3517. `[@Salje2020France]`
- Expert Taskforce for the COVID-19 Cruise Ship Outbreak. Epidemiology of COVID-19 on a cruise ship quarantined at Yokohama. *Emerg Infect Dis.* 2020. doi:10.3201/eid2611.201165. `[@ExpertTaskforce2020Diamond]`
- Leung NHL, Xu C, Ip DKM, Cowling BJ. Fraction of influenza infections that are asymptomatic. *Epidemiology.* 2015. doi:10.1097/EDE.0000000000000340. `[@Leung2015Influenza]`
- Brotherton JML, Delpech VC, Gilbert GL, et al. Influenza A and B outbreak on a cruise ship. *Epidemiol Infect.* 2003. doi:10.1017/S0950268802008166. `[@Brotherton2003Influenza]`
- Ward KA, Armstrong P, McAnulty JM, et al. H1N1 and H3N2 outbreaks on a cruise ship. *Emerg Infect Dis.* 2010. doi:10.3201/eid1611.100477. `[@Ward2010Influenza]`
- Perry RT, Halsey NA. Clinical significance of measles. *J Infect Dis.* 2004. doi:10.1086/377712. `[@Perry2004Measles]`
- Hamilton KA, Prussin AJ, Ahmed W, Haas CN. Outbreaks of Legionnaires’ disease and Pontiac fever. *Curr Environ Health Rep.* 2018. doi:10.1007/s40572-018-0201-4. `[@Hamilton2018Legionella]`
- Diederen BMW. *Legionella* spp. and Legionnaires’ disease. *J Infect.* 2008. doi:10.1016/j.jinf.2007.09.010. `[@Diederen2008Legionella]`
- Kanungo S, Sur D, Ali M, et al. *V. parahaemolyticus* diarrhea and cholera in Kolkata. *BMC Public Health.* 2012. doi:10.1186/1471-2458-12-830. `[@Kanungo2012Vibrio]`
- Tribble DR, Baqar S, Scott DA, et al. Duration of protection in experimental *C. jejuni* infection. *Infect Immun.* 2010. doi:10.1128/IAI.01021-09. `[@Tribble2010Campylobacter]`
- Havelaar AH, van Pelt W, Ang CW, et al. Immunity to *Campylobacter*. *Crit Rev Microbiol.* 2009. doi:10.1080/10408410802636017. `[@Havelaar2009Campylobacter]`
- Miles-Jay A, Snitkin ES, Lin MY, et al. Genomic surveillance of *C. difficile* carriage and transmission. *Nat Med.* 2023. doi:10.1038/s41591-023-02549-4. `[@MilesJay2023Cdifficile]`
- McDonald LC, Gerding DN, Johnson S, et al. Clinical practice guidelines for CDI. *Clin Infect Dis.* 2018. doi:10.1093/cid/ciy149. `[@McDonald2018CDI]`
- Tortosa F, Perre F, Tognetti C, et al. Hantavirus seroprevalence in non-epidemic settings. *BMC Public Health.* 2024. doi:10.1186/s12889-024-20014-w. `[@Tortosa2024Hantavirus]`
- Toledo J, Haby MM, Reveiz L, et al. Evidence for human-to-human hantavirus transmission. *J Infect Dis.* 2022. doi:10.1093/infdis/jiab461. `[@Toledo2021Hantavirus]`
- Kelly JD, Frankfurter RG, Tavs JM, et al. Lower exposure risk, less severe disease, and unrecognized Ebola virus disease. *Open Forum Infect Dis.* 2022. doi:10.1093/ofid/ofac052. `[@Kelly2022Ebola]`

### Source records

- Ten-pathogen severity review: `task:51cfaee6-d2dd-4a60-848f-9b6b62498d6f` (requested provenance identifier).
- Retrievable severity-review record cited by the supplied draft: `task:51cfaee6-57cb-4740-a841-c39566dfc521`.
- Cruise molecular and serological review: `task:9770d466-3daf-40ff-9ade-a425ce8cc69c`.
- Existing model notes: `/workspace/pathogen_notes.md`.
- Incubation, dose-response, shedding, and Trek analog specification: `/workspace/ctb_incubation_spec.md`.
