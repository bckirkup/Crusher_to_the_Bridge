# Tranche 49 — genotype class shares: era-resolved external typing, and the cruise-denominator class difference

**Register rows fed / supersession.** Feeds `prior_genotype_distribution` on
`norwalk_gi` — the uniform 0.3333/0.3333/0.3333 placeholder that
`docs/proposals/pathogen_class_structure_decision.md` §4 flagged as load-bearing
and unsourced — and the class-share declarations recorded in
`docs/ledger/NORO-GENO-01.md`. It **supersedes the uniform placeholder as a
description of circulating shares** (the placeholder remains in the field until
the class mechanism is wired), **withdraws no measurement**, **moves no
constant and adopts none**. The class shares below are *declared inputs to be
swept*, not fitted values — the ruling forbids fitting them to VSP, which
carries no genotype at all.

**Status:** Evidence assembled and interpreted. Nothing implemented. Retrieval
was one Consensus wave, five queries; every share below is read from the
paper's own abstract, table, or Results prose as marked.

**Scope.** Three questions, in the order they were asked:

1. What does external typing surveillance report for the **GII.4-vs-non-GII.4
   share of outbreaks**, era-resolved — and on the cruise denominator
   specifically?
2. What **per-class challenge-grade dose-response** data exists?
3. What share of cruise / passenger-vessel norovirus is **GI (incl. GI.1)**?

## Q1 — the shares, era-resolved

All denominators are **genotyped outbreaks** unless marked (NoroNet and
NoroSurv report sequences). US = CaliciNet.

### GII.4-dominant era (the model's `pre` era)

| Source | Window | Denominator | GII.4 share | Origin |
|---|---|---|---|---|
| Vega 2011, *Emerg Infect Dis* (CaliciNet launch year) | 2009–10 | 552 US outbreaks | **72%** (395/552; 75% of those the new New Orleans variant) | R |
| Vega 2013, *J Clin Microbiol* (DOI 10.1128/jcm.02680-13) | 2009–2013 | 3,960 US outbreaks | **72%** (2,853; 94% New Orleans or Sydney) | Ab |
| Cannon 2017, *J Clin Microbiol* (DOI 10.1128/jcm.00455-17) | 2013–2016 | 2,715 US outbreaks | **58%** (GII.4 Sydney; every other genotype 5–17%/season) | Ab |
| Chhabra 2024, *Eurosurveillance* (DOI 10.2807/1560-7917.es.2024.29.39.2400625) | non-pandemic 3-season average, 2017–2024 | GII detections | **US 53%, England 73%, Germany 47%, Austria 66%, France 64%** | T |
| van Beek 2018, *Lancet Infect Dis* (DOI 10.1016/s1473-3099(18)30059-8) | 2005–2016 | 16,635 NoroNet **sequences**, global | GI 8.2% / GII 91.7%; GII.4 = **37.2%** of healthcare-outbreak entries vs 12.5–13.5% for other genotypes | R + Ab |

**China is a geographic outlier, not a contradiction:** CaliciNet China
2016–2020 (Zhu 2021, *China CDC Weekly*, DOI 10.46234/ccdcw2021.276) ran
GII.2[P16] at **69%** of 1,244 GII outbreaks with GII.4 Sydney ~6% — the
GII.2[P16] recombinant wave. A US/Europe-facing cruise denominator does not
inherit it, but it warns that shares are region- and era-conditioned, which is
exactly why they are declared and swept rather than adopted.

### Post-2020 era — the GII.17 succession

| Source | Window | Denominator | Finding | Origin |
|---|---|---|---|---|
| Barclay 2025, *Emerg Infect Dis* (DOI 10.3201/eid3107.250524) | US 2022–2025 | CaliciNet outbreaks | GII.17 **<10% (2022-23) → 75% (2024-25)**, surpassing GII.4 | Ab |
| Barclay 2026, *J Infect Dis* (DOI 10.1093/infdis/jiag348) | US Sept 2021–Aug 2025 | **1,412 outbreaks** | GII.17 **5.0% → 74.8%**; 93.3% Romania-like cluster | R |
| Chhabra 2024 (as above) | 2023/24 season | GII detections | GII.17 17–64% by country; England 77% into 2024/25 | T |
| Cannon 2026, *J Clin Virol* (DOI 10.1016/j.jcv.2026.105949) | 2020–2025 | 4,113 NoroSurv sequences (medically attended <5y, 22 countries) | GII.4 53% overall; GII.17 ≤5% → 32% by 2024-25 | R |

**Cruise-denominator typing — the load-bearing row for this model:**

- Preston et al. 2026, *Open Forum Infect Dis* (DOI 10.1093/ofid/ofaf695.2359,
  conference abstract **P-2196**, Ab): VSP cruise-ship norovirus outbreaks,
  Sept 2022–Mar 2025 — *"Previously, most norovirus outbreaks in the US and
  cruise travel were attributed to GII.4; recently, GII.17 has become the
  predominate genotype."* The cruise series undergoes the same succession as
  shore-side surveillance. (81% of posted cruise AGE outbreaks since 2019 are
  norovirus.)
- Wang 2016, *J Appl Microbiol* (DOI 10.1111/jam.12978): a Yangzi river-cruise
  outbreak typed **seven genotypes** (GI.1, GI.2, GI.3, GI.4, GI.8, GI.9,
  GII.17) — a point-source multi-strain import, evidence that mixed-genotype
  founder events occur but not a share.

### What the shares declare

On the two-class ruling (GII.4 pandemic lineages vs non-GII.4), era-resolved
declared intervals for `prior_genotype_distribution`'s class mixture:

- **`pre` era:** GII.4 class share ≈ **0.60, interval [0.47, 0.75]** — Chhabra's
  non-pandemic by-country floor (Germany 47%, US 53%) to the CaliciNet 2009–13
  ceiling (72%); non-GII.4 class the complement (includes ~8–11% GI).
- **post-2020 era:** GII.4 class share ≈ **0.15, interval [0.05, 0.30]** —
  GII.17 (non-GII.4 class) is the predominant genotype at 0.5–0.75 of US
  outbreaks by 2024-25, on cruise and ashore alike; the residual GII.4 share
  is bounded above by the pre-succession second-place genotype share.

Both are **declared sweep intervals, never to be fitted** — VSP carries no
genotype, so the shares absorb nothing but external typing.

## Q2 — per-class challenge-grade dose-response: thin by exactly the margin the ruling assumed

- **GII.4:** Frenck 2012 (*J Infect Dis* 206:1386) — human challenge, single
  dose ~5.0e4 units: 16/23 secretor-positive infected (13 ill), 1/17
  secretor-negative infected (read from Teunis 2020's Table A1 compilation,
  Sec). Bernstein 2015 is a GII.4 *vaccine-efficacy* challenge on the same
  inoculum lineage — single dose, no multi-dose titration.
- **non-GII.4 (GII.2):** Rouphael 2022 challenge ID50 **5.1e5** (register row
  `dose_response.alpha/beta`, tranche 6).
- **GII.4 surrogate:** Ramesh gnotobiotic-pig Cin-2 ID50 2.4–3.4e3 RNA copies —
  animal model, Grade C corroboration at best, not a human class value.
- **Teunis 2020** (*Epidemics* 32:100401) is the study that *pools* challenge
  arms multilevel rather than resolving per genotype: GI Se+ 0.28 vs GII 0.076
  per copy; secretor-negative 0.00007 vs 0.015.

**Result: a per-class ID50 table is not present in the literature** — two
single-dose GII.4 arms and one GII.2 multi-dose fit are the whole challenge
evidence for the classes. This *confirms* the ruling's constraint rather than
loosening it: the class difference must enter as a declared/swept offset on a
shared base curve (`transmissibility_multiplier` or the split secretor gate),
not as independently fitted dose-responses.

## Q3 — GI / GI.1 on passenger vessels: no typing support for a class share

- GI overall: **8–11% of outbreaks** (van Beek global 8.2%; Vega US 11%);
  GI.1 is a small share of that GI share.
- Cruise/passenger-vessel typing is GII-dominated end to end: the only
  retrieved cruise event carrying GI.1 is Wang 2016's point-source
  multi-strain import (seven genotypes from contaminated source material), and
  the VSP-era typing record (Preston) names GII.4 → GII.17 only. Mouchtouri
  2024's 45-outbreak cruise review (DOI 10.2807/1560-7917.es.2024.29.10.2300345)
  is the denominator on which no GI share is reported at all.
- **Conclusion:** nothing retrieved supports a non-trivial GI.1 share in the
  cruise boarding pool — GI.1 stays a **scenario arm** (mono-genotype cell for
  the GI-vs-GII contrast), not a mixture class. A named cruise GI series would
  reopen this row.

## Bonus — the class difference is *measured* on the cruise denominator itself

The differential-behavior question does not rest on secretor gate alone;
genotype-stratified severity on VSP's own series exists:

- **Preston 2026 (above):** cases in GII.4 cruise outbreaks were more likely to
  report **>10 vomiting episodes (aOR 1.67, 95% CI 1.15–2.42)** and **longer
  symptom duration (13–24 h aOR 1.43 [1.18–1.74]; >24 h aOR 1.73 [1.37–2.19])**
  than cases in GII.17 outbreaks (2,618 cases, 2022–2025).
- **Barclay 2026 (above):** GII.17 outbreaks were more foodborne-exposure-
  associated (16.4% vs 9.6%) and carried higher vomiting/cramp/fever shares;
  GII.4 outbreaks skewed older.
- **Vega 2013:** non-GII.4 genotypes associated with foodborne transmission at
  OR 1.9–7.1; GII.4 enriched in long-term-care/elderly settings — the
  setting-sorting the ruling calls "between-voyage" signal.
- **Swartling 2022** (*Viruses*, DOI 10.3390/v14071350): in allogeneic-HCT
  patients, GII.4 was detected only in secretors and ran longer (median 36 vs
  15 days) — small n, immunocompromised setting, Grade C corroboration of the
  gate and a duration difference.
- The register already holds the gate itself: Kambhampati pooled ORs →
  non-secretor relative susceptibility **0.10 (GII.4) vs 0.45 (non-GII.4)**.

## What this tranche does not settle

- The **class share interval midpoints** are declared conveniences for sweep
  placement, not estimates; nothing here licenses asserting 0.60 or 0.15 as a
  value.
- Whether class differences in *shedding titre/duration* (beyond symptom
  severity) exist — Frenck/Bernstein/Rouphael report detection and ID50, not
  serial titre, and tranche 16's null (no GII.4 human stool titre time course)
  stands. If the real class difference is emission-side, this tranche cannot
  see it.
- Era boundaries: "post-2020" merges the COVID-gap years with the GII.17
  succession; the shares are declared per era flag, and a voyage dated
  2021-2023 sits in the transition the intervals deliberately span.
