# Tranche 36 — the near field is a two-ring seating structure and a shared bedroom, both bounded by measurement; its effective volume is measured nowhere

**Register rows fed / supersession.** Runs §6 of
[`../near_field_air_spec.md`](../near_field_air_spec.md)
(`AERO-NEAR-01`) and feeds the open ledger's §4 item 16. It **supersedes
nothing** and **withdraws no measurement**. It moves no constant, and it adopts
none: the near-field structure it licenses is topology, and the one magnitude
the structure needs — the near-field effective volume, or equivalently the
near/far exchange rate — is **∅ null on search** and must ship as declared
geometry with a swept exchange axis.

**Status:** Evidence assembled and interpreted. Nothing implemented in this
tranche; `CONTACT-SCALE-01` is unblocked by it, not decided by it.
`AERO-NEAR-01` has since landed on the structure licensed here, off by default
and with no magnitude adopted — the two rings became `retained_fraction` and
`neighbour_table_ratio` as swept axes over declared geometry, and question 4's
null kept `norwalk_gi` out of the continuous near field
([`../near_field_air_spec.md`](../near_field_air_spec.md) §10).

**Source discipline.** The Consensus MCP account is **exhausted for the
period** ("You've used all 500 included searches this month; resets on
October 1st"). Under `docs/sourcing_protocol.md` a blocked read is **not a
null result**, so every row below was retrieved by the approved open-full-text
fallback: Europe PMC REST `fullTextXML`, or the publisher's open PDF for the
one paper PMC holds only as a scan (Marks 2000, read from the Cambridge Core
PDF). Origins are marked **R** (Results prose), **T** (table), **F** (figure),
**A** (abstract only). Where a number is a **CFD prediction** rather than a
measurement it is labelled so in place; the distinction is load-bearing here,
because the only per-table dose ratios that exist are modelled.

**Scope:** the four questions of the proposal's §6 — near/far concentration
versus distance, the Guangzhou restaurant's ring structure, the cabin analogue,
and whether norovirus inhalation extends beyond emesis.

**Result in one line.** The near field is **real and bounded**: at seated
conversational distance a breath tracer runs **~36–44% above the other
distances in the first 20 min** and only **~18% above the volume average by
60 min** (Parhizkar 2022, 27 m³ chamber, ~3 ACH); the Guangzhou restaurant
gives a **two-ring** structure and nothing finer — same-table and
same-air-stream tables at **0.76–1.04** of the index table, the two remaining
tables in the same HVAC zone at **0.40–0.47**, every remote table at
**0.04–0.23** (CFD exposure, Table 3); sharing a bedroom is **aOR 2.99
(1.35–6.71)** and **aOR 4.5 for sharing versus not (1/0.22, 0.10–0.41)** in two
independent SARS-CoV-2 household cohorts, converging on the cruise record's
cabin-mate **RR 3.0 / aOR 3.27**; and for norovirus the airborne route is
**emesis-conditioned and nothing else is supported** — the only distance
gradient in the record is Marks 2000's attack rate by table around a vomiting
diner, **91% → 71% → 56% → 50% → 40% → 25%**. No study measures a near-field
volume, a table's or cabin's near/far exchange rate, or a norovirus inhaled
infectious dose.

---

## 1. Near field versus far field, by distance (§6 question 1)

**Parhizkar H, Fretz M, Laguerre A, Stenson J, Corsi RL, Van Den Wymelenberg
KG, Gall ET (2022).** *A novel VOC breath tracer method to evaluate indoor
respiratory exposures in the near- and far-fields; implications for the spread
of respiratory viruses.* J Expo Sci Environ Epidemiol. DOI
10.1038/s41370-022-00499-6, PMC9686220. Grade **B** — direct measurement, but
of a **VOC breath tracer from one healthy participant** (breath mints), not of
virus, and in a chamber, not a dining room.

| quantity | value | origin |
|---|---|---|
| chamber volume | **27 m³** | R (Methods) |
| ventilation during trials | **~3 ACH** (flushed >20 ACH between trials) | R (Methods) |
| measurement distances from the mouth | **0.76 / 1.52 / 2.28 m**, plus the floor exhaust plenum as the **volume-averaged** reference | R (Methods) |
| first 20 min, 0.76 m versus the other distances | **~36–44% higher** | R (Abstract + Results) |
| after 20 min, approaching 60 min, versus volume average | **~18% (0.76 m), ~11% (1.52 m), ~7.5% (2.28 m)** | R (Abstract + Results) |
| trial length / replication | 1 h per location, **duplicate** trials in random order over 3 days, 1 s resolution | R (Methods) |

Three things this licenses and one it refuses:

- **It licenses the two-compartment form**, and it licenses it as
  *time-dependent*: the near-field enhancement is largest at the start of an
  occupancy event and decays toward the well-mixed value as the plume is mixed
  into the room. A meal is a 1–2 h event; a night in a cabin is 8–9 h.
- **It bounds the steady-state enhancement at a seated 0.76 m to tens of
  percent, not orders of magnitude**, for a room ventilated at ~3 ACH. The
  large near-field ratios that appear in the modelling literature are for
  shorter timescales, closer distances, or unventilated rooms.
- **It refuses a distance kernel.** Three distances in one chamber at one ACH
  is not a curve; the enhancement's dependence on ACH, room volume and
  geometry is unmeasured here, and the model's zones span 20–1,050 m³.
- **It does not give an effective volume.** The paper reports concentration
  ratios, not the volume a near-field compartment would have. See §5.

## 2. The Guangzhou restaurant: how many rings the record supports (§6 question 2)

**Li Y, Qian H, Hang J, Chen X, Cheng P, Ling H, Wang S, Liang P, Li J, Xiao S,
Wei J, Liu L, Cowling BJ, Kang M (2021).** *Probable airborne transmission of
SARS-CoV-2 in a poorly ventilated restaurant.* Build Environ 196:107788. DOI
10.1016/j.buildenv.2021.107788, PMC7954773. Grade **B** for the epidemiology
and the tracer measurement (real outbreak, measured ethane decay and
dispersion); the per-table **exposure** column is a **CFD prediction**, graded
**model output** and never to be read as a measured dose.

Setting (R, Methods/Results): **431 m³**, **89 patrons at 18 tables**, measured
air exchange **0.77 ACH (16:00–17:00)** and **0.56 ACH (18:00–19:30)** →
**1.04 and 0.75 L/s per patron**, average **0.9 L/s per person**. Ten cases in
three neighbouring tables (A, B, C); **none of the 68 patrons at the other 15
tables** and no staff.

Zone attack rates (**T**, Table 2):

| zone | patrons | infected | attack rate | rate difference (95% CI) |
|---|---:|---:|---:|---|
| immediate neighbouring tables | 16 | 5 | **31.25%** | 31.25 (8.54, 53.96) |
| remote neighbouring tables | 63 | 0 | **0%** | — |
| air-conditioning **ABC zone** | 11 | 5 | **45.45%** | 45.45 (16.03, 74.88) |
| non-ABC zone | 68 | 0 | **0%** | — |

Per-table concentrations and exposures (**T**, Table 3; measured tracer exists
for only 6 of 18 tables):

| table | patrons | AR % | measured tracer (norm.) | predicted tracer (norm.) | **predicted droplet-nuclei exposure (norm.)** |
|---|---:|---:|---:|---:|---:|
| TA (index) | 10 | 50.00 | 1.00 | 1.00 | **1.00** |
| TB | 4 | 75.00 | 0.87 | 1.04 | **0.76** |
| TC | 7 | 28.57 | 0.98 | 0.93 | **0.89** |
| T17 | 5 | 0 | 0.86 | 0.75 | **0.47** |
| T18 | 5 | 0 | 0.73 | 0.85 | **0.40** |
| T10 / T15 / T16 | 6 / 8 / 5 | 0 | 0.55 / 0.58 / 0.70 | 0.52 / 0.54 / 0.56 | **0.08 / 0.23 / 0.06** |
| T04–T09, T11–T14 | 0–10 | 0 | – | 0.32–0.63 | **0.00–0.13** |

Measured ethane over 66.67 min (**R**): TA/TB/TC **1.00 / 0.92 / 0.96**, T17
**0.86**, T18 **0.73**, other remote tables **0.55–0.70** — i.e. the *tracer
gas* is nearly uniform, and it is the **droplet-nuclei exposure** (5 μm, with
deposition, 20% AC filtration and virus deactivation modelled) that separates
the rings by an order of magnitude.

**What this licenses:** exactly the **two rings** of the proposal's §5 — the
party at the table, and the tables sharing the local air stream — plus the
already-modelled far field. Ratios, index table = 1: **same air stream
0.76–1.04**, **same HVAC zone but downstream 0.40–0.47**, **remote
0.04–0.23**. **What it refuses:** a continuous distance kernel (the paper's own
separation is by air stream and HVAC zone, not by metres), any claim that these
are measured doses, and any transfer of the magnitudes to a ventilated room —
this restaurant ran at **0.9 L/s/person**, roughly a fifth of the ~4.7 L/s/person
that ASHRAE-style dining-room ventilation implies, and the paper's own
conclusion is conditioned on that.

## 3. The cabin analogue: sharing a bedroom (§6 question 3)

Two independent SARS-CoV-2 household cohorts measure the quantity the cabin
needs — the risk of the *contact* who shares the sleeping compartment, against
household members who do not:

| study | quantity | value (95% CI) | origin | grade |
|---|---|---|---|---|
| **Brown ER, O'Brien MP, Snow B, Isa F, Forleo-Neto E, Chan K-C, Hou P, Cohen MS, Herman G, Barnabas RV (2023)**, *A Prospective Study of Key Correlates for Household Transmission of SARS-CoV-2*, Open Forum Infect Dis, DOI 10.1093/ofid/ofad271, PMC10319621; **n = 943** contacts, placebo arms of two prospective trials | contact **shares bedroom** with index, multivariable | **aOR 2.99 (1.35–6.71)**; univariable 2.88 (1.32–6.32); whole-household-enrolled subset 3.80 (1.34–10.68) | **T** (correlates table) | **B** |
| same | source viral load, per log₁₀ copies/mL | aOR 1.40 (1.07–1.85) | **T** | **B** |
| **Sun K, Loria V, Aparicio A, … Prevots DR (2023)**, *Behavioral factors and SARS-CoV-2 transmission heterogeneity within a household cohort in Costa Rica*, Commun Med, DOI 10.1038/s43856-023-00325-6, PMC10363136 | **not** sharing a bedroom with the index case | **aOR 0.22 (0.10–0.41)** → sharing ≈ **×4.5 (2.4–10)** | **R** (Abstract/Results) | **B** |
| same | household secondary attack rate | 34% (5–75%); 30% of index cases produce 80% of secondary cases | **R** | **B** |

These converge with the two cruise-setting cabin estimates already on the
record in [tranche 35](consensus_tranche_35_crew_berthing.md): ill cabin-mate
**RR 3.0** in a passenger norovirus cohort (Wikswo 2011) and **aOR 3.27** among
crew on *Roald Amundsen* (Kordsmeyer 2022). Four independent estimates, two
pathogens, two settings, all in **×3–×4.5**.

**Influenza bedroom-sharing is ∅ null on search.** A targeted open-access query
for influenza household transmission stratified by bedroom sharing returned
only SARS-CoV-2 household cohorts; the influenza household literature
stratifies by relationship, age and household size, not by sleeping
compartment. The cabin analogue therefore rests on the SARS-CoV-2 and
norovirus rows above, and the influenza arm inherits the **structure**, not a
magnitude.

**What this licenses:** the cabin as an air compartment, and an expectation of
the **direction and rough size** of the effect once it is one — a factor of
three or so on a cabin-mate's risk, not a factor of twenty. **What it refuses:**
using ×3 as a near-field parameter. These are odds ratios on infection, jointly
determined by air, direct contact and the cabin's fomites — three routes the
model already has, two of them already cabin-scoped by `BERTH-01`. Adopting ×3
as an *aerosol* multiplier would double-count the two that exist. The
post-repair check is: does the repaired cabin **produce** a cabin-mate odds
ratio in that range, with no term fitted to it?

## 4. Norovirus inhalation beyond emesis (§6 question 4) — null, and the null is a finding

**Alsved M, Fraenkel C-J, Bohgard M, Widell A, Söderlund-Strand A, Lanbeck P,
Holmdahl T, Isaxon C, Gudmundsson A, Medstrand P, Böttiger B, Löndahl J
(2020).** *Sources of Airborne Norovirus in Hospital Outbreaks.* Clin Infect
Dis. DOI 10.1093/cid/ciz584, PMC7201413. (Cited in the ledger and register as
Alsved 2019 by online-first year; same paper.) Grade **B**.

- **21 of 86** air samples, from **10 of 26** patients, contained norovirus RNA
  (**R**); positives occurred in outbreak wards or shortly before an outbreak.
- **OR 8.1** for a sample taken **within 3 h of a vomiting episode** (**R**).
- Concentrations **5–215 copies/m³** (**R**); RNA in fractions **<0.95 μm** and
  **>4.51 μm**.

**Tan M, Tian Y, Zhang D, Wang Q, Gao Z (2024).** *Aerosol Transmission of
Norovirus.* Viruses 16(1):151. DOI 10.3390/v16010151, PMC10818780. Grade **B**
(review; used for what is and is not established, not for a value): aerosol
transmission is **less common** than contact, food and water; **most reported
aerosol events involve vomiting**; infectivity of airborne norovirus, toilet-flush
aerosolisation, diarrhoea-associated aerosolisation and respiratory emission
(coughing, talking, breathing) are all listed as **unresolved**.

The one distance gradient in the norovirus record is the outbreak the register
already cites for a different purpose — **Marks PJ, Vipond IB, Carlisle D,
Deakin D, Fey RE, Caul EO (2000)**, *Evidence for airborne transmission of
Norwalk-like virus (NLV) in a hotel restaurant*, Epidemiol Infect 124:481–487,
DOI 10.1017/s0950268899003805, PMC2810934 (PMC scan; read from the Cambridge
Core open PDF). One diner vomited at table 2 during a meal for **126 guests in
six parties**, **83 questionnaires** returned, **52 ill**:

| table | attack rate | origin |
|---|---:|---|
| 2 (the vomiter's) | **91%** | **F** (Fig. 3, restaurant plan) |
| 1 | **71%** | **F** |
| 3 | **56%** | **F** |
| 4 | **50%** | **F** |
| 5 | **40%** | **F** |
| 6 (through an archway, separate room) | **25%** | **F** |

χ² = 12.97 on 4 df (P ≈ 0.01); **χ² for linear trend 11.47 on 1 df (P ≈
0.0007)**, deviation from trend 1.50 on 3 df (P ≈ 0.68) (**R**). No food was
implicated; nobody in the separate restaurant fell ill; an extractor fan sat in
the ceiling **almost directly above the vomiter** (**R**, **F**). Corroborating,
**Marks PJ et al. (2003)**, *A school outbreak of Norwalk-like virus: evidence
for airborne transmission*, Epidemiol Infect 131:727–736, DOI
10.1017/s0950268803008689: pupils were more likely to fall ill after **a
vomiting episode in their own classroom, adjusted OR 4.1 (1.8–9.3)** (**A**;
full text not open — recorded as abstract-origin, not upgraded).

**Conclusion for the norovirus arm — a narrowing, not a failure.** The record
supports **no** continuous respiratory emission for norovirus; it supports a
**discrete-event** airborne source, which is exactly the shipped
`airborne_emission_mode = emesis_conditioned`. So the near-field unit for
norovirus is **whoever shares air with a vomiting host** — the table party and
the cabin — and the gradient it must be able to produce is Marks 2000's
91%→25% by table, not a per-diner distance kernel. Two channels the review
lists as unresolved are **absent from the model and remain unlicensed**:
toilet-flush aerosol (which would attach to the cabin toilet `BERTH-01` already
made a fomite compartment) and diarrhoea-associated aerosolisation. Neither may
be added without a measurement; both are now recorded as open.

## 5. The magnitude the structure needs, and does not have

`AERO-NEAR-01` requires one number the literature does not supply: the
**near-field effective volume** for a table party or a cabin — equivalently the
near/far **exchange rate** between the two compartments.

- Parhizkar 2022 gives **ratios at fixed distances in one 27 m³ chamber at
  3 ACH**, not a compartment volume, and no dependence on room size or ACH.
- Li 2021 gives **per-table exposures from CFD** in one 431 m³ restaurant at
  0.56–0.77 ACH; its rings are defined by air stream and HVAC zone, not by a
  volume.
- The household rows give **odds ratios on infection**, jointly over three
  routes.

Therefore, per `docs/sourcing_protocol.md`, the exchange parameter is **∅ null
on evidence** and must ship as a **declared swept axis**, with the near-field
volume derived from the **declared geometry already in each hull's
`spatial_layout.json`** (cabin volume from `cabin_size` and the MLC floor
areas of tranche 35; table volume from `dining_table_size` and seated spacing).
No point in that axis may be selected, and nothing in it may be chosen against
A5, A9, posting frequency, an attack-rate band, or a COVID trajectory anchor.

## 6. What this tranche licenses, in one table

| item | licensed | grade / origin | refused |
|---|---|---|---|
| two-compartment near/far air, far field unchanged | **yes** | B, Parhizkar 2022 R | any claim the near field dominates a whole meal at 3 ACH |
| time-dependence (enhancement decays over the event) | **yes**, qualitatively | B, Parhizkar 2022 R | a time constant transferable to 20–1,050 m³ zones |
| **two rings** at a meal: table party, then tables sharing the air stream | **yes** | B epi + model output, Li 2021 T2/T3 | a third ring, or a continuous distance kernel |
| ring ratios 1.00 / 0.40–1.04 / 0.04–0.23 as a **sanity envelope** | **yes, as an envelope** | **CFD prediction**, Li 2021 T3 | reading them as measured doses, or as cruise magnitudes (0.9 L/s/person) |
| cabin as an air compartment | **yes** | B ×4 convergent (2.99 / ×4.5 / RR 3.0 / aOR 3.27) | ×3 as an aerosol multiplier — three routes already share the cabin |
| norovirus near field = the vomiting host's table or cabin | **yes** | B, Alsved 2020 R; Marks 2000 R/F | continuous respiratory norovirus emission (∅) |
| Marks 2000's 91/71/56/50/40/25% by table | **yes, as the post-repair check** | R/F | fitting any near-field term to reproduce it |
| near-field effective volume / exchange rate | **no** | **∅ null on search** | any point value; ships as declared geometry + swept axis |
| influenza bedroom-sharing magnitude | **no** | **∅ null on search** | inheriting the SARS-CoV-2 aOR as an influenza value |
| toilet-flush and diarrhoea aerosol channels | **no** | review lists both unresolved | adding either channel |
