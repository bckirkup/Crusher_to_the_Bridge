# Register fragment — six quantities whose governing number is abstract-only (tranche 20)

> **Not merged.** Proposed amendments to `docs/parameter_provenance_register.md`
> §3.1 and §3.3. Not authoritative until the lead merges it. Evidence:
> [`../consensus_tranche_20_full_text_reverification.md`](../consensus_tranche_20_full_text_reverification.md)
> findings **F2**, **F3**, **F5**, **F6**, **F8**, **F11**.

**Status:** Additive fragment, not authoritative until the lead merges it. Evidence: tranche 20.

**Nothing changes but the record of where the number was read.** No constant,
interval, curve entry or grade is moved by this fragment. Each row below is
proposed for an evidence-text annotation and an `Origin` cell; whether an
abstract-only origin should also move a grade is a **separate decision for the
lead**, which the register's axis-3 rule reserves.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| `recovery_day` (§3.1) | unchanged | unchanged | *Annotation:* Atmar 2008's **28-day** shedding median and day-4 peak are body-verified; the **1–2 day illness duration** appeared only in the abstract across 2 attempts. The row's claim that both are measured in the same 16 subjects is not contradicted, but is unverified from the body by this route (**F2**) | Atmar 2008: **Ab** (1–2 d illness) + **R** (28 d) | unchanged | — |
| `shedding_curve_log10` decline shape, GII (§3.1) | unchanged | unchanged | *Annotation:* Sabrià 2016 returned **zero chunks**; the 7.51 → 5.28 log10 GC/g figures behind the ≈0.11 log10/day rate are the abstract's. Tu 2008 and Lai 2013, already rejected as not self-consistent, are also abstract-only. The row's conclusion is unaffected; its evidence base is abstract-only throughout (**F3**) | Sabrià 2016: **Ab**, Tu 2008: **Ab**, Lai 2013: **Ab** | unchanged | — |
| `chronic_shedder_fraction` (`norwalk_gi`) (§3.1) | unchanged | unchanged | *Annotation:* van Beek 2017's chronic **duration** (median 218 d, range 32–1,164) is body-verified in a Results chunk; the **4.6% infected and 23/101 = 22.8% chronic** fractions appeared only in the abstract, and the Results chunks returned other denominators. Davis 2020's infectious-shedding confirmation is body-verified (**F5**) | van Beek 2017: **Ab**, Davis 2020: **R** | unchanged | — |
| `hand_to_surface_drying_multiplier` (§3.1) | unchanged | unchanged | *Annotation:* both papers behind the ~100× lever returned **zero chunks** in 2 attempts each, despite both being open access. The interval [0.008, 1.0] is arithmetic on two abstracts: Tuladhar 2013 "13 ± 16% on the first … 0.1 ± 0.2% [after] 10 min of drying" and Sharps 2012's 59% → <1% (**F6**) | Tuladhar 2013: **Ab**, Sharps 2012: **Ab** | unchanged | — |
| `asymptomatic_shedding_log10` (offset), paediatric community (§3.1) | unchanged | unchanged | *Annotation:* Barreira 2009 reports the two medians (8.39 and 7.15 log10 copies/g) and the p-value; the **1.24-log10 offset is arithmetic on them** and is stated in no retrieved text. Dábilla 2017's 0.79 was **?nr** in 2 attempts (**F8**) | Barreira 2009: **Ab** (offset derived, not reported), Dábilla 2017: **?nr** | unchanged | — |
| `symptomatic_fraction` (§3.3, influenza; **the row this annotation was written against, `illness_probability.eta`/`gamma`, was deleted by R3 and the same 66.9% adopted here instead**) | unchanged | unchanged | *Annotation:* Carrat 2008 returned three body chunks — "Infection and viral shedding", "Clinical illness", "Discussion" — and the governing **66.9% symptomatic** appears in none of them; it is in the abstract. The paper's body is indexed and the relevant section was retrieved, so this is not an access limitation (**F11**) | Carrat 2008: **Ab** | unchanged | — |

## Section-of-origin ledger

| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |
|---|---|---|---|---|---|
| Atmar 2008 | illness duration, days; shedding duration, days | "Norwalk virus challenge duration of illness days symptomatic gastroenteritis 16 volunteers results" (2 phrasings) | chunks; the 1–2 d absent from all | **Ab** (illness) + **R** (28 d) | abstract: "illness … lasted 1–2 days"; body: "peaked at a median of 4 days after inoculation", median peak 95×10⁹ copies/g |
| Sabrià 2016 | decline rate, log10 genome copies/g per day | "norovirus food healthcare workers viral load log10 genome copies per gram decline over 19 days symptomatic asymptomatic" | zero chunks | **Ab** | "starting at 7.51±1.80 … decreasing to 5.28±0.76 log10 genome copies/g after 19 days" |
| van Beek 2017 | chronic fraction, %; shedding duration, days | "solid organ transplant recipients norovirus chronic infection percent median duration of shedding days" | chunks | **Ab** (fractions) + **R** (duration) | body: "median duration of shedding 218 days (range 32–1,164)"; abstract: "101 of 2,182 (4.6%) … 23 of 101 (22.8%)" |
| Tuladhar 2013 | transfer, % immediate and after drying | "murine norovirus infectivity transfer percent finger pad stainless steel results table 40 minutes drying" (2 phrasings) | zero chunks | **Ab** | "13 ± 16% on the first … 0.1 ± 0.2% on the first transfer [after] 10 min of drying … 2.0 ± 2.0%" |
| Sharps 2012 | GII transfer, % genome copies | "human norovirus GII transfer rate percent from finger to stainless steel results table log10 genome copies recovered" (2 phrasings) | zero chunks | **Ab** | abstract carries the transfer percentages |
| Barreira 2009 | symptomatic and asymptomatic load, log10 copies/g | "norovirus viral load symptomatic asymptomatic children log10 copies per gram median difference" | zero chunks | **Ab** | "8.39 and 7.15 log(10) copies/g of fecal specimens for symptomatic and asymptomatic children, respectively (p=0.011)" |
| Dábilla 2017 | offset, log10 | "Dabilla norovirus viral load symptomatic asymptomatic difference log10 genome copies per gram" (2 phrasings) | quantity absent | **?nr** | — |
| Carrat 2008 | symptomatic infection frequency, % | "influenza volunteer challenge studies frequency of symptomatic infection percent shedding duration days TCID50" | chunks; quantity absent from all three | **Ab** | abstract: "the frequency of symptomatic infection was 66.9% (95% confidence interval: 58.3, 74.5)" |
