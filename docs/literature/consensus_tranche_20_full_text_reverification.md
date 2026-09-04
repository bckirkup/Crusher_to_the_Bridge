# Tranche 20 — re-verification with full-text chunks: what the register's citations actually say, and where the number was read

**Relation to tranche 19.** Tranche 19 (influenza biphasic surface) reached the
same methodological conclusion independently and from the other end: full text
overturned an abstract-level null, and the quantities it wanted sat in a Results
table absent from the abstract. Neither tranche supersedes the other — 19
establishes that the null was false for one row, this one establishes how far
that generalises across every cited row, and both feed the same skill correction.

**Register rows fed / supersession.** This tranche feeds the evidence-bearing register rows reverified in §1; its four proposed evidence/origin amendments are listed in `fragments/`. No tranche-20 finding is withdrawn; finding F7 supersedes tranche 18's former access claim, and tranche 16's Teunis-2015 explanation is superseded as stated there.

**Status:** Evidence assembled. **No epidemiological constant, profile value,
curve entry, engine default, anchor target or test expectation changes in this
document, and none changed in the change that carries it.** Nothing here is
authoritative about the model; the authoritative per-quantity status is
[`docs/parameter_provenance_register.md`](../parameter_provenance_register.md).
The register rows this tranche feeds are listed in §0.2; the amendments it
proposes to those rows' *evidence text* are in
[`fragments/`](fragments/) as four unadopted fragments, which the lead merges.
Every dose figure in this repository remains void pending refit
([`docs/norovirus/norovirus_open_ledger.md`](../norovirus/norovirus_open_ledger.md)
§1); the ID50s quoted below are the **sources' own published figures**,
reproduced as evidence about those sources, and no model dose figure is quoted,
proposed or implied.

**Scope.** Every register row whose Evidence column names a citation, re-queried
against the Consensus `search` tool with `include_full_text_chunks=true`, with
the quantity **and its unit** named in the query string. The output is the
register's new third axis — section of origin (§1 of the register) — populated
by retrieval rather than by memory, plus the findings in §2 and the
access-reopening results in §3.

---

## 0. Method, and the two things it cannot do

### 0.1 What was run

118 queries in four waves (25 priority, 58 sweep, 45 identity/retry, 15 targeted
retry), each with `include_full_text_chunks=true`, `page_size=3`, and the target
quantity plus its unit in the query terms — `copies/g of stool`, `GEC/ml`,
`log10 per day`, `genome copies per day`, `RT-PCR units`, `% transfer`,
`copies/m³`, `half-life in hours`. Papers that did not surface, or whose target
quantity did not appear in the chunks returned, were re-queried by title and
then by the table or figure the register names. A quantity is recorded `?nr`
(**not retrieved**) only after **at least two** differently-phrased attempts.

**Two things chunk retrieval cannot do, and neither is a null result.** Chunks
are *query-relevant excerpts*, not the paper: absence of a number from the
chunks returned is not evidence that the paper omits it. And a paper that
returns zero chunks has not been shown to be inaccessible — only that this route
did not reach its body. `?nr` therefore means "this route did not retrieve it",
never "the literature does not contain it". Nothing in §2 or §3 is stated as a
null result on the strength of a `?nr`.

### 0.2 Register rows fed by this tranche

Every cited row of §3.1 (norovirus), §3.2 (SARS-CoV-2) and §3.3 (influenza)
carries an `Origin` cell written from this pass — 63 cited rows in total. The
rows whose *evidence text* this tranche proposes to amend, through the
fragments, are: the voyage denominator; `dose_response.alpha`/`beta` (GII
interval); `recovery_day`; `chronic_shedder_fraction`;
`hand_to_surface_drying_multiplier`; the two `asymptomatic_shedding_log10`
offset rows; `shedding_curve_log10` decline shape; the two non-porous transfer
fractions; `never_symptomatic_fraction`; and influenza
`illness_probability.eta`/`gamma` — which R3 deleted between this pass and the
merge, its 66.9% moving to `symptomatic_fraction`, so that annotation now reads
against the replacement row (F11). No fragment is adopted here.

### 0.3 The fan-out conclusion this pass contradicts

The sourcing fan-out concluded that **the binding constraint was full-text
access, not search**. That is now shown to be wrong for a substantial minority
of the register and right for a different reason than it claimed:

- **Paywall status did not predict retrieval.** Atmar 2014 (*J Infect Dis*,
  paywalled) returned its Results including both HID50 stratifications;
  open-access Sharps 2012 and Tuladhar 2013 returned no chunks at all across two
  attempts each.
- **What predicts retrieval is whether the body is indexed as chunks**, and that
  is a property of the record, not of the subscription.
- **The constraint that actually binds** is that a quantity can be
  chunk-retrievable while the specific stratum the register needs is not: the
  All-GI aggregate row of Kirby 2016 Table 3 came back; the GII.2 row of the same
  table did not, twice (§2, F1).

---

## 1. Origin, per governing citation

The register's `Origin` column is the summary; this is the ledger it summarises.
Codes are the register §1 set: `R` Results prose, `Tn` Table *n*, `Fn·dig`
figure digitized, `Me` Methods, `Ab` abstract only, `Sec` secondary, `Tr`
transcribed, `?nr` not retrieved. Only governing citations appear — corroborators
not re-queried in this pass are marked as such in the register cell rather than
silently classed.

| Citation | Quantity + unit, as queried | Retrieval | Origin | Verbatim locator |
|---|---|---|---|---|
| Kirby 2016 | GII.2 emesis titre, GEC/ml; cumulative emesis shed, GEC | chunks | **R** + **T3 partial** + **Me** | "the cumulative virus shedding per subject was high (1.8×10⁸ GEC +/- 7.8×10⁷, Norwalk and Snow Mountain viruses only)"; Methods: emesis weighed, 1 g treated as 1 ml |
| Atmar 2014 | Norwalk HID50, RT-PCR units | chunks (paywalled) | **R** + Ab | "3.3 RT-PCR units … for secretor-positive blood group O and A participants" and "7.0 RT-PCR units … for all secretor-positive participants" |
| Atmar 2008 | peak faecal load, genomic copies/g; shedding duration, days; illness duration, days | chunks | **R** (peak, 28 d) + **Ab** (1–2 d illness) | "peaked at a median of 4 days after inoculation"; median peak 95×10⁹ copies/g, range 0.5–1,640×10⁹ |
| Teunis 2008 | ID50, genome equivalents; aggregate size, particles per aggregate | **not retrieved** (3 attempts) | **?nr** | — |
| Teunis 2020 | per-genogroup infectivity ratio, per aggregate | not retrieved (2 attempts) | **?nr** — chunks returned only the electronic appendix and R code | — |
| Guix 2020 | illness ID50, genome copies/day | chunks | **R** (+ **Sec** for the volunteer range it cites) | "2,934 (95% CI 1,683–5,044) genome copies/day for norovirus GII"; and, citing others, "range from 18 (95% CI 1–4,350) … to 2,800 (95% CI, 290–25,000) genome equivalents" |
| Rouphael 2022 | GII.2 ID50, GEC; Table 1 attack rates | abstract only (2 attempts) | **Ab** | abstract: "median infectious dose (ID50) … 5.1×10⁵ GEC" |
| Kambhampati 2015 | secretor:non-secretor odds ratio | chunks | **Sec** + **R** | "secretors were 9.9 times more frequently infected with GII.4 … 2.2 times … non-GII.4" |
| Teunis 2014 | peak load, /g faeces; duration, days | chunks | **R** | Summary: "average peak levels ranged from 10⁵–10⁹/g faeces … duration 8–60 days" |
| Teunis 2015 | symptomatic/asymptomatic medians, log10 gc/wet g | chunks returned; quantity absent | **?nr** | — |
| Kirby 2014 | GII.2 stool load, log10 copies/g; day of peak | not retrieved (2 attempts) | **F·dig** + **?nr** | — |
| Cheng 2021 | shedding cessation, day | chunks | **R** | "most viral shedding in feces had ceased by day 15 (Fig. 1)" |
| Ge 2023 | time to peak, days | chunks | **R** + Ab | "the time of virus peak decreased from 2.3 (95% CrI 2–2.8) to 1.5 (95% CrI 1.3–1.8) days" |
| Costantini 2015 | prolonged shedding, % ≥21 days | chunks | **R** + Ab | "prolonged shedding of ≥21 days in 16 of 35 (47%)" |
| van Beek 2017 | chronic shedding duration, days; chronic fraction, % | chunks | **R** (218 d) + **Ab** (4.6%, 22.8%) | "median duration of shedding 218 days (range 32–1,164)" |
| Davis 2020 | infectious shedding duration, days | chunks | **R** | ">418 days" of infectious virus in chronic paediatric cases |
| Chaimongkol 2024 | chronic load, copies/g | chunks | **R** | body chunk, copies/g of stool in chronic immunocompromised shedders |
| Harpaz 2016 | immunosuppressed adults, % | chunks | **R** | "an estimated 2.7% of US adults self-reported that they were immunosuppressed" |
| Martinson 2024 | immunosuppressed adults, % (2021, 2022) | not retrieved (2 attempts) | **?nr** | — |
| Lopez-Gigosos 2020 | immunosuppressed travellers, % | not retrieved (2 attempts) | **?nr** | — |
| Freeland 2016 | VSP-report voyages per year, count | chunks | **R** (MMWR body) | "a total of 32,084 voyages required submission of a VSP report, ranging annually from 4,404 in 2012 to 4,808 in 2014 (Table); among these, 29,107 (90.7%) were voyages of 3–21 days and included >100 passengers" |
| Jenkins 2021 | unduplicated voyages, count; rate per 10⁷ travel days | chunks | **R** + Ab | body chunk carries the voyage count and the travel-day denominator |
| Koo 1996 | qualifying voyages, count | not retrieved (2 attempts) | **?nr** | — |
| Tung-Thompson 2015 | aerosolised fraction, % of total virus | chunks; the range retrieved on the third attempt, phrased as the paper phrases it (**corrected** from `?nr`, see F12) | **R** | "The amount of MS2 aerosolized as a percent of total virus 'vomited' ranged from a low of 7.2 x 10−5 ± 0.00006 to a high of 2.67 x 10−2 ± 0.03 (Table 2)" |
| Booth & Frost 2019 | vomitus volume, ml per episode | quantity absent (2 attempts) | **?nr** | — |
| Zargar 2025 | FCV airborne decay, log10 PFU/m³/min | abstract only | **Ab** | "rates of biological decay of HCoV-OC43, RV-14 and FCV were … 0.0081 ± 0.0031 (as log10 PFU/m³/min)" |
| van Doremalen 2020 | aerosol half-life, hours | abstract only (2 attempts) | **Ab** | — |
| Purhonen 2024 | aerosol infectivity | chunks | **R** + Ab | body chunks on aerosolised infectivity |
| Boles 2021 / Bonifait 2015 / Kittigul 2025 / Rupprom 2024 | airborne norovirus, copies/m³ | chunks | **R** (+ Ab) | body chunks carry copies/m³ |
| Alsved 2019 | airborne norovirus, copies/m³ | abstract | **Ab** | — |
| Sharps 2012 | GII fingertip→steel transfer, % | not retrieved (2 attempts) | **Ab** | abstract only |
| Tuladhar 2013 | MNV-1 transfer, % immediate and dried | not retrieved (2 attempts) | **Ab** | abstract: "13 ± 16% on the first … 0.1 ± 0.2% [after] 10 min of drying … 2.0 ± 2.0%" |
| Lopez 2013 | transfer efficiency, % | chunks | **R** | Results chunk carries transfer percentages |
| Bidawid 2004 / Ansari 1988 / Grove 2015 / Julian 2010 | transfer, % | abstract; zero chunks | **Ab** | — |
| Wikswo 2011 | cabin/household share, % | chunks; the split absent | **R** partial | transmission-mode sections returned |
| Tsang 2018 | household transmission, % | chunks | **R** + Ab | — |
| Chimonas 2008 | cabinmate secondary risk, % | abstract (2 attempts) | **Ab** | — |
| Matsuyama 2018 | cabin attack rate, % | not retrieved (2 attempts) | **?nr** | — |
| Kobayashi 2021 | asymptomatic prevalence, % | abstract chunk only | **Ab** | "112 (2.5%, GI 57, GII 54, GI+GII 1) were norovirus-positive" |
| Qi 2018 | pooled asymptomatic prevalence, % | highlights/abstract | **Ab** (**Sec** by design) | "Global prevalence of asymptomatic norovirus infection is about 7%" |
| Wang 2023 | pooled asymptomatic prevalence, % | chunks | **Sec** + **R** | — |
| Jeong 2021 | food-handler prevalence, % | not retrieved | **?nr** | — |
| Barreira 2009 | symptomatic vs asymptomatic load, log10 copies/g | abstract | **Ab** | "8.39 and 7.15 log(10) copies/g … (p=0.011)" |
| Dábilla 2017 | offset, log10 | quantity absent (2 attempts) | **?nr** | — |
| Sabrià 2016 / Tu 2008 / Lai 2013 | decline rate, log10 per day | abstract; zero chunks | **Ab** | Sabrià abstract: "7.51±1.80 … decreasing to 5.28±0.76 log10 genome copies/g after 19 days" |
| Ozawa 2007 / He 2017 / Aoki 2010 / Lee 2007 | GII load, copies/g | abstract or not surfaced | **Ab** / **?nr** | — |
| Gray 1994 | symptomatic fraction of infected | not retrieved (2 attempts) | **Ab** | — |
| Baker 2026 | symptomatic share, % | zero chunks | **Ab** | — |
| Frenck 2012 | GII.4 infection/illness, % | chunks | **R** | Discussion and susceptibility chunks |
| Green 2014 | persistence mechanism | abstract | **Ab** | — |
| Lee 2013 | incubation, hours | chunks | **Sec** + **R** | body chunks of the systematic review |
| Wei 2021 | incubation GSD | not retrieved (2 attempts); identity unconfirmed | **?nr** | — |
| He 2020 | presymptomatic interval, days | chunks; the 44% absent | **R** + **?nr** | Summary/Discussion chunks |
| Schuit 2020 | airborne half-life | chunks | **R** | half-life in body chunk |
| Xu 2023 | surface half-life, hours | chunks | **R** + Ab | — |
| Keske 2023 | viable shedding duration, days | chunks | **R** | median culture-positive duration in body chunks |
| Coleman 2021 | emission, copies per minute | chunks; per-minute rate absent | **R** + **?nr** | Results chunk |
| Zheng 2022 | emission, copies per hour | chunks (Discussion); rate in abstract | **Ab** + **R** | — |
| Lin 2022 / Despres 2022 / Puhach 2022 | copies per infectious unit | chunks; the ratio absent | **R** partial + **?nr** | — |
| Schijven 2020 | emission, copies per hour | chunks; value absent | **Ab** + **R** partial | — |
| Buitrago-García 2020 | asymptomatic fraction, % | chunks | **Sec** + **R** | — |
| Lessler 2009 | incubation, days | chunks; the 1.4 d figure in abstract | **Ab** + **R** | — |
| Ip 2017 | presymptomatic shedding, days | zero chunks (2 attempts) | **Ab** | — |
| Carrat 2008 | symptomatic fraction, % | chunks returned; 66.9% absent from all of them | **Ab** | abstract: "the frequency of symptomatic infection was 66.9% (95% CI 58.3, 74.5)" |
| Alford 1966 | infectious dose, TCID50 | zero chunks (2 attempts) | **Ab** | — |
| Memoli 2015 | challenge dose, TCID50 | chunks | **R** | Discussion + validation chunks |
| Yan 2017 | emission, copies per 30 min | chunks; the figure absent | **R** + **?nr** | fine-aerosol infectious-virus chunks |
| Greatorex 2011 / Qian 2023 | surface and aerosol persistence, hours | chunks | **R** | — |
| Thompson 2017 / Perry 2016 | surface persistence, hours | zero chunks (2 attempts each) | **Ab** | — |
| Kormuth 2018 | aerosol half-life | chunks; half-life absent | **Ab** + **R** | — |

---

## 2. Findings — where re-verification contradicts the register or a tranche

Each is a **finding**, not a fix. No constant, interval, curve entry or test
expectation is changed by this document.

**F1 — Kirby 2016's GII.2 cumulative emesis shed looks like a transcription
defect, and the row's own consistency check depends on it.** §3.1 records
"Kirby 2016 Table 3 … GII.2 Snow Mountain 1.8e7 GEC (SEM 1.8e7), GI.1 2.3e8".
Kirby's Results prose says the cumulative shedding per subject was 1.8×10⁸ GEC
± 7.8×10⁷ for "Norwalk and Snow Mountain viruses only" and that the two were
**similar**; the Table 3 All-GI row retrieved is 2.3×10⁸ (SEM 1.0×10⁸). A GII.2
value of 1.8e7 is ~13× below GI — inconsistent with "similar" — and is exactly
10× below the pooled 1.8e8 whose SEM digits it shares. The GII.2 Table 3 row
itself was **?nr** in two attempts, so this is a candidate defect, not a settled
one. If it holds, the row's justification that a log-uniform on [1e5, 1e8] has
mean 1.45e7 "within 1.25× of the measured 1.8e7" loses its check. **The same
query confirmed the titre row is right**: Results give GII.2 1.6×10⁵ GEC/ml
against the abstract's pooled 3.9×10⁴, which is the defect the register already
records.

**F2 — `recovery_day`'s illness duration is abstract-only.** The row states
"Atmar 2008 measures both in the same 16 subjects: symptomatic illness 1–2 days,
faecal RT-PCR shedding median 28 days". The 28-day median and the day-4 peak
came back in Results chunks; the 1–2 day illness duration appeared **only in the
abstract**, across two attempts. The claim that both are measured in the same 16
subjects is not contradicted — it is unverified from the body by this route.

**F3 — the only GII decline rate with unambiguous units is abstract-only.**
§3.1's decline-shape row rests on Sabrià 2016's ≈0.11 log10/day, derived from
7.51 → 5.28 log10 GC/g over 19 d. Sabrià returned **zero chunks**; the figures
are the abstract's. Tu 2008 and Lai 2013, which the row already rejects as
not self-consistent, are also abstract-only. The row's conclusion stands; its
evidence base is one grade weaker than the row reads.

**F4 — both upper endpoints of `immunocompromised_fraction` are unretrieved.**
The interval [0.02, 0.074] is Lopez-Gigosos 2020 (2.0%) to Martinson 2024
(7.4%). Neither paper surfaced with body chunks in two attempts each; only
Harpaz 2016's 2.7% is body-verified ("an estimated 2.7% of US adults
self-reported that they were immunosuppressed", Discussion). Affects §3.1 and
the shared §3.2 row identically.

**F5 — `chronic_shedder_fraction`'s 23/101 = 22.8% is abstract-only.** van Beek
2017's chronic *duration* (218 d, 32–1,164) is body-verified in a Results chunk;
the 4.6% infected and 22.8% chronic fractions appeared only in the abstract, and
the Results chunks returned different denominators. The row presents 22.8% as a
measured fraction; that reading is not body-confirmed by this route.

**F6 — the ~100× drying lever is entirely abstract-only.**
`hand_to_surface_drying_multiplier` rests on Tuladhar 2013 (13% → 0.1%) and
Sharps 2012 (59% → <1%). Both papers returned **zero chunks** in two attempts
each, despite both being open access. The interval [0.008, 1.0] is arithmetic on
two abstracts.

**F7 — the voyage denominator is no longer a transcription.** Tranche 18 records
the VSP voyage counts as transcribed from CDC/MMWR documents, with the
Results unreachable. Freeland 2016's **body** returned them: "a total of 32,084
voyages required submission of a VSP report, ranging annually from 4,404 in 2012
to 4,808 in 2014 (Table); among these, 29,107 (90.7%) were voyages of 3–21 days
and included >100 passengers". Jenkins 2021's voyage count and travel-day
denominator likewise came back in body chunks. The **numbers are unchanged** —
this changes their origin from `Tr` to `R`, and it means MMWR is chunk-indexed,
which the access class in tranche 18 §4 assumes it is not.

**F8 — the paediatric offset's 1.24 log10 is arithmetic, not a reported
quantity.** §3.1's second `asymptomatic_shedding_log10` row reads "8.39 vs 7.15
log10 copies/g, a 1.24-log10 offset (p = 0.011)". Barreira 2009 reports the two
medians and the p-value; the difference is computed here, and is stated in no
retrieved text. Dábilla 2017's 0.79 was **?nr** in two attempts.

**F9 — Rouphael 2022's "Table 1" attribution is unverified.** §3.1 and tranche
11 attribute to Rouphael 2022 Table 1: "44 adults, infection in 90% and illness
in 70% at the highest dose, ID50 5.1×10⁵ GEC". Rouphael returned **zero
chunks** in two attempts; the ID50 and the cohort size are in the abstract. The
figures are not contradicted, but nothing in this pass reached Table 1, and the
row's α-interval lower endpoint (0.072) is derived from an abstract-only ID50.

**F10 — the SARS-CoV-2 incubation citation cannot be confirmed.** §3.2's
`incubation` row cites "Wei 2021, ancestral" for lognormal 5.8 d, GSD 1.57. The
GSD was **?nr** in two attempts, and 5.8 d matched only in a same-topic COVID
incubation meta-analysis whose identity with the cited paper could not be
established from the record. The row is already flagged "wrong for Omicron";
this adds that its provenance string does not resolve to a verified paper.

**F11 — influenza's symptomatic fraction is abstract-only despite a body
hit.** §3.3's `illness_probability` row cites Carrat 2008's 66.9%. Carrat
returned three body chunks — "Infection and viral shedding", "Clinical
illness", "Discussion" — and 66.9% appears in **none** of them; it is in the
abstract. This is the clearest case of the pattern the axis exists to catch: a
paper whose body is retrievable, whose relevant section is retrievable, and
whose governing number is still only in the abstract.

F11 landed on a moving row. Between this re-verification and the merge, R3
deleted the influenza `illness_probability` η/γ pair and adopted the same 66.9%
(CI 0.583–0.745) as a dose-independent `symptomatic_fraction`, on a row that
reads "verified in Carrat's Results". The two readings are not symmetrical
evidence: R3's rests on the opened paper, F11's on retrieval, and a `?nr` cannot
refute an opened PDF. What F11 establishes is narrower and still worth carrying
on the row — the number is **not reproducible from chunk retrieval**, so any
later re-check of this constant has to open the paper rather than re-query it.
The origin cell records `Ab` plus that qualification; nothing about the adopted
0.669 is contested here.

**F12 — one of this tranche's own ledger rows was wrong, and re-query fixed
it.** §1 recorded Tung-Thompson 2015's aerosolised-fraction *range* as `?nr`
after two attempts, which is exactly the state that must never be read as
absence. Re-queried on 2026-09-04 as "percent of total virus vomited", the
Results prose came back carrying it verbatim: "The amount of MS2 aerosolized as
a percent of total virus 'vomited' ranged from a low of 7.2 x 10−5 ± 0.00006 to
a high of 2.67 x 10−2 ± 0.03 (Table 2)". The origin is **R**, not `?nr`, and the
ledger row is corrected in place. This is the ledger's own demonstration of the
rule: two phrasings are a floor, not a guarantee, and the phrasing that worked
was the paper's, not the register's.

**No finding contradicted a shipped value in a way that would move it**, and
none is proposed for adoption here.

---

## 3. Access reopening — what resolved, what did not, and what class it is in

### 3.1 Resolved by chunks (previously blocked, downgraded or transcribed)

| Quantity / row | Previous status | Now |
|---|---|---|
| VSP voyage denominator | transcribed from CDC/MMWR documents (T18) | **R** — MMWR body chunks (F7) |
| Norwalk HID50, both stratifications | paywalled, abstract-only | **R** — Atmar 2014 Results |
| GII illness ID50, genome copies/day | cited as an outbreak reconstruction | **R** — Guix 2020 body, plus its own **Sec** restatement of the 18–2,800 GEC volunteer range |
| GII chronic shedding duration | abstract | **R** — van Beek 2017 Results |
| Infectious (not RNA) chronic shedding | abstract | **R** — Davis 2020 body |
| GII prolonged shedding ≥21 d | abstract | **R** — Costantini 2015 body |
| GII shedding cessation day | abstract | **R** — Cheng 2021 body |
| Secretor odds ratios by genotype | abstract | **R** — Kambhampati 2015 body |
| Immunosuppressed US adult prevalence, 2013 | abstract | **R** — Harpaz 2016 Discussion |
| Peak faecal load and duration, GI.1 challenge | abstract | **R** — Atmar 2008 Results |
| Time to peak, fitted | abstract | **R** — Ge 2023 body |
| Airborne norovirus copies/m³ (four papers) | abstract | **R** — body chunks |
| Influenza and SARS-CoV-2 persistence half-lives (Greatorex, Qian, Schuit, Xu) | abstract | **R** — body chunks |

### 3.2 Not reopened by this route (`?nr` or abstract-only after ≥2 attempts)

**Journal articles whose bodies this route did not reach** — no claim about
their accessibility by other means: Teunis 2008 (3 attempts, including the table
by number — this is the paper the shipped dose-response pair derives from, and
its aggregation parameter remains the register's open question), Teunis 2020
(chunks returned only its electronic appendix and R code, so the withdrawn 3.7×
genogroup ratio could not be re-examined), Kirby 2014 (the GII shedding-peak and
day-of-peak source; the digitized figure values remain the only route to it),
Rouphael 2022, Sharps 2012, Tuladhar 2013, Thompson 2017, Perry 2016, Alford
1966, Ip 2017, van Doremalen 2020, Sabrià 2016, Tu 2008, Lai 2013, Gray 1994,
Baker 2026, Aoki 2010, Zargar 2025, Green 2014, Barreira 2009, He 2017, Ozawa
2007, Kobayashi 2021, Chimonas 2008, Matsuyama 2018, Jeong 2021, Dábilla 2017,
Huynen 2013, Lee 2007, Lee 2021, Martinson 2024, Lopez-Gigosos 2020, Koo 1996,
Wei 2021 (identity unresolved), Booth & Frost 2019.

**Sources that are not journal articles at all**, and are in no literature index
at any subscription price — they are reachable only as documents, and belong to a
separate class from everything above:

- **CDC VSP posting archive** (the outbreak numerator series) — a web posting
  archive, not a publication.
- **CDC/MMWR reports** — `Tr` was the right class for the *posting archive*, but
  **not** for MMWR articles, which this pass shows are chunk-indexed (F7).
  Freeland 2016 and Jenkins 2021 move out of this class.
- **DHS and industry occupancy/voyage reports** cited in tranche 18 — no index,
  no DOI, no chunks.

The register's `Tr` code covers this class, and the correction F7 makes is that
it was over-applied: MMWR is literature for retrieval purposes.

### 3.3 Where the register's own account was right

- The **emesis titre** abstract-versus-Results defect is exactly as recorded
  (§2, F1).
- The **airborne emission fraction** null is unaffected: it is a
  commensurability null — copies/g of stool against copies/m³ of air, never in
  the same subjects — and no retrieval could resolve it. Six of the papers
  behind it are now body-verified for their own quantities, and none of them
  reports the ratio.
- The **contact transfer** row's block is by definition (emission as the
  denominator, which no assay uses), not by access; chunk retrieval does not
  touch it.
- **GII shedding peak** remains figure-digitized: Kirby 2014's body was not
  reached, and Teunis 2015's medians were absent from the chunks its body did
  return. Tranche 16's account of *what* the sources say stands; its explanation
  — that publishers' Results sections were unreachable — is now known to be the
  wrong reason for at least Teunis 2015, whose body is indexed.

---

## 4. What this changes about how sourcing is run

Both skills are corrected in the same change, and one of them moved underneath
this pass. R2 trimmed `searching-literature-evidence` to repo-specific guidance
and delegated the retrieval mechanics — the tool surface, the mandatory
`include_full_text_chunks: true`, query construction, and section recording — to
the org-level `consensus-literature-retrieval` skill. The corrections this pass
owes are therefore filed on the side that is repo-specific: the repo skill now
names the register's axis-3 vocabulary and where it lives, states the
quantity-and-unit rule as the condition for a `?nr`, and closes the loophole its
own final section left open by separating three cases that were being conflated
— nothing measures this, the paper could not be opened, and the quantity was not
in the excerpts returned. `model-parameter-provenance` now requires the section
of origin in the provenance comment at the point of definition, kept separate
from the evidence grade.

**Open, and outside this change's reach:** the mechanics half of the correction
belongs in the org-level skill, which is not in this repository. `?nr` as a
retrieval state, the two-differently-phrased-attempts floor, and "absence from
the chunks returned is not absence from the paper" should be stated there rather
than only here.
