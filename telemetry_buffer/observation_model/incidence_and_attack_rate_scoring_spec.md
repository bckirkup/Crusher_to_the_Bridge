# Joint scoring: overall AGE incidence and posted attack rate, by hull class and era

Status: Partially implemented. The observed-side A4 targets are derived in
`telemetry_buffer/observation_model/vsp_class_era_scoring.py` and scored by
`telemetry_buffer/observation_model/score_anchors.py`; A8/A9 model-side
aggregation is implemented there using
`telemetry_buffer/observation_model/midrs_incidence_targets.py` and the source
record `telemetry_buffer/observation_model/midrs_observed_targets.md`.
The A10 trajectory channels remain Proposed.
Owner anchors: A4 (revised), A8 (new), A9 (new), A10 (new)
Last updated: 2026-08-30

## Why this exists

Every VSP statistic the repository currently scores is conditional on VSP
posting a voyage: A4 compares `reported_case_attack_rate_passenger` against a
hull-class IQR of posted outbreaks, and A7 compares a posted-outbreak
difference-in-differences across the COVID break. An intervention that stops
introductions from taking off never appears in either. Those voyages are simply
not posted, and the effect lands entirely in the posting *rate* -- the one
quantity the outbreak series cannot supply, because a posted-outbreak table has
no voyage denominator.

That is the gap this spec closes. It adds two unconditional channels and puts
all three on the same class x era grid, so that a configuration cannot buy
agreement on severity while being silently wrong about frequency.

| channel | anchor | conditional on posting? | what it identifies |
|---|---|---|---|
| overall reported AGE incidence | A8 | no | endemic transmission plus small clusters |
| posting probability per voyage | A9 | no (it *is* the posting rate) | take-off frequency |
| attack rate among posted outbreaks | A4 | yes | severity given take-off |

A8 and A9 are the channels the take-off-prevention mechanisms act on. A4 is the
channel the attack-rate-capping mechanisms act on. Scoring only A4, as the
repository does today, cannot distinguish a model that gets both right from one
that produces far too many outbreaks of the right size, or too few.

## The denominator, found

The missing voyage denominator is published. Jenkins KA, Vaughan GH Jr,
Rodriguez LO, Freeland A. *Acute Gastroenteritis on Cruise Ships -- Maritime
Illness Database and Reporting System, United States, 2006-2019.* MMWR Surveill
Summ 2021;70(6):1-19. https://www.cdc.gov/mmwr/volumes/70/ss/ss7006a1.htm

MIDRS is the mandatory AGE reporting system behind the posting rule: every ship
in VSP jurisdiction files a 24-hour report of passenger and crew AGE case counts
before its first US port call, a 4-hour update if counts rise, and a special
report at 2% or 3%. VSP posts an outbreak at 3%. So the posted outbreaks in
`vsp_outbreak_series.csv` are a subset of exactly the voyages MIDRS counts, and
the same exclusions apply on both sides -- voyages under 3 days or over 21 days
and vessels carrying under 100 passengers are excluded from the MMWR analysis,
which is the truncation the posting rule already imposes.

That gives us, for 2006-2019:

- **37,258 unduplicated voyages** from 252 ships (MMWR Table 1);
- those voyages **broken out by ship size**, which is the denominator per class;
- **AGE incidence rates per 100,000 travel days** for passengers and crew by
  ship size and by voyage length, with 95% CIs (MMWR Table 2).

Travel days are `passengers (or crew) onboard x voyage days`, so a rate converts
to a per-voyage cumulative reported incidence by multiplying by voyage days.

## Hull class to VSP ship-size band

MMWR strata are gross registered tonnage, our hulls are passenger complements,
so the mapping needs a space ratio. Each hull is anchored to a real ship whose
tonnage and capacity are both published, rather than to an assumed ratio.

| hull | pax | representative ship | tonnage | GT/pax | VSP band |
|---|---|---|---|---|---|
| `expedition_cruise_450` | 450 | Silver Wind | 16,800 GT / 294 pax | 57.1 | extra small/small/medium (<=30,000) |
| `classic_cruise_1900` | 1,900 | Coral Princess | 91,627 GT / 1,970 pax | 46.5 | extra large (60,001-120,000) |
| `spirit_cruise_3000` | 3,000 | Voyager class | 138,000 GT / 3,114 pax | 44.3 | mega (120,001-140,000) |
| `mega_cruise_5000` | 5,000 | Oasis class | 225,282 GT / 5,400 pax | 41.7 | super mega (>=140,001) |

Space ratio runs 42-57 GT/pax across the four, tightening with size, which is
the expected direction: expedition tonnage buys space per passenger, mega
tonnage buys passengers. Each mapping is unambiguous at the ratio of its own
anchor ship -- no hull sits within 15% of a band edge -- except that at the
low end the expedition hull would need a ratio below 67 GT/pax to stay inside
the <=30,000 band, which Silver Wind's 57.1 satisfies but not by much for a
higher-space-ratio expedition vessel. Record that as the one soft edge.

No hull maps to the **large** band (30,001-60,000 GT, roughly 650-1,400
passengers). Its observed rates are recorded below but nothing is scored
against them; a fifth hull would be needed.

## A8 -- overall reported AGE incidence, unconditional (implemented)

The model-side aggregation is implemented in
`telemetry_buffer/observation_model/score_anchors.py`. It uses all runs in a
cell, including non-take-off runs, and weights each reported case by its
passenger or crew complement over that run's travel-days. The observed targets
and fixed hull-to-GRT mapping are transcribed in
`telemetry_buffer/observation_model/midrs_incidence_targets.py` from
`telemetry_buffer/observation_model/midrs_observed_targets.md`.

Observed, MMWR Table 2, per 100,000 travel days (95% CI):

| VSP band | hull | passengers | crew |
|---|---|---|---|
| <=30,000 | `expedition_cruise_450` | 10.9 (9.94-12.1) | 6.4 (5.52-7.45) |
| 30,001-60,000 | *(unmapped)* | 23.7 (23.2-24.2) | 16.7 (16.1-17.4) |
| 60,001-120,000 | `classic_cruise_1900` | 23.0 (22.9-23.1) | 19.8 (19.6-20.0) |
| 120,001-140,000 | `spirit_cruise_3000` | 26.7 (26.1-27.4) | 14.7 (14.0-15.4) |
| >=140,001 | `mega_cruise_5000` | 29.2 (27.8-30.5) | 16.0 (14.8-17.4) |

Voyage-length rates from the same table, passengers then crew:

| voyage length | voyages | passengers | crew |
|---|---|---|---|
| 3-5 d | 13,772 | 13.3 (13.1-13.5) | 17.5 (17.1-17.8) |
| 6-7 d | 6,031 | 17.8 (17.5-18.1) | 22.1 (21.6-22.6) |
| 8-10 d | 12,239 | 23.2 (23.0-23.4) | 19.0 (18.7-19.3) |
| 11-14 d | 3,111 | 35.0 (34.6-35.5) | 17.4 (17.0-17.9) |
| 15-21 d | 2,105 | 40.0 (39.5-40.5) | 20.9 (20.4-21.5) |

**These are marginal rates, not adjusted ones, and the two covariates are
confounded.** Passenger rates rise with size and rise with length, and larger
ships in this period disproportionately sailed the shorter Caribbean
itineraries. Our hulls all run 168 one-hour epochs, that is a 7-day voyage, so
the length-matched comparison is the 6-7 day row (17.8 passengers, 22.1 crew),
while the size column pools all lengths. Consequently:

- score the model against the **size band** value only after confirming the
  simulated voyage length distribution matches the MIDRS mix within that band;
- otherwise score against the size band and report the 6-7 day value alongside,
  and treat a miss that flips sign between the two as unresolved rather than as
  a model failure.

The model observable is the reported-case channel over **all** simulated
voyages, take-off or not:

```text
A8_passenger = 1e5 * sum(reported_cases_passenger) /
               sum(passengers_onboard * voyage_days)
```

Non-take-off voyages must be in the denominator and the numerator. Dropping
them is the exact error A4 already makes by construction.

### The pathogen-mix caveat, which makes A8 one-sided

MIDRS AGE is all-cause and syndromic: any three loose stools in 24 hours, or
vomiting plus one other symptom, reported to the medical centre. The model
simulates norovirus alone. Norovirus is roughly 80% of *posted outbreaks*, but
its share of endemic shipboard AGE is not published, and it is certainly lower,
since background AGE absorbs other agents, foodborne illness, motion sickness
misclassification and unrelated gastrointestinal complaints.

So A8 is scored as **an upper bound plus a reported ratio**, never as an
equality:

- **fail** if modelled norovirus reported incidence exceeds the observed
  all-cause rate's upper CI -- the model cannot produce more norovirus AGE than
  all AGE observed;
- otherwise **report** the implied norovirus share of AGE and judge whether it
  is plausible, without treating any particular share as a target.

No parameter may be chosen to hit a share. If a share is ever needed as a
number, it has to come from a shipboard aetiology study, and none was found.

## A9 -- posting probability per voyage (implemented)

The model-side VSP posting rule and eligibility filter are implemented in
`telemetry_buffer/observation_model/score_anchors.py`. The denominator is every
eligible simulated voyage, while ineligible runs are reported separately. The
fleet target remains an interval spanning the MMWR-investigated and project
posted outbreak definitions; per-hull numerators are unpublished.

```text
A9_observed(band, era) = postings(band, era) / voyages(band, era)
A9_model(hull, era)    = simulated voyages passing the VSP posting rule /
                         all simulated voyages
```

The posting rule is VSP's own: at least 3% of passengers or of crew reporting
AGE to the medical centre, on a voyage of 3-21 days carrying 100 or more
passengers.

Numerator, pre arm: postings in `vsp_outbreak_series.csv` with `voyage_end` in
2006-2019. **All** postings count, including the rows whose case counts CDC
never published (`counts_published = data_not_available`) -- a posting is a
posting whether or not its numerator survived to the web page. This is why band
assignment for A9 cannot use `pax_total`, which those rows lack.

Denominator, pre arm: MMWR Table 1 voyage counts by band -- 1,500 / 4,510 /
30,039 / 917 / 292 for the five bands in order.

Band assignment therefore comes from **ship tonnage, by ship name**, not from
passengers aboard. Two reasons: the count-less rows have no passenger figure at
all, and `pax_total` is passengers *aboard*, which exceeds double-occupancy
capacity (Allure of the Seas appears at 6,364 aboard against 5,400 lower
berths), so a ratio conversion would push ships up a band. A sourced
ship-to-tonnage reference table is a prerequisite for A9; 138 distinct ships
carry counts in the series and 172 appear in total.

### Post arm: the denominator is reconstructed, and says so

No MIDRS analysis has been published past 2019. Searched CDC's VSP data pages,
MMWR, and the peer-reviewed literature; the 2021 surveillance summary remains
the only one. So for 2022 onward the voyage denominator has to be reconstructed
from industry volume, and it is Grade C:

- CLIA global ocean-going passengers: 29.7 M (2019), 20.4 M (2022), 31.7 M
  (2023), 34.6 M (2024); worldwide average cruise length 7.1 days (2024).
- These are global, and VSP jurisdiction is voyages touching a US port; North
  America was 20.5 M of the 34.6 M in 2024.

A reconstruction on that basis carries at least a jurisdiction-share
uncertainty, a per-class capacity-mix change (the fleet grew at the top end
across the break), and a reporting-behaviour uncertainty. It is fit for
detecting a large change in posting probability across the break and unfit for
a per-class point estimate. State the interval; do not quote a point.

## A4 -- attack rate among posted outbreaks, revised per class and era

### The current target values have no provenance and are not reproducible

`score_anchors.py` carries:

```python
VSP_TARGETS = {
    "expedition_cruise_450": {"median": 0.0856, "q1": 0.0451, "q3": 0.1360},
    "classic_cruise_1900":   {"median": 0.0559, "q1": 0.0446, "q3": 0.0776},
    "spirit_cruise_3000":    {"median": 0.0564, "q1": 0.0444, "q3": 0.0790},
    "mega_cruise_5000":      {"median": 0.0561, "q1": 0.0340, "q3": 0.0745},
}
```

There is no derivation script and no dataset in the repository from which these
reproduce. The ledger did record sample sizes alongside them -- n = 17, 172, 52,
9 -- and those are the strongest evidence that the source was not this series:
every revision of `vsp_outbreak_series.csv` in the repository's history (the
original extraction, the CDC-archive rebase, and the header-bound re-extraction)
yields 328, 314 and 333 usable postings and a small-class count of 53, 52 and 54,
never 17, and never a total of 250. Recomputing the same statistic from
`vsp_outbreak_series.csv` under capacity bands, and under every alternative
band edge tried (500/700/900/1,000/1,200 for the small class; 1,000-2,500,
1,200-2,600, 2,387-3,873, 2,500-4,000, and 3,000+/3,873+/4,000+ for the rest),
never reproduces a triple. The expedition class is the worst: target median
0.0856 against 0.0507 measured pre-2020 and 0.0724 post-2020, with no binning
landing between 0.0558 and 0.1077. The classic class is close but not equal
(0.0446/0.0559/0.0776 target against 0.0417/0.0539/0.0726 measured over
1,000-2,500 passengers).

The values therefore predate the series and their source is unrecorded.
**A4's target is withdrawn and replaced by values recomputed from the repository's own dataset, per class and
per era.** The replacement must ship with the code that computes it, so that it
can never again be a number without a derivation.

### Measured, from `vsp_outbreak_series.csv`

Reported passenger attack rate among posted outbreaks, by capacity band. 333 of
428 postings carry a passenger denominator; the 87 `legacy_pre2004` rows carry
none at all, so that era cannot be scored.

| hull | era | n | q1 | median | q3 | max |
|---|---|---|---|---|---|---|
| `expedition_cruise_450` | pre | 34 | 0.0370 | 0.0507 | 0.1018 | 0.4265 |
| `expedition_cruise_450` | post | 18 | 0.0331 | 0.0724 | 0.1351 | 0.2903 |
| `classic_cruise_1900` | pre | 174 | 0.0418 | 0.0546 | 0.0770 | 0.2519 |
| `classic_cruise_1900` | post | 32 | 0.0411 | 0.0506 | 0.0689 | 0.1248 |
| `spirit_cruise_3000` | pre | 50 | 0.0431 | 0.0542 | 0.0667 | 0.2064 |
| `spirit_cruise_3000` | post | 13 | 0.0353 | 0.0473 | 0.0635 | 0.1349 |
| `mega_cruise_5000` | pre | 4 | 0.0298 | 0.0535 | 0.0782 | 0.0893 |
| `mega_cruise_5000` | post | 3 | -- | -- | -- | -- |

**The mega hull has no usable A4 anchor in either era** -- four postings before
the break and three after. That is the hull the campaign manifests centre on.
Its A8 anchor rests on 292 voyages, which is thin but real; its A4 anchor is
not an anchor. Say so wherever a mega-hull A4 result is reported.

Note the direction disagreement worth keeping in view: A8 says passenger
incidence *rises* with ship size (10.9 to 29.2), while A4 says the posted
attack rate is flat to *falling* with size (expedition medians are the highest
of the four). Both can be true at once -- bigger ships have more introductions
and more contacts, so more voyages cross 3%, while a small ship that does cross
3% crosses it with a handful of cases and can run much further. A model that
reproduces one and not the other is telling us which of the two mechanisms it
has wrong, so the two must be scored together and never averaged.

## A10 -- duration trajectories

Norovirus gives us no within-voyage time series anywhere. There is no shipboard
norovirus cohort with per-day case counts, so there is no trajectory to fit the
way a COVID cohort study is fitted. What MMWR 70(6) does contain is two
*duration* trajectories -- recovered across voyages rather than within one --
and they are independent of the incidence levels A8 already scores.

### A10a -- incidence against voyage length

The passenger length rates tabulated in the A8 section (13.3, 17.8, 23.2, 35.0,
40.0 per 100,000 travel days over 3-5, 6-7, 8-10, 11-14 and 15-21 days) are a
*per-day* rate, and it roughly triples across the range. A per-day rate that
rises with duration means cumulative incidence grows superlinearly in voyage
length. That constrains epidemic growth rate rather than level, and it is the
closest thing to a trajectory this data offers.

Model side: run the same hull at 3-5, 6-7, 8-10, 11-14 and 15-21 day voyage
lengths and compare the shape of reported cases per travel day against those
five points. Score the **gradient**, not the levels -- the levels are A8's job,
and the all-cause/norovirus mix caveat recorded there applies to them.

### A10b -- the crew trajectory as the discriminator

Crew rates over the same five bands are flat: 17.5, 22.1, 19.0, 17.4, 20.9.
Two populations on the same hulls, one duration-dependent and one not, is a much
harder constraint than either level alone, and it is the same passenger-versus-
crew differencing A7 already uses.

Plausible mechanisms, stated without being asserted: crew turnover and crew
pre-existing immunity from continuous exposure would both flatten the crew
curve. Neither is measured here. A10b is therefore scored as "passenger gradient
positive, crew gradient flat" and **not** as a ratio.

### A10c -- outbreak reports against voyage length

MMWR Table 3, 2006-2019. Of 156 passenger AGE *outbreak* reports the
distribution over the same length bands is 7 (4%), 2 (1%), 30 (19%), 57 (37%),
60 (38%); of 16 crew outbreak reports it is 6 (38%), 4 (25%), 3 (19%), 2 (13%),
1 (6%). The passenger outbreak share rises steeply with voyage length while the
crew share falls steeply -- a second, independent duration trajectory, on the
outbreak channel rather than the incidence channel, with the same sign contrast
between the two populations.

**These are shares of outbreak reports, not rates.** Table 3 carries no voyage
denominator per length band, so converting a share to a per-voyage probability
requires the Table 1 length denominators (13,772 / 6,031 / 12,239 / 3,111 /
2,105 voyages). The derived quantity, `passenger outbreak reports / voyages`,
per 1,000 voyages:

| voyage length | outbreak reports (Table 3) | voyages (Table 1) | per 1,000 voyages |
|---|---:|---:|---:|
| 3-5 d | 7 | 13,772 | 0.51 |
| 6-7 d | 2 | 6,031 | 0.33 |
| 8-10 d | 30 | 12,239 | 2.45 |
| 11-14 d | 57 | 3,111 | 18.32 |
| 15-21 d | 60 | 2,105 | 28.50 |

So the per-voyage outbreak probability rises from roughly 0.5 per 1,000 voyages
at 3-5 days to roughly 29 per 1,000 at 15-21 days, a factor of about 56 across
the range. The 6-7 day band sits *below* the 3-5 day band, so the rise is not
monotone at the short end; the steep part is 8-10 days upward. Both source
tables are named above so the arithmetic is reproducible.

### The confound, which is a blocker and not a footnote

Length and ship size are confounded in Table 2. Those are marginal rates, not
adjusted ones, and larger ships in this period disproportionately sailed the
shorter Caribbean itineraries, so a length gradient partly carries a size
gradient with the opposite composition. MMWR publishes no size-by-length
cross-tabulation, so the size mix per length band is unknown, and the same
confound applies to the Table 3 shares.

A10a and A10c are therefore scored as **sign and rough magnitude of the
gradient only**. A quantitative growth-rate claim is blocked pending either a
size-by-length cross-tabulation or a per-voyage reconstruction. Do not present
this gradient as a clean growth-rate measurement.

## Era grid and what is missing

| channel | pre (2006-2019) | shutdown (2020-2021) | post (2022-) |
|---|---|---|---|
| A8 incidence | measured, Grade A | not applicable | **no published analysis** |
| A9 posting rate | measured, Grade A | not applicable | reconstructed, Grade C |
| A4 posted attack rate | measured, Grade B | 5 postings, not scored | measured, Grade B |

The shutdown years are never pooled into either arm: cruising was suspended
under the No Sail Order and then the Framework for Conditional Sailing, so
those years carry almost no voyages and would dilute any rate computed across
them.

The post-era A8 gap is the one that matters, and it cannot be papered over: the
post-2020 health-practice configuration changes exactly the channel we have no
post-2020 observation for. A pre-arm A8 match plus a post-arm A4 match is the
most that can honestly be claimed until a post-2020 MIDRS analysis exists.

## Anti-fitting rules for this scoring framework

1. The pre-2020 arm may be used to set what the repository already treats as
   fittable. The post-2020 arm may not: its health-practice configuration comes
   from `post_covid_configuration_sources.md` and nothing in it is chosen from
   an A4, A8 or A9 residual.
2. No physical constant is adjusted to move A8 or A9. They are scored, so by
   the rule in `AGENTS.md` they are off limits as fitting targets.
3. The norovirus share of all-cause AGE is not a free parameter. A8 is a bound
   plus a reported ratio precisely so that this share never has to be assumed.
4. A9's post-arm denominator is an interval. A configuration that passes only
   at one end of it has not passed.
5. Class-to-band mappings are fixed by the tonnage table above before any
   scoring run, never re-chosen afterwards.
6. Every target in this document ships with the code that derives it from a
   dataset in the repository, or with a citation to a specific published table.
   The withdrawn `VSP_TARGETS` triples are what happens otherwise.

## Implementation surface

- `vsp_class_era_scoring.py` -- recomputes the A4 targets per class and era from
  the series, and reports posting counts. Exists.
- ship-to-tonnage reference table -- prerequisite for A9 band assignment. Does
  not exist.
- A8/A9 model-side aggregation -- needs per-voyage reported case counts,
  passengers and crew onboard, and voyage days across all runs in a cell,
  including non-take-off runs. `score_anchors.py` currently discards
  non-take-off cells.
- VSP posting flag per run -- already an open item; A9 depends on it.

## Sources

- Jenkins KA, Vaughan GH Jr, Rodriguez LO, Freeland A. Acute Gastroenteritis on
  Cruise Ships -- Maritime Illness Database and Reporting System, United States,
  2006-2019. MMWR Surveill Summ 2021;70(6):1-19. Tables 1, 2 and 3.
  Retrieved 2026-08-30.
- CDC Vessel Sanitation Program, Outbreaks on Cruise Ships in VSP's
  Jurisdiction (posting rule). Retrieved 2026-08-30.
- CDC Vessel Sanitation Program, AGE on Cruise Ships 2006-2019 summary page.
  Retrieved 2026-08-30.
- CLIA Global Market Report 2024 and 2023 Year End (passenger volumes, average
  cruise length). Retrieved 2026-08-30.
- Tonnage and capacity for Silver Wind, Coral Princess, Voyager class and
  Oasis class: builder and operator specifications as tabulated on the
  respective ship articles. Retrieved 2026-08-30.
