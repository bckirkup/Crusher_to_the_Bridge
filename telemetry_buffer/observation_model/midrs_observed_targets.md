# MIDRS observed targets for A8, A9 and A10

Status: Source record. The tables below are transcribed from the published
source and are the only authority for the A8/A9/A10 observed values. The
implementation that consumes them does not exist yet.
Owner anchors: A8, A9, A10
Last updated: 2026-08-30

Source: Jenkins KA, Vaughan GH Jr, Rodriguez LO, Freeland A. Acute
Gastroenteritis on Cruise Ships -- Maritime Illness Database and Reporting
System, United States, 2006-2019. MMWR Surveill Summ 2021;70(6):1-19.
Transcribed from the article PDF, Tables 1, 2 and 3 plus the Results text.
Retrieved 2026-08-30.

## Why this file exists separately

Every number an anchor is scored against has to be readable without trusting a
paraphrase. The design lives in
`telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md`;
this file holds the transcription, the denominators, and the three places where
the source contradicts itself or contradicts our own dataset. Those three are
not footnotes -- each one changes what an honest target is.

## Table 1 -- voyage reports by characteristic (the A9 denominators)

"No. voyage reports (unduplicated) 37,258 (100)"; "No. ships (unduplicated)
252 (100)". The three report types sum exactly to 37,258 (18,040 24-hour +
18,606 4-hour + 612 special), so a voyage contributes exactly one row and
37,258 is a **voyage count**, not a report count inflated by resubmission.

| Ship size (GRT) | voyage reports | share |
|---|---:|---:|
| Extra small, small, medium (<=30,000) | 1,500 | 4% |
| Large (30,001-60,000) | 4,510 | 12% |
| Extra large (60,001-120,000) | 30,039 | 81% |
| Mega (120,001-140,000) | 917 | 3% |
| Super mega (>=140,001) | 292 | 1% |

| Voyage length | voyage reports | share |
|---|---:|---:|
| 3-5 d | 13,772 | 37% |
| 6-7 d | 6,031 | 16% |
| 8-10 d | 12,239 | 33% |
| 11-14 d | 3,111 | 8% |
| 15-21 d | 2,105 | 6% |

## Table 2 -- AGE incidence per 100,000 travel days

Rate definition, verbatim: `[(Total no. passenger/crew cases) / (total
passengers/crew onboard x total number of voyage days during a voyage)] x
100,000 travel days`.

| Ship size (GRT) | n | total | passengers | crew |
|---|---:|---:|---:|---:|
| <=30,000 | 1,500 | 9.06 | 10.9 | 6.4 |
| 30,001-60,000 | 4,510 | 21.4 | 23.7 | 16.7 |
| 60,001-120,000 | 30,039 | 22.1 | 23.0 (Ref) | 19.8 (Ref) |
| 120,001-140,000 | 917 | 22.9 | 26.7 | 14.7 |
| >=140,001 | 292 | 24.4 | 29.2 | 16.0 |

| Voyage length | n | total | passengers | crew |
|---|---:|---:|---:|---:|
| 3-5 d | 13,772 | 14.5 | 13.3 (Ref) | 17.5 (Ref) |
| 6-7 d | 6,031 | 19.0 | 17.8 | 22.1 |
| 8-10 d | 12,239 | 22.0 | 23.2 | 19.0 |
| 11-14 d | 3,111 | 29.5 | 35.0 | 17.4 |
| 15-21 d | 2,105 | 33.8 | 40.0 | 20.9 |

All passenger contrasts against the extra-large referent carry p < 0.0001
except large ships at p = 0.0125; the 11-14 day crew contrast is the one
non-significant cell in the length panel (p = 0.9442).

## Table 3 -- outbreaks investigated, by voyage length

156 passenger outbreaks and 16 crew outbreaks, 2006-2019.

| Voyage length | passenger outbreaks | crew outbreaks |
|---|---:|---:|
| 3-5 d | 7 (4%) | 6 (38%) |
| 6-7 d | 2 (1%) | 4 (25%) |
| 8-10 d | 30 (19%) | 3 (19%) |
| 11-14 d | 57 (37%) | 2 (13%) |
| 15-21 d | 60 (38%) | 1 (6%) |

Table 3 carries no denominator. Dividing by the Table 1 length counts gives the
per-voyage passenger outbreak probability used by A10c:

| Voyage length | outbreaks / voyages | per 1,000 voyages |
|---|---|---:|
| 3-5 d | 7 / 13,772 | 0.51 |
| 6-7 d | 2 / 6,031 | 0.33 |
| 8-10 d | 30 / 12,239 | 2.45 |
| 11-14 d | 57 / 3,111 | 18.32 |
| 15-21 d | 60 / 2,105 | 28.50 |
| all | 156 / 37,258 | 4.19 |

## The calendar trend, which decides what "pre-COVID" means

From the Results text: passenger incidence fell from **32.5 to 16.9** per
100,000 travel days across 2006-2019, and crew from **13.5 to 5.2**. So every
pooled rate in Table 2 is an average over a period in which the quantity
roughly halved, and the pooled 23.0 describes no year in particular.

**Scoring decision.** Our pre-COVID configuration represents late-2010s
practice, not 2006 practice, so A8 reports a plausibility band with the
**end-of-period** rate -- 16.9 passengers, 5.2 crew -- and the pooled Table 2
size-band rate alongside it as the period average, never instead of it. These
endpoints come from different stratifications: the calendar endpoint is
fleet-wide, while the pooled rate is GRT-band-specific. The band is not a
confidence interval. For <=30,000 GRT, the fleet endpoint 16.9 is above the
pooled band rate 10.9, proving the pair is not ordered by construction.
Scoring a late-2010s configuration against 23.0 would demand roughly 1.4x the
incidence the last observed year shows. No band-specific calendar endpoint is
reconstructed because MIDRS does not publish one. The two figures must both
appear in any A8 report, and the size-band and length-band breakdowns are only
available pooled, so a size-specific target inherits the period average and is
used for gradient shape rather than level.

The trend also differences: crew fell 2.6x while passengers fell 1.9x, over the
same voyages and the same reporting system.

## Three conflicts, none of them resolvable by preference

**1. The source's own Results text mislabels Table 2.** The text states that
"for crew members, rates were significantly higher for mega (26.7 per 100,000
travel-days) and super-mega (29.2 per 100,000 travel days) ships". In Table 2
those two values are the **passenger** rates; the crew rates for those bands
are 14.7 and 16.0, and crew peak on extra-large ships at 19.8 -- which the very
next sentence of the same paragraph states correctly. Table 2 is authoritative
here and the prose is wrong. Recorded so that a later reader does not "correct"
our constants from the abstract.

**2. Ships and voyage reports are conflated.** The abstract and Results say "Of
the 252 cruise ships, 80.6% were extra large", but 80.6% is 30,039/37,258 --
the share of **voyage reports**, not of ships. The per-ship size distribution
is not published. This matters because A9's denominator is voyages, so the
Table 1 counts are the right denominator regardless; but no claim about how many
*ships* of each class existed can be sourced from this paper.

**3. MMWR counts 156 passenger outbreaks; our own series carries 208.** For the
same 2006-2019 window, `vsp_outbreak_series.csv` holds 208 postings with a
usable passenger denominator across 103 ships, against MMWR's 156 investigated
outbreaks. The definitions differ -- MMWR counts outbreaks VSP *investigated*,
the public list counts outbreaks VSP *posted* -- and the ratio, 1.33, is a
direct measure of how much slack the word "outbreak" carries between two CDC
products describing the same period. A9's numerator must be one definition or
the other, stated, for both the observed and the model side; mixing them
inflates or deflates the posting rate by up to a third. Until that choice is
made explicit in the scorer, A9 is reported as an interval spanning both.

## What is still missing

- **Outbreak counts by GRT band.** Table 3 breaks the 156 outbreaks down by
  voyage length and by region, not by ship size. So A9 *per hull class* has a
  denominator (Table 1) but no published numerator; only the fleet-wide 4.19
  per 1,000 voyages and the length breakdown are available. A per-class A9
  target requires either an unpublished cross-tabulation or a reconstruction
  from our own posting series against Table 1 denominators, which mixes the two
  outbreak definitions above and must be reported as such.
- **Travel-day totals.** The rates are published with confidence intervals but
  the underlying passenger-days and crew-days per band are not, so an observed
  rate cannot be re-derived or re-aggregated across bands. Bands are therefore
  compared one at a time, never pooled by us.
- **Everything after 2019.** No MIDRS surveillance summary covers the post-COVID
  period, so A8 and A9 have no post-arm observation at all.
- **An annual denominator, in a defined voyage unit.** Table 1's 37,258 is a
  single pooled total of *unduplicated voyage reports* over fourteen years, so
  A9's target is a period average and no year of it can be separated out. The
  only annual counts CDC publishes are Freeland 2016's, for 2008-2014, in two
  other units that do not reconcile with this one; #13 declares the unit used
  here rather than closing the gap, and carries the Freeland series as a
  diagnostic in `vsp_voyage_denominator.py`.
