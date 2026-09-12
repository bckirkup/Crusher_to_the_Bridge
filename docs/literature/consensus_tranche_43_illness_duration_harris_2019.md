# Tranche 43 — illness duration: the Harris 2019 survival table

**Read first:** this tranche digitizes one figure and states one sampling
convention. It supplies the dispersed illness-duration arm (`illness_duration`
on `norwalk_gi`); it does not change the shipped default, which remains the
`recovery_day` = 3 point value. Nothing here is fitted to a VSP, MIDRS or
A-anchor target.

**Register rows fed.** Feeds the `illness_duration` row of
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
and amends the `recovery_day` row of §3.1 there: the point value's Atmar basis
is a challenge illness, a different population and exposure from the community
cohort sourced here.

**Retrieval.** Figure digitization, not a Consensus query: the quantity is a
survival *curve*, and the paper reports it as a figure. Source image:
`https://media.springernature.com/full/springer-static/image/art%3A10.1186%2Fs12879-019-3706-z/MediaObjects/12879_2019_3706_Fig4_HTML.png`.

**Status:** Implemented as a default-off selectable arm; the digitization is
cross-checked against the paper's own summary statistics (§3) and the arm is
unmeasured until a campaign runs it.

---

## 1. What the figure measures — and what it does not

Harris, Iturriza-Gomara, Allen, Kelly & O'Brien 2019, "Norovirus strain
types found within the second infectious intestinal diseases (IID2) study:
an analysis of norovirus circulating in the community", *BMC Infect Dis*
19:87, DOI 10.1186/s12879-019-3706-z, published 25 January 2019 (Europe PMC
PMC6346499, PMID 30683063). IID2 is a UK national community cohort study
conducted April 2008–August 2009, with a GP arm and a self-reporting postal
arm; the paper's denominator statement is 477 norovirus-positive samples —
that is the study's positive-sample count, **not** a stated denominator for
Fig 4, whose panel denominators are not reported. Fig 4 panel C, dotted
curve: **percent still ill by number of days following illness onset, adults
and children aged ≥ 5 years** — the ≥ 5 band includes school-age children,
not adults only — for the diarrhoea symptom. The population is a community
cohort — the model's population.

The curve measures **self-reported diarrhoea duration** in that cohort. It is
not shedding duration, not RT-PCR detectability, not infectiousness, and not
reportability; none of those may be inferred from it. It is also **not** the
Atmar challenge illness the `recovery_day` = 3 default was carried from:
Atmar 2008's 1–2 days of symptomatic illness comes from 16 experimentally
challenged adults, a different population and a different exposure.

## 2. The digitized table

S(d) = P(illness still present at d days after onset), the dotted diarrhoea
curve of panel C:

| d (days after onset) | S(d) |
|---:|---:|
| 0 | 1.00 |
| 1 | 0.63 |
| 2 | 0.355 |
| 3 | 0.22 |
| 4 | 0.13 |
| 5 | 0.079 |
| 6 | 0.057 |
| 7 | 0.030 |
| 8 | 0.023 |
| 9 | 0.019 |
| 13 | 0.00 |

Days 10–12 are not digitizable — the legend overlies the curve there — and
both curves are at zero by day 13, so days 10–12 are interpolated linearly
between d = 9 and d = 13.

**Calibration.** Source image 1945×1373 grayscale. Panel C axis rows: 334 px
(0%) and 307.5 px (10%) → 2.65 px per percentage point. X-axis label centroids
give day 0 at col 97.5 and 141.2 px per day. The curve is read as the topmost
dark pixel per day column, with the 10% reference line and the axis masked.
Read error ≈ ±1 percentage point.

**Grade B** — direct measurement of illness duration in a community cohort of
the right age band, not in a cruise setting. **Origin F4·dig** — the numbers
are read from the figure, not from text.

## 3. Cross-check against the paper's own summaries

The digitization is validated by reproducing the paper's own reported
statistics — from the abstract, verbatim: *"85% of people recovered within
two days for vomiting; diarrhoea symptoms were reported to day 4 for 83% of
the cases, and 10% of people reported symptoms of diarrhoea lasting between
five and six days"*, and *"both diarrhoea and vomiting symptoms lasted
longer in children aged < 5 years compared to adults"*. Under the discrete
sampling convention `P(T = d) = S(d-1) − S(d)`:

- **Median T = 2 days** — the table gives exactly 2; the abstract reports
  no diarrhoea median, but 85% of vomiting cases resolved within two days
  and diarrhoea tracks vomiting on the figure's paired panels, so a median
  of 2 is consistent with the reported resolution speed.
- **E[T] = 2.57 days** — the ≥ 5 curve is shorter than the all-ages one
  (the abstract: symptoms last longer in < 5 than in adults), so the ≥ 5
  table's 2.57 landing below the all-ages figure is the correct direction.
- **P(T ≤ 4) = 0.87** — the table gives exactly 0.87 against the
  abstract's 83% resolved by day 4 for all ages; the ≥ 5 band being
  shorter means above 0.83 is the correct direction.

## 4. Sampling convention

Integer days, discrete. Draw u ~ Uniform(0, 1) and invert: T is the smallest
integer d in 1..13 with S(d) ≤ u, so `P(T = d) = S(d-1) − S(d)`. The
convention is deliberate and must not become a continuous draw: the
underlying data are integer-day self-reports, and this convention is what
makes the §3 cross-check exact.

## 5. What was implemented

`engines/illness_duration.py` adds `IllnessDurationModel`: `draw: point`
(default — stamps nothing, consumes no RNG, bit-identical to the
pre-distribution model) or `draw: empirical_survival`, which draws once per
infection and stamps `inf["recovery_day"]`, which `clearance_days`
(`engines/natural_history.py`) already reads ahead of the profile. The stamp
lands before the onset-time pharmaceutical override in the same
`advance_infections` call, so treatment shortens the host's drawn duration
rather than the profile constant. The block is carried on `norwalk_gi` only.

## 6. What it does not do

- Does not change the shipped default: `recovery_day` = 3 is the `point` arm.
- Does not create symptomatic-at-boarding hosts or a VSP pre-boarding screen
  — those depend on this arm and are a later change.
- Does not touch the `resolving` symptom-phase `dpi_max` fallback in
  `engines/transmission_core.py`, which still reads the profile `recovery_day`
  (3) even under the dispersed arm — recorded as an open ledger item.
