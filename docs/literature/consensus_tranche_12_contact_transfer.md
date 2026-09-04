# Tranche 12 — contact transfer efficiency: two directions, two orders of magnitude, and an anchor that belongs to neither


**Register rows fed / supersession.** This tranche feeds `contact_transfer_fraction` and the two non-porous fomite-transfer rows in §3.1. No later withdrawal or supersession is recorded in the register or the norovirus open ledger.

**Status:** Evidence assembled. **No profile constant, engine constant or
screen interval changes in this document.** Nothing here is authoritative about
the model; the register row this tranche proposes lives in
[`fragments/contact-transfer.md`](fragments/contact-transfer.md) and is the
lead's to merge.

**Scope:** task #22 — `contact_transfer_fraction`. The repository carries an
approximate **0.25** anchor for a hand/surface contact transfer fraction whose
provenance has never been traced to a primary measurement
(`docs/norovirus/norovirus_model_history.md` §10; register row #22). Tracing it
or refuting it is the job. §7 also records what the engine field of that name
actually multiplies, which is **not** the quantity the literature measures.

**Method:** Consensus MCP, seven queries, **all unfiltered** (no `year_min`,
no `study_types`, no `exclude_preprints`, no `sample_size_min`); the one filter
argument used anywhere was `page: 1` on query Q5, and it returned the same page
as the default. Queries were fixed from the definition of the quantity —
directional, material-paired, moisture-stated — before any value was compared
with anything the model ships. Truncated result sets were read from the
overflow files named in each truncation notice, not from the visible first page;
three of the numerically most useful papers (Grove, Lopez, Mbithi) ranked below
reviews and models in the result lists.

**Two conventions used throughout.** *Transfer fraction* is always
`recipient recovery / donor inoculum recovered at contact time`, the
denominator every one of these assays actually uses. *Infectivity* (plaque
assay) and *genome copies* (RT-qPCR) are labelled per row and never mixed
inside a range: a genomic transfer fraction bounds an infectious one from above
and is not a substitute for it.

---

## 1. The definition problem, resolved before the numbers

Transfer efficiency is directional and the two directions are not the same
quantity:

* **surface → hand** — pickup / fomite acquisition;
* **hand → surface** — deposit / fomite contamination.

Every paper below that reports both directions finds them different, and
Anderson 2021 finds direction a statistically significant factor
(*P* < 0.05) for MS2. The two directions are therefore reported separately
here and **never pooled**. A paper reporting a single undirected "transfer
efficiency" is not usable as an interval for either direction; §5 lists the
three such papers found and the reason each is rejected for that use.

The second axis is **moisture**, and on the deposit direction it is the larger
lever of the two. Tuladhar's MNV-1 finger → stainless steel falls from
13 ± 16 % to 0.1 ± 0.2 % on ten minutes of drying — a factor of about 130 —
while the same paper's steel → finger pickup after forty minutes of drying is
still 2.0 ± 2.0 %. Sharps sees the same asymmetry in genome copies: 58–60 %
wet versus < 1 % dry on deposit, against 1–50 % wet versus 2–11 % dry on
pickup. This is the asymmetry PR #378 added a drying axis for, and it is
confirmed here by two independent groups on two different assays.

Third axis, **material**: non-porous donors and recipients (stainless steel,
plastic, laminate, glass) are the maritime-relevant case — handrails, buffet
tongs, cabin fixtures. Porous and food materials transfer differently by an
order of magnitude (Lopez: non-porous up to 57 % against porous < 6.8 % at the
same humidity; Rusin: porous fomites < 0.01 %) and are excluded from the
intervals in §2–§4, not averaged into them. §5 lists the food/porous
measurements found, so the next reader does not re-find them and read the
omission as an oversight.

Fourth, **pressure, duration and friction** are part of the quantity's
definition and are given per row where the paper states them. They are not
free parameters: Mbithi measured a ~3× increase in HAV transferred when
contact pressure alone rose from 0.2 to 1.0 kg/cm², and a further two- to
threefold increase when friction was added. The assays below span
0.2–1.9 kg/cm² and 1–10 s, so part of the spread in every interval is contact
mechanics, not biology.

## 2. Direction A — surface → hand, non-porous donors

Norovirus and norovirus surrogates first, then other viruses as analogous
evidence. All grades are **B**: none of this is measured on a ship, and the
infectivity measurements are all surrogates.

| Source | Organism / assay | Donor → recipient | Moisture | Contact | Transfer fraction | n | Grade |
|---|---|---|---|---|---|---|---|
| Grove 2015, *Int J Food Microbiol*, DOI 10.1016/j.ijfoodmicro.2014.12.023 | MNV-1, infectivity (log-transformed transfer %) | contaminated **stainless steel spigot → clean bare hand** | not stated in abstract (food-service task, turning a spigot) | task-realistic grasp, unspecified | **24 %** (1.4-log transfer %) | ≥ 9 replicates per scenario | B |
| Tuladhar 2013, *Int J Food Microbiol*, DOI 10.1016/j.ijfoodmicro.2013.09.018 | MNV-1, infectivity | **stainless steel → finger pad** | dried 40 min | 0.8–1.9 kg/cm², ~2 s | **2.0 ± 2.0 %** | 1st of 7 sequential transfers | B |
| Tuladhar 2013, same | MNV-1, infectivity | **Trespa® laminate → finger pad** | dried 40 min | 0.8–1.9 kg/cm², ~2 s | **4.0 ± 5.0 %** | as above | B |
| Sharps 2012, *J Food Prot*, DOI 10.4315/0362-028x.jfp-12-052 | human NoV GI + GII and MNV-1, **RT-qPCR genome copies** | **stainless steel → gloved fingertip** (first leg of the reported fomite chain) | wet | immediate interface | **1–50 %** (all viruses) | not stated in abstract | B |
| Sharps 2012, same | as above, genome copies | **stainless steel → gloved fingertip** | dried before contact | — | **2–11 %** | — | B |
| Bidawid 2004, *J Food Prot*, DOI 10.4315/0362-028x-67.1.103 | feline calicivirus, infectivity | **brushed stainless steel disk → finger pad** | air-dried inoculum | 0.2–0.4 kg/cm², 10 s | **7 ± 1.9 %** | adult subjects, not stated | B |
| Lopez 2013, *Appl Environ Microbiol*, DOI 10.1128/aem.01030-13 | MS2 coliphage and poliovirus 1 (with three bacteria), infectivity | **non-porous fomites → finger** | dried 30 min, **low RH 15–32 %** | 1.0 kg/cm², 10 s | **up to 57 %** | 9 fomites × 5 organisms | B |
| Lopez 2013, same | as above | **non-porous fomites → finger** | dried 30 min, **high RH 40–65 %** | 1.0 kg/cm², 10 s | **up to 79.5 %** | as above | B |
| Ansari 1988, *J Clin Microbiol*, DOI 10.1128/jcm.26.8.1513-1518.1988 | human rotavirus Wa, infectivity, 10 % faecal suspension | **stainless steel disk → clean hand** | dried, contact at 20 min / 60 min | ~1 kg/cm², 10 s | **16.8 %** (20 min); **1.6 %** (60 min) | volunteers, not stated | B |
| Ansari 1991, *J Clin Microbiol*, DOI 10.1128/jcm.29.10.2115-2119.1991 | rhinovirus 14, infectivity | **metal disk → finger** | dried 20 min | 5 s | **0.7–0.9 %** (direction-independent in this assay) | volunteers, not stated | B |
| Ansari 1991, same | human parainfluenza 3, infectivity | **metal disk → finger** | dried 20 min | 5 s | **1.5 %** | as above | B |
| Gerba 2021, *Infect Control Hosp Epidemiol*, DOI 10.1017/ice.2021.428 | human coronavirus 229E, infectivity | **various hard surfaces → finger pads** | not stated in abstract | not stated | **0.46–49.0 %** | not stated | B |
| Behzadinasab 2021, *Sci Rep*, DOI 10.1038/s41598-021-00843-0 | SARS-CoV-2, titre | **glass / stainless steel / Teflon → artificial skin** | droplet **still wet** | 3 N light force | **13–16 %** | not stated | B |
| Behzadinasab 2021, same | SARS-CoV-2, titre | same | **after evaporation** | 3 N | **3–9 %** | — | B |
| Pitol 2024, *PLOS One*, DOI 10.1371/journal.pone.0325235 | SARS-CoV-2 (Phi 6 used to validate the skin model against volunteers' fingers) | **plastic and metal → LabSkin 3D skin model** | dried inoculum | not stated | **~13 %** | not stated | B |
| Walker 2022, *Viruses*, DOI 10.3390/v14051048 | artificial and pooled human saliva as a **tracer**, not a virus assay | **high-touch surfaces → artificial finger pad** | aerosol-deposited, RH-controlled | **15 N, 1 s** | **< 10 %** at RH < 40 %; rising to **~50 %** maximum above RH 40 % | not stated | B |
| Rusin 2002, *J Appl Microbiol*, DOI 10.1046/j.1365-2672.2002.01734.x | pooled *M. luteus*, *S. rubidea*, phage PRD-1 | **phone receiver → hand**; **kitchen faucet → hand** | normal-use, inoculum not dried to a stated schedule | ordinary usage, not standardised | **38.5–65.8 %** (receiver); **27.6–40.0 %** (faucet) | volunteers, not stated | B |

**What the pickup direction supports.** Restricting to norovirus and norovirus
surrogates on non-porous materials with the moisture state stated, the
infectivity measurements run **2.0 % to 24 %** (Tuladhar 2.0 ± 2.0 % dried;
Bidawid 7 ± 1.9 % air-dried; Grove 24 % moisture unstated), with human-NoV
**genomic** transfer at **2–11 %** dry and **1–50 %** wet (Sharps) bounding it
from above. Widening to all analogous viruses and tracers on non-porous
donors, the same direction spans roughly **0.5 % to 80 %**, with humidity
(Lopez, Walker) and time since deposition (Ansari) each worth an order of
magnitude inside that span.

## 3. Direction B — hand → surface, non-porous recipients

| Source | Organism / assay | Donor → recipient | Moisture | Contact | Transfer fraction | n | Grade |
|---|---|---|---|---|---|---|---|
| Tuladhar 2013, DOI 10.1016/j.ijfoodmicro.2013.09.018 | MNV-1, infectivity | **finger pad → stainless steel** | **immediate (wet)** | 0.8–1.9 kg/cm², ~2 s | **13 ± 16 %** (1st transfer), falling to 0.003 ± 0.009 % by the 6th | 7 sequential transfers | B |
| Tuladhar 2013, same | MNV-1, infectivity | **finger pad → stainless steel** | **dried 10 min** | as above | **0.1 ± 0.2 %** (1st), 0.013 ± 0.023 % by the 5th | as above | B |
| Grove 2015, DOI 10.1016/j.ijfoodmicro.2014.12.023 | MNV-1, infectivity | **contaminated hand → stainless steel spigot** | not stated in abstract | task-realistic | **0.6 %** (−0.2-log transfer %) | ≥ 9 | B |
| Sharps 2012, DOI 10.4315/0362-028x.jfp-12-052 | **human NoV GII**, RT-qPCR genome copies | **gloved fingertip → stainless steel** | **wet** | immediate | **58–60 %** | not stated | B |
| Sharps 2012, same | human NoV GI + GII + MNV-1 cocktail, genome copies | **gloved fingertip → stainless steel** | wet | immediate | **20–70 %** | — | B |
| Sharps 2012, same | as above, genome copies | fingertip → **all** recipient surfaces | **dry** | — | **< 1 %** (GII), 4–12 % (cocktail) | — | B |
| Bidawid 2004, DOI 10.4315/0362-028x-67.1.103 | feline calicivirus, infectivity | **finger pad → brushed stainless steel disk** | air-dried, transferred after drying | 0.2–0.4 kg/cm², 10 s | **13 ± 3.6 %** | not stated | B |
| Dallner 2021, *Viruses*, DOI 10.3390/v13071352 | MNV-1, infectivity, cellular maintenance medium | **contaminated hand → stainless steel** | medium-suspended | not stated | **9.19 %** | not stated | B |
| Dallner 2021, same | human coronavirus OC43, infectivity, **in faecal material** | hand → stainless steel | faecal matrix | not stated | **0.52 %** (no transfer at all without organic material, and none for 229E) | not stated | B |
| Ansari 1988, DOI 10.1128/jcm.26.8.1513-1518.1988 | human rotavirus Wa, infectivity | **contaminated hand → clean steel disk** | dried, contact at 20 / 60 min | ~1 kg/cm², 10 s | **16.1 %** (20 min); **1.8 %** (60 min) | not stated | B |
| Ansari 1991, DOI 10.1128/jcm.29.10.2115-2119.1991 | human parainfluenza 3, infectivity | finger → metal disk | dried 20 min | 5 s | **not detectable** | not stated | B |
| Zhang 2026, *Int J Hyg Environ Health*, DOI 10.1016/j.ijheh.2026.114766 | influenza A, **RT-qPCR genomic RNA**, artificial skin | hand ↔ fomite, both directions | multifactorial | contact force varied (n.s., *P* = 0.313) | **direction effect significant (*P* < 0.001)**; no usable per-direction value in the abstract | 74 experiments / 444 events | B, magnitude not extractable |

**What the deposit direction supports.** On non-porous recipients with the
organism and moisture named, the deposit direction splits cleanly by moisture
rather than forming one interval:

* **wet / immediate:** **9.2 % to 60 %** (Dallner 9.19 %, Tuladhar 13 ± 16 %,
  Sharps GII 58–60 % in genome copies).
* **dried:** **0.1 % to 1.8 %** (Tuladhar 0.1 ± 0.2 %, Grove 0.6 %,
  Sharps < 1 %, Ansari 1.8 % at 60 min).

Bidawid's 13 ± 3.6 % is the one measurement that does not fit that split: the
inoculum was air-dried, yet it lands with the wet group. The likely reason is
timing — Bidawid transferred once, immediately after drying, at 0.2–0.4 kg/cm²,
where Tuladhar's dried value is measured after a further ten minutes and
Ansari's after twenty to sixty. Recorded here as a real disagreement rather
than dropped: it is the reason the dried interval above should not be read as
tight.

## 4. The third direction nobody asked for, and it matters here — hand → hand

The engine field named `contact_transfer_fraction` is applied to
**person-to-person** direct contact (§7), so the hand → hand measurements are
the ones nearest its meaning. There are only three, none of them norovirus:

| Source | Organism / assay | Contact | Moisture | Transfer fraction | Grade |
|---|---|---|---|---|---|
| Ansari 1988, DOI 10.1128/jcm.26.8.1513-1518.1988 | human rotavirus Wa, infectivity, faecal suspension | contaminated hand pressed to clean hand, ~1 kg/cm², 10 s | dried, at 20 min / 60 min | **6.6 %** (20 min); **2.8 %** (60 min) | B |
| Ansari 1991, DOI 10.1128/jcm.29.10.2115-2119.1991 | rhinovirus 14, infectivity | finger → finger, 5 s | dried 20 min | **0.7–0.9 %** | B |
| Ansari 1991, same | human parainfluenza 3, infectivity | finger → finger, 5 s | dried 20 min | **not detectable** | B |

So the hand → hand direction spans **0.7 % to 6.6 %** across two viruses,
below both fomite directions in the same assays, and **there is no norovirus or
norovirus-surrogate measurement of it at all** — see the null in §6.3.

Mbithi 1992 (*J Clin Microbiol*, DOI 10.1128/jcm.30.4.757-763.1992) measured
HAV finger → finger alongside finger → disk and disk → finger, but the abstract
reports the three modes as one pooled PFU range (2,667–3,484 PFU transferred at
20 min of drying from a ~10⁴ PFU inoculum, i.e. roughly 27–35 %, falling to
0–50 PFU by 4 h). Because the pooling is across directions, the percentage is
not attributable to any one of them and is not used in an interval; the paper
is retained for its pressure and friction effect sizes (§1).

## 5. Rejected candidates, with the reason

Not clutter — each of these will be re-found by the next reader, and the reason
for the omission should not have to be guessed.

**Rejected as direction-free (the abstract's headline number pools both
directions):**

| Candidate | Number | Why rejected |
|---|---|---|
| Anderson 2021, *Appl Environ Microbiol*, DOI 10.1128/aem.01215-21 | MS2 mean **0.26**, Phi6 mean **0.17**, 360 events, 20 volunteers, stainless steel / painted wood / plastic | The means are explicitly "all surfaces and both transfer directions combined". Used here only for its **sign**: MS2 transfers significantly more readily surface → finger than finger → surface. The per-direction distributions are in the paper's data set, not its abstract, and were not opened for this tranche. |
| Julian 2010, *J Appl Microbiol*, DOI 10.1111/j.1365-2672.2010.04814.x | **0.23 ± 0.22**, 656 events, 20 volunteers, MS2/φX174/fr, **glass** | Direction-free mean; direction reported as a significant factor without per-direction values in the abstract. Glass is non-porous but is not a maritime material pair. |
| Zhang 2026, DOI 10.1016/j.ijheh.2026.114766 | direction effect *P* < 0.001 | Direction significant but no per-direction magnitude in the abstract; genomic RNA on artificial skin. Kept in §3 as directional evidence only. |

**Rejected as model output, not measurement** (adopting any of these while the
model is scored on attack rates would be circular):

| Candidate | Why rejected |
|---|---|
| Wilson 2020, *J R Soc Interface*, DOI 10.1098/rsif.2020.0121 | Transfer efficiencies are ABC-inferred posteriors, not direct measurements. Grade C by construction. |
| Canales 2019, *J Occup Environ Hyg*, DOI 10.1080/15459624.2018.1531131 | Outputs are infection/illness risks (70–72 % / 21–70 %) and a 25–82 % fomite contribution from a simulation seeded with outbreak surface concentrations. No transfer fraction is measured; the outputs are compared against attack rates. |
| Jin 2022, *Int J Infect Dis*, DOI 10.1016/j.ijid.2022.05.047 | Video observation feeding a surface-transmission model; reports modelled intake change, not a transfer fraction. |
| Zhang 2021, *Build Environ*, DOI 10.1016/j.buildenv.2020.107578 | 98,000 observed touches are a real measurement of **touch behaviour**, but every transferred-virus figure (3 %, 53 %, 65 %, 93 %) is a simulation output. Relevant to contact rates, not to this quantity. |
| Chang 2025, *J Environ Manage*, DOI 10.1016/j.jenvman.2025.128184 | Force-dependent transfer *model* combining lab measurements with behavioural data; the reported 20–86 % figures are exposure differences between model variants. |
| Pérez-Rodríguez 2019, DOI 10.1016/j.ijfoodmicro.2018.09.029; Iulietto 2020, DOI 10.2903/j.efsa.2020.e181106; Kraay 2018, DOI 10.1186/s12879-018-3425-x; Abney 2024, DOI 10.1007/s12560-023-09580-1; Wilson 2020 AJIC, DOI 10.1016/j.ajic.2019.09.010 | QMRA / transmission models that **consume** transfer fractions from the papers in §2–§4. Citing them would launder a primary measurement through a model and lose its moisture and direction conditions. |

**Rejected on material — porous or food surfaces, a different quantity:**

| Candidate | Number | Why rejected |
|---|---|---|
| Rönnqvist 2014, *Appl Environ Microbiol*, DOI 10.1128/aem.01162-14 | glove → cucumber 1.5 ± 1.9 % (HuNoV), 1.2 ± 0.6 % (MNV); cucumber → glove 0.5 ± 0.4 % / 0.7 ± 0.5 % | Food material; also glove rather than skin. Direction-specific and well measured, but not a maritime surface pair. |
| Tuladhar 2013 (food legs) | finger → cucumber slices 7 ± 8 %, → tomatoes 0.3 ± 0.5 % | Food; the paper itself attributes the difference to the cucumber's moisture content. |
| Bidawid 2004 (food legs) | finger → ham 46 ± 20.3 %, → lettuce 18 ± 5.7 %; ham → hand 6 ± 1.8 %, lettuce → hand 14 ± 3.5 % | Food materials. |
| Dallner 2021 (food legs); Wang 2012 ×2; Escudero 2012; Verhaelen 2013; Stals 2013; Derrick 2021; Grove's lettuce/board/knife legs (25 %, ~100 %, 2.1 %, 1.2 %) | — | Food or utensil-to-food pairs. Stals 2013 additionally gives no per-direction number in the abstract beyond "stainless steel → gloves more efficient than gloves → stainless steel". |
| Sattar 2001, DOI 10.1046/j.1365-2672.2001.01347.x; Marples 1979, DOI 10.1017/s0022172400025651 | fabric ↔ hand; 10 % moist / 0.05 % dried, 85 % wet hand → fabric | Porous fabric, and bacteria not viruses. Retained here only as independent confirmation that drying costs ~2 logs on the deposit direction. |
| Rusin 2002 porous fomites | **< 0.01 %** | Porous; quoted in §1 for the porous/non-porous contrast only. |

**Rejected on other grounds:**

| Candidate | Why rejected |
|---|---|
| Gwaltney 1978, *Ann Intern Med*, DOI 10.7326/0003-4819-88-4-463 | Reports that virus transferred in **20 of 28 (71 %)** 10-s hand contacts. That is a *frequency of detectable transfer events*, not a fraction of load — a different quantity with a different denominator. |
| Abney 2022, *J Appl Microbiol*, DOI 10.1111/jam.15758 | MS2 1.10 ± 0.81 % (PBS) / 3.02 ± 4.03 % (ASTM soil load) is labelled "hand-to-toilet seat" while the method describes sampling hands **after lifting** an inoculated seat. Direction is ambiguous in the abstract, so it cannot be filed under either. Its finger → lip values (23–53 %) are a mucosal transfer, a third quantity again. |
| Wolfensberger 2018, DOI 10.1017/ice.2018.156 | Pooled transfer **frequencies** (33 % / 30 % / 10 % of contacts) from a healthcare meta-analysis, not fractions of load, and mostly bacteria. |
| Sattar 1993, *Appl Environ Microbiol*, DOI 10.1128/aem.59.5.1579-1585.1993 | Rhinovirus disinfectant-intervention study; the abstract gives no clean untreated baseline transfer fraction. |
| Bidawid 2004 / Grove 2015 / Eggers 2023 hand-hygiene arms | Post-intervention transfer (≤ 0.9 % after washing; 2.8–3.0 log reductions) measures an intervention, not the untreated contact quantity. |
| Marano 2026, DOI 10.1186/s12866-026-05312-0; Chareyre 2025, DOI 10.1128/aem.00802-25; Cunliffe 2026, DOI 10.1128/aem.02304-25; Patil 2025, DOI 10.1016/j.fm.2025.104901; Chen 2001, DOI 10.4315/0362-028x-64.1.72 | Bacterial/antimicrobial-surface or food-processing methods work. The 3–17 % interlaboratory bacterial surface transfer in Marano is a method-validation artefact spread, not a pathogen transfer fraction. |
| Pitol 2018 data set, DOI 10.25678/000099 | Finger ↔ **water/saliva** transfer (skin–liquid interface), not a solid surface pair. |
| Anderson 2021 bioRxiv, DOI 10.1101/2021.06.22.449538 | Preprint duplicate of the published paper already recorded. |

## 6. Null results

**6.1 No measurement of this quantity in a maritime setting, at all.** No study
returned by any of the seven queries measured hand/surface transfer on a ship,
or on a handrail, buffet tong, cabin fixture or any other named maritime
object. Every value above is Grade **B** on setting alone. The nearest
material analogues are stainless steel (galley, handrails), plastic and
laminate (Trespa®, cabin fixtures), and the nearest realistic-task measurement
is Grove's water spigot in a food-service kitchen.

**6.2 No human-norovirus *infectivity* transfer measurement exists in either
direction.** Human NoV does not culture readily, so every HuNoV transfer number
found (Sharps 58–60 % wet, < 1 % dry, 1–50 %/2–11 % pickup; Rönnqvist;
Tuladhar's GI.4 and GII.4 legs) is in **genome copies by RT-qPCR**. Every
*infectious* transfer number is a surrogate: MNV-1, feline calicivirus, MS2,
Phi6, φX174, fr, poliovirus 1, or a non-norovirus (rotavirus, rhinovirus,
HPIV-3, HCoV, SARS-CoV-2). A genomic transfer fraction is an upper bound on
the infectious one and must not be presented as a norovirus measurement.
This caps the whole quantity at Grade **B**: there is no Grade A available for
norovirus contact transfer anywhere in this literature.

**6.3 No norovirus measurement of hand → hand transfer.** The person-to-person
direction has been measured for rotavirus, rhinovirus, HPIV-3 and HAV, and for
none of norovirus, MNV-1, FCV or any phage surrogate. This is the null that
bears directly on the engine field (§7).

**6.4 No study measures the engine field's definition.** The schema defines
`contact_transfer_fraction` as "fraction of a contacted partner's **emission**
that reaches the target". No transfer assay in this literature uses emission as
its denominator; all of them use *the inoculum recovered from the donor surface
at the moment of contact*, after a deliberate deposition of a known titre.
There is no measured quantity whose denominator is a shedding rate, and no
experiment in which the donor's virus arrived on the hand by shedding rather
than by pipette. As defined, the field is **not measurable in this
literature** — which is a statement about the field's definition, not about the
strength of the evidence in §2–§4.

## 7. What `contact_transfer_fraction` actually is in this repository, and what the ~0.25 can and cannot be

Two distinct mechanisms are involved and the register row must not blur them:

* **`contact_transfer_fraction`** (`engines/transmission_core.py`, read in the
  direct-contact pathway; default **1.0** when no profile sets it, and neither
  active profile sets it) multiplies the dose a susceptible agent receives from
  **the partners it contacts** — `_direct_contact_dose` and
  `_per_partner_contact_dose`. It is a person-to-person quantity. Its nearest
  measured analogue is §4 (hand → hand, 0.7–6.6 %, no norovirus data), and its
  literal definition is unmeasurable (§6.4).
* The **fomite chain** is a separate mechanism with its own already-directional
  constants, `SURFACE_TO_HAND_LOGNORMAL` and `HAND_TO_SURFACE_LOGNORMAL`. §2
  and §3 are evidence about *these*, not about the field named
  `contact_transfer_fraction`.
  `docs/literature/edison_norovirus_influenza_bundle_review.md` already records
  one instance of surface-transfer values being mapped onto the wrong field;
  this tranche does not repeat it, and proposes no mapping either way.

**The trace, and its outcome.** The ~0.25 anchor recorded in
`docs/norovirus/norovirus_model_history.md` §10 is numerically indistinguishable
from three different things in this literature:

* Anderson 2021's MS2 mean **0.26** — direction-free, three surfaces pooled;
* Julian 2010's **0.23 ± 0.22** — direction-free, glass;
* Grove 2015's **24 %** — a single direction (surface → hand), MNV-1.

Nothing in the repository states which, and the three have different meanings,
so the anchor **cannot be attributed to a primary measurement** on the evidence
available; it is consistent with a direction-free surrogate pooled mean having
been read as a general "contact transfer efficiency". That is a refutation of
its *status*, not of its magnitude: as a **direction-free** contact transfer
fraction it is refuted, because §1–§3 show the two directions differ by up to
two orders of magnitude under drying and no single number represents both.

**Where 0.25 sits, as arithmetic only** — no recommendation follows from any
line of this:

| Interval from this tranche | 0.25 relative to it |
|---|---|
| surface → hand, non-porous, norovirus + surrogates, infectivity, **2.0–24 %** | **at the top edge**, essentially equal to Grove's 24 % |
| surface → hand, all analogous viruses/tracers, non-porous, **0.5–80 %** | inside |
| hand → surface, non-porous, **wet, 9.2–60 %** | inside |
| hand → surface, non-porous, **dried, 0.1–1.8 %** | **above, by roughly 14× to 250×** |
| hand → hand, **0.7–6.6 %** (no norovirus data) | **above, by roughly 4× to 36×** |
| the shipped screen interval `0.06–0.50` (Grade B, `bounded_screen.py`) | inside |
| the engine's effective value, **1.0 by omission** | far below |

The Morris screen in PR #368 found this factor clears none of the measured
noise floor (`docs/norovirus/bounded_screen_results.md`). That is a statement
about the factor's influence and it is not evidence that any value of it is
correct; it did not license a loose bound here, and none of the intervals above
was widened or narrowed to accommodate it.

## 8. Queries run, verbatim

All seven were run against the Consensus MCP `search` tool. **All were
unfiltered** except for the noted `page` argument on Q5.

1. `hand to hand virus transfer efficiency between people fingerpad to fingerpad contact`
2. `transfer efficiency dried versus wet inoculum non-porous surface to finger relative humidity percent transferred`
3. `fraction of pathogen dose transferred during person to person physical contact quantitative direct contact route`
4. `norovirus transfer hand to hand between volunteers percent infectious virus transferred` — with `page: 1`
5. `murine norovirus transfer coefficient log transfer percentage hand to spigot cutting board cross-contamination`
6. `norovirus transfer efficiency surface to hand and hand to surface stainless steel direction`
7. `fraction of virus transferred single contact fingerpad fomite transfer efficiency quantitative measurement`

Each returned 20 results; each result set was read in full from the overflow
file named in its truncation notice. Queries 1–3 and 7 deliberately avoided the
word "norovirus" so that the mechanism literature would not be crowded out by
norovirus reviews and QMRA models; queries 5 and 6 named the organism and the
material to reach the food-service and direction-specific measurements. Q5 was
the query that returned **Grove 2015 as its first result** — the paper
`docs/literature/consensus_tranche_5.md` §2b recorded as not reliably
retrievable by targeted search. Its numbers are now confirmed from the
Consensus abstract: 24 % spigot → hand versus 0.6 % hand → spigot, ≥ 9
replicates per scenario, MNV-1, log-transformed transfer percentages. Tranche
5's provenance null on Grove is retired; correcting that document is not this
unit's to do.

## 9. Limits of this tranche

* **Abstracts, not Results sections.** Every number above is taken from the
  Consensus abstract. For the four papers that carry the intervals — Tuladhar,
  Sharps, Grove and Bidawid — the moisture state, material pair and assay are
  stated *in* the abstract, which is why they are usable at all; but the
  dispersions (Tuladhar's ± 16 % on a 13 % mean) and the exact denominators
  come from text, not tables. Anderson's and Julian's per-direction
  distributions exist in their data sets and would settle the pickup/deposit
  ratio properly for phage. Fetching those four DOIs and Anderson's data set is
  the obvious next step and was not done here.
* **Grove's moisture state is unstated**, and it is the single measurement
  nearest both the 0.25 anchor and a realistic maritime task. Its 24 % sits
  with the *wet* group in every other paper's pattern, which would matter for
  any use of it.
* **No maritime measurement exists** (§6.1), so nothing here can be graded A,
  and no amount of further searching in this literature will change that.
