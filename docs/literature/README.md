# Literature

> **Status:** Reference. Raw literature-search output, kept as evidence.

These are the search results and review syntheses behind parameter choices. They
are **not** specifications and nothing in them is authoritative about the model.

The fleet-wide register
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
carries the per-quantity status these tranches are the evidence for; where the two
disagree, the citation is here and the status is there.

A constant's provenance lives at its point of definition in code, with an
evidence grade (A = measured in this setting, B = measured in an analogous
setting, C = inferred or assumed) — see
`.agents/skills/model-parameter-provenance/SKILL.md`. Use this directory to check
a citation or to avoid repeating a search, not as a source of truth.

Two warnings, because both are easy to get wrong:

- **A search result is not a parameter.** Several of these PDFs are Consensus
  queries whose top hits were rejected on inspection. The decision is recorded in
  the constant's comment or in
  [`../norovirus/norovirus_model_history.md`](../norovirus/norovirus_model_history.md),
  not here.
- **Documented negative results matter.** Where a search found nothing usable,
  that is recorded so the search is not repeated — the per-zone-class cleaning
  schedule search in
  `telemetry_buffer/observation_model/cleaning_schedule_sweep_spec.md` is the
  worked example.

| File | Query or scope |
|------|----------------|
| `For_a_norovirus-infected_adult_what_is_the_total_.pdf` | Total faecal shedding per norovirus-infected adult |
| `How_frequently_do_people_touch_shared_surfaces_in_.pdf` | Shared-surface touch frequency — behind the #353 contact-rate correction |
| `How_much_does_routine_cleaning_and_disinfection_re.pdf` | Cleaning and disinfection efficacy — behind the #355 surface-cleaning constants |
| `When_norovirus_is_inhaled_as_an_aerosol_from_vom.pdf` | Aerosolised vomitus inhalation — behind the #352 emesis pathway |
| `Im_parameterizing_the_worlds_most_sophisticated_.pdf` | Open-ended parameterisation search |
| `Cruise Ship Dining Model Data.pdf` | Dining service patterns and rotation |
| `Cruise Ship Outbreak Model Parameterization _ Literature Insights.pdf` | General outbreak-model parameterisation review |
| `Cruise Ship Medical Care & Staffing_ Practical Reports & Lived Experience.md` | Shipboard medical staffing, clinical operations, infirmary capacity — relevant to the ~0.60 infirmary capture constraint |
| `parameter_sourcing_bundle.md` | Per-arm count of profile scalars carrying a citation; first Consensus tranche on the blank high-sensitivity factors; the null result on norovirus airborne decay; the question list for Edison Science |
| `edison_provenance_request.md` | The provenance questions put to Edison Science, written to be readable without a checkout — 17 questions across the three arms, none of which a paper can answer |
| `consensus_tranche_2.md` | Second Consensus tranche, ordered by the Morris ranking: genogroup-stratified secretor evidence, emesis titre bounds, influenza emission/dose in one unit system, the conditional-illness functional form, and two recorded nulls. **§1–§2 superseded by tranche 3 §1** — the evidence is sound, the arm it was attached to was not |
| `consensus_tranche_3.md` | Third Consensus tranche: the correction to tranche 2 (the arm declares itself GII, so the GII non-secretor interval governs and the *dose-response* is the mis-genogrouped term); COVID severity from three sources none of which is a five-state vector, with Emery 2020 barred as calibrated on our training set; PCR sensitivity as a function of time since exposure; total norovirus shed copies, which retires the stool-mass null rather than filling it, and disagrees with our second-ranked factor by 1–2.4 orders. **§4's Kirby/Ge conflict is retired by tranche 4 §1** — it was a mean/median plus genogroup artefact of comparing abstracts |
| `consensus_tranche_4.md` | Fourth Consensus tranche, from primary texts rather than abstracts: the Kirby/Ge emesis "discrepancy" dissolves (like-for-like GII.2 1.8 × 10⁷ against Ge's 3.0 × 10⁷; the rest is a 20× mean/median ratio on a heavy tail), and in dissolving it exposes that the shipped `EMESIS_TITRE_GEC_PER_ML` = 3.9 × 10⁴ is Kirby's *abstract* pooled-GII figure including a 2-subject pilot the paper's Results excludes — the GII.2 measured value is 1.6 × 10⁵; plus Alsved 2019's measured airborne norovirus as a check the emesis pathway has never faced, and a SARS-CoV-2 emission/denominator pair quoted in the same units at last (task #30) |
| `edison_v3_spec_review.md` | Review of Edison's `formal_spec_v3.md` and `pre_establishment_clearance_params_v3.json`: what they answer (dose-response is beta-frailty, not the classic approximation; shedding curve is copies/g), where they are stale, and the identifiability concern with the clearance rates |
| `edison_norovirus_influenza_bundle_review.md` | Review of Edison's norovirus sourcing bundle and influenza parameter bundle: the Teunis 2008 provenance it supplies for the shipped dose-response and conditional-illness rows, the secretor condition that comes with it, and where the influenza bundle's units and dose-response do not yet meet ours. Received and reviewed; nothing adopted |
| `consensus_tranche_6.md` | Sixth Consensus tranche, on the norovirus dose axis and the secretor interval: the shipped beta-Poisson pair (α 0.111 / β 32.81) is the disaggregated GI.1 challenge arm of Teunis 2008 and lies *inside* the human GII interval α ∈ [0.072, 0.161] at fixed β (Rouphael 2022 GII.2 challenge, Guix 2020 GII outbreak illness ID50 as a lower bound, Ramesh 2020 gnotobiotic-pig GII.4 as Grade C corroboration), within 3% of that interval's geometric centre — so the dose axis becomes declared-and-swept rather than blocked; the “≈3.7× GI-vs-GII per genome copy” comparison is **withdrawn as a unit error** (reproducing Teunis 2020's 0.076 in the shipped family needs α = 2.85 and an ID50 of ≈10 copies, five orders below every challenge measurement, because those fits report risk per *aggregate*); and Kambhampati 2015's genotype-specific pooled ORs widen the secretor interval to [0.04, 0.83], a width that is genotype composition rather than measurement error |
| `consensus_tranche_5.md` | Fifth Consensus tranche, on the two surface constants that gate the admissible-region search: the norovirus `surface_decay_per_day` interval recut to [0.14, 0.84] from five surrogate studies (an order of magnitude in rate, with Edison's fast-end citation not checking against the paper it names), and task #42 reframed — the profile's `surface_deposition_fraction` feeds the airborne pool, not the surface pool, and the hand-to-surface literature spans 0.1% to 60% governed by wet-versus-dry rather than by direction, so a 0.6% point value would have been 20x low against the same study cited for the other direction |
| `edison_covid_influenza_bundle_review.md` | Review of Edison's SARS-CoV-2 and influenza sourcing bundles: the Killingley 2022 human challenge that gives the COVID arm its first unit-compatible dose anchor (and disagrees with Zhang & Wang by 1-2 orders, which sets beta's interval rather than its value), an independent withdrawal of the Watanabe attribution, and three conversion or mechanism errors — the influenza half-life arithmetic, Edison's two influenza bundles disagreeing on the value that clamps to total surface loss, and an influenza illness form that contradicts Carrat's dose-independence. Received and reviewed; nothing adopted |
| `consensus_tranche_7.md` | Seventh Consensus tranche, on the norovirus shedding clock: `recovery_day` is simultaneously the illness duration and the infectious period, so a host reaches only curve indices 0–2 of the authored 15 and 69.1% of the authored symptomatic curve integral is never emitted (measured through the real progression seam by `telemetry_buffer/observation_model/shedding_clock_check.py`), against Atmar 2008's separately measured 1–2 days of illness and median 28 days of shedding, Kirby 2014's shedding up to three weeks past symptom resolution and Cheng 2021's GII cessation by day 15; the repair is a new `shedding_duration_days` field (proposed 15, interval [12, 30]), a prerequisite for #45; the immunocompromise evidence is duration and infectiousness, never acquisition (van Beek 2017 median 218 days, Davis 2020 infectious virus confirmed, Chaimongkol 2024 magnitude 10⁴–10¹¹), so `immunocompromised_multiplier` = 2.0 is withdrawn as a quantity while `immunocompromised_fraction` is bounded to [0.02, 0.074]; and the curve's 11.0 peak is Atmar's GI.1 value with GII.2 about two logs below, declared but not adoptable because emission scale and dose-response enter as a product |
| `mql_tranche_9_sars_cov2.md` | Ninth tranche, on the SARS-CoV-2 arm, from the DHS Master Question List (January 2024) read as an index into its primaries rather than as a source: emission is measured in absolute units after all (Alsved 2022 at 4.2–6.6 × 10³ copies h⁻¹, Zheng 2022 at 4.4–5.8 × 10⁷, the shipped arm inside them), so #30 narrows from both-terms-free to β-identifiable-given-a-4-log-bracket; the dose-response denominator stays blocked because both numeric candidates are fitted to attack-rate data and the one independent challenge measurement is in TCID50 (#43's unit trap); the #31 severity ladder arrives with a four-order age dependence that matters against Pavli's mean passenger age of 72.6; `airborne_half_life_hours` 1.1 is outside the measured [1.43, 2.7] h and was mis-cited to the paper reporting 2.7; `surface_decay_per_day` 0.95 is corroborated under both readings of the field; and the arm still carries no `shedding_duration_days`, so 7 of its 15 authored curve days are unreachable |
| `consensus_tranche_10.md` | Tenth tranche, on the norovirus importation channel (#45 part 3): the boarding prevalence the model has never had is directly measured in non-outbreak adults — 2.5% of 4,536 healthy adults of mean age 58 (Kobayashi 2021) against Qi 2018's pooled adult 4% and 0.71–3% in food handlers — giving passengers [0.025, 0.040] and crew [0.007, 0.030]; the chronic-shedder prevalence #45 predicted would matter is derived two ways that disagree by 2.5 orders (1.4e-5 to 4.2e-3) and is one to three orders *below* the general channel, so it is recorded as a bounded null and chronic shedding belongs in the model as a swept duration axis rather than a prevalence; and the 18–22% asymptomatic prevalence measured *during outbreaks* is recorded as the excluded value, because adopting it as a boarding input would seed the model with the outcome it is scored on |
