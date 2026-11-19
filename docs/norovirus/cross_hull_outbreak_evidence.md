# Which explanations are compatible with the cross-hull outbreak record?

**Status:** Retrospective evidence readout for Edison. Historical input snapshot `7cd051da472fd88821176ed5212a12cc51ecfcec`. Archived model readouts retain their own measurement revisions below.

**The evidence favors more than one route across outbreaks.** A shared upstream food source is well supported for one investigated multi-ship cluster. A separate investigation supports introduction by a crew member followed by person-to-person spread, with most reported cases ultimately in passengers. Either history can produce a passenger-heavy final count. The cross-hull summaries add constraints on these explanations but do not identify the source of the mega outbreaks or estimate the fraction attributable to each route.

## Historical attack rates and role splits

The AR and role comparisons cover public postings in 2006–2019, including sailings outside the MIDRS voyage eligibility criteria. Of 208 public postings with case counts, 162 name norovirus alone. The primary comparison below uses those 162. Each voyage contributes one attack rate (AR) per role, calculated as reported cases divided by people onboard in that role. Brackets show the middle half of the observed voyages. Percentages measure reported illness. Population infection rates would require independent ascertainment.

| Passenger-capacity group | Postings (distinct ship names) | Passenger AR, median [IQR], % | Crew AR, median [IQR], % | Final AR ≥3% in passenger only / crew only / both / neither |
|---|---:|---:|---:|---:|
| Expedition | 6 (5) | 6.94 [4.95, 13.68] | 2.73 [0.67, 7.51] | 4 / 0 / 2 / 0 |
| Classic | 46 (21) | 5.84 [4.50, 8.85] | 1.42 [0.90, 2.04] | 41 / 0 / 5 / 0 |
| Spirit | 96 (53) | 5.70 [4.67, 7.79] | 1.15 [0.76, 1.68] | 89 / 0 / 5 / 2 |
| Mega | 14 (12) | 6.00 [3.65, 7.48] | 1.13 [0.80, 1.60] | 10 / 1 / 2 / 1 |

On these postings, the middle half of passenger AR overlaps across all four groups. The 3% threshold in either role selects the sample. Several ships recur, expedition has six observations, and an IQR describes dispersion rather than precision of a population median. Of 162 postings, 144 ended above or at threshold in passengers alone. Final counts cannot tell which group fell ill first. CDC can publish events of public health significance below threshold.

In the sensitivity analysis including **all 208 postings**, passenger medians are 6.19%, 5.73%, 5.57%, and 5.61% in hull order, with crew medians of 2.76%, 1.38%, 1.15%, and 1.01%. This preserves the broad role and hull pattern. It does not convert the all-cause surveillance denominators into norovirus-specific denominators. The [aggregate CSV](cross_hull_outbreak_evidence.csv) includes both cohorts.

## Posting frequency and timing

- **Posting frequency.** Jenkins et al. counted 156 investigated passenger outbreaks among 37,258 unduplicated voyage reports (4.19 per 1,000). To approximate the same eligible population for public AGE postings, subtract the embarkation date from the disembarkation date in the committed series and retain voyages of 3–21 elapsed days with at least 100 passengers and positive crew complement. Of the 208 postings, 14 fail the duration screen and four others have fewer than 100 passengers. The resulting 190/37,258 is **5.10 postings per 1,000 reports**. Counting both voyage endpoints as days gives 187 postings (5.02 per 1,000). These are cross-source estimates. Individual voyages have not been matched and two AIDAdiva dates disagree between indexes. The unrestricted 208/37,258 mixes eligibility criteria. [Jenkins et al., Methods and Tables 1–3](https://www.cdc.gov/mmwr/volumes/70/ss/ss7006a1.htm) · [Extraction log](../../telemetry_buffer/observation_model/vsp_outbreak_series_extraction_log.md)
- **Class posting frequency.** Applying the project's tonnage-assignment method to the 190 screened postings gives 5–14 candidate postings / 1,500 reports in the expedition band (3.3–9.3 per 1,000), 100–151 / 34,549 in the combined classic/spirit bands (2.9–4.4), and 9–48 / 292 in the super-mega band (30.8–164.4). The lower count includes voyages assigned wholly to the band or group of bands. The upper count includes any voyage that could fall there. The wide super-mega range reflects uncertainty in inferring tonnage from passenger complement. It does not quantify sampling uncertainty or correct incomplete reporting. The model mega maps to Jenkins's **super mega**. The AR table uses a different classification based on nearest passenger complement. Dividing its posting counts by the tonnage denominators would mix classifications. [Class reconstruction method](vsp_ship_class_denominators.md)
- **Voyage duration.** Passenger AGE incidence rises from 13.3 to 40.0 reported cases per 100,000 passenger travel-days between 3–5 and 15–21 day voyages. Crew incidence is 17.5 and 20.9 at those endpoints and varies nonmonotonically between them. Investigated passenger outbreaks per 1,000 reports in the five successive duration bands are 0.51, 0.33, 2.45, 18.32, and 28.50. Ongoing transmission or repeated exposures can contribute to this pattern. A single early exposure followed by no secondary cases would give a declining per-day rate once all resulting cases had appeared, **if** exposure probability, ascertainment, and voyage mix were comparable. Duration and hull size are confounded in the published marginals. [Jenkins et al., Tables 1–3](https://www.cdc.gov/mmwr/volumes/70/ss/ss7006a1.htm)
- **Within-voyage timing.** The public series contains voyage dates and final counts. It lacks symptom-onset dates, first-report dates, and threshold-crossing dates. The duration gradient therefore supplies no cross-hull estimate of day of onset or day of posting. Individual investigations can provide that chronology. In one CDC investigation, crew illness preceded passenger illness across successive voyages even though 356 of 410 final cases were passengers. Those figures count cases across voyages, not role-specific ARs. [Crisp et al., Investigation and Outcomes and figure](https://www.cdc.gov/mmwr/volumes/72/wr/mm7230a5.htm)

## What the archived model contributes

These are the same predefined station-lot stratum across the three solver screens. Each solver used the same 16 selected seeds within a hull. Entries give discrete / continuous in that order. Each AR and posting epoch is a median among runs that posted. The two solvers can post on different subsets. The screen readouts and their companion seed manifests identify the measurements.

| Hull (measurement revision) | Posted out of 16 per solver | Passenger AR % | Crew AR % | Posting epoch (1 h) |
|---|---:|---:|---:|---:|
| Expedition (`6742f1a4`) | 16 / 16 | 8.54 / 7.75 | 1.49 / 1.12 | 70 / 83.5 |
| Classic (`455f9ff7`) | 9 / 10 | 5.68 / 6.05 | 1.22 / 1.22 | 64 / 63 |
| Spirit (`455f9ff7`) | 7 / 8 | 5.71 / 5.31 | 1.44 / 1.38 | 59 / 58 |
| Mega (`c6c3c25f`) | 1 / 1 | 4.55 / 4.45 | 2.38 / 1.48 | 56 / 75 |

Passenger AR in the selected posted runs is of the same order as in surveillance, including the single shared mega posting. The continuous mega crew value lies inside the historical norovirus IQR and the discrete value above it. Neither comparison tests a population effect with one posted seed. Changing the solver gave no resolved paired effect capable of explaining the cross-hull pattern in these screens. The decline in the simulated posting fraction with hull size describes **selected seeds**. There are no inclusion weights linking those strata to ordinary voyages. Comparing 1/16 directly with a fleet rate, or treating 56–75 hours as a historical timing window, would give a spurious source attribution. [Expedition](supply_solver_screen_01_readout.md) · [Classic and spirit](supply_solver_screen_02_readout.md) · [Mega](supply_solver_screen_03_readout.md)

## Compatibility of explanations

| Explanation | What the evidence supports | What would distinguish it historically |
|---|---|---|
| Shared upstream supply across ships | Supported in the 2019 cluster. Three investigated voyages had passenger AR 3.7–5.7% and crew AR 1.3–1.6%. The source attribution rests on matching lot records across ships, questionnaires, food and patient laboratory evidence, and cessation after withdrawal. The ARs alone would have been ambiguous. The ships on those three voyages fall in the spirit passenger-capacity group. Extrapolation to mega is unverified. | Linked procurement and recall records for affected **and unaffected** voyages, with dated illness evidence and relevant laboratory results. [Rispens et al., field investigation](https://www.cdc.gov/mmwr/volumes/69/wr/mm6916a3.htm) |
| Introduction by a traveler followed by onboard transmission | Supported in a separate investigation through the order of crew and passenger cases. Compatible with passenger-heavy final counts and with increasing passenger incidence on longer voyages. The review by Mouchtouri et al. found person-to-person transmission alone or in combination in 35 of 41 outbreaks with route information (45 reviewed). A documented transmission route can follow a different initial introduction. | Deidentified onset dates by role across successive voyages, contact histories, boarding illness records, and case typing. [Crisp et al., investigation and figure](https://www.cdc.gov/mmwr/volumes/72/wr/mm7230a5.htm) · [Mouchtouri et al., Results and Table 3](https://doi.org/10.2807/1560-7917.ES.2024.29.10.2300345) |
| Shared exposure on one ship, with or without secondary spread | Compatible with similar posted passenger ARs across hulls. Aggregate surveillance cannot resolve upstream sharing, onboard handling, lot size, or which groups actually ate the same food. The archived solver comparison does not isolate those structural alternatives. A uniform, early, single-exposure-only explanation for all voyages is in tension with the duration evidence and the documented propagated outbreak. | Exposure histories from cases and unaffected travelers, time-resolved onset curves, and traceback to independently recorded deliveries. |
| Hull size, surveillance threshold, and reporting differences | Can alter which voyages appear and how large the reported passenger/crew gap looks. The same percentage threshold requires different absolute counts across hulls. In one passenger cohort, 95 of 236 questionnaire-defined cases had not reported to the infirmary. This establishes that incomplete reporting occurs. It does not estimate a crew/passenger reporting ratio or explain the laboratory-linked cluster. | Consistent all-voyage denominators by ship and duration, plus paired active case finding and clinic records in both roles. [Wikswo et al., Results](https://doi.org/10.1093/cid/cir144) |

**Decision for Edison.** Report source diversity as supported and the fleet mixture as unresolved. Historical tracebacks identify a shared source in some outbreaks. Passenger-heavy ARs, repeated voyages, and threshold crossings also occur with person-to-person transmission. The most discriminating addition for mega would be a historical line list with onset by role linked to voyage, ship and existing traceback records, including comparable unaffected voyages. That would distinguish cross-ship clustering around a shared delivery from persistence aboard the same ship and quantify how reporting delays affect their apparent timing.

## Reproducing the historical table

From the repository root and its locked environment, run this block as Python. It produces the companion CSV on stdout. The fixed 2006–2019 extract contains paired counts for all 208 postings. The check makes a future change in count availability visible. The dedicated norovirus cohort excludes mixed-agent and unknown rows.

```python
import csv
import sys
from collections import defaultdict

from telemetry_buffer.observation_model import vsp_class_era_scoring as vsp

groups = defaultdict(list)
ships = defaultdict(set)
with vsp.SERIES.open(newline="") as source:
    for row in csv.DictReader(source):
        if not 2006 <= int(row["year"]) <= 2019:
            continue
        assert row["counts_published"] == "full"
        pax, crew = int(row["pax_total"]), int(row["crew_total"])
        hull = next(h for edge, h in vsp.BAND_EDGES if pax < edge)
        posting = vsp.Posting(int(row["year"]), row["era"], hull, pax,
                              int(row["pax_ill"]) / pax, int(row["crew_ill"]) / crew)
        cohorts = ["all_posted"]
        if row["causative_agent"] == "norovirus":
            cohorts.append("norovirus_only")
        for cohort in cohorts:
            groups[hull, cohort].append(posting)
            ships[hull, cohort].add(row["ship"])

writer = csv.writer(sys.stdout, lineterminator="\n")
writer.writerow(["hull", "cohort", "n_posted", "n_ship_names",
                 "pax_q1_pct", "pax_median_pct", "pax_q3_pct",
                 "crew_q1_pct", "crew_median_pct", "crew_q3_pct",
                 "pax_only", "crew_only", "both", "neither"])
for hull in vsp.SCORED_HULLS:
    for cohort in ("norovirus_only", "all_posted"):
        sample = groups[hull, cohort]
        rates = [vsp.quantiles([p.pax_rate for p in sample]),
                 vsp.quantiles([p.crew_rate for p in sample])]
        quantiles = [f"{100 * rate[q]:.4f}" for rate in rates for q in ("q1", "median", "q3")]
        channels = vsp.observed_posting_channels(sample)
        counts = [channels[k] for k in ("passenger_only", "crew_only", "both", "neither_at_threshold")]
        writer.writerow([hull, cohort, len(sample), len(ships[hull, cohort]), *quantiles, *counts])
```
