# HOST-AGE-03 design — sourced age structure for the severity draw (norwalk_gi, influenza_a)

Status: frozen — the mechanism contract, constants, and admissibility
gates below are frozen before implementation; nothing here may be revised
after it lands. Any scoring sweep of the declared bands or the `flat`
baseline is a later stage with its own frozen admissibility.

## Grounding

Benjamin's directive (2026-10-05), continuing the HOST-AGE line after the
HOST-AGE-02 presentation structure merged (PR #901):

> "Time to implement" → option **B**: the next stage of the age-structure
> line — age conditioning for the remaining draws literature can source.

This stage arms the **severity draw** — the five-state case-mix
(`severity_model.base_probabilities_by_age_band`, machinery shipped with
covid's ladder in HOST-AGE-01 / #31) — on `norwalk_gi` and `influenza_a`,
shipped default-ON with the pooled vector as the labelled baseline mode.

## What the draw is, and the denominator it needs

`draw_symptom_severity` draws a presenting host's peak state among the
four non-asymptomatic rungs, renormalising the band's vector over
`states[1:]`. A band moves the **case mix among presenters** and never
the probability of presenting (the asymptomatic entry is
validator-pinned to the reference share). The commensurable source
denominator is therefore **severe outcome per symptomatic case** —
the same denominator the draw renormalises over — not per-population
rates (hospitalization surveillance) or per-infection ratios that fold
in the asymptomatic share.

`severe_critical` carries the whole severe-outcome class:
`fatality_probability_by_severity` is null on every arm, so
hospitalisation and death fold into the one rung — the convention the
covid ladder's register row already states ("Levin's IFR ladder enters
nothing — fatality is not modelled on this arm").

## Sourced partitions

### norwalk_gi — senior vs everything else (the coarsest sourced partition)

Calderwood 2021 (*Clin Infect Dis*, DOI 10.1093/cid/ciab808): the decade
of US NORS LTCF norovirus outbreaks 2009–2018 — 13,092 outbreaks,
416,284 outbreak-associated cases — reports **21.6 hospitalisations and
2.3 deaths per 1000 cases**: severe share **0.0239** among cases.

- Armed labels: `senior`, `65-74`, `75+` →
  `[0.25, 0.55, 0.17384, 0.008235, 0.017925]` — severe = 0.0239 × the
  non-asymptomatic mass (0.75); asymptomatic and subclinical held at the
  reference 0.25/0.55; mild and moderate resplit at the pooled
  0.19:0.009 ratio.
- Every other band reads the pooled vector. No admissible design
  measures a per-case severe-outcome rate in non-institutional age
  groups (community cohorts see ~zero hospitalisations; LTCF series
  report attack rates, the wrong denominator for per-case severity), so
  no split is invented — the same discipline as the `never_symptomatic`
  row's ≥65 null.
- Grade **C**: the population analog is institutionalised elderly
  (residents + staff pooled in NORS — a resident-only rate runs higher),
  shipboard infirmary care differs from nursing-home care, and GII.4
  dominates the LTCF record while this profile is partly GI-analog (the
  `illness_probability` row's genogroup caveat). Trivedi 2012 (*JAMA*,
  DOI 10.1001/jama.2012.14023) bounds the non-attributable background at
  ~9–11% (mortality RR 1.11 during outbreaks) — the severe share is
  outbreak-attributable to ~90%.
- Consequence, recorded not softened: on a senior-skewed hull (Pavli
  72.6) the pooled severe share rises well above the declared 0.001
  reference; the Dirichlet prior's mean vector is unchanged (it is the
  pooled reference, not a band).

### influenza_a — full ladder from one commensurable design

CDC 2023–24 influenza burden estimates (Rolfes 2018 methodology,
DOI 10.1111/irv.12486; cdc.gov/flu-burden Table 1): symptomatic
illnesses, hospitalisations and deaths by age group in one
model-consistent estimate.

| band (CDC group) | (hosp + deaths) / symptomatic illnesses | severe_critical |
|---|---|---|
| `0-4` | 0.00706 | 0.005651 |
| `5-17`, `child` | 0.00277 | 0.002215 |
| `18-49` (`young_adult`, `adult`, `18-24`, `18-34`, `25-34`, `35-44`, `35-49`, `45-54`) | 0.00578 | 0.004623 |
| `50-64` (`middle_aged`, `50-64`, `55+`) | 0.01124 | 0.008988 |
| `65+` (`senior`, `65-74`, `75+`) | 0.09820 | 0.078563 |

`severe_critical` = ratio × the non-asymptomatic mass (0.8); mild and
moderate resplit at Carrat's pooled 0.459:0.2 ratio inside the
Carrat-anchored symptomatic mass; asymptomatic/subclinical stay at the
reference shares. `18-49` covering both adult bands is a **sourced
same-value declaration** — the source resolves no finer. `55+` reads the
`50-64` group (declared: the label's lower decade dominates its
population).

- Grade **B**: US surveillance-derived model estimate on an analogous
  population; the 65+ arm folds in LTCF deaths — also the analog most
  like a cruise passenger pool.
- Caveats: preliminary single-season estimates (severity ratios vary by
  season and strain mix; the profile is influenza-A-generic);
  surveillance population mixes clinical risk groups.
- Corroborating direction, not used numerically: Vandemaele 2011
  (*PLoS Med*, DOI 10.1371/journal.pmed.1001053) — deaths per
  hospitalization rise monotonically with age to ≥65.
- Consequence: the ladder is U-shaped at the young end (0-4 sits above
  5-17) and steep at the elder end — on a senior-skewed hull the pooled
  severe share rises well above the flat 0.01 reference. Recorded, not
  softened.

## Mechanism contract

`severity_probabilities(severity, age_band, profile)` in
`engines/natural_history.py`:

- `base_probabilities_by_age_band` exact-label lookup →
  `base_probabilities` fallback — the existing contract, now armed.
- **`severity_age_mode`** is the labelled-baseline axis on the whole
  term, the severity analogue of `presentation_age_mode`:
  `"flat"` reads the reference vector for every band; default
  `"by_age_band"` (and any unstated mode) applies the map.
  `_validate_age_graded_terms` rejects unknown values; the
  `PathogenProfile` schema declares it.
- No engine changes are needed to arm the map itself — HOST-AGE-01
  built it generically; this stage only wires the baseline switch and
  declares the constants.

## Axes considered and left unarmed

- **`host_factors.age_bands` incubation multipliers**: no admissible
  design measures incubation duration by age for either pathogen at
  publishable grade — challenge cohorts are adult-only and observational
  series do not stratify incubation by age. Left undeclared rather than
  invented.
- **noro non-senior severity**: measured-null justification above;
  unnamed bands pooled.

## Boundaries

- **No anchor fitting.** The severe shares are measured per-case ratios,
  not fitted to VSP/attack-rate/MAARI anchors; the pooled consequences
  on a senior-heavy hull are recorded, not corrected.
- covid's ladder untouched; boarding import (`never_symptomatic_fraction`
  /`age_draw`) untouched; the noro `severity_model.prior` Dirichlet
  stays — it is the pooled reference's uncertainty, unchanged.
- `presentation_age_mode` (HOST-AGE-02) and `severity_age_mode` are
  independent switches — one gates the presentation term, the other the
  severity term; `"flat"` on either reproduces that draw's pre-age
  behaviour.

## Open edges for a later stage

- A season-averaged or strain-resolved flu ladder (CDC publishes per
  season; 2023-24 is preliminary).
- A non-institutional per-case severe-outcome design for noro would
  support a finer partition.
- `55+` spanning two CDC groups reads the lower group; a source that
  splits 55-64 from 65+ would arm it properly.
