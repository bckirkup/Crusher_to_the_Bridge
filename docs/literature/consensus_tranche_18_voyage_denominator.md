# Tranche 18 — the voyage denominator for VSP posting rates: CDC published one for 2008–2014, only in aggregate for 2006–2019, and nothing outside CDC matches the jurisdiction

**Status:** Evidence assembled. **No profile constant, engine constant, anchor
target or observation-model constant changes in this document.** Nothing here is
authoritative about the model; the authoritative per-quantity status is
[`docs/parameter_provenance_register.md`](../parameter_provenance_register.md),
and this tranche's proposed row for it is
[`fragments/voyage-denominator.md`](fragments/voyage-denominator.md), which the
lead integrates. This document reports what was found, including what was not.

**Scope:** task #13, sourcing unit "voyage-denominator". The quantity is the
**external denominator for VSP outbreak posting rates**: the number of
qualifying voyages (or passenger-days) per year sailed by ships under VSP
jurisdiction, over the period covered by
`telemetry_buffer/observation_model/vsp_outbreak_series.csv` (pre-COVID window
2004–2019; post window 2022–2026). The repository holds the numerator (posted
outbreaks) and the class-level MIDRS transcription in
`telemetry_buffer/observation_model/midrs_observed_targets.md`; it does not hold
an annual denominator, so no posting rate can be computed year by year.

**What this unit did not do.** It did not compute any candidate's effect on
anchors A4, A8 or A9, did not divide the repository numerator by any candidate,
and does not recommend a value. Rates quoted below are the *source's own*
published rates, reproduced as evidence about that source's denominator.

---

## 1. The quantity, and the two jurisdictional filters that define it

VSP jurisdiction (CDC, restated identically in Freeland 2016, Jenkins 2021, the
2018 Operations Manual and the FY2026 fee notice, 90 FR 39393): a passenger
vessel that **carries ≥13 passengers** and **has a foreign itinerary with a US
port call**. Illness reporting under MIDRS is required for such a ship **within
15 days of arrival at a US port** from a foreign port.

The repository's posting-series criteria (`vsp_series_spec.md`) add the
analysis filters CDC applies in its own rate papers: **≥100 passengers**,
voyages of **3–21 days**, and an outbreak threshold of **≥3 %** of passengers or
crew, with the caveat that VSP may also post outbreaks of public-health
significance that miss the threshold. So a matching denominator must be:

1. VSP-jurisdiction voyages (≥13 pax, foreign itinerary, US port call);
2. restricted, or restrictable, to ≥100 pax and 3–21 days;
3. resolved by **year** across 2004–2019 and 2022–2026;
4. counted in the same unit the numerator uses — a *voyage* (one sailing with a
   unique voyage number), or passenger-days if the rate is per travel-day.

No single published source meets all four. Section 5 says which meet which.

## 2. Method

Read first: `.agents/skills/searching-literature-evidence/SKILL.md`,
`.agents/skills/model-parameter-provenance/SKILL.md`,
`docs/parameter_provenance_register.md`, `docs/literature/README.md`,
`docs/literature/consensus_tranche_10.md` (header form),
`telemetry_buffer/observation_model/vsp_series_spec.md`,
`telemetry_buffer/observation_model/midrs_observed_targets.md`, and the
year-by-year counts of `vsp_outbreak_series.csv`.

Consensus MCP: `list_tools` confirmed `search`; all searches below were run
**unfiltered** (no `year_min`, `study_types`, `controlled` or other filter was
applied in any query). Truncated outputs were read from the overflow files the
truncation notices named. Web sources were fetched directly (CDC MMWR HTML and
PDF, BTS/MARAD tables, BREA/CLIA economic-impact reports, Federal Register).

### 2.1 Consensus queries, verbatim

| # | Query | Filters | What came back |
|---|---|---|---|
| Q1 | `cruise ship gastroenteritis outbreaks per 1000 voyages denominator` | none | 20 results. Koo 1996, Cramer 2006, Freeland 2016, Jenkins 2021, Cramer 2003, Addiss 1989 are the denominator-bearing ones; the rest are reviews, single-outbreak reports and COVID models |
| Q2 | `cruise ship outbreak rate per 10 million passenger-days` | none | 20 results. Koo 1996 first; then reviews and Diamond Princess models (Rocklöv 2020, Mosleh 2024, De Bellis 2024 — all model outputs, none denominators) |
| Q3 | `Vessel Sanitation Program voyages per year surveillance denominator` | none | 20 results. Jenkins 2021, Cramer 2003, Cramer 2006, Dannenberg 1982, Addiss 1989, Marti 1995; the rest inspection-score papers (Dahl 2018, Taylor 2018, Carling 2009) and off-topic port-state-control / vessel-traffic papers |
| Q4 | `number of cruise voyages calling at United States ports per year` | none | 20 results, dominated by tourism-economics literature. Only Lee 2013 (~30,000 US-homeport voyages, occupancy analysis) and Jenkins 2021 touch a voyage count |
| Q5 | `cruise ship acute gastroenteritis incidence travel days Maritime Illness Database` | none | 20 results. Jenkins 2021, Freeland 2016, Cramer 2006, Mouchtouri 2017, Koo 1996, Merson 1975, Dannenberg 1982, Crisp 2023 (Notes from the Field) |

Earlier in the session the same tool surface was probed with a broader
cruise-outbreak-epidemiology query whose verbatim string was not preserved
across a context checkpoint; every denominator-bearing paper it surfaced
(Cramer 2006, Jenkins 2021, Freeland 2016, Koo 1996, Addiss 1989, Marshall
2016) reappears in Q1–Q5 above, so nothing in this tranche rests on it.

### 2.2 Web sources fetched

| Source | URL | Fetched as |
|---|---|---|
| Freeland et al. 2016, MMWR 65(1) — HTML and PDF (Table on p. 3) | `https://www.cdc.gov/mmwr/volumes/65/wr/mm6501a1.htm`, `.../pdfs/mm6501.pdf` | full text |
| Jenkins et al. 2021, MMWR SS 70(6) — PDF | `https://www.cdc.gov/mmwr/volumes/70/ss/pdfs/ss7006a1-H.pdf` | full text |
| CDC VSP "AGE on Cruise Ships, 2006–2019" plain-language page (27 Feb 2024) | `https://www.cdc.gov/vessel-sanitation/php/data-research/index.html` | full text |
| Federal Register, 90 FR 39393 (15 Aug 2025), VSP inspection fees FY2026 | `https://www.govinfo.gov/content/pkg/FR-2025-08-15/pdf/2025-15595.pdf` | full text |
| BTS *Passenger Travel Facts and Figures 2015*, Table 2-10 (MARAD data) | `https://www.bts.gov/archive/publications/passenger_travel_2015/chapter2/table2_10` | full table |
| BTS Special Report, *U.S. Ocean Passenger Terminals* (Dec 2010), Tables 1–2 (MARAD data) | `https://doi.org/10.21949/1520890` | search-result excerpt of Tables 1–2 |
| BTS *By the Numbers*, Figure 6, North American cruise vessel calls by quarter 2006–2011 (MARAD Snapshot 2011) | `https://www.bts.gov/archive/publications/by_the_numbers/maritime_trade_and_transportation/figure_06` | full table |
| MARAD press release via MarineLink, 18 May 2012, "Record Year 2011" | `https://www.marinelink.com/news/american-industry-record344795` | excerpt |
| BREA for CLIA, *Economic Contribution of the International Cruise Industry in the US in 2019* (Nov 2020) | `https://cruising.org/sites/default/files/2025-03/2019%20USA%20Cruise%20EIS.pdf` | executive summary |
| BREA for CLIA, same series, 2018 edition (Nov 2019) | `https://safety4sea.com/wp-content/uploads/2019/11/CLIA-Contribution-of-the-International-Cruise-Industry-to-the-US-Economy-2018-2019_11.pdf` | executive summary |
| Census *Statistical Abstract 2011*, Table 1259 (CLIA data 2004–2008) | `https://www2.census.gov/library/publications/2010/compendia/statab/130ed/tables/11s1258.pdf` | full table |
| BTS "North American Cruise Departures 2019–2023" (CLIA data) | `https://www.bts.gov/browse-statistical-products-and-data/info-gallery/north-american-cruise-departures-2019-2023` | landing page only; the `.xlsx` download returned an HTML page, so the 2019–2023 values were **not** recovered |
| Europe PMC REST abstracts for Cramer 2006 and Koo 1996 | `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:...` | abstracts (Results paragraphs) |

## 3. Candidates that carry a denominator — peer-reviewed / CDC

### 3.1 Freeland, Cramer, Regan, Rodriguez Suarez, Jenkins (CDC). *Acute Gastroenteritis on Cruise Ships — United States, 2008–2014.* MMWR 2016;65(1):1–5. DOI 10.15585/mmwr.mm6501a1. **Grade A.**

The only source found that publishes **annual** VSP-jurisdiction voyage counts.
Table, p. 3 (transcribed from the PDF):

| | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | Σ |
|---|---|---|---|---|---|---|---|---|
| Voyages that required a VSP report (≥13 pax, foreign itinerary, US arrival) | 4,694 | 4,506 | 4,627 | 4,621 | 4,404 | 4,424 | 4,808 | 32,084 |
| Voyages included in analysis (3–21 days **and** >100 pax) | 4,098 | 3,964 | 4,155 | 4,189 | 4,168 | 4,146 | 4,387 | 29,107 |
| Passenger AGE outbreaks (≥3 %) investigated by VSP | 20 | 17 | 21 | 15 | 27 | 17 | 15 | 132 |
| Crew AGE outbreaks | 1 | 4 | 3 | 1 | 1 | 1 | 4 | 15 |
| Passenger outbreaks per 1,000 voyages (source's own) | 4.4 | 4.0 | 3.8 | 3.3 | 6.5 | 4.2 | 3.0 | |
| Passenger outbreaks per 10 million travel-days (source's own) | 2.9 | 2.5 | 2.7 | 1.9 | 3.3 | 2.1 | 1.8 | |

Text: 73,599,005 passengers and 28,281,361 crew travelled on the 29,107
included voyages over the seven years; 133 (0.5 %) of the 29,107 voyages had an
outbreak. Travel-days are defined as persons on board × voyage days; the paper
does not print annual travel-day totals, but the "per 10 million travel-days"
row and the outbreak counts together imply them (e.g. 20 / 2.9 × 10⁷ ≈
6.9 × 10⁷ passenger travel-days in 2008). Both sums check (4,694 + … + 4,808 =
32,084; 4,098 + … + 4,387 = 29,107).

Measurement status: **measured** — administrative counts of MIDRS voyage
reports, per ship and voyage, most recent report per voyage. Coverage: exactly
VSP jurisdiction, with the ≥100-pax and 3–21-day filters applied in the second
row. Period: 2008–2014 only — seven of the sixteen pre-COVID years in the
repository series.

### 3.2 Jenkins, Vaughan, Rodriguez, Freeland (CDC). *Acute Gastroenteritis on Cruise Ships — MIDRS, United States, 2006–2019.* MMWR Surveill Summ 2021;70(6):1–19. DOI 10.15585/mmwr.ss7006a1. **Grade A for the 14-year aggregate; no annual denominator.**

Table 1: **37,258 unduplicated voyage reports** from **252 ships**, 2006–2019,
after excluding voyages <3 or >21 days and ships with <100 passengers or no
crew. Strata: 24-hour reports 18,040, 4-hour 18,606, special 612; by voyage
length 3–5 d 13,772 / 6–7 d 6,031 / 8–10 d 12,239 / 11–14 d 3,111 / 15–21 d
2,105; by arrival region California 5,021, Caribbean 2,267, Hawaii 250,
Northeast 3,756, Northwest 3,384, South 2,767, Southeast 19,813. The abstract
says 37,276; the repository already records this and resolves to 37,258 because
the report-type strata sum exactly.

Outbreaks: 156 passenger and 16 crew outbreaks investigated 2006–2019 (Table
3, by length and region; Figure 10 by year as *percentages*, not counts). The
report gives **no annual voyage counts** and **no annual travel-day totals**;
Figure 1 plots annual incidence per 100,000 travel-days without printing the
denominators. The companion CDC page (27 Feb 2024) adds "approximately 127
million passengers sailed on 252 cruise ships in VSP jurisdiction" 2006–2019.

Measurement status: **measured** (administrative). Coverage: exactly VSP
jurisdiction with the ≥100-pax / 3–21-day filters. Period: 2006–2019, which is
the closest match to the repository's pre-COVID window, but resolved only as a
single total.

### 3.3 Cramer, Blanton, Blanton, Vaughan, Bopp, Forney (CDC). *Epidemiology of gastroenteritis on cruise ships, 2001–2004.* Am J Prev Med 2006;30(3):252–7. DOI 10.1016/j.amepre.2005.10.027. **Grade A for its period; denominator not printed in the abstract.**

Results (Europe PMC abstract): outbreaks per 1,000 cruises rose from **0.65 in
2001 to 5.46 in 2004**; outbreak counts 2 in 2001, median 15/yr 2002–2004;
population "cruise ships calling on U.S. ports, carrying 13 or more passengers"
(Gastrointestinal Illness Surveillance System). The cruise counts behind the
rates are in the full-text Results, which were not retrieved here (paywalled);
the abstract's numbers imply on the order of 3,000 cruises/yr but that is an
inference, not a transcription. Period 2001–2004 predates the repository's
2004 series start except for one year.

### 3.4 Koo, Maloney, Tauxe (CDC). *Epidemiology of diarrheal disease outbreaks on cruise ships, 1986 through 1993.* JAMA 1996;275(7):545–7. DOI 10.1001/jama.1996.03530310051032. **Grade B (method is the value; wrong period).**

The one paper that states the denominator's *construction*: "denominator data
were summations of cruise ship data on the number of passengers and length of
cruises collected during routine diarrheal illness surveillance, available only
for the period 1989 through 1993." Result: for cruises of 3–15 days, **1.4
outbreaks per 1,000 cruises** or **2.3 per 10 million passenger-days**.
Measured; VSP jurisdiction; but 1989–1993, a decade before the repository
series, and a 3–15-day window rather than 3–21.

### 3.5 Cramer, Gu, Durbin (CDC). *Diarrheal disease on cruise ships, 1990–2000.* Am J Prev Med 2003;24(3):227–33. DOI 10.1016/S0749-3797(02)00644-X. **Grade A for its period; rates per passenger-day only.**

Incidence 29.2 → 16.3 cases per 100,000 passenger-days 1990→2000 (quoted in
Cramer 2006's background), for cruise ships entering the United States. No
voyage counts in the abstract; the period ends before the repository series.

### 3.6 Older CDC series — Addiss 1989 (1975–85, DOI 10.1017/S0950268800030363), Dannenberg 1982 (1975–78, DOI 10.2105/ajph.72.5.484), Merson 1975 (JAMA, DOI 10.1001/jama.1975.03240190027011). **Grade B — wrong period.**

Establish that the 24-hour-before-arrival report has been the denominator's raw
material since the 1970s. Not usable for 2004–2019.

## 4. Candidates from government and industry statistics (web pass)

### 4.1 MARAD *North American Cruise* statistics (US DOT), as republished by BTS. **Measured; Grade B — different population.**

Cruises departing US ports, by year (BTS Table 2-10, MARAD source, as of March
2015): **2004 4,465; 2005 4,462; 2006 4,435; 2007 4,498; 2008 4,239; 2009 4,126;
2010 4,216; 2011 4,222.** An earlier BTS print of the same MARAD table
(Dec 2010, "Cruise Detail Table updated 07/07/09") gives 2007 4,464 and 2008
4,212 — the series was revised between releases, by up to 34 cruises. Passengers
departing US ports: 2004 9,418,317; 2005 9,747,188; 2006 9,970,922; 2007
10,288,583; 2008 9,914,755. MARAD 2011: 10.9 million passengers, 4,222 cruises,
**71.8 million passenger-nights**. Vessels active per quarter 2006–2011: 76–105.

Coverage: cruises *departing a US port*, all durations, including **Hawaii
(domestic, 87–240/yr)** and **cruises to nowhere (5–14/yr)**, which are not
foreign itineraries; it **excludes** VSP-jurisdiction voyages that embark
abroad and *call* at a US port (Vancouver–Alaska, Quebec–New England,
transatlantic arrivals, repositioning). Direction of mismatch against the VSP
"required a report" count for the one overlapping year with both numbers
(2008: MARAD 4,239 or 4,212 vs VSP 4,694): MARAD is **~10 % lower**. Whether
the gap is entirely foreign-embarkation voyages, or partly a report-counting
difference on the CDC side (see §5.2), cannot be determined from the published
material. MARAD stopped publishing the annual snapshot after 2011 in the form
BTS reproduced; the 2012–2019 continuation was not found.

### 4.2 BREA for CLIA, *Economic Contribution of the International Cruise Industry in the United States* (annual/biennial). **Industry estimate; Grade C.**

US-port embarkations (millions): 2010 9.69; 2012 10.09; 2014 11.06; 2016
11.66; 2018 12.68; 2019 13.79. Passengers *sourced* from the US: 2012 10.67;
2014 11.33; 2016 11.50; 2018 13.09; 2019 14.20. These are CLIA member-line
figures compiled by a consultancy; the reports do not publish voyage counts or
passenger-days, do not state a ≥13-passenger or foreign-itinerary filter, and
count embarkations (a passenger embarking in Miami on a Bahamas cruise and again
a week later counts twice), so the unit differs from the numerator's voyage
unit. Not a measured denominator.

### 4.3 CLIA global passenger volumes (via Census Statistical Abstract Table 1259; BTS F2-16). **Industry estimate / projection; Grade C, rejected as a denominator.**

Global embarkations 2004–2008: 10.85, 11.5, 12.0, 12.56, 13.0 million; US
share 8.1–9.2 million. CLIA's headline annual figures for later years are
frequently forward-looking ("expected to reach"); the BTS 2019–2023 departures
chart is CLIA-sourced and its spreadsheet did not download. Global totals cover
every cruise line and itinerary worldwide, of which the VSP population is a
minority; the direction of mismatch is **large and upward** (the 2006–2019 VSP
population is ~127 million passengers over 14 years, ~9 million/yr, against
global volumes of 12–30 million/yr over the same span).

### 4.4 CDC VSP inspection records and fee notices. **Measured, wrong unit.**

Twice-yearly inspection of every VSP-jurisdiction ship gives a *ship* count
(252 ships over 2006–2019 per Jenkins; fee notices define a "weighted number of
annual inspections" but do not print voyage counts). Ships, not voyages: no
denominator.

### 4.5 Lee & Ramdeen 2013, *Tourism Management*, DOI 10.1016/j.tourman.2012.03.009. **Grade C for this purpose.**

Occupancy analysis of "almost 30,000" voyages disembarking in US homeports over
an unstated multi-year window; a commercial dataset, US-homeport only, with no
year table in the abstract. Not a denominator.

## 5. Matching analysis

### 5.1 Coverage table

| Candidate | ≥13 pax, foreign itinerary, US call | ≥100 pax, 3–21 d | Unit | Years resolved | Status |
|---|---|---|---|---|---|
| Freeland 2016 (§3.1) | yes | yes (second row) | voyages; travel-days implied | **2008–2014 annually** | measured |
| Jenkins 2021 (§3.2) | yes | yes | voyages | 2006–2019 as one total | measured |
| CDC 2024 page (§3.2) | yes | yes | passengers | 2006–2019 as one total | measured, rounded |
| Cramer 2006 (§3.3) | yes | not stated | cruises (rate only) | 2001–2004 | measured, denominator not printed |
| Koo 1996 (§3.4) | yes | 3–15 d | cruises, passenger-days | 1989–1993 | measured |
| MARAD/BTS (§4.1) | **no** — US departures, incl. domestic Hawaii & nowhere; excl. foreign embarkations | no | cruises, passengers, passenger-nights | 2004–2011 annually | measured |
| BREA/CLIA US (§4.2) | no — member-line embarkations at US ports | no | embarkations | 2010–2019, biennial | industry estimate |
| CLIA global (§4.3) | no | no | passengers | annual | estimate / projection |
| VSP inspections (§4.4) | yes | n/a | ships | annual | measured, wrong unit |

### 5.2 Three things that stop the two CDC denominators being combined blindly

**(a) The two MMWR products are not mutually consistent in the same unit.**
Freeland's *included* voyages sum to 29,107 for 2008–2014 under the stated
≥100-pax / 3–21-day filters. Jenkins reports 37,258 *unduplicated voyage
reports* for 2006–2019 under the same filters. If both counted the same thing,
the remaining seven years (2006–2007, 2015–2019) would hold only 8,151 voyages
(~1,160/yr) against Freeland's ~4,160/yr — implausible for a fleet that grew
over the period. The likely explanation is that Freeland counts *reports*
(MIDRS receives a 24-hour and often a 4-hour report per arrival) or
*arrivals* rather than unique voyage numbers, while Jenkins deduplicates on
voyage number; but neither paper says so, and this is an **inference from the
arithmetic, not a documented definition**. Whoever adopts either must state
which unit they mean by "voyage".

**(b) The numerators differ from the repository's.** CDC's per-voyage rates use
outbreaks *investigated* by VSP (Freeland: 132 passenger outbreaks 2008–2014;
Jenkins: 156 for 2006–2019). The repository's series is outbreaks *posted* on
the public VSP outbreak-update pages with usable passenger denominators: by
year 2008–2014 it holds 14, 15, 14, 14, 16, 9, 9 = **91** rows, and 208 rows
for 2006–2019 (`midrs_observed_targets.md` already records the 208-vs-156
conflict). The posted series is therefore *smaller* than the investigated
series for 2008–2014 and *larger* for 2006–2019 — the two series are not the
same population of events in either direction. A rate formed from the
repository numerator over a CDC denominator is a **posting** rate, not the
**investigation** rate CDC publishes, and the two must not be compared as if
they were the same quantity.

**(c) Two of the three MMWR denominators are pre-filtered.** The 3–21-day /
>100-pax restriction is a CDC analysis choice matching `vsp_series_spec.md`;
the *first* row of Freeland's table (32,084) is the unfiltered jurisdiction
count and is the right one only if the numerator is likewise unfiltered.

### 5.3 Verdict

* **A matching annual voyage denominator exists, measured, Grade A, for
  2008–2014 only** (Freeland 2016, Table): 4,404–4,808 VSP-report voyages per
  year, of which 3,964–4,387 per year are 3–21 days with >100 passengers. Its
  travel-day denominator is recoverable only by back-calculation from the
  published rates.
* **For 2006–2019 the matching denominator exists only as a 14-year total**
  (37,258 voyages, ~127 million passengers), unresolved by year, and in a unit
  that does not reconcile with Freeland's annual counts (§5.2a).
* **For 2004–2005, 2015–2019 and 2022–2026 no matching annual denominator was
  found anywhere.** MARAD covers 2004–2011 in a different population (US
  departures), and nothing covers 2015 onward except industry embarkation
  estimates that fail the jurisdiction filter and the unit.
* **No industry or port statistic matches VSP jurisdiction.** Every one either
  includes voyages VSP does not cover (domestic Hawaii, cruises to nowhere,
  non-US itineraries) or excludes voyages VSP does cover (foreign embarkations
  with a US call), and none applies the ≥13-passenger rule.

**What would produce a valid denominator for the full series:** the annual
count of unduplicated MIDRS voyage numbers, 2004–2019 and 2022–present, with
the ≥100-pax and 3–21-day flags and per-voyage passengers × days, from CDC VSP
directly (a data request or FOIA to `vsp@cdc.gov`; MIDRS is the system that
already produced the two MMWR tables). Absent that, the honest statement is
that the posting rate is computable for **2008–2014 only**, and only after
choosing and declaring which CDC voyage unit is meant.

## 6. Rejected candidates, with reasons

| Candidate | Reason |
|---|---|
| Diamond Princess / cruise COVID models (Rocklöv 2020; Mosleh 2024; De Bellis 2024; Guagliardo 2021) | Model outputs about transmission, not denominators; surfaced by Q2 because of "per passenger-day" vocabulary |
| Mouchtouri 2017, Eurosurveillance (DOI 10.2807/1560-7917.ES.2017.22.45.16-00576) | Five ships' syndromic data 2010–2013, incidence 2.81 per 10,000 traveller-days; a ship-level cohort, not a jurisdiction denominator, and European operators |
| Marshall 2016, BMC Public Health (DOI 10.1186/s12889-016-2991-3) | One Caribbean port's medical-visit rates; a port, not the VSP fleet |
| Pavli 2016, Travel Med Infect Dis | One ship, three years, Mediterranean; not VSP |
| Bert 2013; Mouchtouri 2024 (DOI 10.2807/1560-7917.ES.2024.29.10.2300345); Neumann 2024/2025; Kak 2015; Lawrence 2004; Rooney 2004 | Reviews; no primary denominator |
| Dahl 2018; Taylor 2018; Carling 2009 | Inspection-score correlations; ship counts, not voyage counts |
| Wikswo 2011; Chimonas 2008; Gunn 1980; McEvoy 1996; Cramer 2003 MMWR (2002 outbreaks); Widdowson 2004; Crisp 2023 | Single-outbreak or single-season investigations |
| Marti 1995, J Travel Res | Programme description; no counts |
| Lee & Ramdeen 2013 | US-homeport commercial dataset, unstated years, occupancy not coverage |
| CLIA global volumes | Wrong population, part projection (§4.3) |
| BREA/CLIA US embarkations | Wrong unit (embarkations) and no jurisdiction filter (§4.2) |
| VSP inspection counts | Ships, not voyages (§4.4) |
| Cope 2020; Sheriff 2025; tourism-economics results of Q4 | Off-topic (vessel traffic monitoring, port state control, cruise tourism economics) |

## 7. Null results

* No peer-reviewed or government source publishes **annual** VSP-jurisdiction
  voyage or passenger-day counts for **2004–2007, 2015–2019, or 2022–2026**.
* No source publishes annual **travel-day** totals for any year; Freeland's are
  implied by rate × count only.
* No source outside CDC applies the **≥13-passenger, foreign-itinerary, US-call**
  filter; the denominator is a CDC-only construct.
* The MARAD annual cruise series was not found for **2012 onward**; the BTS
  2019–2023 CLIA-sourced spreadsheet did not download.
* Full-text Results of Cramer 2006 and Cramer 2003 (paywalled) were not read;
  their cruise counts for 2001–2004 remain untranscribed.

## 8. Definition problems for the register

The field "voyages per year under VSP jurisdiction" is expressible, but the
literature offers it in **two irreconcilable units** (Freeland's per-year
"voyages that required a report" vs Jenkins's "unduplicated voyage reports"),
and the repository numerator is a **third population** (posted, not
investigated). Any register row must name the unit and the numerator it pairs
with; the fragment does so.
