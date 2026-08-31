# Literature

> **Status:** Reference. Raw literature-search output, kept as evidence.

These are the search results and review syntheses behind parameter choices. They
are **not** specifications and nothing in them is authoritative about the model.

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
