# External data request — an annual MIDRS extract from CDC VSP

> **Status:** Proposed — drafted, not yet sent. The artifact this document
> specifies (a CDC-supplied annual extract) does not exist. Nothing in the tree
> may assume it will arrive; the register row it would unblock stays blocked
> until it does.

## Why this request exists

Task #13 (item **B4** of [`defect_resolution_plan.md`](defect_resolution_plan.md))
resolved as a declaration: the VSP posting rate cannot be computed, and the
reason that survived every other repair is a **numerator definition mismatch**
that no literature search can close.

`telemetry_buffer/observation_model/vsp_outbreak_series.csv` is a numerator
scraped from CDC's public outbreak-update pages: 428 posted voyages, 1993–2026.
Every published CDC denominator, however, is paired with outbreaks CDC
*investigated*, not outbreaks CDC *posted*, and the two counts do not stand in a
fixed relation:

| Window | Our posted rows | CDC investigated (published) | Ratio |
|---|---:|---:|---:|
| 2008–2014 (Freeland 2016, MMWR 65(1)) | 91 | 132 passenger outbreaks (Table; the Results text says 133) | 0.69 |
| 2006–2019 (Jenkins 2021, MMWR SS 70(6)) | 208 | 156 passenger outbreaks | 1.33 |

The ratio **inverts**. So the posted series is neither a subset of the
investigated series nor a stable fraction of it: in one window CDC investigated
outbreaks it did not post, and in the other the public list carries voyages the
surveillance summary did not count as outbreaks. No conversion factor exists to
be sourced, and constructing one from these two ratios would be fitting a
definition to make a rate come out — prohibited by
[`../sourcing_protocol.md`](../sourcing_protocol.md) and
`.agents/skills/model-parameter-provenance/SKILL.md`.

Two further gaps are also only closeable by CDC, not by literature:

- **No annual resolution outside 2008–2014.** 2004–2007 and 2015–2019 have no
  annual voyage count in any unit; Jenkins publishes one pooled 2006–2019 total.
- **No post-2020 denominator of any kind.** The arm that exists to measure the
  post-COVID discontinuity cannot express it as a rate at all.

## What is being asked for

An extract from the Maritime Illness Database and Reporting System (MIDRS),
**annual, calendar years 2004–2026**, with these columns per year:

1. **Voyages required to submit a VSP AGE report** — the unit Freeland 2016's
   Table calls "voyages requiring submission of a VSP report".
2. **Of those, voyages of 3–21 days carrying >100 passengers** — Freeland's
   analysed subset, and the same eligibility filter our scorer applies.
3. **Passenger AGE outbreaks investigated** — voyages meeting the ≥3%
   passenger-illness outbreak threshold, on the definition used in the MMWR
   summaries.
4. **Passenger AGE outbreaks published** to the public cruise-ship outbreak
   update list, and, if it differs, the count of voyages for which an outbreak
   update page was created.
5. **Crew AGE outbreaks investigated**, on the same definition (for the crew
   arm, which has its own anchor).

Plus, in prose, the three definitional statements without which the columns
cannot be used:

6. **The posting criterion.** What determines whether an investigated outbreak
   receives a public outbreak-update page — is it a threshold, a discretionary
   decision, or a change in policy over time? This is the question the two
   inverted ratios above raise, and the single most valuable line in the reply.
7. **The unit reconciliation.** Whether "voyage", "voyage report" and
   "unduplicated voyage report" denote the same countable event, and if not,
   how Freeland's 29,107 (2008–2014) sits inside Jenkins's 37,258 (2006–2019),
   which as published would leave only ~8,151 voyages for the other seven years
   of a period whose traffic grew.
8. **Whether any of this changed in or after 2020**, in either the reporting
   requirement or the posting practice, since a change there is confounded with
   the discontinuity we are trying to measure.

One small correction query, worth including because it is cheap and specific:

9. **The 2010 row of Freeland 2016's Table appears internally inconsistent.**
   The printed rate of 3.8 passenger outbreaks per 1,000 voyages, at the printed
   21 investigated outbreaks, implies ~5,526 voyages — above both published 2010
   voyage counts (4,627 required to report; 4,155 analysed). Recomputing gives
   4.54 and 5.05 respectively. Which of the three 2010 cells is the erratum? (In
   the other six years the printed rates track the required-report column to
   within 8.5%, mean 4.8%, so 2010 is the only year that does not reconcile.)

## Draft message

Confirm the current VSP contact address on CDC's Vessel Sanitation Program
contact page before sending; if a direct request is declined, the same field
list works as a FOIA request to HHS/CDC, and the definitional questions in 6–8
should be asked separately of the VSP program, since FOIA will return records
rather than explanations.

```text
Subject: Request for an annual MIDRS extract: voyage denominators and outbreak
counts, 2004-2026

Dear Vessel Sanitation Program,

I am building a publicly documented simulation model of acute gastroenteritis
transmission on cruise ships, and validating it against the outbreak statistics
VSP publishes. I am writing because one quantity the validation needs cannot be
recovered from the published record, and I would rather ask than estimate.

I have assembled a series of the voyages listed on the public cruise-ship
outbreak update pages (428 voyages, 1993-2026). To turn that into a rate I need
the number of qualifying voyages that sailed, and the published sources do not
cover it: Freeland et al. (MMWR 2016;65(1)) give annual voyage counts for
2008-2014 only, Jenkins et al. (MMWR Surveill Summ 2021;70(6)) give a single
pooled total for 2006-2019, and nothing has been published for 2020 onward.

More importantly, the numerator definitions do not match. Over 2008-2014 the
public list holds 91 voyages against the 132 passenger outbreaks Freeland
reports as investigated; over 2006-2019 it holds 208 against Jenkins's 156. The
relation inverts, so the public list is evidently neither a subset of the
investigated outbreaks nor a fixed share of them, and I do not want to assume a
conversion between them.

If it is possible to provide an extract from MIDRS, I am asking for annual
figures for calendar years 2004-2026:

  1. voyages required to submit a VSP AGE report;
  2. of those, voyages of 3-21 days carrying more than 100 passengers;
  3. passenger AGE outbreaks investigated (>=3% passenger illness);
  4. passenger AGE outbreaks published to the public outbreak update list;
  5. crew AGE outbreaks investigated.

Aggregate annual counts are sufficient; I am not requesting voyage-level or any
identifiable data.

Three questions matter as much as the counts, and I would be grateful for even
a brief answer to any of them:

  6. What determines whether an investigated outbreak receives a public
     outbreak update page, and has that criterion changed over time?
  7. Do "voyage", "voyage report" and "unduplicated voyage report" count the
     same event across the two MMWR reports? As published, Freeland's 29,107
     voyages for 2008-2014 inside Jenkins's 37,258 for 2006-2019 would leave
     about 8,151 for the remaining seven years, which I suspect means the units
     differ rather than that traffic fell.
  8. Did either the reporting requirement or the posting practice change in or
     after 2020?

Finally, a small apparent erratum: in Freeland et al. Table, the 2010 rate of
3.8 passenger outbreaks per 1,000 voyages, taken with the 21 investigated
outbreaks printed for that year, implies roughly 5,526 voyages, which exceeds
both voyage counts printed for 2010 (4,627 and 4,155); those give 4.54 and 5.05
per 1,000. The other six years reconcile to within about 5%. Would you be able
to say which of the three 2010 figures is in error?

Any counts you are able to share will be cited to VSP as the source, with the
extract date, in a public provenance register. I am happy to send the assembled
public-list series in return if it is of any use.

With thanks,
Benjamin Kirkup
```

## What happens to each possible answer

Recorded in advance, so the reply cannot be read selectively after the fact.

| Reply | Consequence in the model |
|---|---|
| Annual counts arrive with a stated posting criterion | The B4 register row unblocks: a posting rate becomes computable per year in one declared unit, and A9 can be re-expressed on an annual denominator instead of a pooled period average. The posting step still enters as a **declared** ascertainment quantity, not a fitted one. |
| Counts arrive, posting criterion not explained | Denominator gaps close; the numerator mismatch does **not**. The rate stays blocked, and the alternative becomes modelling the posting step as a swept observation-model parameter (a new Track B item), not choosing a ratio. |
| Only 2008–2014 confirmed, nothing new | No change. The row stays blocked with its current four reasons and the class-composition observable remains the only post-2020 fleet statistic. |
| The 2010 erratum is identified | `FREELAND_INCONSISTENT_YEARS` in `telemetry_buffer/observation_model/vsp_voyage_denominator.py` loses its entry and the corrected cell is quoted with the correction's origin; the residual assessment is restated. |
| No reply, or declined | This document moves to `history/` with the outcome recorded, so the request is not silently repeated. |

In no case does an arriving number get chosen for what it does to anchors A4,
A8 or A9, and in no case does the marginal effect on a fit justify preferring
one voyage unit over another.
