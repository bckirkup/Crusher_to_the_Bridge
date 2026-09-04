# Register fragment — four rows whose citations did not resolve, and one candidate transcription defect (tranche 21)

> **Not merged.** Proposed amendments to `docs/parameter_provenance_register.md`
> §3.1 and §3.2. Not authoritative until the lead merges it. Evidence:
> [`../consensus_tranche_21_full_text_reverification.md`](../consensus_tranche_21_full_text_reverification.md)
> findings **F1**, **F4**, **F9**, **F10**.

**Status:** Additive fragment, not authoritative until the lead merges it. Evidence: tranche 21.

**No value is corrected here.** F1 in particular is reported as a **candidate**
defect and deliberately not fixed: the deciding table row was not retrieved, so
correcting the number would be substituting arithmetic for evidence.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| Emesis cumulative shed, GII.2 (§3.1) | unchanged | unchanged | *Finding, no change proposed:* the register records Kirby 2016 Table 3 GII.2 = **1.8e7 GEC (SEM 1.8e7)** against GI.1 2.3e8. Kirby's **Results prose** reads "the cumulative virus shedding per subject was high (1.8×10⁸ GEC +/- 7.8×10⁷, Norwalk and Snow Mountain viruses only)" and says the two genogroups' cumulative titres were **similar**; the retrieved Table 3 **All-GI** row is 2.3×10⁸ (SEM 1.0×10⁸). 1.8e7 is ~13× below GI — inconsistent with "similar" — and exactly 10× below the pooled 1.8e8 whose SEM digits it shares. The **GII.2 Table 3 row was ?nr in 2 attempts**, one naming the table and genogroup, so this is a candidate transcription defect only. If it holds, the row's own check — a log-uniform on [1e5, 1e8] having mean 1.45e7, "within 1.25× of the measured 1.8e7" — loses its basis (**F1**) | Kirby 2016: **R** + **T3 partial** (All-GI retrieved, GII.2 **?nr**) + **Me** (1 g of emesis treated as 1 ml) | unchanged | — |
| `immunocompromised_fraction` (§3.1 and the shared §3.2 row) | unchanged | unchanged | *Annotation:* **both endpoints of [0.02, 0.074] are unretrieved.** Lopez-Gigosos 2020 (2.0%) did not surface with body chunks in 2 attempts; Martinson 2024 (6.6% in 2021, 7.4% in 2022) returned zero chunks in 2 attempts. Only Harpaz 2016's 2.7% is body-verified — "an estimated 2.7% of US adults self-reported that they were immunosuppressed" (Discussion). The row's own statement that the width is population and era rather than uncertainty is unaffected (**F4**) | Martinson 2024: **?nr**, Lopez-Gigosos 2020: **?nr**, Harpaz 2016: **R** | unchanged | — |
| `never_symptomatic_fraction` (§3.1) | unchanged | unchanged | *Annotation:* the challenge-design interval [0.22, 0.36] rests on a mixture of origins. **Body-verified:** Atmar 2014 (Results, both HID50 stratifications and the infected-illness split) and Frenck 2012 (Discussion and susceptibility chunks). **Abstract-only:** Gray 1994 (zero chunks, 2 attempts), Baker 2026 (zero chunks), Qi 2018 (highlights). **Rouphael 2022's "Table 1" attribution — 44 adults, 90% infection and 70% illness at the highest dose — was not reached in 2 attempts** and is abstract-sourced as it stands (**F9**). Wang 2023 is body-verified. Corroborators not re-queried in this pass: Cannon, El-Heneidy, Lopman, Miura, Newman, Qu, Teunis | Gray 1994: **Ab**, Rouphael 2022: **Ab** (Table 1 **?nr**), Baker 2026: **Ab**, Qi 2018: **Ab**, Atmar 2014: **R**, Frenck 2012: **R**, Wang 2023: **R** | unchanged | — |
| `incubation` (3 fields, §3.2 SARS-CoV-2) | unchanged | unchanged | *Finding:* the row cites "Wei 2021, ancestral" for lognormal median **5.8 d, GSD 1.57**. The **GSD was ?nr in 2 attempts**, and 5.8 d matched only in a same-topic COVID incubation meta-analysis whose identity with the cited paper could not be established from the record retrieved. The row is already flagged "wrong for Omicron"; this adds that its provenance string does not currently resolve to a verified paper. **No value change is proposed** — the citation needs resolving first (**F10**) | Wei 2021: **?nr**, identity unconfirmed | unchanged | — |

## Section-of-origin ledger

| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |
|---|---|---|---|---|---|
| Kirby 2016 | cumulative emesis shed, GEC; emesis titre, GEC/ml | "Kirby vomiting norovirus challenge Table 3 cumulative shedding per subject in emesis Snow Mountain GII.2 genome equivalent copies GEC" (2 phrasings) | chunks; the GII.2 table row absent | **R** + **T3 partial** + **Me** | Results: "the cumulative virus shedding per subject was high (1.8×10⁸ GEC +/- 7.8×10⁷, Norwalk and Snow Mountain viruses only)"; Table 3 All-GI 2.3×10⁸ (SEM 1.0×10⁸); Methods: emesis weighed, 1 g treated as 1 ml |
| Harpaz 2016 | immunosuppressed adults, % | "prevalence of immunosuppression among US adults percent National Health Interview Survey 2013" | chunks | **R** | "an estimated 2.7% of US adults self-reported that they were immunosuppressed" |
| Martinson 2024 | immunosuppressed adults, % | "prevalence of immunosuppression among United States adults 2021 2022 percent survey increase" (2 phrasings) | zero chunks | **?nr** | — |
| Lopez-Gigosos 2020 | immunosuppressed travellers, % | "immunosuppressed international travellers prevalence percent travel clinic cohort" (2 phrasings) | not surfaced | **?nr** | — |
| Atmar 2014 | HID50, RT-PCR units; illness among infected, % | "norovirus human infectious dose HID50 RT-PCR units secretor positive Norwalk GI.1 challenge genome equivalents" | chunks (paywalled) | **R** + Ab | "3.3 RT-PCR units … for secretor-positive blood group O and A participants"; "7.0 RT-PCR units … for all secretor-positive participants" |
| Frenck 2012 | GII.4 infection and illness, % | "GII.4 norovirus challenge secretor status infection illness percent volunteers" | chunks | **R** | Discussion and susceptibility chunks |
| Gray 1994 | symptomatic share of infected | "Norwalk virus specific antibodies volunteers challenged IgM IgA IgG symptomatic asymptomatic 17 volunteers" (2 phrasings) | zero chunks | **Ab** | — |
| Wei 2021 | incubation median, days; GSD | "COVID-19 incubation period lognormal median 5.8 days geometric standard deviation ancestral strain meta-analysis" (2 phrasings) | chunks from same-topic papers; identity unconfirmed | **?nr** | — |
