# Tranche 24 — second pass on the never-symptomatic null: what an adult natural-exposure design would have to measure, and why none of them does

**Status:** Evidence assembled and interpreted; the tranche-11 null is
**re-searched and confirmed**. **No profile constant, engine constant, config
value or interval changes in this document.** One structural finding about
`initial_infected` (#54) is recorded here and acted on in `engines/initiation.py`
in the same change. **#54 is since resolved** (Track C, C1): the shipped
`norwalk_gi` profile now boards through `initiation.boarding` with
`never_symptomatic_fraction` supplied as a swept interval, never a point — §3
records both the original blocker and how it was cleared.

Tranche 11 searched `never_symptomatic_fraction` and found two admissible
designs — adult challenge studies at `[0.22, 0.36]` and community birth cohorts
at `[0.59, 0.68]` — which it declined to pool, and recorded a null for the
model's own population: adults, natural exposure, whole course of infection.
This tranche asks the narrower question the register's state depends on: **is
that null a gap in our reading, or a gap in the designs?** It is the second.

## §0 — the target quantity, stated so a design can fail it

The field is the fraction of **infected** hosts who **never** develop
gastroenteritis over the **whole course** of the infection. Three properties
follow, and they are what the searches below are graded against:

1. **The denominator is infections**, not people, not person-time, and not
   positive specimens.
2. **The numerator is an episode-level outcome**, resolved over the whole
   episode — a host sampled once while asymptomatic may be pre-symptomatic.
3. **Ascertainment must not be conditioned on symptoms** in either direction.
   An AGE-triggered enrolment has no asymptomatic arm; an asymptomatic-only
   screening has no symptomatic arm. Either way the ratio is undefined, not
   merely imprecise.

## §1 — queries (Consensus MCP, 2026-09-05)

All seven ran with `exclude_preprints=true`; the first four with `year_min`
(2010, then 2005), the last three unrestricted.

| # | Query | Outcome |
|---|---|---|
| 1 | proportion of norovirus infections asymptomatic in adults prospective community cohort | Returns the Qi 2018 meta-analysis of asymptomatic **prevalence** and the Kobayashi adult screening pair — no infection-denominator design |
| 2 | asymptomatic norovirus infection adults household transmission cohort serial stool sampling | Rate-limited; re-run as #4 |
| 3 | norovirus infection symptomatic fraction older adults long-term care prospective surveillance | Returns LTCF **outbreak** investigations (Costantini 2015 and kin) — excluded by the standing outbreak-conditioning rule, not by design quality |
| 4 | norovirus infections asymptomatic proportion adults household contacts serial stool sampling | Returns the sample-share family (Phattanawiboon 2020, Juniastuti 2023) and a second China outbreak meta-analysis (Wang 2024) — §2 F3 |
| 5 | asymptomatic and symptomatic norovirus infection incidence adults cohort weekly stool specimens | Returns the Kobayashi pair again plus PREVAIL — i.e. it returns **children** when it returns an infection denominator at all |
| 6 | norovirus incidence adult cohort proportion of infections resulting in acute gastroenteritis | Returns AGE-triggered incidence studies (ORION/Schmidt 2026, MAAGE/Burke 2021, Grytdal 2016, Campbell 2025) — §2 F1(b), F2 |
| 7 | community cohort all ages norovirus infection asymptomatic and symptomatic episodes routine stool collection incidence | Returns paediatric community cohorts (Yu 2024 Philippines, El-Heneidy 2022) and Campbell 2025 — no adult stratum with both arms |

**Recorded negative:** across seven queries, **zero** studies measure the
symptomatic share of norovirus infections in adults under natural exposure with
an infection-level denominator. This is now a twice-searched null. Everything in
§2 is **Ab** (abstract-level, retrieved through Consensus); no number here is
promoted to an interval, so abstract-level retrieval is sufficient for the
negative and would **not** be sufficient if anything were being adopted.

## §2 — findings

### F1 — the adult designs fail at the denominator, in three distinguishable ways

**(a) Asymptomatic-only screening.** Kobayashi 2021 (*Clin Microbiol Infect*,
DOI 10.1016/j.cmi.2021.06.004) screens 4,536 apparently healthy adults, mean age
58, and finds 2.5% norovirus-positive; Kobayashi 2022 (*Infect Dis*,
DOI 10.1080/23744235.2022.2134447) follows 288 of them and finds 4.9% positive at
a median 599 days. Both enrol **on the absence of symptoms**, so the symptomatic
arm does not exist by construction. These are the papers the *boarding
prevalence* row (tranche 10) is built on, and that is the only thing they can be:
**a prevalence among asymptomatic adults is not a share of infections**, and
reading Qi 2018's pooled adult 4% as this field would be the same category
error one meta-analysis deeper.

**(b) AGE-triggered enrolment.** ORION (Schmidt 2026, *Open Forum Infect Dis*,
DOI 10.1093/ofid/ofaf695.380) is the largest and most recent adult community
design available — 3,527 adults across four Kaiser Permanente sites, weekly
symptom reporting, 525 AGE episodes over 15,329 person-weeks, 15 of 325 tested
stools norovirus-positive. Stool is self-collected **only on an AGE episode**, so
the study cannot see an infection that never presents. Burke 2021 (MAAGE,
*Clin Infect Dis*, DOI 10.1093/cid/ciab033) and Grytdal 2016 (*PLoS One*,
DOI 10.1371/journal.pone.0148395) are medically-attended designs, one further
filter down the same ladder.

**(c) Sample-share designs.** Phattanawiboon 2020 (*PLoS One*,
DOI 10.1371/journal.pone.0236502) samples 38 people in 16 Bangkok families for a
year and reports that **89.1% of norovirus-positive samples came from
individuals with no diarrhoea episode**; Juniastuti 2023 (*J Med Virol*,
DOI 10.1002/jmv.29164) samples three households weekly and reports "most
positive samples" asymptomatic without counts. These are the only adult-inclusive
designs that sample irrespective of symptoms, and their denominator is
**positive specimens**, which is the wrong one in a way that has a **known
sign**: asymptomatic and convalescent shedding both outlast the 1–2 days of
illness (tranche 7), so specimen-share is **length-biased upward** relative to
episode-share by an unknown factor. 89.1% is therefore not a candidate value for
a field defined over episodes — and the cohorts are mixed-age families, so even
the biased figure is not an adult figure.

### F2 — Campbell 2025 is the closest design, and it still measures something else

Campbell 2025 (*Am J Trop Med Hyg*, DOI 10.4269/ajtmh.24-0331) runs active
all-ages AGE surveillance in San Jerónimo, Peru — household visits two to three
times weekly, 4,176 person-years — and adds an **asymptomatic control household
for every fifth case**: 186 of 1,014 case stools (18%) and 56 of 672
asymptomatic-control stools (8%) were positive, odds ratio 2.2 (1.6–3.1). It has
both arms, in adults among others, under natural exposure. It still cannot yield
this field: cases enter **by AGE** and controls enter **by household selection**,
so the two arms have incommensurable denominators, and their contrast is a
prevalence odds ratio rather than a symptomatic share. That a design this close
does not produce the quantity is the strongest available evidence that the null
is structural.

### F3 — the outbreak-conditioned exclusion stands, and gains a member

Wang 2024 (*J Med Virol*, DOI 10.1002/jmv.29393) pools asymptomatic norovirus
prevalence across 97 Chinese outbreak reports; Costantini 2015 (*Clin Infect
Dis*, DOI 10.1093/cid/civ747) is the long-term-care outbreak analogue. Both are
excluded for the tranche-10 reason already recorded in the register: a population
assembled **because an outbreak occurred** is conditioned on the outcome the
model is scored against, so importing its asymptomatic share would seed the model
with its own answer. Nothing in this pass revisits that.

### F4 — the paediatric interval is not transportable, and the direction is known

The community interval remains child-measured (El-Heneidy 2022, Baker 2026
PREVAIL, and now Yu 2024, *IJID Regions*, DOI 10.1016/j.ijregi.2024.100549:
10.8% of 2,031 asymptomatic stools against 17.4% of 527 diarrhoeal episodes in
children under 4). Tranche 11 already records that the never-symptomatic
fraction **falls with age** across the first two years; the model's population is
adult passengers of measured mean age 72.6. A paediatric interval is therefore
not conservative in a known direction for a geriatric population — the age trend
is measured only over the range where immunity is being acquired, and nothing
measures where it goes after that.

## §3 — the structural half (#54): why the shipped profile kept `initial_infected`, what changed instead, and how the block was cleared

**As found (first pass of this tranche).** Migrating `norwalk_gi` off `initial_infected` has a destination — the boarding
prevalence channel of `engines/initiation.py` — and that destination was closed:
enabling boarding requires `state_split.never_symptomatic_fraction`, §1–§2 license
no value for it, and the engine refuses to default one. The intermediate move —
keeping the fiat index case but relocating it to `initiation.explicit_seeds` in
`crusher_labs/config.yaml` — was examined and **rejected on a defect it would
introduce**:

- Initiation ownership is per pathogen, and an owned pathogen is **dropped from
  legacy seeding** (`_seed_legacy_infections` is called only for unowned
  pathogens in `orchestrator_init.py`).
- The mega-cruise campaign sweeps `initial_infected` as a **pathogen override on
  `crusher_labs/config.yaml`** — tiers `sr*`, `vd*`, the sentinel-recovery cells
  and the calibration iterators all write `path_over[pathogen_id]
  ["initial_infected"]`, and the value is stamped into the run id as `init<N>`.
- So an `explicit_seeds` entry for `norwalk_gi` in the shipped config would make
  every campaign run take the seed's count instead of the swept one, **silently**,
  while the run id still carried the swept label. An axis would become a naming
  convention.

The corresponding engine defect is that the collision was silent at all: the
existing load error covered `boarding` over `initial_infected` but not
`explicit_seeds` over it. That is now one refusal covering both mechanisms
(`_refuse_legacy_index_case`), so the migration cannot be performed halfway
without the run failing to load and saying why. At that point the shipped `norwalk_gi`
profile was left at `initial_infected: 1` and the migration was
recorded as blocked on two named prerequisites — a licensed or swept
`never_symptomatic_fraction`, and re-keying the campaign's index-case axis onto
whichever channel replaces the field.

**Resolution (#54 / C1).** Both prerequisites were met without licensing a value:

- `never_symptomatic_fraction` enters as a **swept axis**, not a point. The two
  tranche-11 intervals stay **separate regimes** — `adult_challenge`
  `[0.22, 0.36]` and `community_cohort` `[0.59, 0.68]` — and a campaign tier
  names which regime it sweeps (`never_symptomatic_regime`) or lists explicit
  fractions (`never_symptomatic_fractions`). The union is deliberately not
  offered as a single range: §F4 shows the paediatric interval is not
  transportable to a mean-age-72.6 population and that the fraction falls with
  age, so the adult-challenge regime is the campaign default. Its midpoint
  (0.29) is the coordinate an unswept run carries and is recorded as a campaign
  parameter, **not** adopted into the register as a value.
- `crusher_labs/config.yaml` gained an `initiation.boarding.norwalk_gi` block
  carrying all four `BoardingSpec` coordinates: prevalence at the register
  interval midpoints (passenger 0.0325, crew 0.0185), the adult midpoint above,
  and the derived `presymptomatic_share_of_presenting` 0.04. The shipped
  profile's `initial_infected` is `null`, so `_refuse_legacy_index_case` passes
  and `initiation_owned_pathogens` drops `norwalk_gi` from legacy seeding.
- The campaign axis was re-keyed (`picard_framework/runs/mega_cruise_campaign/
  boarding_axis.py`): every site that wrote `path_over["norwalk_gi"]
  ["initial_infected"]` now writes `config_overrides["initiation"]["boarding"]`,
  the run id carries the swept coordinate (`nsf22`, `bp25c7`, `psp4`) instead
  of `init<N>`, and a tier that still lists a count axis for an owned pathogen
  is a generation error unless it declares `fiat_index_case: true`. Unowned
  pathogens keep their legacy count axis unchanged.

## §4 — what changes, and what does not

**Changes:** this file; the `never_symptomatic_fraction` register row's evidence
and state, to record the second-pass null and the #54 blocker; the
`defect_resolution_plan.md` C1 row; the initiation spec's outstanding-work
section; and the seed-side load error plus its two tests.

**Does not change:** the two tranche-11 intervals, which no source in this pass
narrows or widens, and which the later #54 resolution sweeps rather than adopts.

**Changed later, by the #54 resolution recorded in §3:** the shipped `norwalk_gi`
profile (`initial_infected: null`); `crusher_labs/config.yaml`, which now carries
an `initiation.boarding` block; and the boarding gate, which is open for
`norwalk_gi` with the never-symptomatic coordinate supplied by the campaign axis.

**Changed again, by #54's follow-on:** the coordinates moved off `config.yaml`
and onto each profile, so every shipped pathogen except `legionella_pneumophila`
boards through its own block and `config.yaml` keeps only the gate. The two
never-symptomatic regimes recorded here are unchanged and remain unpooled;
they now apply to `norwalk_gi` and `norovirus_gii4`, and the other pathogens
carry their own Consensus-sourced plausible defaults (register §3.5), each a
swept starting point rather than an adopted value. Nothing in §§1–3 is
narrowed by that pass: no adult natural-exposure design with an infection
denominator was found for any of them either.
