# Register fragment — influenza `surface_decay_per_day` and `illness_probability` (task #44, tranche 14)

> **Merged.** This fragment was merged into [`../../parameter_provenance_register.md`](../../parameter_provenance_register.md) by the sourcing-wave-1 integration pass, with the lead's corrections applied at merge time. It is kept as the audit trail of what the sourcing unit proposed; it is **not** a live proposal, and where it and the register differ the register holds the status.

**Status:** Additive fragment, not authoritative. Proposed replacement rows for
[`../../parameter_provenance_register.md`](../../parameter_provenance_register.md)
§3.3, for the lead to merge. Sourcing tranche:
[`../consensus_tranche_14_influenza_surface.md`](../consensus_tranche_14_influenza_surface.md).
No value is adopted or recommended here, and no measurement has been converted
into the shipped field's units.

## Proposed §3.3 rows

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `surface_decay_per_day` | 0.94 | C | **∅ null as defined**: no study measures a surviving fraction, or a single per-day rate, spanning material/matrix/RH. What is measured, all infectious-virus assays: **half-life 4.5–5.9 h** on steel/ABS/PS/glass in **human airway surface liquid**, 23% RH, 22–24 °C (Qian 2023, *Appl Environ Microbiol*, DOI 10.1128/aem.00633-23; steel 4.52 h, 95% CrI 2.41–8.56; **donor-culture spread 3.2–8.1 h is wider than the between-material spread**); **t½ ≈ 1.5 h** in BSA/DMEM at 17–21 °C, 23–24% RH, steel undetectable by 24 h (Greatorex 2011, DOI 10.1371/journal.pone.0027932); **99% reduction at 174.9 h** on steel in 0.3% BSA, viable to 2 weeks (Thompson 2017, DOI 10.1016/j.jhin.2016.12.003); **<2 log10 over 7 days** on steel in mucin/FBS/medium at 18–25 °C, 20–55% RH, AH significant p<0.0001, strain not p=0.45 (Perry 2016, DOI 10.1128/aem.04046-15); 24–48 h recoverable on steel/plastic (Bean 1982, DOI 10.1093/infdis/146.1.47; Oxford 2014, DOI 10.1016/j.ajic.2013.10.016). Decay on steel is **non-monotone in RH** (fastest mid-range, Qian 2023). RNA persists 1–3 orders longer than infectivity on the same coupons (Greatorex: 0.06 log10 RNA loss vs >4.2 log10 infectivity at 24 h on steel; Thompson: 7 weeks PCR vs 2 weeks viable) | ⊘ **field** — confirmed by search, not argument: the scalar has no measured referent, and the sourced quantity is a matrix- and RH-conditioned **interval of half-lives**, not a point. Evidence recorded; no value adoptable until the field moves to the measured unit (as norovirus did in #41) | #44 |
| Same key in Edison's *proposed* bundle (not in `data/`) | **4.8**, range [2.0, 16.0] | P | Unchanged by this tranche: nothing found measures influenza surface persistence in any unit in which 4.8/day is a coherent value | **must not be loaded** | #44 |
| `illness_probability.eta` / `gamma` | 0.67 / 0.1 | C | **Refuted at the cited source, verified in Carrat's Results** (*Am J Epidemiol* 2008;167:775–785, DOI 10.1093/aje/kwm375): "The proportion of symptomatic infection (any symptoms) was 66.9 percent (95 percent CI: 58.3, 74.5). No significant difference was noted according to the virus type … or the initial infectious dose (p = 0.12)." Denominator **522 infected individuals in 38 subgroups**, from 56 studies / 1,280 challenged, inoculum **3–7.2 log10 TCID50** (4.2 orders). Lower-respiratory symptoms 21.0% (14.0–30.3) likewise dose-independent. The one clinical dose association runs the **wrong way**: fever OR **0.56 per log10 TCID50** (0.42–0.73, p<0.001), which the authors call striking and unexplained. The only contrary claim found is Teunis 2010 (DOI 10.1016/j.epidem.2010.10.001), whose "slightly higher illness risk due to the higher doses involved" is an output of a **fitted** hierarchical dose-response model, class C, and therefore circular for an attack-rate-scored model | ⊘ mech → **refuted**: the field `1 − (1 + η·dose)^−γ` is strictly increasing in dose and the measured endpoint is flat over 4.2 orders. 0.67 is a pooled population fraction with a CI, not a dose-curve parameter. No replacement form proposed here | #44 |

## Notes for the merge

* Grades: Qian, Perry, Greatorex, Thompson, Bean, Oxford, Sakaguchi, Noyce,
  Rockey = **B** (direct measurement, analogous setting: laboratory coupons, not
  a cabin). Carrat's illness endpoint = **A** for the endpoint as the model
  defines it (pooled human challenge studies), with the dose test being a
  meta-regression across subgroups. Teunis 2010, Watanabe 2012, Canini 2010 =
  **C**, fitted.
* Nothing in §3.3 was ranked or excluded by its effect on VSP, the Diamond
  Princess, the Greg Mortimer or any anchor; no such quantity was computed.
* Open gaps worth their own items: no infectious half-life for influenza A on
  steel or plastic in **human saliva** at cabin temperature with a stated CI;
  no single-cohort measurement of illness-given-infection against dose;
  Teunis 2010 primary text unread (paywalled).
