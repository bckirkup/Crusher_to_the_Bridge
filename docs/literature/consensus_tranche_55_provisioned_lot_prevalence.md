# Consensus tranche 55 — provisioned-lot norovirus prevalence for `q_source`

> **Status:** Reference. Feeds the `generic_cruise_port` entry of
> `data/config/provisioning_sources.json` (PROVISIONED-SOURCE-01 contract
> §1.3) and register §3.12; adopts no value into any campaign.

Evidence retrieved 2026-11-05 for the PROVISIONED-SOURCE sourcing leg: what
the literature measures for the **per-lot norovirus contamination
prevalence of provisioned food, by item line**, and how that folds through
the station census into the hull-invariant per-station Bernoulli
`q_source`. Retrieval: 24 Consensus `search` passes, every one with
`include_full_text_chunks: true`, each naming the quantity (per-sample /
per-batch norovirus RNA prevalence, percent positive) **and** the matrix.
Origins per row: `R` Results, `Tn` Table n, `Ab` abstract only, `Sec`
secondary (cited by another paper), `?nr` queried, not returned. Queries
were fixed by the quantity's definition before the model's needs were
looked at; no paper was screened by which value helps an anchor.

## 1. The quantity, and the definitional choices made before reading values

- **Engine quantity.** `q_source` is a per-(served-venue, item-line) station
  Bernoulli per voyage; objects per voyage = Binomial(N_lots, q),
  N_lots = served Dining venues × `COMMON_SOURCE_LOT_ITEM_LINES` (7 lines:
  shellfish, salad_leaf, fresh_produce, deli, bakery, dairy, garnish) —
  21/35/63/70 on exp/cls/spr/mega.
- **Literature quantity.** Per-sample (≈ per-lot / per-batch) RT-qPCR
  norovirus RNA detection prevalence, by commodity.
- **Point in the chain.** A provisioned lot is bought at dispatch /
  wholesale / retail grade, so the commensurate denominator is
  **dispatch-centre batches or retail/market samples** — not production
  areas or farms (which the meta-analyses show run 3–8× higher).
- **Source covariate.** `generic_cruise_port` stands for a high-income
  embarkation-port supply chain (US/EU/UK/Canada surveillance). Domestic
  LMIC-market strata (China domestic, Egypt) are recorded as strata for a
  future source id, not folded in (§3).
- **Commensurability with the titre draw.** Under the shipped
  `titre_draw_mode: "two_mode"` every minted `provisioned_lot` draws the
  **implicated** band (150–5,000 GEC/g; NORO-IMPLICATED-TITRE-01). An
  RNA-positive lot at 10–100 GEC/g is background stock, which the engine
  does not mint. The commensurate `q_source` is therefore
  RNA prevalence × P(titre at implicated scale | RNA-positive) (§4.2).

## 2. Retrieved prevalences — by item line

### shellfish (oysters)

| Source | Setting / denominator | Value | Origin |
|---|---|---|---|
| EFSA BIOHAZ (Aerts et al. 2019), *EFSA J* 17(7):5762, DOI 10.2903/j.efsa.2019.5762, [Consensus](https://consensus.app/papers/details/ddaaa680d0405a1fa752107741029184/) | EU baseline, **2,129 batches from dispatch centres** (89% French origin), 2 yr | **10.8% (CI 8.2–14.4)**; production areas 34.5% (30.1–39.1); dispatch by area class A 3.7% / B 20.0% (T19); Pacific cupped 9.8% (T20); "above LOQ in <10% of samples" | R (Terms of reference c/d), T19–T21 |
| Lowther et al. 2018, *Food Environ Virol* 10:278, DOI 10.1007/s12560-018-9338-4, [Consensus](https://consensus.app/papers/details/64ff5e0eb2f2593dbccc65acde3a7746/) | UK **point of sale**, 630 samples, 1 yr, 88% UK origin | **68.7%** positive; by origin UK 71.7%, IE 84.0%, NL 31.0% (T1); **9.7% of samples >100 copies/g** | R, T1 |
| Woods & Burkhardt 2010 (cited in Lowther 2018 Discussion) | US market shellfish | 3.9% | Sec |
| Schaeffer et al. 2013 (cited in Lowther 2018) | France point of sale | 9% | Sec |
| Dirks et al. 2021, *Int J Food Microbiol* 339:109089, DOI 10.1016/j.ijfoodmicro.2021.109089, [Consensus](https://consensus.app/papers/details/0b4902023f475ad9bd9bb1294d751dfd/) | NL oysters along the chain (post-harvest/dispatch/retail), Sept–Mar only | 31.6% oysters (n=266), 53.1% mussels | Ab |
| Jiang et al. 2018, *Food Control* 86:110, DOI 10.1016/j.foodcont.2017.11.043, [Consensus](https://consensus.app/papers/details/e83b9dded3a95ac0b151c59d22532a96/) | China retail markets, 652 oysters | 20.7% (Beijing 16.0%, Qingdao 25.9%) | Ab, R (§3.1) |

### fresh_produce (berries / fruit)

| Source | Setting | Value | Origin |
|---|---|---|---|
| Steele et al. 2022, *Int J Food Microbiol* 378:109840, DOI 10.1016/j.ijfoodmicro.2022.109840, [Consensus](https://consensus.app/papers/details/1e6300b32df9533d869c95751003d5a4/) | CFIA retail, 11 Canadian cities, 4,218 fresh+frozen berries/arils | **0.36%** (GI+GII) | Ab |
| Cook et al. 2019, *Food Microbiol* 79:85, DOI 10.1016/j.fm.2018.12.003, [Consensus](https://consensus.app/papers/details/9090d8dee9f45151b348342ce0172415/) | UK retail | fresh raspberries **2.3%** (7/310); frozen raspberries **3.6%** (10/274) | Ab |
| Miotti et al. 2024, *Int J Food Microbiol* 413:110577, DOI 10.1016/j.ijfoodmicro.2024.110577, [Consensus](https://consensus.app/papers/details/dec7dd2b73c159ff9780ed5d7799473f/) | global meta-analysis, berries (NoV+HAV), I² = 82% | **2.12% (CI 1.74–2.59)**; decreasing with sampling year; farm > retail for GI; Africa highest | Ab (subgroup tables `?nr` after 2 phrasings) |
| Gao et al. 2019, *Food Microbiol* 82:119, DOI 10.1016/j.fm.2019.01.017, [Consensus](https://consensus.app/papers/details/b5b0a16ff6b2563681d5740e4daa8c18/) | Heilongjiang, China, 2,667 berries | domestic frozen **9.0%** (81/900), domestic fresh **12.11%** (109/900), **export frozen 0/677** | Ab |
| Fokas et al. 2025, *Pathogens* 14:135, DOI 10.3390/pathogens14020135, [Consensus](https://consensus.app/papers/details/82bb4277482258f5b0cafdde2920da92/) | Greece official-control samples | soft fruits/berries 6.45% (2/31) | R |
| Ekundayo & Ijabadeniyi 2022, *J Appl Microbiol* 134:lxac009, DOI 10.1093/jambio/lxac009, [Consensus](https://consensus.app/papers/details/1dab4e2f3c805e1996048c6fd6655ee4/) | global meta-analysis, fresh produce | fruits 9.8% (3.7–23.5); Europe 5.6%, N America 12.4% — mixed farm/retail | Ab |

### salad_leaf (leafy greens / RTE salad)

| Source | Setting | Value | Origin |
|---|---|---|---|
| Cook et al. 2019 (above) | UK retail lettuce | **5.3%** (30/568) | Ab |
| Terio et al. 2017, *Int J Food Microbiol* 249:61, DOI 10.1016/j.ijfoodmicro.2017.03.008, [Consensus](https://consensus.app/papers/details/979edc7174fb52998736ba05de01301a/) | Italy retail RTE vegetables, 911 samples | **0/911** NoV | Ab |
| Gao J et al. 2024, *Int J Food Microbiol* 413:110603, DOI 10.1016/j.ijfoodmicro.2024.110603, [Consensus](https://consensus.app/papers/details/df8a769e1371567c8da1e712ed8796a7/) | global meta-analysis, vegetables, 27 studies | pooled 7% (3–13); **retail 4% (1–8)**; farm 18% (5–37); RTE 2% (0–8) | Ab |
| Kokkinos et al. 2012, *Food Environ Virol* 4:179, DOI 10.1007/s12560-012-9087-8, [Consensus](https://consensus.app/papers/details/4f50df9a14f75fd394c50e4932e5a492/) | GR/RS/PL supply chain incl. production | NoV GI 2% (6/299), GII 2.95% (8/271) | Ab |
| Terio et al. 2020, *Appl Sci* 10:5176, DOI 10.3390/app10155176 | 135 bagged RTE salads from **two** plants, Italy | GII 74.8% — single-processor cluster, not a prevalence of the market | Ab |
| Losio et al. (cited in Terio 2017 Introduction) | Italy RTE retail | <0.1% | Sec |

### deli, bakery, dairy, garnish — the null/blocked record

| Line | Queries (quantity + unit named) | What came back | Record |
|---|---|---|---|
| deli | "ready-to-eat foods deli sandwiches retail RT-qPCR percent positive"; "deli meats sliced ham RTE meat products retail survey percent positive" | Markantonis 2018 *J Food Saf* DOI 10.1111/jfs.12436: **0/42** RTE pork products (2/48 plant swabs, slicer + worker hand) (Ab); Fokas 2025 processed meals 1/4 (R, n too small) | **∅ commensurable retail prevalence**; one measured zero (0/42, one-sided 95% upper ≈ 7%) |
| bakery | "dairy products … and bakery products prevalence"; "bakery products cakes pastries bread … prevalence survey genome copies" | method-validation and metagenomics papers only | **∅lit** after 2 phrasings — no survey prevalence |
| dairy | "dairy products milk cheese … prevalence percent positive"; "pasteurised dairy products … retail survey" | Silva 2021 DOI 10.1007/s12560-021-09491-z: Brazilian **raw-milk** artisanal cheese 29/100 (Ab); Yılmaz & Kale 2025 raw-milk cans, Turkey, NoV GI 16% (Ab) | **∅ for pasteurised provisioned dairy**; raw-milk strata incommensurable (cruise provisioning is pasteurised) |
| garnish | "fresh herbs basil parsley coriander retail percent positive"; "fresh herbs and green onions imported retail Canada US Europe" | Wang 2026 DOI 10.1007/s12560-026-09685-3 coriander 32.5% (13/40), Shijiazhuang retail (Ab); Elmahdy 2022 DOI 10.1007/s12560-022-09516-1 Egyptian leafy herbs NoV GI 20% / GII 30% (Ab) — LMIC strata only | **∅ for the high-income stratum** (`?nr` after 2 phrasings; CFIA herb surveys are agency material — not in the index) |

## 3. Report on discovery: the shellfish line stratifies; it is not averaged

Retail/dispatch oyster prevalence spans **3.9% (US market) → 10.8% (EU
dispatch batches) → 31–32% (NL chain, winter only) → 68.7% (UK point of
sale; 72–84% for UK/IE-origin)**. Origin and season stratify it (EFSA: class-A
areas 3.7% vs class-B 20%; strong Nov–Apr peak; Lowther: NL 31% vs UK 72% vs
IE 84%). These are different supply chains, not sampling noise around one
value. For `generic_cruise_port` the band is the **multi-origin dispatch/market
denominator, [3.9%, 14.4%]** (US market floor; EFSA dispatch CI ceiling;
central 10.8%). The UK/IE-origin stratum (~0.7–0.8) belongs to a distinct
source id and is shown only as the Fold A′ sensitivity in §4. Berries
stratify the same way by origin (China domestic 9–12% vs China export 0/677
vs Canada retail 0.36%). The meta-analyses' downward secular trend (Miotti)
is a third stratifier.

## 4. Construction

### 4.1 Item-line → station mapping

Each served venue carries one station per item line (`_cs_station_census`:
zones × `COMMON_SOURCE_LOT_ITEM_LINES`). With per-line prevalence p_i,
E[contaminated stations] = V · Σ_i p_i, so the **hull-invariant scalar that
preserves every hull's expectation exactly is q̄ = (1/7) Σ_i p_i**. This
mapping is exact and needs no venue-level menu data. The residual gaps,
documented rather than filled:

1. **Every venue serves every line.** The census has no per-venue menu, so a
   specialty venue with no shellfish still carries a shellfish station.
   There are no item-line-resolved venue menus in any hull's platform JSON.
2. **Stations are independent across venues.** Real provisioning shares one
   lot per item line across venues, and often across the fleet. Rispens
   2020 (below) is exactly that: one 22,000 lb raspberry lot supplied the
   whole fleet of cruise line X for months. The mean is unaffected
   (V · p_i either way), but the variance and multi-venue co-occurrence are
   not. The `extra_lot_probability` fiat tail was the old stand-in for that.
3. **Per-voyage independence.** A contaminated lot persists across
   consecutive voyages (June → October in Rispens). The registry draws q
   once per voyage, independently.

### 4.2 Arithmetic (reproducible)

RNA-detection band per line, high-income dispatch/retail stratum
(lo, central, hi):

| Line | lo | central | hi | Basis |
|---|---|---|---|---|
| shellfish | 0.039 | 0.108 | 0.144 | US market (Sec) / EFSA dispatch point + CI upper (R) |
| salad_leaf | 0.000 | 0.0265 | 0.053 | Terio 2017 0/911 / midpoint / Cook 2019 lettuce (Ab); Gao 2024 retail 4% inside |
| fresh_produce | 0.0036 | 0.0212 | 0.036 | Steele 2022 / Miotti 2024 pooled / Cook 2019 frozen raspberry (Ab) |
| deli, bakery, dairy, garnish | 0 | 0 | 0 | ∅ (§2) — carried at the 0 floor; can only **raise** q̄ |

The implicated-scale share **f = 0.097 / 0.687 = 0.141** (Lowther 2018:
share of RNA-positive POS oysters above 100 copies/g). It is the only
retrieved direct measurement of P(titre ≥ ~implicated floor | positive).
The 100 copies/g threshold sits below the 150 GEC/g implicated floor, so f
is an upper estimate at that floor. It is carried to the produce lines as
analogous, the same carry the implicated titre band already makes
(NORO-IMPLICATED-TITRE-01 §2). EFSA reports only "above LOQ in <10% of
samples"; its ≥300 cpg proportion was `?nr` after two phrasings.

```python
lines = ["shellfish","salad_leaf","fresh_produce","deli","bakery","dairy","garnish"]
p = {"shellfish":(0.039,0.108,0.144),"salad_leaf":(0.0,0.0265,0.053),
     "fresh_produce":(0.0036,0.0212,0.036)}          # ∅ lines carried at 0
qbar = [sum(p[k][j] for k in p)/len(lines) for j in range(3)]
f = 0.097/0.687
```

| Rung | lo | central | hi | × declared [2e-4, 5e-4] |
|---|---|---|---|---|
| **A — RNA detection**, ∅ = 0 | 6.09e-3 | 2.22e-2 | 3.33e-2 | 30× / 67× |
| A′ — A with the UK POS stratum as shellfish hi (0.687) | 6.09e-3 | 2.22e-2 | 1.11e-1 | (sensitivity only) |
| B — A with garnish, deli at the salad_leaf band (analogue) | 6.09e-3 | 2.98e-2 | 4.84e-2 | (sensitivity only) |
| **A × f — implicated-titre-commensurate** (shipped) | **8.6e-4** | **3.14e-3** | **4.7e-3** | **4.3× / 9.4×** |
| B × f | 8.6e-4 | 4.21e-3 | 6.84e-3 | (sensitivity only) |

The registry `generic_cruise_port.q_source` carries **[0.00086, 0.0047]**
(rung A × f), drawn U[lo, hi] per voyage by the existing grammar. The
schema admits no log-uniform shape for `q_source`; a two-order span would
want one, so that is part of the extension proposal below. Grade: **B** for
the shellfish and berry prevalences (direct per-batch/per-sample
measurement in an analogous retail/dispatch setting), **C** for f carried
to produce and for the ∅ lines' zero floor. The composite interval is
**Grade C (sourced composite)**, not a declared assumption.

## 5. Secondary anchors (plausibility, not prevalence inputs)

- **Rispens et al. 2020**, *MMWR* 69(16):501–502, DOI
  10.15585/mmwr.mm6916a3, [Consensus](https://consensus.app/papers/details/3e80656d58ce5ade8b19745b6336acf7/)
  (`R`, full text): three AGE outbreaks on two ships of cruise line X
  (Sept–Oct 2019). Ship B: 85/2,166 passengers (3.9%) and 10/612 crew;
  ship A: 83/2,251 (3.7%) and 10/610. Nearly 80% of ill-passenger
  questionnaires implicated a smoothie of frozen fruit and berries; 9/11
  stools were GII.2[P16]. FDA tested 16 items and 3 were positive
  (raspberries GII, tropical fruit cocktail GI, berry mix GI); raspberry vs
  stool sequences were 97.5% similar. **Lot numbers matched across ships.
  The vendor bought ~22,000 lb of one frozen-raspberry lot from a Chinese
  supplier from late June 2019, and it was supplied to the entire fleet.**
  There were no further outbreaks after removal; a WHO recall followed
  (RASFF 2019.3843). What it documents: one contaminated lot →
  fleet-wide, multi-voyage, multi-ship exposure. That is evidence for the
  §4.1 correlation gaps, not a prevalence.
- **Vehicle attribution on cruise outbreaks.** Mouchtouri et al. 2024,
  *Eurosurveillance* 29(10):2300345, DOI 10.2807/1560-7917.es.2024.29.10.2300345
  (`T3`, partial): of 45 norovirus outbreaks on 26 ships (1990–2020), 41
  had mode data. Person-to-person was involved in 35 (14 single-mode, 21
  mixed); **single-mode food-borne 3**; of 31 subsequent-cruise outbreaks,
  2 were food-borne. The mixed-mode rows naming food were not fully
  returned (`T3 partial`). Freeland et al. 2016 *MMWR* 65(1), DOI
  10.15585/mmwr.mm6501a1 (`R`): **133 outbreaks / 29,107 voyages (0.46%)**
  in 2008–2014. Its mode-of-transmission breakdown was `?nr`, and the VSP
  outbreak-investigation archive is agency material outside every index.
- **Plausibility arithmetic (inferred).** Food-vehicle outbreak voyages ≈
  0.46% × (3/45 … 6/41) ≈ **3–7 × 10⁻⁴ per voyage**. At the shipped
  rung's central q = 3.14e-3, P(≥1 lot) = 0.064/0.104/0.180/0.198
  (exp/cls/spr/mega). Times the measured P(post | minted)
  0.93/0.58/0.36/~0.10 (PROVISIONED-SOURCE-01 waves 1–3), that is
  **≈6% of voyages posting from food alone** on the small hulls (2% mega).
  This is ~25–300× the VSP-implied food-vehicle bound. It is a
  measurement about the model's chain from minted lot to posting (or about
  RNA-positive ≠ infectious lots), not a reason to move q: the interval
  was sourced from the prevalence definition and is reported as it lands.

## 6. Agency / non-index sources (separate access class, not attempted as literature)

FDA FY-sampling assignments (e.g. the FDA microbiological surveillance
sampling of fresh herbs, cucumbers and frozen berries), CFIA targeted
surveys (herbs, leafy greens, frozen berries), EU RASFF notification
counts, and the CDC VSP outbreak-investigation archive (mode of
transmission per outbreak) are **not in any literature index**. They are
recorded as **blocked — agency access class**. They are not null results.
FDA and CFIA retail surveys are the likeliest route to the ∅ garnish and
deli lines for the high-income stratum, and VSP investigation pages are
the route to a full vehicle-attribution share. Remedy: browser fetch from
the agency archive in a later leg.

## 7. Proposal: per-item-line registry extension (not landed)

`_resolve_provisioned_source_block` reads one `q_source` scalar|[lo, hi],
and the registry schema is `additionalProperties: false`, so the grammar
cannot consume per-line structure today. Proposed tranche for a later
engine leg (no engine change here):

```json
"q_source_by_item_line": {
  "shellfish":     {"interval": [0.039, 0.144], "evidence": "B", "origin": "R/Sec"},
  "salad_leaf":    {"interval": [0.0,   0.053], "evidence": "B", "origin": "Ab"},
  "fresh_produce": {"interval": [0.0036,0.036], "evidence": "B", "origin": "Ab"},
  "deli": null, "bakery": null, "dairy": null, "garnish": null,
  "implicated_share": {"value": 0.141, "evidence": "B shellfish / C produce", "origin": "R"}
}
```

Consumption: one Bernoulli per (venue, line) against p_line × f, in the
same canonical census order (contract §2), which preserves nesting and
seed-pairing. Once the census can drop stations a venue does not serve,
it would also want (i) a per-venue menu, (ii) an optional shared-lot
correlation across venues (Rispens), and (iii) a log-uniform shape.
Separate source ids would carry the §3 strata (`uk_ie_shellfish`,
`lmic_domestic_market`).
