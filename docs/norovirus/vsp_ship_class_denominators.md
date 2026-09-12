> **Status:** Implemented — current record; documents existing constants and records a decision; nothing here is a proposal or unbuilt.

# VSP ship-class denominators, and why one tonnage band has no hull

Findable record of what the project holds on the **denominator** side of the A9
posting rate when it is cut by ship class, what it does *not* hold, and the
decision not to build a hull for the one tonnage band no hull occupies.

Constants live in `telemetry_buffer/observation_model/midrs_incidence_targets.py`;
the verbatim source transcription is
`telemetry_buffer/observation_model/midrs_observed_targets.md`; the
denominator-unit discussion is
`telemetry_buffer/observation_model/vsp_voyage_denominator.py`.

## 1. The class denominators exist, and are already in the tree

`MIDRS_VOYAGE_COUNTS_BY_GRT_BAND`, from Jenkins 2021 (*MMWR Surveill Summ*
70(6)) Table 1, pooled 2006-2019, unit **unduplicated voyage reports**:

| Jenkins label | GRT band | voyage reports | share | hull mapped here |
|---|---|---:|---:|---|
| Extra small / small / medium | <=30,000 | 1,500 | 4% | expedition_cruise_450 |
| Large | 30,001-60,000 | 4,510 | 12% | classic_cruise_1900 (low edge) |
| Extra large | 60,001-120,000 | 30,039 | 81% | classic_cruise_1900 (high edge), spirit_cruise_3000 |
| **Mega** | 120,001-140,000 | 917 | 3% | **none** |
| **Super mega** | >=140,001 | 292 | 1% | mega_cruise_5000 |

The five sum to the 37,258 total that A9's fleet target already divides by.

**The two middle bands aggregate to 34,549**, and that aggregate is the unit a
class-cut posting rate has to use: `classic_cruise_1900` straddles the 60,000
edge and admits both, while `spirit_cruise_3000` sits inside the upper one, so
the two hulls cannot be separated on the denominator side. Aggregating them is
not a loss of resolution the source offers — it is the resolution the
hull-to-band mapping permits.

## 2. The label collision that makes this confusing

Jenkins's **"Mega"** is 120,001-140,000 GT. The project's `mega_cruise_5000`
hull is Jenkins's **"Super mega"** (>=140,001), *not* Jenkins's Mega. Any
reader matching the word "mega" across the two will mis-map the hull by a band.

Hulls map to tonnage through the published space-ratio span
(`SPACE_RATIO_SPAN`, 41.7-57.1 GT/pax, from the four ships in
`SPACE_RATIO_ANCHORS` that publish both tonnage and lower berths). Each hull's
declared **passenger** complement therefore becomes a tonnage *interval*, and
every band the interval meets is returned:

This interval mapping replaced an earlier one that picked a single representative ship per hull against its passenger-plus-crew total, which put the classic and spirit hulls one band too high; the ledger's B3 (#29) passage records that repair.

| hull | passengers | GRT interval | bands admitted |
|---|---:|---|---|
| expedition_cruise_450 | 300 | 12,516-17,143 | <=30,000 |
| classic_cruise_1900 | 1,350 | 56,321-77,143 | 30,001-60,000 and 60,001-120,000 |
| spirit_cruise_3000 | 2,100 | 87,610-**120,000** | 60,001-120,000 |
| mega_cruise_5000 | 5,000 | 208,594-285,714 | >=140,001 |

Two edges worth keeping in view. Spirit's upper end is *exactly* 120,000 GT, so
one more ton of space ratio would add the Mega band to it. And the mega hull
starts at 208,594 GT — its own anchor, Oasis class, is 225,282 GT for 5,400
lower berths — so it clears 140,001 with no ambiguity and cannot land in the
917-report band under any admissible ratio.

## 3. Why 120,001-140,000 is empty, on both sides

**On the observed side** it is genuinely sparse, not mis-transcribed. It is a
20,000-GT slice between a 60,000-wide band below it and an unbounded one above,
and 2006-2019 is the period in which 81% of all voyage reports came from the
60,001-120,000 class. Only a thin set of hulls occupied 120-140k (Voyager class
at 138,000 GT sits at its top edge); Grand/Caribbean-class ships fall below it
and Freedom/Oasis-class jump over it. 3% of voyage reports is where shipbuilding
went, not a gap in the record.

**On the model side** `UNMAPPED_GRT_BANDS` returns exactly
`('120,001-140,000',)`. Nothing is scored against it; its rates are transcribed
so that a later reader does not reconstruct them. The four hulls also leave the
whole 120,000-208,594 GT range unoccupied, of which the Mega band is the part
the source names.

## 4. Decision: no hull is being built for that band

Recorded so the question does not get re-opened without new reasons.

What a 120-140k hull would buy is one additional A8 comparator point (Table 2:
passenger 26.7, crew 14.7, total 22.9 per 100,000 travel days) in a band
carrying 3% of voyage reports. It would buy **no** A9 posting target, because
the per-band outbreak numerator is unpublished (§5). Against that it costs a
spatial layout, airflow paths, a complement split, a CONTAM project,
referential-integrity and data-contract work, and a re-baseline of per-hull
scoring.

The decisive argument is that the experiment is not discriminating. The
expedition (450), classic (1,910) and spirit (3,000) posting campaigns
reproduced the same posting shape — too-early posting at 7 days and a
voyage-length gradient several-fold shallower than observed — across a 6.7x
complement range, which located both departures in the transmission chain
rather than in the hull. A fourth complement inside that range is expected to
land on the same curve.

If a hull is added later for mechanistic reasons, the axis that has **not** been
varied is topology — compartmentation, dining and venue structure, crew-to-
passenger ratio — not tonnage. Filling a tonnage band is bookkeeping; varying
topology would be an experiment.

## 5. What is still missing: the per-class numerator

Jenkins Table 3 publishes outbreak counts by voyage length but **not** by GRT
band, which is why `a9_targets()` returns `per_hull: {target: None, reason:
"per-hull outbreak numerator unpublished"}`. That reason is about the
numerator; §1 shows the denominator was never the obstacle.

The project's own posted series (`vsp_outbreak_series.csv`) carries `pax_total`
per posting, so a numerator *can* be derived by pushing each posting's
complement through the same space-ratio mapping. Restricting to the 208
pre-COVID postings dated 2006-2019 — the rows whose window matches the Jenkins
denominator — gives:

| class | postings (clean) | postings (max) | denominator | per 1,000 voyage reports |
|---|---:|---:|---:|---|
| <=30,000 | 9 | 21 | 1,500 | 6.0-14.0 |
| 30,001-120,000 (aggregate) | 109 | 164 | 34,549 | 3.2-4.7 |
| 120,001-140,000 | 0 | 69 | 917 | 0.0-75.2 |
| >=140,001 | 9 | 49 | 292 | 30.8-167.8 |

Fleet comparators on the same denominator: 5.58 per 1,000 posted (208/37,258)
and 4.19 investigated (156/37,258).

The interval is the whole point, and it is wide for a reason: **81 of the 208
postings have a tonnage interval that straddles a class edge**, so they cannot
be assigned. The low column counts only unambiguous assignments (biased down,
because the denominator is still the full band). The high column counts a
straddling posting in *every* class it could belong to (biased up, and it
double-counts). Only the 30,001-120,000 aggregate is narrow enough to be worth
comparing against, at 3.2-4.7 per 1,000.

Three declared caveats attach to any use of this table:

1. **Unit mismatch.** The numerator counts CDC postings; the denominator counts
   unduplicated voyage reports. This is the same mismatch the existing
   fleet-pooled target carries (208/37,258), so the table is exactly as
   licensed as that target and no more.
2. **Assignment ambiguity**, quantified above as the low/high interval.
3. **Complement is not capacity.** `pax_total` is passengers actually onboard
   on the outbreak voyage, which is at or below lower-berth capacity, so the
   mapping runs slightly low in tonnage.

Nothing in this table is adopted as a scored anchor, and no constant is chosen
from it. It is a class-resolved plausibility comparator, recorded so the
class cut is available without implying the source published it.
