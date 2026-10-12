# NORO-IMPLICATED-TITRE-01 — outbreak-implicated food-item titre review

> **Status:** Findings — sourced census of outbreak-implicated food-item titres,
> the shipped-draw reading, and a concrete (unapplied) proposal for a conditioned
> two-mode lot-titre draw. No engine change; nothing fitted to anchors.
> Ledger: [`docs/ledger/NORO-IMPLICATED-TITRE-01.md`](../ledger/NORO-IMPLICATED-TITRE-01.md).

## 1. Question and denominator

NORO-DOSE-POS-01 (`docs/norovirus/noro_dose_position_audit.md`) measured that
delivered cumulative food doses sit at Hill position p ≈ 0.2–0.35 while the
challenge-cohort reference position (p = 0.71) sits ~5 orders of magnitude
higher in ledger dose units. The hypothesis carried into this review: a tail of
contaminated-lot titres above the shipped `COMMON_SOURCE_LOT_TITRE_GEC_PER_G_RANGE
= (1e1, 1e4)` loguniform ceiling might be the missing dose.

The denominator of this review is the **implicated item** — a food item
epidemiologically or laboratory-linked to a reported outbreak — per the
commensurable-denominator rule. Background, harvest-area surveillance, and
retail/market measurements appear only in the contrast table (§3).

All dose positions are stated on the declared illness Hill
`p = 1 − (1 + η·dose)^(−γ)` with η = 0.508, γ = 0.095. The dose ledger is
withdrawn (open-ledger §4 item 00): this document reports raw titre figures
(GEC/g or copies/g as published) and positions on the declared curve only —
never an absolute "infectious dose".

## 2. Census — implicated-item titre measurements

| Study | Item / setting | n, denominator | Reported titre | Read from |
|---|---|---|---|---|
| Lowther 2012, *J Food Prot* (10.4315/0362-028X.JFP-11-360) | Oysters, 16 UK outbreak-associated samples vs 24 non-outbreak positive | implicated retained samples | GM **1,048** copies/g digestive tissue vs 121 background; **no outbreak sample < 152** | Ab |
| Flannery 2013, *Epidemiol Infect* (10.1017/S0950268813003014) | Restaurant oysters implicated in a 2010 Ireland outbreak | 2 implicated samples | **2,350** and **2,040** GII copies/g DT (upstream post-outbreak harvest samples 2,890 / 1,920) | T1 |
| Polo 2016, *Emerg Infect Dis* (10.3201/eid2212.160841) | Oysters implicated in 8 French outbreaks | 8 implicated batches | **43–1,170** RNA copies/oyster (digital PCR, GI+GII) | Ab + R |
| Rexin 2024, *J Food Prot* (10.1016/j.jfp.2024.100363) | NZ shellfish from illness-associated investigations | 20 samples | **44–4,630** GC/g DT; 40% < 200 | Ab |
| Le Guyader 2006, *J Clin Microbiol* (10.1128/JCM.01327-06) | Oysters implicated in international outbreak | implicated lots | "up to hundreds of genomic copies per oyster" (semi-quantitative) | Ab |
| le Mennec 2017, *Food Environ Virol* | Production-area oysters linked to repeated outbreaks | implicated lots | qualitative positive; depuration failure (half-life ~18 d) | Ab |
| Papafragkou 2024, *J Food Prot* (10.1016/j.jfp.2024.100395) | Wedding fruit salad (handler-mediated) | leftover salad, sealed stock | NoV-positive, **qualitative** — sequence match, no titre | R |
| Derrick 2021, *Int J Food Microbiol* (10.1016/j.ijfoodmicro.2021.109151) | Implicated celebration cake | ~400 g retained sample | detected, **qualitative** — no titre | R |
| Duan 2025, *Front Public Health* | Red-bean cake, school outbreak | implicated item | RT-qPCR positive, Ct only — no titre | R |

**Per-gram band of the census:** the quantitative implicated measurements span
a floor of ~1.5e2 copies/g (Lowther's outbreak minimum 152; Polo's per-oyster
floor is consistent at tens–hundreds per gram of digestive tissue) to a ceiling
of 4,630 GC/g (Rexin). Every outbreak-implicated quantification found falls
inside `[1.5e2, 5e3]` per gram.

**Honest gap:** no quantitative titre exists for an implicated RTE/produce item.
Every RTE or produce implicated item found in the literature is a qualitative
positive (fruit salad, cake) — the quantitative implicated record is entirely
shellfish.

## 3. Contrast — where >1e4 figures actually live (non-implicated denominators)

| Study | Denominator | Reported range |
|---|---|---|
| Rajko-Nenow 2012, *Int J Food Microbiol* (10.1016/j.ijfoodmicro.2012.10.001) | Monthly harvest-area surveillance, closed area | 97–**20,080** copies/g |
| Jiang 2018, *Food Control* (10.1016/j.foodcont.2017.11.043) | Beijing/Qingdao **retail** oysters | 3.55e3–**1.45e6** copies/g |
| EFSA BIOHAZ/Aerts 2019 | EU production / dispatch batches | 34.5% pos mean 337 cpg; 10.8% mean 168 cpg (register rows T11–T21) |
| Dirks 2021 | Ready-for-sale shellfish | 1.76–2.04 log10 gc/g |
| Gao 2025 | Guangzhou retail oysters | mostly 1e3–1e4, some **1e5–1e6** GC/g |
| Tunyakittaveeward 2019 | Market survey | to 1.62e4 GII |

**Verdict (the settled prior holds):** no outbreak-implicated item measurement
exceeds ~4.6e3 GC/g. The >1e4 tail exists only in surveillance and retail
denominators — a different population of lots. **The titre-tail hypothesis fails
on titre grounds.**

## 4. Implicated-item attack rates among exposed

Point-source denominators (per-eater, not population):

| Study | Item | AR among exposed |
|---|---|---|
| Polo 2016 | 8 oyster outbreak clusters | **43–100%** per cluster |
| Papafragkou 2024 | wedding fruit salad | 23/56 interviewed = **41%**; salad-eaters RR 3.2 (95% CI 1.1–8.3) |
| Zhu 2025, MMWR | imported Ireland oysters | ~179/~400 interviewed ≈ **45%** met case definition |
| Alfano-Sobsey 2011 | steamed oysters, restaurant | case-control OR 12 (4.8–28); secondary household SAR 14% |
| Duan 2025 (contrast) | red-bean cake, school | 2.21% — **population denominator** (52/2,352), included only to show why the per-eater denominator is the commensurable one; the item-specific signal is OR ≈ 1,248 |

For position reference only (not an outbreak): the challenge-cohort illness
share ~0.71 is the Hill reference at ~8.98e5 ledger units; per-genome-copy
infection risk is ~0.076 (GII) and illness ~0.035 (Teunis 2020); Atmar 2014's
HID50 estimate ≈ 2,800 GEC (quoted second-hand via Duret 2017).

## 5. Per-serving delivery reading vs the shipped draw

Shipped mechanics (Grade B/C constants, `engines/transmission_core.py`):
`per_serving_GEC = titre(logU 1e1–1e4) × serving_mass(U 50–250 g)`, credited
losslessly to lot takers. Median serving ≈ 4.7e4 GEC → **p ≈ 0.62**; draw
ceiling 2.5e6 → **p ≈ 0.74**. Reaching the p = 0.71 challenge reference
(8.98e5 units) needs the joint tail — titre ≥ ~3.6e3 (top ~15% of the
loguniform) together with near-ceiling mass.

Census reading: an implicated item at the observed band `titre ∈ [1.5e2, 5e3]`
× typical mass ~150 g delivers ~2e4–7.5e5 GEC → **p ≈ 0.5–0.72**, median
~1.3e5 → **p ≈ 0.65**. The real implicated-serving band overlaps the measured
point-source AR band (0.41–1.0) — consistent; no tail needed to explain real
attack rates at the per-serving position the model already draws.

## 6. Where the ~3-order raw→delivered attenuation goes

Two chains that must not be conflated:

**(a) In-engine (measured, NORO-DOSE-POS-01).** The gap between median raw
serving (~4.7e4) and median delivered cumulative dose (27–107) is
**compositional**, not a per-serving attenuation: the median acquisition is a
routine-route dose, not a lot serving — lot pans credit `per_serving`
losslessly (declared bound) to the minority who take one. On the handler/diner
arm, `deposit = contacts × Tr(hand→food) × hand_load ÷ pan_servings` with
`Tr ~ U(0.003, 0.46)` — and the shipped range already **brackets** the
literature: Duret 2017 meta-analysis hand→food median 0.05 (range
1.1e-3–0.71), glove→food 0.31; Rönnqvist 2014 glove→cucumber 1.5% ± 1.9% per
preparation event (5.4% recovery-corrected), bare-hand→produce ~50% (Tuladhar
2013); ≥3 log10 hand load transfers ≥1 infective particle to a sandwich, ≥4
log10 reaches all servings.

**(b) Physical item→gut chain** for a real implicated serving:

| Step | Literature reading | Grade |
|---|---|---|
| Item titre → *measured* titre (extraction recovery) | ISO 15216-2 oyster recovery **2.1% ± 0.8%** (Li 2022); modified methods ~11–47% (Zhang 2020, Li 2022). Published titres under-read true in-item load ~**5–50×** | B |
| Survival/prep inactivation | Vasickova 2010: persistence days→weeks on surfaces/produce; cooking only partial (steamed oysters still infectious — Alfano-Sobsey 2011). Small for raw/lightly-cooked items | B |
| Ingestion fidelity | ~lossless physically; lossless in-engine by declared bound | C (declared) |
| GEC → infectious particles | **Refused** as a repo constant — GC:PFU spread 1.4–4.3 log10, non-identifiable with the dose-response intercept (register; STAN-03 lineage). Absorbed by the Hill intercept by construction | — (refusal) |

## 7. Least-sourced step — stated explicitly

The **in-item titre → Hill dose-unit conversion** is the least-sourced link:
extraction recovery is measured (~5–50× under-read, Grade B) but is never
applied to census numbers, and GC:infectivity is refused as non-identifiable.
This step **cannot be re-sourced upward** — any lever here is a dose-ledger
units question, not mechanism evidence. The attenuation chain is therefore NOT
a candidate explanation for the challenge-dose gap that more literature could
close: the chain is either lossless-by-declaration or refusal-bounded.

## 8. Proposal — (a) conditioned two-mode draw, inside the shipped interval

**Physical argument for (a) over (b)/(c):**

- The shipped `logU(1e1, 1e4)` is, shape-for-shape, the **background**
  distribution: EFSA dispatch mean 168 cpg, Dirks ready-for-sale ~57–110,
  Lowther non-outbreak GM 121. Its mass is concentrated where non-implicated
  stock sits.
- But a `provisioned_lot` object only mints conditional on the voyage carrying
  a contaminated lot — **the firing event is already the implicated
  denominator**. ~39% of shipped draws fall below the smallest observed
  implicated value (Lowther floor 152/g) — impossible titres for a fired
  object — while the top ~15% (>3.6e3) is supported only by non-implicated
  surveys (§3). Both tails are the wrong denominator.
- (b) attenuation-side re-sourcing cannot carry the residual gap: lot pans are
  lossless by declared bound, the handler-arm transfer range already brackets
  the measured fractions, and the only uncertain link (GC:infectivity) is
  refused as non-identifiable (§7).
- (c) remains the residual framing for the challenge-dose gap itself — a
  units/ledger question, not a draw change.

**Concrete proposal** (source + grade on every number; nothing fitted):

- **Background mode** — `logU(1e1, ~1e3)`: market/production stock (EFSA
  168–337 mean, Dirks ~57–110, Lowther background GM 121). Grade B.
- **Implicated mode** — `logU(1.5e2, 5e3)`: floor from the smallest observed
  implicated quantification (Lowther 152/g; Polo 43/oyster at comparable
  per-gram scale), ceiling from Rexin 4,630 GC/g — the largest
  outbreak-implicated measurement in the census. Grade B for shellfish item
  lines (direct implicated measurements); **Grade C for produce/RTE lines** —
  no quantitative implicated titre exists (§2), the shellfish band is carried
  as analogous until an RTE titre appears.
- **Mode selection**: conditioned on the object mint — a fired
  `provisioned_lot` object draws from the implicated mode; background-stock
  uses (if modelled) draw the background mode. No new probability parameter.
- **Arithmetic effect (not fitted):** median implicated serving ≈ 8.7e2 ×
  150 g ≈ 1.3e5 → p ≈ 0.65 vs current 0.62 — a ~3-point median shift plus
  removal of the impossible ~39% low tail. It deliberately does NOT
  manufacture challenge-scale doses: the residual gap belongs to the refused
  GC:infectivity link — option (c)'s units question.
- No number above was chosen to make VSP posting or attack-rate anchors come
  out right: both modes are bounded by the census floor/ceiling and the
  background surveys, independent of any model outcome.

**Open caveat for the next session:** whether item-line structure should split
implicated titres per food class (shellfish vs produce/RTE) — the quantitative
census is shellfish-only.

## 9. Sources

| Reference | Contributes | Section-of-origin |
|---|---|---|
| Lowther 2012, *J Food Prot* 75:2040 | implicated GM 1,048 vs 121, floor 152 cpg | Ab |
| Flannery 2013, *Epidemiol Infect* 142:2095 | implicated 2,350/2,040 GII cpg DT | T1 |
| Polo 2016, *EID* 22:2124 | implicated 43–1,170 copies/oyster; AR 43–100% | Ab, R |
| Rexin 2024, *J Food Prot* | implicated 44–4,630 GC/g, 40% <200 | Ab |
| Le Guyader 2006, *JCM* 44:4133 | implicated "hundreds of copies/oyster" | Ab |
| le Mennec 2017, *Food Environ Virol* 9:42 | depuration failure on implicated lots | Ab |
| Papafragkou 2024, *J Food Prot* 87:100395 | implicated fruit salad (qual), AR 41%, RR 3.2 | R |
| Derrick 2021, *IJFM* 357:109151 | implicated cake (qual); sandwich-sim recovery 1.1–7.4% | R |
| Duan 2025, *Front Public Health* | implicated cake (Ct only); population AR 2.21% | R |
| Alfano-Sobsey 2011 | steamed-oyster outbreak OR 12, secondary SAR 14% | R |
| Zhu 2025, MMWR | imported-oyster outbreak ~45% AR | R |
| Rajko-Nenow 2012, *IJFM* 158:143 | surveillance contrast to 20,080 cpg | Ab |
| Jiang 2018, *Food Control* 92:89 | retail contrast to 1.45e6 cpg | Ab |
| Tunyakittaveeward 2019 | market contrast to 1.62e4 | Ab |
| Gao 2025 | retail contrast 1e5–1e6 | Ab |
| Duret 2017, *Risk Anal* (PMC6032842) | transfer-efficiency meta-table; shedder prevalence 15%; dose-response params | T, R |
| Rönnqvist 2014, *AEM* (PMC4136105) | glove→cucumber 1.5%/5.4%; hand-load thresholds | R |
| Tuladhar 2013 | bare-hand→produce ~50% (via Rönnqvist) | Sec |
| Vasickova 2010 | surface/produce persistence days–weeks | R |
| Li 2022, *IJFM* 366:109957 | ISO 15216-2 extraction recovery 2.1% oyster | Ab |
| Zhang 2020, *Food Control* 118:107032 | modified extraction ~11% | Ab |
| Teunis 2020 | per-copy infection/illness risk | R |
| Atmar 2014 | HID50 ≈ 2,800 GEC | Sec (via Duret) |
| Barclay 2014 | control-measure review (context) | R |
| Nicolay 2011, Ozawa 2007, Barrabeig 2010, Wu 2019 | food-handler-implicated outbreaks / shedding (handler-arm context; no titre) | Ab/R |
