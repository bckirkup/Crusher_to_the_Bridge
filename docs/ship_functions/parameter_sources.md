# Ship-function capacity: parameter sources

> **Status:** Proposed — sourcing record for
> [`ship_function_capacity_spec.md`](ship_function_capacity_spec.md)
> (sourcing task SHIP-FUNC-01). Adopts no value, authorises no fit. Every row
> here is a spec-stage declaration: no `ship_functions`/`ship_systems`/fatigue
> field exists in-tree yet, so nothing in this document describes current
> behaviour.

## 0. Scope and reading rules

This document covers every tunable the ship-function capacity spec declares,
one row per tunable, under the provenance discipline of
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
§1 (classes M/B/I/A/C/P/F/X/S, origins R/Tn/Fn·dig/Me/Ab/Sec/Tr/?nr, states).
Retrieval followed the `searching-literature-evidence` and
`consensus-literature-retrieval` skills: every number below was read in a
Consensus full-text chunk or the returned abstract — §8 records the query,
the section, and the verbatim locator for each governing citation.

Three conventions this table uses:

- **Epoch = 1 hour** (`engines/sim_clock.py`), so a spec'd
  `fatigue_rate_per_epoch` is a per-wear-hour rate and the literature's
  per-hour-of-wear quantities map onto it directly.
- **Claim kind.** Each row is tagged `physical` (a claim about the world the
  literature could, in principle, measure) or `arm` (a dimensionless
  operational arm — a model dial whose *existence* is a design choice, not a
  physical assertion). Arms carry declared intervals; physical rows carry
  what was measured.
- **NULL-SOURCE.** An explicit `NULL-SOURCE` cell means the quantity was
  searched and no measurement of *that quantity* exists — it ships, if at
  all, as a declared assumption (`∅lit` in register terms). Construction
  fields (`health_start`, `degradation.model`, `labor_class`,
  `repair_priority`, `fatigue_susceptibility`, `capacity_multiplier_at_failure`)
  are `X`-class: unmeasurable by definition, and no source is owed.

## 1. `symptomatic_effectiveness` (spec §4)

Fraction of a watch a symptomatic crew member still delivers. The spec text
says "no source exists"; one does — it was under-searched, not absent.

| Parameter | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `symptomatic_effectiveness` | arm (dimensionless effectiveness) | **[0.55, 0.85]** declared widen of measured band | **B** | Sec | Nichol et al. (n = 497 working adults aged 50–64 with ILI), read via the Frimpter 2022 systematic review (PharmacoEconomics 40, DOI 10.1007/s40273-022-01224-9): workers reporting presenteeism "rated their level of work effectiveness to be **70–75% of normal** for the days they worked while ill" — mean 4.4 days of presenteeism per episode. Corroborator in the same review: ILI workers averaged 2.5 h/day reduced productivity vs 1.1 h non-ILI ≈ ~0.7 of an 8-h day. |

The measured band is [0.70, 0.75] on self-rated effectiveness during
influenza-like illness in office-age working adults; the shipped interval is
widened to [0.55, 0.85] because the spec's IMPAIRED state covers norovirus
gastroenteritis and other presentations whose decrement is plausibly larger
than ILI's, and because self-ratings correlate only weakly-to-moderately with
objective productivity (the WPAI instrumentation caveat — §8, row 1). This is
a dimensionless operational arm, not a physical rate; it sweeps, never tunes.

## 2. `ppe_types` registry values (spec §7.1)

Five types × three fields. The honest headline first: **no per-wear-hour
fatigue rate is measured anywhere in the literature** — every
`fatigue_rate_per_epoch` row is a declared arm. What the literature does
measure is (a) the *ordering* of burden across types, and (b) symptom
incidence at shift granularity. Both are recorded; neither is converted into
a fake rate.

### 2.1 `fatigue_rate_per_epoch` (≈ per wear-hour)

| Type | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `surgical_mask.fatigue_rate_per_epoch` | arm | NULL-SOURCE, declared [0.05, 0.30] | C | — | Lightest respiratory burden in every comparison (§2.2). |
| `n95.fatigue_rate_per_epoch` | arm | NULL-SOURCE, declared [0.20, 0.70] | C | — | N95 consistently worse than surgical on discomfort/fatigue symptoms (Su 2021; Scarano 2020; Li 2005). Rebmann 2013: mean ~200 min to first removal; prior work put average tolerance <8 h. |
| `papr.fatigue_rate_per_epoch` | arm | NULL-SOURCE, declared [0.20, 0.90] | C | — | Powell 2017: cardiopulmonary response ≈ N95 over 1 h treadmill; discomfort (not exertion) grows with wear time. Herstein 2021: full PAPR-*level ensemble* causes severe heat strain — the fatiguing object is the ensemble, not the blower. |
| `latex_gloves.fatigue_rate_per_epoch` | arm | NULL-SOURCE, declared [0.0, 0.20] | C | — | No fatigue-channel mechanism measured; hand fatigue from disposable gloves is small. |
| `chemical_gloves.fatigue_rate_per_epoch` | arm | NULL-SOURCE, declared [0.05, 0.50] | C | — | Thickness-scaled manual-task cost is real (§2.3) but that is dexterity, not fatigue; declared wider than latex. |

**Governing evidence for the ordering** (no governing numeric rate exists):

- Su et al. 2021 (RCT, 68 HCWs, 8 h, DOI 10.3390/ijerph182413308): N95
  produced significantly more shortness of breath, headache, dizziness,
  difficulty talking and fatigue than surgical masks; cites Lim et al.:
  headache in 37.3% of participants after >4 h N95 wear, 32.9% needing
  analgesia. Origin R/Sec.
- Rebmann et al. 2013 (AJIC 41, DOI 10.1016/j.ajic.2013.02.017): 90% of
  nurses tolerated two 12-h shifts; mean ~200 min to first removal; 22% of
  removals for discomfort; adjustments increased over time. Origin R/T1.
- Powell et al. 2017 (JOEH 14, DOI 10.1080/15459624.2017.1358817, 27 HCWs,
  7 respirators + medical mask, 8-h crossover): "discomfort increased
  over time with continual respirator use over an 8-hr period… exertion
  increased only marginally"; "respirator-related discomfort, but not
  exertion, negatively influences respirator tolerance". Origin R/Ab.
- ICU cohort (DOI via Consensus, prospective 75 HCWs): mean donning
  duration 3.1 h; exertion and discomfort rose significantly after 4 h of
  N95 + PPE. Origin R.

### 2.2 `heat_load`

| Type | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `surgical_mask.heat_load` | arm | NULL-SOURCE, declared [0.0, 0.20] | C | — | Lowest measured thermal burden (see below). |
| `n95.heat_load` | arm | NULL-SOURCE, declared [0.15, 0.45] | C | — | N95 > surgical on facial skin temperature, microclimate humidity, perceived heat (Scarano 2020; Li 2005; Gu 2023). |
| `papr.heat_load` | arm | NULL-SOURCE, declared [0.10, 0.70] | C | — | **Two regimes — see the flag below.** |

Physical evidence behind the ordering:

- Scarano et al. 2020 (IJERPH 17, DOI 10.3390/ijerph17134624, n=20, 1-h
  crossover): "N95 respirators are able to induce an increased facial skin
  temperature, greater discomfort and lower wearing adherence when compared
  to the medical surgical masks." Origin Ab/R. Grade B for the ordering.
- Li et al. 2005 (Ergonomics 48, treadmill, climate chamber 25 °C/70% RH):
  microclimate and skin temperatures inside surgical masks were
  significantly *lower* than inside N95s; heart rates, humidity/heat/
  breath-resistance and discomfort ratings all lower for surgical.
  Origin R. Grade B.
- Gu et al. 2023 (Urban Climate 50): perioral temperature highest under
  cloth; relative humidity highest under cloth/N95 at moderate–vigorous
  intensity. Origin Ab.
- Cates et al. 2023 (J Appl Physiol, DOI 10.1152/japplphysiol.00487.2022):
  at rest 60 min, microclimate temperature and EtCO2 effects were mild,
  similar between surgical and N95, and reversed within 1–2 min — the
  rest-state burden is real but small. Origin R. Bound from below.
- Powell et al. 2017: "loose-fitting PAPRs *ameliorated* facial temperature
  vs the N95 FFR" and produced "lack of any significant effect of PAPRs on
  core temperature" — for the **respirator alone**, PAPR heat load is
  plausibly **≤ N95**, not greater. Origin R.
- Herstein et al. 2021 (JOEH 18, DOI 10.1080/15459624.2021.1949459): in
  **PAPR-level full ensemble** high-level isolation care, max core
  temperatures of six participants ranged 37.4–39.9 °C over a 4-h shift and
  half exceeded the 38.5 °C limit. Origin Ab. Grade B.

**Flag for the sibling mechanism session.** The spec example orders
`papr.heat_load` (0.6) > `n95.heat_load` (0.3). The literature supports that
ordering *only when `papr` names the whole PAPR-level ensemble* (gown,
hood, taping, PAPR). For the respirator alone the evidence points the other
way — powered filtered airflow cools the face (Powell 2017). The declared
interval [0.10, 0.70] spans both regimes; which regime the `papr` entry
means is a registry definition question, and the spec's example value is
defensible only under the ensemble reading.

### 2.3 `dexterity_impairment`

| Type | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `surgical_mask.dexterity_impairment` | arm | 0.0 declared | C | — | No fine-motor channel. |
| `n95.dexterity_impairment` | arm | 0.0 declared | C | — | No fine-motor channel (vision/communication effects exist but are not dexterity). |
| `papr.dexterity_impairment` | arm | NULL-SOURCE, declared [0.0, 0.25] | C | — | Belt/hose bulk and full-facepiece vision obstruction are plausible but unmeasured as dexterity; Powell 2017 notes eye dryness with the tight full-facepiece. |
| `latex_gloves.dexterity_impairment` | physical-ish arm | **[0.0, 0.15]** | B | Ab/R | Sawyer & Bennett 2005 (Ann Occup Hyg, DOI 10.1093/annhyg/mei066): latex gave ~8.6% better fine dexterity than nitrile — disposable-glove impairment is single-digit %. Heydarnia 2025: all four cut-resistant gloves significantly reduced finger dexterity (heavier gloves than latex). |
| `chemical_gloves.dexterity_impairment` | physical-ish arm | **[0.10, 0.50]** | B | Ab | Bensel 1993 (Ergonomics 36, DOI 10.1080/00140139308967930): task completion time increases linearly with chemical-glove thickness (0.18/0.36/0.64 mm) — thickness is the driver. Khanlari 2023 (Heliyon, DOI 10.1016/j.heliyon.2023.e13592): structural firefighting gloves impair far more than general protective gloves — the 0.5 end covers heavy chemical ensembles, not thin nitrile. |

## 3. Secondary-condition incidence (spec §7.4 `fatigue_conditions`)

The spec's unit is `rate_per_wear_hour`. **No study reports a per-wear-hour
hazard.** What exists is prevalence among habitual wearers and, for gloves,
a wear-hours dose-response in odds-ratio form. Every `rate_per_wear_hour`
row is therefore a declared conversion of a measured prevalence — the
prevalence is recorded as the bound, and the hazard stays NULL-SOURCE.
This is "measurable in principle, unmeasured in practice" (∅lit), not
unmeasurable in principle.

| `condition_id` (suggested) | Wear type | Measured evidence | Per-wear-hour rate |
|---|---|---|---|
| `mask_associated_acne` | surgical_mask, n95 | Berjawi 2023 (DOI 10.1155/2023/9470636, 201 HCWs): 40.2% developed mask-acne; >8 h/day usage significantly associated. Abbas Ali 2024 (Diyala J Med): 32.17% new-onset; published range 1.3–53.1%. Yaqoob 2021 (CCID, DOI 10.2147/CCID.S333221): acne in 53.4%, 44.7% among N95 users. Measured band ~**[0.32, 0.53] prevalence** among regular wearers | NULL-SOURCE — declared conversion only |
| `sinonasal_complaints` | n95 | Timbadia et al. 2025 (Cureus, DOI 10.7759/cureus.88837, n=232): nasal itch 49.6%, rhinorrhoea 42.2%, blocked nose 34.1%, worse sneezing 19%; symptoms start ~1 h into wear and resolve <1 h after removal — a **wear-state propensity** [0.19, 0.50], not a cumulative incidence | NULL-SOURCE — declared conversion; note the spec's "symptomatic: true" write fits: onset is fast and reversible |
| `facial_skin_damage` | n95, papr | Yaqoob 2021 citing a Chinese HCW survey: PPE-related skin damage in ~97% of wearers, nasal-bridge involvement 83.1% (Origin Sec — the primary is the cited Chinese study, not retrieved) | NULL-SOURCE |
| `occlusion_dermatitis` | latex_gloves, chemical_gloves | Larese Filon et al. 2020 (JEADV, DOI 10.1111/jdv.17096, 16-study review): occupational contact dermatitis incidence in HCWs 0.6–6.7 per 10⁴ person-years (register studies) to 15.9–780 per 10⁴ py (cohorts incl. apprentices/dental). Gondar Ethiopia cross-sectional: self-reported CD OR ≈1.0 at 2–6 glove-h/day, OR ≈1.5–1.7 at >6 h/day vs <2 h/day — a wear-hours dose-response, the closest thing to a hazard found | NULL-SOURCE for `rate_per_wear_hour`; cohort-band conversion ~[1e-6, 1e-4]/wear-hour at ~2,000 glove-h/yr is a declared arithmetic bound, not a measurement |
| `papr_heat_strain` | papr | Herstein 2021: 3/6 participants exceeded 38.5 °C core temperature during one 4-h PAPR-ensemble shift — symptomatic heat strain ~0.5 per 4-h shift in that setting (n=6, flagged) | NULL-SOURCE — declared conversion ~[0.01, 0.2]/wear-hour spanning that single shift-level reading |
| `respirator_headache` | n95, papr | Lim et al. (via Su 2021, Origin Sec): headache in 37.3% of HCWs after >4 h N95, 32.9% needing analgesia | NULL-SOURCE — declared conversion |

## 4. `sustenance_deficit` → fatigue (spec §6.2)

The task brief warns the meal literature is thin; it is. What exists is a
habitual-pattern association, not an acute missed-meal hazard.

| Parameter | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `sustenance_deficit` → fatigue/performance coefficient | arm | NULL-SOURCE, declared proxy [0.05, 0.20] transient performance decrement per missed/degraded meal | C (proxy: B-grade evidence) | Ab | Imran et al. 2025 (DIET FACTOR, n=540 office workers): habitual breakfast skipping → self-rated morning productivity 6.2 vs 7.4 (−16%), psychomotor vigilance 345 vs 310 ms (+11%), presenteeism 28% vs 14%, low-energy OR 2.45. That is a *habitual* pattern in seated work — the honest label is "sleep-adjacent meal proxy". Maritime context only: Mansyur et al. 2021 — tugboat crew fatigue prevalence 40.2%, >72 h/week adjusted OR 13.32 (hours/sleep, not meals). |

No maritime or acute per-meal measure surfaced; the maritime operational
declarations keep `∅lit` state. The proxy stays a proxy — do not let a
campaign arm silently promote it to a sourced constant.

## 5. `ship_systems` defaults (spec §5)

| Parameter | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `degradation.rate_per_day` | physical→arm | **[0.001, 0.02]** logU | B | Ab/R | Marine machinery reliability records (§8): refrigeration auxiliary (filter-dryer) MTBF 864 h ≈ 36 d; Caterpillar C32 marine diesel cooling-water system MTBF 1,279.65 h ≈ 53 d, availability 0.719 (4-yr logbook); 512 container-ship diesel components Weibull β = 1.8, α = 18,500 h ≈ 770 d characteristic life, MTTF extended to 22,000 h under predictive maintenance (Budimir 2025, JMSE 13:798); marine diesel-generator subsystem availability 67% (lubricating) / 38% (cooling) (Daya 2024, Machines 12:294). Mapping declared: linear health loss to a 0.3 failure threshold ⇒ rate ≈ 0.7/MTBF_days → auxiliaries ~0.013–0.02/day, main-engine components ~0.001/day. |
| `repair.rate_per_person_hour` | arm | NULL-SOURCE, declared [0.01, 0.1] logU | C | — | No literature measures health restored per person-hour. Bounded by corrective-maintenance norms: auxiliary repairs run single-digit to tens of person-hours, so 0.02 (the spec example ⇒ 35 person-hours to restore 0.7 health ≈ a multi-shift repair) sits inside a defensible declared band. |
| `failure_threshold` | arm | NULL-SOURCE, declared [0.1, 0.5] | C | — | Operational trip point, not a measured quantity. Budimir 2025's three-state Markov chain (normal/degraded/failure) is a precedent for thresholded degradation models, but thresholds are model construction. |
| `health_start`, `degradation.model`, `repair.labor_class`, `repair_priority`, `effects.*.capacity_multiplier_at_failure` | X construction | — | X | — | Construction/policy fields; no source owed. |

**Report-line check** (the session brief's order-of-magnitude rule): the
measured auxiliary MTBFs imply linear `rate_per_day` of roughly 0.013–0.02
for a 0.3 failure threshold — about 3–4× the spec's 0.005 example, *inside*
one order of magnitude. Worth knowing: the example value corresponds to a
~140-day time-to-failure, slower than either measured auxiliary (36–53 d).
No order-of-magnitude conflict; flagged because the first instinct will be
to trust the example.

## 6. Fatigue → compliance/refusal (spec §7.3)

| Parameter | Kind | Interval | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `fatigue_refusal_threshold` | arm | NULL-SOURCE, declared | C | — | No threshold draw exists in the literature. |
| `fatigue_refusal_probability_per_epoch` | arm | NULL-SOURCE, declared | C | — | No per-epoch refusal hazard exists. Direction evidence only. |

Direction evidence (supports the *mechanism*, no rates):

- Rebmann 2013: 22% of respirator removals were for discomfort; N95
  adjustments increased over time; one subject (10%) withdrew outright.
- Scarano 2020: N95 produced "lower wearing adherence" than surgical.
- Powell 2017: discomfort, not exertion, is what erodes tolerance over
  prolonged wear.
- Timbadia 2025 (Discussion): "Nasal discomfort with N95 mask wearing can
  lead to inefficient use and reduced compliance with mask usage" —
  authors' mechanism claim, not a measured rate.
- Schrank et al. 2024 (ICHE, DOI 10.1017/ice.2024.157): agreement with
  universal masking fell 84% → 55% over the pandemic window; 63% reported
  annoyance — institutional-timescale decay, not a per-wear-hour hazard.
- Longitudinal IPC adherence (When-Risk-Persists cohort): PPE-replacement
  adherence declined 58.4% → 50.9%, pre-contact hand hygiene 55.5% → 48.6%
  between waves — decay at months scale.

## 7. The complete NULL-SOURCE inventory

For the sibling implementation sessions — every spec'd tunable that ships
as a declared assumption, in one place:

- All five `fatigue_rate_per_epoch` values (ordering evidence only).
- All five `heat_load` values (ordering evidence; PAPR is two-regime — §2.2).
- `papr.dexterity_impairment` (bulk/vision plausible, unmeasured).
- Every `fatigue_conditions.rate_per_wear_hour` (prevalence data recorded;
  hazards never measured).
- `sustenance_deficit` coefficient (habitual-pattern proxy only).
- `repair.rate_per_person_hour`, `failure_threshold` (declared/bounded).
- `fatigue_refusal_threshold`, `fatigue_refusal_probability_per_epoch`
  (direction evidence only).
- X-construction fields: `health_start`, `degradation.model`,
  `repair.labor_class`, `repair_priority`,
  `effects.*.capacity_multiplier_at_failure`, `fatigue_susceptibility`.

## 8. Evidence ledger

One row per governing citation, register fragment schema:
`| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |`

| # | Citation | Quantity + unit | Retrieval | Section | Verbatim locator |
|---|---|---|---|---|---|
| 1 | Frimpter et al. 2022, PharmacoEconomics 40:1263–1285, DOI 10.1007/s40273-022-01224-9 (SLR; governing quote is Nichol et al.'s data) | work effectiveness fraction while ill, dimensionless | chunks | Sec → R (review Results prose) | "those reporting presenteeism rated their level of work effectiveness to be 70–75% of normal for the days they worked while ill" (Nichol, n=497, ILI, ages 50–64; mean 4.4 d presenteeism) |
| 2 | Su et al. 2021, IJERPH 18:13308, DOI 10.3390/ijerph182413308 | symptom incidence by mask type over 8 h, fraction | chunks | R + cited Sec | N95 significantly worse than surgical on shortness of breath, headache, dizziness, difficulty talking, fatigue; "Lim et al. reported that healthcare workers who wore N95 respirators for more than 4 h might cause headache in 37.3% of the participants, and 32.9% of them needed pain killers" |
| 3 | Rebmann et al. 2013, AJIC 41:1218–1223, DOI 10.1016/j.ajic.2013.02.017 | tolerated wear duration, min; removal causes, fraction | chunks | R, T1 | "90% (n=9) tolerated wearing respiratory protection for two 12-hour shifts"; "Almost one-quarter (22%) of respirator removals were due to reported discomfort"; mean 214/199 min before first removal; "prior research… average time health care personnel would tolerate N95 usage was less than 8 hours" |
| 4 | Powell et al. 2017, JOEH 14, DOI 10.1080/15459624.2017.1358817 | discomfort/exertion trajectory and cardiopulmonary response over 8 h; PAPR vs N95 facial temperature | chunks | R + Discussion | "discomfort increased over time with continual respirator use over an 8-hr period… exertion increased only marginally"; loose-fitting PAPRs ameliorated facial temperature vs N95 FFR; "lack of any significant effect of PAPRs on core temperature" |
| 5 | Herstein et al. 2021, JOEH 18, DOI 10.1080/15459624.2021.1949459 | core temperature, °C, PAPR-level ensemble | chunks | Ab | "Maximum core temperatures of the six participants ranged from 37.4 °C to 39.9 °C during the 4-hr shift; core temperatures of half (n = 3) of the participants exceeded 38.5 °C, the upper core temperature limit" |
| 6 | Scarano et al. 2020, IJERPH 17:4624, DOI 10.3390/ijerph17134624 | facial skin temperature, discomfort, adherence — surgical vs N95 | chunks | R/Ab | "A significant difference in heat flow and perioral region temperature was recorded between the surgical mask and the N95 respirator (p < 0.05)… N95 respirators are able to induce an increased facial skin temperature, greater discomfort and lower wearing adherence" |
| 7 | Li et al. 2005, Ergonomics 48 | mask microclimate T/RH, heart rate, subjective sensations — surgical vs N95 | chunks | R | "The microclimate and skin temperatures inside the facemask were significantly lower [surgical] than… N95"; surgical rated significantly lower for humidity, heat, breath resistance, discomfort |
| 8 | Gu et al. 2023, Urban Climate 50:101720 | perioral temperature / RH by mask type × activity | chunks | Ab | "perioral temperature was the highest under cloth masks and perioral relative humidity was the highest under cloth or N95 masks during moderate and vigorous intensity activities" |
| 9 | Cates et al. 2023, J Appl Physiol, DOI 10.1152/japplphysiol.00487.2022 | microclimate temperature, EtCO2 at rest, 60 min | chunks | R | "the time course and magnitude of changes… were mild in magnitude, not physiologically relevant, equivalent between barrier types, and immediately reversible on removal" (returned to baseline in 1–2 min) |
| 10 | Sawyer & Bennett 2005, Ann Occup Hyg, DOI 10.1093/annhyg/mei066 | fine dexterity change under disposable gloves, % | chunks | Ab | latex ~8.6% better fine dexterity than nitrile; no gross-manual difference |
| 11 | Bensel 1993, Ergonomics 36, DOI 10.1080/00140139308967930 | task completion time vs chemical-glove thickness | chunks | Ab | linear increase in task completion time with thickness over 0.18/0.36/0.64 mm; best bare-handed, worst at 0.64 mm |
| 12 | Khanlari et al. 2023, Heliyon 9:e13592, DOI 10.1016/j.heliyon.2023.e13592 | dexterity impairment, structural vs general protective gloves | chunks | Ab/R | structural firefighting gloves impair substantially more than general protective gloves |
| 13 | Heydarnia et al. 2025 | finger dexterity under cut-resistant gloves | chunks | R | all four cut-resistant glove types significantly reduced finger dexterity |
| 14 | Berjawi et al. 2023, Dermatol Ther 2023:9470636, DOI 10.1155/2023/9470636 | mask-acne prevalence + duration association | chunks | R/Ab | 40.2% of 201 HCWs developed mask-acne; >8 h/day usage significantly associated |
| 15 | Abbas Ali 2024, Diyala J Med | mask-acne prevalence | chunks | R | "37 (32.17%) were suffering from new-onset mask induce acne"; intro range "1.3% to 53.1%" |
| 16 | Yaqoob et al. 2021, Clin Cosmet Investig Dermatol 14:1427, DOI 10.2147/CCID.S333221 | acne prevalence; N95 subgroup; PPE skin damage (Sec) | chunks | R + Sec | "acne was prevalent in 103 (53.4%)"; "Out of 73 HCWs using N-95 masks, 46 (44.7%) developed acne"; cites Chinese survey ~97% PPE-related skin damage, 83.1% nasal bridge |
| 17 | Timbadia et al. 2025, Cureus 17:e88837, DOI 10.7759/cureus.88837 | sinonasal symptom prevalence + onset/resolution timing | chunks | R | "115 (49.6%) experienced nasal itching, 98 (42.2%) had rhinorrhoea, 79 (34.1%) developed a blocked nose, and 44 (19%) users experienced worse sneezing"; "Most of the symptoms start after one hour of continued mask wear… resolve within one hour of mask removal" |
| 18 | Larese Filon et al. 2020, JEADV, DOI 10.1111/jdv.17096 | occupational contact dermatitis incidence, per 10⁴ person-years | chunks | Ab/R | register studies 0.6–6.7; cohort studies 15.9–780 per 10,000 person-years |
| 19 | Gondar (Ethiopia) HCW glove study, cross-sectional | self-reported contact dermatitis vs glove hours/day, OR | chunks | T | OR ≈1.0 for 2–6 glove-h/day, ≈1.5–1.7 for >6 h/day vs <2 h/day reference |
| 20 | Imran et al. 2025, DIET FACTOR | productivity / PVT / presenteeism by breakfast-skipping habit | chunks | Ab | productivity 6.2 vs 7.4; PVT 345 vs 310 ms; presenteeism 28% vs 14%; low energy OR 2.45 (n=540, subset n=312 PVT) |
| 21 | Mansyur et al. 2021 | seafarer fatigue prevalence and determinants | chunks | R | "40.2% of the subjects were classified as having fatigue… [adj. OR = 13.32; 95%-CI (4.78-31.23)]" for >72 h/week |
| 22 | Ship refrigerator maintenance study (Indonesian, mixed-methods) | auxiliary machinery MTBF, h | chunks | Ab | "the Filter Dryer has the highest damage rate (25%) and the lowest MTBF (864 hours)" |
| 23 | Caterpillar C32 marine diesel cooling-water reliability study (Nigerian Navy logbook, 4 yr) | MTBF, h; availability | chunks | Ab | "MTBF = 1,279.65 hrs"; availability 0.719 |
| 24 | Budimir et al. 2025, JMSE 13:798, DOI 10.3390/jmse13040798 | component failure model parameters, h | chunks | Ab/R | "Weibull distribution (β = 1.8; α = 18,500 h)… 512 diesel engine components"; "MTTF up to 22,000 h"; "64.3% of ship engine components experience failures (S3 state)" → 40% optimized |
| 25 | Daya et al. 2024, Machines 12:294, DOI 10.3390/machines12050294 | marine diesel-generator subsystem availability, fraction | chunks | R | lubricating system availability 67%, cooling system 38% (BBN estimate) |
| 26 | Schrank et al. 2024, Infect Control Hosp Epidemiol, DOI 10.1017/ice.2024.157 | universal-masking agreement over time, % | chunks | R | "Agreement with universal mask use decreased from 84% early in the pandemic to 55%"; "63% expressed any level of annoyance with mask wearing" |
| 27 | When-Risk-Persists longitudinal IPC cohort | PPE/hand-hygiene adherence decay between waves, % | chunks | R/T6 | PPE replacement "always" 58.38% → 50.86%; pre-contact hand hygiene 55.49% → 48.55% |
| 28 | Prolonged-use mask simulator study | mask replacement guidance interval, h | chunks | R | inspiratory resistance rose dramatically after 2 h; moisture permeability declined after 4 h; "the hospital staff was instructed to replace their masks every two hours" |
| 29 | CleanSpace/Halo PAPR field study (Chong et al., via Powell-era Discussion) | PAPR comfort duration, h | chunks | Sec | "38% of Halo users found the respirator to be comfortable for up to 1 hour of wear, and 40% reported… 'comfortable or fairly comfortable' with >4 hours of long-term wear" |
| 30 | ICU prospective cohort (75 HCWs, N95 + PPE) | donning duration, h; exertion trajectory | chunks | R | "mean duration of donning to be 3.1 hours"; "level of exertion… increased significantly after 4 hours of wearing N95" |

Searches that returned nothing governing (recorded so nobody re-spends the
query): maritime MTTR in person-hours per repair event (naval
maintainability papers are evaluation frameworks, not measured repair
times — `?nr`); per-wear-hour condition hazards for every
`fatigue_conditions` row (literature is prevalence/dose-response form —
`?nr`); acute missed-meal performance decrements aboard ships (`?nr`);
PAPR weight/bulk quantified as manual dexterity loss (`?nr`).

## 9. `environmental_hazards` constants (spec §8 — ENV-HAZARD-01)

The chemical-hazard arm declares a VOC refrigerant leak in
`Engine_Room_Aft` on `mega_cruise_5000` (`enabled: false`). Every number
in it is a NULL-SOURCE declared arm: the literature was not searched for
this arm because the spec itself prescribes the mechanism shape (Haber
c·t threshold crossing, continuous-concentration sensors), and a declared
VOC leak's dose bookkeeping is in *model* mass units — a rescaling the
declaration owns, so no physical constant is being asserted.

| Parameter | Kind | Shipped value | Grade | Origin | Basis |
|---|---|---|---|---|---|
| `haber_ct_threshold` | arm (cumulative dose-units × epochs) | 400.0 | **C** | ?nr | NULL-SOURCE. Haber's law is a model *shape* (onset at a declared c·t product), not a fitted constant; the unit is the declaration's own mass unit, so the value scales the worked example, nothing more. Refrigerant-VOC incapacitation thresholds in these units do not exist in the literature. |
| `base_emission_rate_per_day` | arm (mass-units/day) | 240.0 | **C** | ?nr | NULL-SOURCE declared leak rate; chosen so the reservoir crosses the sensor LOD inside the 168-epoch example voyage. Sweeps, never tunes. |
| `exposure_probability_per_day` | arm (fraction/day) | 0.6 | **C** | ?nr | NULL-SOURCE; occupancy-conditioned contact with the source zone, matching the declared-arm convention the environmental-reservoir machinery already uses. |
| `spore_decay_rate_per_day` | arm (fraction/day) | 0.5 | **C** | ?nr | NULL-SOURCE declared substance decay (the field name is the machinery's; for a chemical it is first-order loss of the declared mass unit). |
| `colonization_rate_per_day` | arm (growth/day) | 0.0 | **C** | X | A chemical does not grow; declared 0 to keep the reservoir emission-only. |
| `lod_mass_per_m3` (air sensor) | arm (mass-units/m³) | 0.01 | **C** | ?nr | NULL-SOURCE declared detector LOD. Real PID detector LODs exist (ppm-class) but the model mass unit is declared, so a physical LOD would be a category error. |
| `lod_mass_per_cm2` (surface sensor) | arm (mass-units/cm²) | 0.001 | **C** | ?nr | NULL-SOURCE declared wipe/monitor LOD, same unit reasoning. |
| `noise_sigma_log` (both sensors) | arm (log-space σ) | 0.1 | **C** | ?nr | NULL-SOURCE declared measurement dispersion on the continuous monitors, matching the lognormal-noise convention the air sniffer uses. |

Deliberate absences, recorded so nobody re-spends the reasoning: no
incubation, no shedding curve, no `severity_model`/`observation_model`
(the presentation flag lands on the §7 seam directly), no
`transmission_route_weights` scaling beyond the declared `hvac_airborne`
route tag, and no per-host susceptibility draw — the threshold is
deterministic, so the arm consumes no RNG at all.

## 10. What the sibling sessions should take from this

1. `symptomatic_effectiveness` is **sourced**, B grade, [0.55, 0.85] U — the
   spec text's "no source exists" is stale (§1).
2. Every `fatigue_rate_per_epoch`, `heat_load`, and
   `fatigue_conditions.rate_per_wear_hour` is a declared arm — the
   literature supplies orderings and prevalences, not per-hour hazards
   (§§2–3, §7).
3. `papr.heat_load` needs a definitional decision: respirator-alone
   (≤ N95, Powell) or ensemble (severe, Herstein). The spec example assumes
   the ensemble (§2.2).
4. `degradation.rate_per_day` has a real marine-reliability interval
   [0.001, 0.02] logU; the example 0.005 is inside it but on the slow side
   for auxiliaries (§5).
5. `repair.rate_per_person_hour`, both refusal parameters, and the
   sustenance coefficient are NULL-SOURCE declared arms — sweep them, never
   fit them (§§4–6).
