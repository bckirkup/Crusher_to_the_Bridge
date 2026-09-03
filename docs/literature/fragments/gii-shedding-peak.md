# Register fragment — `gii-shedding-peak` (task #47, tranche 16)

> **Merged.** This fragment was merged into [`../../parameter_provenance_register.md`](../../parameter_provenance_register.md) by the sourcing-wave-1 integration pass, with the lead's corrections applied at merge time. It is kept as the audit trail of what the sourcing unit proposed; it is **not** a live proposal, and where it and the register differ the register holds the status.

**Status:** Additive fragment for
[`docs/parameter_provenance_register.md`](../../parameter_provenance_register.md)
§3.1 (norovirus, active arm). **Not merged; the register is untouched by this
unit.** Evidence and provenance are in
[`consensus_tranche_16_gii_shedding_peak.md`](../consensus_tranche_16_gii_shedding_peak.md).
Nothing here is adopted, no profile or engine constant changes, and no single
central value is recommended.

Row format is the register's:
`| Quantity | Shipped | Class | Evidence / interval | State | Task |`

## Proposed replacement for the existing `shedding_curve_log10` peak row

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `shedding_curve_log10` peak magnitude | 11.0 log10 copies/g | I → **M, mis-genogrouped; GII interval now measured** | 11.0 remains Atmar 2008's **GI.1** median peak (95×10⁹ = 10^10.98). Tranche 16 sources the **GII** quantity in its own units. Per-subject symptomatic GII peaks, unambiguous **copies (or genome equivalents) per gram of wet stool**: interval **[7.0, 9.1] log10** — Kirby 2014 GII.2 challenge, n=9, median 7.06 (3.63–8.92, digitized from the paper's figures, §2.1); Tu 2008 GII aged-care outbreak, observed maximum 9.14 (digitized); Teunis 2015's 161 observed GII.4 samples top out at 8.94. Acute-phase single-specimen GII medians fall inside it: Lee 2007 GII.4 n=40 median **8.93 log10 copies cDNA/g stool** (IQR 8.22–10.24); He 2017 GII n=201 geometric mean **9.03 ± 1.71 log10 copies/g stool (w/w)**; Barreira 2009 GII children symptomatic **8.39**; Ozawa 2007 GII/4 mean 7.96×10⁹ /g (9.90). Immunocompromised/chronic hosts run to 10.4–11 (He 2017 severe stratum; Chaimongkol 2024, 10⁴–10¹¹ /g) — a different population from a passenger. **Grade B is the ceiling**: no GII faecal titre has ever been measured in the target setting, and no GII.4 challenge study quantifies a stool time course at all | ⊘ **joint, unchanged** — emission scale and dose-response enter as a **product** (#366) and every dose figure is void pending refit, so the measured GII interval is *recorded, not applied*. **No GI→GII correction factor is proposed** (a Kirby-derived offset applied to an Atmar-derived peak crosses two assays whose own GI.1 medians differ by ~2.3 logs). Shipped 11.0 lies above every GII central estimate and above every observed GII maximum in an immunocompetent host — declared, not acted on | #47 evidence recorded |

## Proposed new rows

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `shedding_curve_log10` **time to peak** (GII) | curve index of the authored maximum | **B as an interval** | **Days 2–4 post inoculation** in the only GII challenge with serial quantification (Kirby 2014 GII.2, digitized day-of-peak median 4, range 2–6, n=9); **day 3 post onset** with the rise continuing to day 9 in paediatric GII cohorts (Lee 2021; Cheng 2021, rise days 2–9, decline after day 9). Ge 2023's 1.5–2.3 d is a **fitted** GI.1 quantity (grade C) and is not used | evidence recorded, not adopted | #47 |
| `shedding_curve_log10` **decline shape** (GII) | authored tail over 15 indices | **B for the shape, ⊘ unit for the rate** | Log-linear decline after peak; the only decline rate with unambiguous units is Sabrià 2016's ≈**0.11 log10/day** (symptomatic 7.51 ± 1.80 → 5.28 ± 0.76 log10 GC/g over 19 d; asymptomatic 6.49 ± 1.93 → 4.52 ± 1.45, mixed genogroup). Tu 2008 (0.76/day, half-life 2.5 d) and Lai 2013 (0.66/day, half-life 1.7 d) are **not self-consistent** under either a natural-log or a log10 reading and neither states the rate's units, so they cannot be adopted as published | ⊘ **blocked by unit ambiguity** in the published rates | #47 |
| `asymptomatic_shedding_log10` (offset), **GII-specific evidence** | peak 0.5 log10 below symptomatic | C, **direction contested for GII** | Tranche 16 adds the contradiction the existing row does not carry: for GII the offset is **either absent or ≈1 log**. Absent: Ozawa 2007 (GII means similar in symptomatic and asymptomatic food handlers); Teunis 2015 observations (symptomatic median 5.79 vs asymptomatic 5.91 log10 gc/wet g, n=115 / 46); Costantini 2015 (cases and exposed controls shed similar amounts); Huynen 2013 (higher in symptomatic for **GI**, P = 0.03, but **not for GII**). Present, 0.8–1.2 log10: Barreira 2009 (1.24, GII, P = 0.011); Dábilla 2017 (0.79, mixed); Sabrià 2016 (≈1.0 at first sample, mixed). The GII challenge literature supplies **no asymptomatic peak at all** | ⊘ **not identifiable** as a single ratio; keep 0.5 as an authored placeholder, now with its interval [0, 1.2] and its contradiction recorded | #47 |
| `shedding_duration_days` — GII confirmation | 15 | B (already adopted, interval [12, 30]) | Tranche 16 adds GII-specific support and does **not** move the interval: Kirby 2014 GII.2 first-to-last positive median **5 d** (a minimum estimate; last sample still positive in two subjects) with shedding to **3 weeks past symptom resolution**; Tu 2008 GII outbreak mean **28.7 d**; Aoki 2010 mean **14.3 d** (9–32); Costantini 2015 **47% of GII.4 cases shed ≥21 d**; Cheng 2021 cessation by day 15; Lee 2021 decline days 10–15. Shedding far outlasting the 1–3 day illness is confirmed for GII | ✓ interval unchanged, GII support added | #46 done / #47 |

## Null results the register should carry

| Quantity | Finding | State |
|---|---|---|
| GII.4 faecal shedding time course | **No GII.4 human challenge study reports a quantitative stool titre time course.** Frenck 2012, Bernstein 2014 and Rouphael 2022 report detection, proportions positive or ID50 only. The sole GII challenge with serial quantification is GII.2 Snow Mountain — a genotype, not the pandemic GII.4 | null result, recorded |
| GII faecal titre in the target setting | **No measurement exists on a ship.** Grade A is unattainable for this quantity; B is the ceiling | blocked by setting |
| Prospective community cohort, serial GII quantification in copies/g | **None found.** Community designs recovered (IID2, LoewenKIDS, Kobayashi's matched adult cohorts, Cannon 2026) report detection, genotype or Ct, not per-subject quantified peaks | null result, recorded |

## Provenance caveats the lead must carry into the register if these rows are merged

1. The Kirby 2014, Tu 2008, Teunis 2015 and Aoki 2010 **per-subject numbers above
   are digitized** from the papers' figures by the public `shedding-hub` dataset
   repository, not read from the papers' own tables; the publishers' Results
   sections were unreachable. They are the only per-subject GII series available,
   and an adoption should not rest on them without the full texts.
2. Papers reporting **cycle thresholds** (Shioda 2017, Parrón 2021, Harris 2019),
   **per-swab** (Gustavsson 2017), **per-mL emesis** (Kirby 2016) or **per-mL
   saliva** (Anfruns-Estrada 2020) denominators are excluded from every interval
   above; the differences are multiple logs.
3. **Grade C, excluded from the intervals:** Teunis 2014/2015's fitted peak range
   10⁵–10⁹/g (the source of the shipped `shedding_variance_log10`), Teunis 2020
   (fitted to challenge *and outbreak* data — circular against scored attack
   rates), and Ge 2023 (Bayesian re-analysis, GI.1).
4. No candidate was selected, ranked or excluded by reference to VSP rates, the
   Diamond Princess, the Greg Mortimer, or any anchor in `docs/anchors/`, and no
   effect on any anchor was computed.
