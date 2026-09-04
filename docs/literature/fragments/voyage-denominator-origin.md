# Register fragment — voyage denominator: the transcription is now confirmed against MMWR body text (tranche 21)

> **Not merged.** Proposed amendment to `docs/parameter_provenance_register.md`
> §3.1, observation-model block, row "External voyage denominator for VSP
> posting rates". Not authoritative until the lead merges it. Evidence:
> [`../consensus_tranche_21_full_text_reverification.md`](../consensus_tranche_21_full_text_reverification.md)
> §3.1 and finding **F7**. Supersedes the access claim in
> [`voyage-denominator.md`](voyage-denominator.md), not its numbers.

**Status:** Additive fragment, not authoritative until the lead merges it. Evidence: tranche 21.

**No count changes.** The register's numbers are reproduced verbatim by the
source's own body text; what changes is that "transcription unverified" no
longer holds, and that the row's origin is `R`, not `Tr`. The denominator
remains **blocked by field** for the reason the register already gives — posted
versus investigated outbreaks, and CDC's two disagreeing voyage units. This
fragment does not unblock it and proposes no posting rate.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| External voyage denominator for VSP posting rates (qualifying voyages per year under VSP jurisdiction, ≥100 pax, 3–21 d) | **absent** — unchanged | **M for 2008–2014; ∅ null elsewhere** — unchanged | *Amendment only:* the Freeland 2016 counts are **no longer transcription-unverified**. The paper's own body text, retrieved as full-text chunks on 2026-09-04, reads: "a total of 32,084 voyages required submission of a VSP report, ranging annually from 4,404 in 2012 to 4,808 in 2014 (Table); among these, 29,107 (90.7%) were voyages of 3–21 days and included >100 passengers", and "73,599,005 passengers … 28,281,361 crew members". Every count the register carries for 2008–2014 is reproduced. The two internal defects the lead found remain: the published per-1,000-voyage rates are still not reproducible from these counts for 5 of 7 years, and the text-versus-table 133/132 disagreement is unaffected — both are properties of the source, not of the transcription. Jenkins 2021's voyage count and travel-day denominator likewise came back in body chunks. Koo 1996: **?nr** after 2 attempts | Koo 1996: **?nr**, Freeland 2016: **R** (MMWR body chunks, chunk-verified 2026-09-04), Jenkins 2021: **R** + Ab | ⊘ **blocked by field** — unchanged | #13 |

## Section-of-origin ledger

| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |
|---|---|---|---|---|---|
| Freeland 2016 | VSP-report voyages per year, count; passengers and crew, count | "cruise ship acute gastroenteritis voyages per year VSP report submission count passengers crew travel days 2008-2014" | chunks | **R** (MMWR body) | "a total of 32,084 voyages required submission of a VSP report, ranging annually from 4,404 in 2012 to 4,808 in 2014 (Table); among these, 29,107 (90.7%) were voyages of 3–21 days and included >100 passengers" |
| Jenkins 2021 | unduplicated voyage reports, count; rate per 10⁷ travel days | "acute gastroenteritis cruise ships unduplicated voyage reports count rate per 10 million travel days 2006-2019" | chunks | **R** + Ab | body chunk carries the voyage count and the travel-day denominator |
| Koo 1996 | qualifying voyages, count | "Koo 1996 cruise ship gastroenteritis outbreaks vessel sanitation program surveillance three percent threshold voyages" (2 phrasings) | not retrieved | **?nr** | — |

**Class consequence.** Tranche 18 §4 places CDC/MMWR material in the
"not in any literature index at any subscription price" class. That is correct
for the **VSP posting archive** and for the DHS/industry occupancy reports, and
**wrong for MMWR articles**, which are chunk-indexed. The register's `Tr` code
should not be applied to MMWR.
