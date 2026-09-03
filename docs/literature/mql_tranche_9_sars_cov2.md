# Tranche 9 — the DHS Master Question List against the SARS-CoV-2 arm: emission becomes bounded, the denominator stays circular

**Status:** Evidence assembled and interpreted. **No pathogen-profile constant,
no engine constant and no screen interval changes in this document.** Three
in-tree comparisons are computed here and their arithmetic is reproducible from
the shipped profile; the changes they justify are specified in §6 and left to
their own items (#50 records this tranche, #51 the defect in §5).

**Scope:** items #30 (SARS-CoV-2 emission scale and dose-response denominator,
jointly) and #31 (severity and observation models), prompted by a direct
question about whether the DHS Master Question List answers them.

**Source under review:** *Master Question List for COVID-19 (caused by
SARS-CoV-2)*, DHS Science and Technology Directorate, Annual Report edition,
updated 2024-01-25, cleared for public release
(`dhs.gov/sites/default/files/2024-04/24_0125_mql_sars_cov-2.pdf`), 61 pages.

**Method:** the document read end to end against the shipped `sars_cov2_resp`
profile in `data/pathogens/active_profiles.json`, with each quantity traced to
the primary the MQL cites and each comparison recomputed in the model's own
units (the epoch is one hour, `epoch_duration_hours: 1`).

---

## 0. What the document is, and what that means for grading

The MQL states in its own foreword that it is a quick-reference synthesis of
publicly available sources and "should not be regarded as comprehensive". It is
a **secondary compilation**, so it carries no evidence grade of its own. Nothing
in it is citable as M or B on the strength of appearing in it; it is an *index*,
and each grade below is the grade of the primary the MQL points at.

That is not a small role. Its value here is that it collects, in one place and
in units that can be reconciled, the two quantities the #366 audit found were
not separately identifiable.

---

## 1. The emission scale is measured in absolute units, and the shipped value is inside the measurements

The #366 finding was that the emission scale and the dose-response denominator
enter only as a product against attack rates, so neither is identifiable from
outbreak data alone. That is true of *outbreak* data. It is not true of the
literature, which measures emission into air directly and in genome copies per
unit time.

| Source | Setting | Measured | In model units (copies/epoch) |
|---|---|---|---|
| Alsved et al., *Clin Infect Dis* 2022 (MQL ref 81) | 38 COVID-19 cases, exhaled aerosol particles | median 70 / 110 / 80 RNA copies min⁻¹ breathing / talking / singing; substantial between-person variation; higher nearer symptom onset | 4.2 × 10³ / 6.6 × 10³ / 4.8 × 10³ |
| Zheng et al. 2022 (MQL ref 82) | 25 Omicron patients | 40% exhaled detectable virus; 11 patients at 4.4–5.8 × 10⁷ genome copies h⁻¹ | 4.4–5.8 × 10⁷ |

Evidence grade **B** for both: direct measurement of the right quantity in the
right units, in a clinical rather than a maritime setting.

The shipped arm implies, at the curve's peak:

```
10 ** 9.0  (shedding_curve_log10 peak)  ×  5e-5  (airborne_emission_fraction)
        =  5 × 10⁴ copies per epoch
```

which is **7.6× above Alsved's talking median** and about **one thousandth of
Zheng's** figure. The two measurements are themselves **4.1 logs apart**, and the
shipped value sits inside them, towards the low end.

Two consequences, and the second is the one that matters:

1. The emission scale stops being a free knob. It is bounded by measurement —
   widely, but bounded, and by evidence that is independent of any attack rate.
2. `airborne_emission_fraction` becomes **derivable** on this arm rather than
   assumed: it is the measured emission rate divided by the modelled specimen
   titre. Item #42 records that no study reports emission *as a fraction of
   shedding*; that remains true, and is now beside the point, because both sides
   of the ratio are measured separately in copies.

**#30 therefore narrows from "both terms free" to "β identifiable given a 4-log
emission bracket".** Narrowed, not broken.

**This does not contradict the register's "2–4 orders high" row on
`shedding_curve_log10` (magnitude), and the difference between the two
statements is itself worth recording.** That row compares the raw curve — 10⁹ at
peak, a nasal *concentration* — against measured emission *rates*, and it is
right about every path that consumes the curve directly: the droplet and
direct-contact pathways read `current_shedding` and scale it by route
multipliers, never by `airborne_emission_fraction`. The airborne pool is the one
path that passes through the fraction, and there the shipped arm lands within an
order of Alsved. So the mis-dimensioning is **path-dependent**: one factor of
5 × 10⁻⁵ is doing the work of a unit conversion on one route and is absent on the
other three. That is a stronger reason to fix the units at the source than
either observation alone.

## 2. The dose-response denominator does not get an independent value

The MQL offers three candidates, and the distinction between them is the whole
finding.

| Candidate | MQL ref | What it is | Usable as β here? |
|---|---|---|---|
| Prentiss et al., ID50 ≈ 361–2,000 particles (≈250–1,400 PFU) | 39 | **Modelled** from high-attack-rate events | **No** — fitted to attack rates |
| Riediker et al., infection from ≈500 / 300 / 100 copies (WT / Delta / Omicron) | 40 | **Modelled** aerosol transmission estimate | **No** — same circularity, plus a copies-per-particle assumption |
| Killingley et al., *Nat Med* 2022 human challenge: 10 TCID50 (≈7 PFU) intranasal, 36 adults 18–29, 53% infected, 89% of those mild/moderate | 11 | **Measured**, and the only independent one | **Not yet** — TCID50, not genome copies |

The first two are fitted to attack-rate data, Prentiss explicitly to
superspreading events. Adopting either and then scoring the model on Diamond
Princess or Greg Mortimer attack rates is fitting a physical constant to an
anchor the model is scored against, which the repository rules forbid, and which
would be undetectable afterwards because the number would carry a citation.

Killingley is the genuinely independent measurement and it is denominated in
TCID50 — **the same unit trap as item #43** on the norovirus arm, where a
literature ID50 cannot be dropped into a genome-copy dose axis without a
copies-per-infectious-unit conversion. The MQL's own figures show the conversion
is not a detail: 10 TCID50 ≈ 7 PFU against modelled infectious doses of 10²–10³
*copies*.

Also recorded from the same section, not adoptable but bounding: the average
transmission bottleneck is estimated at ~1,200 viral particles, with household
estimates of 1–8 and a traced Delta outbreak at ~1,000. A bottleneck is not an
inhaled ID50 and the three must not be pooled.

**β stays blocked (⊘ joint).** What changed is that its uncertainty is now
inherited from a *measured* emission bracket rather than shared with a second
free parameter.

## 3. #31: the severity ladder exists, and it should read the agent's age

`sars_cov2_resp` carries **no `severity_model` and no `observation_model` at
all**, where `norwalk_gi` carries both. The MQL supplies, via its primaries:

| Quantity | Value | Primary (MQL ref) | Grade |
|---|---|---|---|
| Share of symptomatic cases that are mild | 81% | Wiersinga 2020 (221) | B |
| ICU admission among hospitalised, US | 29–34% | Mody 2021, Nguyen 2021 (230–231) | B |
| Death among hospitalised, US | 12.6–13.6% | same | B |
| Age-specific infection fatality rate | 0.004% (0–34), 0.068% (35–44), 0.23% (45–54), 0.75% (55–64), 2.5% (65–74), 8.5% (75–84), 28.3% (85+) | Levin 2020 meta-analysis (273) | B |
| Asymptomatic share, <19 years | 21–28% | (292, 297–298) | B |
| Omicron vs Delta hospitalisation or death | 59% lower | Ulloa 2022 (224) | B |

The structural point is the age ladder rather than any single number. It spans
**four orders of magnitude across the age range**, and cruise passengers are not
a general population — Pavli's measured mean passenger age is 72.6. A severity
vector fitted to a population average would understate this population by more
than an order, and no single vector can be right for both a crew arm and a
passenger arm on the same hull. Severity should be **a function of the agent's
age**, which the model already carries, rather than one fitted five-state prior.

That is the same shape of finding as the three-curves discussion: the fix is
where the quantity is read from, not what value it takes.

## 4. Two in-tree constants checked against the same document

**`airborne_half_life_hours` = 1.1 is below every dark measurement.**

| Source | MQL ref | Measured aerosol half-life |
|---|---|---|
| Schuit et al. 2020 | 579 | ≈86 min (1.43 h), simulated saliva, darkness; humidity alone no significant effect; simulated sunlight gives 90% loss in 6–19 min |
| van Doremalen et al. 2020 | 576 | 2.7 h (<5 µm, 21–23 °C, 65% RH, no sunlight) |
| Fears et al. | 578 | infectivity retained up to 16 h (23 °C, 53% RH, no sunlight) |

Sourced interval **[1.43, 2.7] h**, grade B. The register's §3.2 row grades this
field **M, citing van Doremalen** — but van Doremalen's measurement *is* the 2.7 h
figure, so the row attributes the shipped 1.1 to a paper that reports something
else. This is the fourth instance of the campaign's recurring archetype: a
citation attached to a value the cited paper does not contain. The class drops
to **I** (inherited) until a value inside the interval is adopted.

The shipped 1.1 h clears the
airborne pool faster than the fastest measurement, and per-epoch survival moves
from 0.533 at 1.1 h to 0.616–0.774 across the measured interval — a direction,
not a wash. The same inherited 1.1 sits on `norwalk_gi`, where tranche 5 recorded
a **null** on norovirus airborne decay: one number, two arms, and it was never
measured for either.

**`surface_decay_per_day` = 0.95 is corroborated**, which makes it the first
inherited SARS-CoV-2 constant a search has confirmed. The field is the
fraction-valued deprecated alias (Wave 2 made `surface_decay_log10_per_day` the
preferred key, converting f = 1 − 10⁻ᵏ), and the ambiguity does not bite here
because **both readings land inside the measurement**:

| Reading | Implied half-life |
|---|---|
| 0.95 as a per-day fraction | 5.55 h |
| 0.95 → 1.30 log10 day⁻¹ | 7.6 h |
| Xu 2023 review (ref 571), stainless steel / plastic / glass at 22 °C | **5–9 h** |

Recorded also, and not adoptable as a single constant: persistence is strongly
material- and condition-dependent (porous surfaces 1–5 h; up to 28 days at 20 °C
in darkness with a protein-rich matrix, Riddell ref 575; 90% loss every 6.8–12.8
min under simulated UVB, Ratnesar-Shumate ref 577), and the MQL states fomite
transmission is not considered common.

## 5. The defect the document exposed: the COVID arm still has one clock

Tranche 8 separated the shedding clock from the illness clock and added
`shedding_duration_days`. **`norwalk_gi` carries it at 15. `sars_cov2_resp` does
not carry it at all**, so clearance falls back to `recovery_day` = 7 while the
authored curve runs 15 days: **days 8–14 are unreachable, 7 of 15 authored
days**.

Unlike norovirus this is *not* a dose defect. The COVID tail is 2.0–5.5 log10
against a 9.0 peak, so the unreachable days are **0.021% of the authored
cumulative curve mass** — against 38.5% for norovirus before the tranche-8 fix
on the same measure. It is a **detectability** defect: a host that stops shedding
on day 7 cannot test positive on day 10.

The literature the MQL indexes measures exactly that tail:

- Keske 2023 (ref 213): viral culture positivity — a surrogate for infectious
  shedding — of **83%, 52%, 13.5% and 8% at days 5, 7, 10 and 14** after the
  first positive test in 53 Omicron-infected healthcare workers; **19% shed
  infectious virus after symptoms stopped**.
- Median RNA shedding by nasopharyngeal swab ≈7 days; RNA detectable to 21 days
  (14 in faeces) in samples containing **no viable virus** — so an RNA-based
  duration is the wrong quantity for an infectiousness clock and the right one
  for a PCR-positivity clock. The model needs both, and they differ.
- No viable virus isolated beyond 9 days post-onset in a systematic review;
  most individuals not infectious beyond 10 days.

This bears directly on #33: Diamond Princess was a **repeat-testing campaign over
weeks**, so an arm that stops shedding on day 7 cannot reproduce the observed
positivity series regardless of how the emission scale is set. Recorded as #51.

## 6. What this tranche licenses, and what it does not

**Licensed as evidence (not applied here):**

1. An emission-rate bracket for the SARS-CoV-2 arm, 4.2 × 10³ – 5.8 × 10⁷ copies
   per epoch at peak shedding, grade B, from two independent studies — with
   `airborne_emission_fraction` derivable as measured-rate ÷ modelled titre
   rather than assumed.
2. An aerosol half-life interval of [1.43, 2.7] h, grade B, against a shipped
   1.1 h that lies outside it.
3. Corroboration of `surface_decay_per_day` = 0.95 under both readings of the
   field, grade B.
4. A severity ladder for #31, grade B, to be read **as a function of agent age**
   rather than adopted as a single five-state vector.
5. A measured infectious-duration series (Keske) and the RNA-versus-viable
   distinction, for the shedding-duration and observation work in #51 and #33.

**Explicitly not licensed:**

- No value for the dose-response denominator β. The two numeric candidates are
  fitted to attack rates, and the independent measurement is in TCID50.
- No adoption of a modelled copy threshold (500 / 300 / 100) as a measured ID50.
- No treatment of RNA shedding as infectious shedding, in either direction.
- No conversion of aerosol genome-copy emission into infectious-virus emission;
  every emission figure above is RNA.
- No maritime-specific quantity of any kind. The MQL contains no shipboard
  measurement, no cruise observation sensitivity, and no ventilation-conditioned
  emission figure.
