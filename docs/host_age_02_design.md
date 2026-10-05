# HOST-AGE-02 design — sourced age structure for the presentation draw (norwalk_gi, influenza_a)

Status: frozen — the mechanism contract, constants, and admissibility
gates below are frozen before implementation; nothing here may be revised
after it lands. Any scoring sweep of the declared bands or the `flat`
baseline is a later stage with its own frozen admissibility.

## Grounding

Benjamin's directive (this session's prompt, 2026-10-05):

> "Let's get sourced noro and flu age structure in place first. Design,
> build, turn on by default."

i.e. the age-structured presentation draw becomes the shipped default for
`norwalk_gi` and `influenza_a`; the pre-age-structure behaviour survives
only as a labelled baseline mode, never default-off.

The measured motivation is committed:
`docs/norovirus/noro_symptom_course_01_decomposition.md`
(NORO-SYMPTOM-COURSE-01, PR #900) measured pooled ill/inf ≈ 0.18
hull-invariant while the shipped Hill realizes 0.234 presentation —
below both sourced never-symptomatic regimes (community 0.32–0.41 sf,
challenge 0.64–0.78 sf). The hull's age mix is senior-skewed (Pavli
measured passenger mean 72.6), which is the argument covid's ladder
already made (HOST-AGE-01 / #31): read the agent's age instead of one
vector.

## The stated fact that fixes the design form

**norwalk_gi's `illness_probability` pair (η = 0.508, γ = 0.095) is the
attributed dose-conditional measurement** — provenance register §3.1,
class **I → M**, Teunis 2008 GI.1 challenge, same table as the
dose-response pair. The row's `⊘ mech` state is a **genogroup caveat on
the pair** (a GI.1 measurement carried on a GII profile with no
GII-specific replacement measured), not a defect in the dose-conditional
form. Nothing age-resolved and dose-conditional exists to replace it.

That decides the form the prompt posed: **age multiplies the Hill, it
does not replace it.** Deleting the Hill for a flat by-band share would
discard the only dose-conditional measurement this arm carries — the
covid deletion precedent does not transfer because covid's η/γ were
unattributed near-neighbours, which noro's pair is not.

For `influenza_a`, `symptomatic_fraction` is already the measured
proportion (Carrat 2008, grade B), and there is no dose-conditional
mechanism to preserve — age conditions the proportion directly, through
the map HOST-AGE-01 already built.

## Mechanism contract

The presentation probability is `presentation_probability(inf, prof,
age_band)` in `engines/natural_history.py`, evaluated inside
`draw_symptom_onset` at the host's own onset epoch — both
`presentation_draw_mode`s (`once_per_course` default and the
`daily_hazard` baseline) flow through it unchanged.

Three terms, in evaluation order:

1. `symptomatic_fraction_by_age_band` — a per-band **replacement share**
   (exact-label lookup; the severity ladder's convention). A band the map
   names reads its own measured proportion. Existing seam, previously
   armed only on `sars_cov2_resp`; now armed on `influenza_a`.
2. `symptomatic_fraction` — the flat measured proportion; the reference
   an unnamed band (or a band-free host) reads on a fraction profile.
3. `illness_probability` — the dose-conditional Hill. New term:
   `illness_probability.age_factor_by_age_band`, a per-band
   **multiplier** on the Hill output — factor, not share, so the curve
   stays dose-conditional at every band. A band the map does not name
   multiplies 1.0 (the adult/reference level), which is what makes the
   coarsest sourced partition expressible without inventing a full
   five-band vector.

`presentation_age_mode` is the baseline-mode convention on this axis:
the default (and any unstated mode) is `"by_age_band"`, which applies
the declared maps; `"flat"` is the labelled baseline — the share ignores
both age terms and every host reads the pooled value, the pre-HOST-AGE-02
behaviour bit-for-bit. Load-time validation
(`_validate_age_graded_terms`, extended) bounds the factor map as finite
non-negative multipliers and rejects any other `presentation_age_mode`
value, so a typo'd mode is a load error rather than a silent default.

Unarmed profiles are inert by construction: no map and no factor means
the draw is unchanged; `flat` on a profile with no age terms is a no-op
that names the baseline.

The same convention now covers every age-graded axis: `severity_age_mode`
(HOST-AGE-03) on `severity_model.base_probabilities_by_age_band`, and
`susceptibility_age_mode` on `dose_response.susceptibility_by_age_band`
(HOST-AGE-01) — each `"flat"` is the labelled pre-map baseline on its own
axis, applied or not in exactly the way `presentation_age_mode` is.

## Sourced declarations

### `norwalk_gi` — `illness_probability.age_factor_by_age_band`: `{"0-4": 0.51, "5-17": 0.51, "child": 0.51}`

The sourced partition is **child-vs-adult, the coarsest the literature
defends**:

- Numerator — pediatric community cohorts, symptomatic share of
  PCR-confirmed infections under natural exposure: the register's
  `community_cohort` never-symptomatic interval [0.59, 0.68] →
  sf ≈ **0.365** midpoint (Baker 2026 PREVAIL, Clin Infect Dis
  10.1093/cid/ciag033 — ~one-third of 402 GI+GII infections in children
  <3 symptomatic; El-Heneidy 2022 ORChID, PIDJ 10.1097/inf.0000000000003667
  — 82/209 = 39.2%; Cannon 2026 Pediatrics 10.1542/peds.2025-072461
  corroborates ~two-thirds asymptomatic across enteric viruses on the
  same cohort).
- Denominator — adult challenge cohorts, the register's
  `adult_challenge` interval [0.22, 0.36] never-symptomatic → sf ≈
  **0.71** midpoint (Gray 1994, Atmar 2014, Newman 2016, Frenck 2012
  GII.4, Rouphael 2022 GII.2), the same population the Hill was fitted
  on.
- Factor = 0.365 / 0.71 ≈ **0.51** — a cross-design ratio of two regimes
  the register keeps deliberately unpooled for the boarding split, so
  Grade C as an adaptation even though both regimes are Grade B as
  intervals.

Declared caveats, recorded not softened (profile notes carry the same
text): (1) the child sources are 0–2y cohorts while `child`/`5-17` read
5–17 under the severity model's band convention; the fraction
demonstrably **rises** through childhood (never-symptomatic 71.1% in
year 1 → 61.2% in year 2), so 0.51 likely understates presentation in
the band's older half — it is the measured child end, not an
interpolation; (2) **no admissible design measures
p(symptomatic|infection) in ≥65** — the register's `never_symptomatic`
row states this outright — so `senior`, `middle_aged`, `adult` and
`young_adult` stay at the ×1.0 reference rather than reading an invented
elderly split, and on the senior-skewed hull the pooled draw therefore
sits at the adult level; (3) LTCF outbreak series (Parrón 2021 Catalonia,
Cardemil 2021 NORS, Inns 2019) report resident *attack rates*, not
per-infection symptomatic shares — a different denominator, not usable.

### `influenza_a` — `symptomatic_fraction_by_age_band`: Hoy 2022, full label set

One commensurable design carries the whole ladder: **Hoy 2022, "The
Spectrum of Influenza in Children"** (Clin Infect Dis, DOI
10.1093/cid/ciac734) — Managua household cohorts 2011–2020, PCR/HAI-
confirmed influenza infections, asymptomatic fraction by age (Results /
Fig. 2): children 0–14y 6.6% asymptomatic of 1,272 infections, stratified
1.7% (0–1y) / 3.5% (2–4y) / 9.1% (5–14y); **≥15y 26.6% asymptomatic of
662 infections, with no further trend by age** (P = .596; no deviation
between ≥15 age groups, P = .816).

Declared as symptomatic = 1 − asymptomatic under the severity model's
band→midpoint convention (`child`/`young_adult`/`adult`/`middle_aged`/
`senior` = 5–17/18–34/35–49/50–64/65+):

- `0-4` = **0.965** (the 2–4y stratum at the label's 2y midpoint)
- `5-17`, `child` = **0.909** (the 5–14y stratum)
- every ≥15 label (`18-24`, `18-34`, `young_adult`, `25-34`, `35-44`,
  `35-49`, `adult`, `45-54`, `50-64`, `middle_aged`, `55+`, `65-74`,
  `senior`, `75+`) = **0.734** — the pooled ≥15 value, because the source
  itself reports no resolution inside ≥15. This is a sourced same-value
  declaration across bands, not an invented split.

Grade B — a community household cohort is an analogous setting, but it
is the direct measurement of the same screened-denominator quantity
`symptomatic_fraction` reads from Carrat. The adult map value (0.734)
deliberately differs from the pooled Carrat 0.669, which stays the
fallback for an unnamed band — different studies of the same quantity,
recorded not averaged. Corroborating direction, not used numerically:
PHIRST (Cohen 2021, Lancet Glob Health 10.1016/s2214-109x(21)00141-8,
56% of 478 infections symptomatic, higher in children <5, reduced with
increasing age) and Flu Watch (Hayward 2014, Lancet Respir Med,
underpowered for an age effect but consistent).

## Boundaries

- **Boarding is untouched.** `never_symptomatic_fraction`/`age_draw` are
  importation splits — the share of *arriving* infections that never
  present. This design conditions the *on-board* presentation draw. The
  two meet only downstream of `draw_symptom_onset`; a join would be a
  separate argument and is explicitly a non-goal.
- **Severity ladders are untouched.** `base_probabilities_by_age_band`
  already conditions severity per band; presentation and severity are
  separate draws.
- **Covid is untouched** — its maps keep applying under the default mode;
  its HOST-AGE-01 detector pins stand.
- **No anchor fitting.** No declared value was chosen against VSP, Park,
  Ward 2010, Millman 2015, or any scored anchor; the noro factor is a
  ratio of pre-existing register regimes, not a new fitted constant.

## Open edges recorded for the ledger

- The noro child factor reads a 0–2y measurement for a 5–17 band — the
  honest coarse partition, and the direction (rising sf through
  childhood) says the true 5–17 factor is *higher* than 0.51; a finer
  partition needs a 5–17 or ≥65 infection-denominator design that does
  not exist today.
- On a senior-skewed hull the noro pooled draw is essentially unchanged
  (all named non-child bands sit at ×1.0) — the structure matters where
  children board, not in the pooled passenger mean; the direction for
  flu runs the other way (children present *more*, so a child-light hull
  reads near the adult 0.734 rather than Carrat's 0.669).
- `severity_model.base_probabilities`' asymptomatic entry is renormalised
  away for presenters on both arms — same consistency debt covid's
  ladder already carries, recorded not silently aligned.
