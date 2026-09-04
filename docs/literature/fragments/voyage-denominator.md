# Register fragment — external voyage denominator for VSP posting rates (tranche 18)

> **Merged.** This fragment was merged into [`../../parameter_provenance_register.md`](../../parameter_provenance_register.md) by the sourcing-wave-1 integration pass, with the lead's corrections applied at merge time. It is kept as the audit trail of what the sourcing unit proposed; it is **not** a live proposal, and where it and the register differ the register holds the status.
>
> **The grade below was corrected at merge and must not be quoted from here.** The Freeland 2016 counts are claimed as Grade **A** below; the register carries **Grade M, transcription unverified**, because the sourcing unit transcribed the table from a source it could not re-open (cdc.gov returned 403, no PMC copy), the paper's own published per-1,000-voyage rates are not reproducible from those counts for 5 of 7 years, and its text says 133 where its table says 132. The denominator remains **blocked** either way and no posting rate may be computed from these counts until the primary is re-read.

**Status:** Merged row for `docs/parameter_provenance_register.md` §3.1
(observation-model block); kept as the audit trail. Evidence
in [`consensus_tranche_18_voyage_denominator.md`](../consensus_tranche_18_voyage_denominator.md).

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| External voyage denominator for VSP posting rates (qualifying voyages per year under VSP jurisdiction, ≥100 pax, 3–21 d) | **absent** — the series holds posted outbreaks only; anchors A4/A8/A9 use class-level MIDRS aggregates | **M for 2008–2014; ∅ null for 2004–2007, 2015–2019, 2022–2026** | Freeland 2016 (MMWR 65(1), DOI 10.15585/mmwr.mm6501a1, Table): VSP-report voyages per year **4,404–4,808** (2008–2014; Σ 32,084), of which 3–21 d and >100 pax **3,964–4,387** per year (Σ 29,107); 73.6 M passengers and 28.3 M crew over the seven years; travel-days recoverable only by back-calculation from the published per-10⁷-travel-day rates. Jenkins 2021 (MMWR SS 70(6), DOI 10.15585/mmwr.ss7006a1): **37,258** unduplicated voyage reports and ~127 M passengers, 2006–2019, as a single total — **not year-resolved**, and not reconcilable with Freeland's annual counts in the same unit (29,107 of 37,258 would fall in 7 of the 14 years). Koo 1996 (JAMA, DOI 10.1001/jama.1996.03530310051032) documents the construction (passengers × cruise length from routine 24-h reports) for 1989–1993 only. MARAD/BTS US-departure cruises 2004–2011 (4,126–4,498/yr) and BREA/CLIA embarkations (9.7–13.8 M, 2010–2019) are **measured / estimated in a different population** (US departures incl. domestic; no ≥13-pax or foreign-itinerary filter) and are excluded as denominators; CLIA global volumes are part projection. Grade **A** for 2008–2014, **none** elsewhere | not recorded — proposed before axis 3 existed; see [tranche 21](../consensus_tranche_21_full_text_reverification.md) §1 | ⊘ **blocked by field** — the numerator is *posted* outbreaks (91 rows 2008–2014; 208 rows 2006–2019) while every CDC denominator pairs with *investigated* outbreaks (132; 156), and CDC's two voyage units disagree; a posting rate is computable for 2008–2014 only after declaring the voyage unit, and for no other year without an annual MIDRS extract from CDC VSP | #13 |

## Section-of-origin ledger

Not recorded: this fragment predates the register's section-of-origin axis. The
retrieval ledger covering its citations is
[tranche 21](../consensus_tranche_21_full_text_reverification.md) §1.
