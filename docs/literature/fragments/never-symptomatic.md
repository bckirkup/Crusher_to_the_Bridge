# Register fragment — `never_symptomatic_fraction` (norovirus)

**Status:** Additive fragment from task #53, tranche 11. Not authoritative:
the row below is a **proposal** for
[`docs/parameter_provenance_register.md`](../../parameter_provenance_register.md),
to be merged by the lead in one pass with the other fragments. This file changes
no model value and edits no shared document. Evidence and rejected candidates:
[tranche 11](../consensus_tranche_11_never_symptomatic.md).

**State:** evidence recorded — **two design-separated intervals, no value
licensed**. The field as the model's population defines it (adults, natural
exposure, whole-course) remains **unmeasured**, so the boarding load error
should stay in place.

Proposed replacement for the existing `never_symptomatic_fraction` row:

| Quantity | Shipped | Grade | Evidence | State | Item |
|---|---|---|---|---|---|
| `never_symptomatic_fraction` — share of imported infections that never present, in a boarding population | **none shipped** | **B as two intervals; C for the model's own population** | **Searched** ([tranche 11](literature/consensus_tranche_11_never_symptomatic.md)). Two admissible designs disagree and are **not pooled**. **Challenge studies, infected adults, illness = diarrhoea and/or vomiting: [0.22, 0.36]** — GI.1 5/14 (Gray 1994, *J Clin Microbiol*, DOI 10.1128/jcm.32.12.3059-3063.1994) and 7/26 (Newman 2016, *Clin Exp Immunol*, DOI 10.1111/cei.12772), GI.1 33% of 21 infected (Atmar 2014, *J Infect Dis*, DOI 10.1093/infdis/jit620), **GII.4** 4/16 infected secretors (Frenck 2012, *J Infect Dis*, DOI 10.1093/infdis/jis514), **GII.2** ≈6/24 infected (Rouphael 2022, *J Infect Dis*, DOI 10.1093/infdis/jiac045, Table 1) — at inocula far above natural exposure. **Community birth cohorts, weekly sampling: [0.59, 0.68]** overall, **[0.59, 0.63]** for GII — 214/328 infections (Baker 2026 PREVAIL, *Clin Infect Dis*, DOI 10.1093/cid/ciag033; GII.4 Sydney 30/51, other GII 83/131, GI 30/37) and 127/209 (El-Heneidy 2022, *Pediatr Infect Dis J*, DOI 10.1097/inf.0000000000003667, 183/221 infections GII) — but in children under 3, in whom the fraction falls with age (71.1% year 1 → 61.2% year 2, no symptomatic infection before 4 months). **The definition moves the value more than the population does:** the same GII.2 trial reads 25% (Rouphael, diarrhoea and/or vomiting) or 64% (Qu 2025, *J Med Virol*, DOI 10.1002/jmv.70546, AGE presentation). Outbreak-conditioned figures — Miura 2018's 32.1% (also a fitted MLE), Wang 2023's 21.8%, Wang 2024's 17.6%, Qi 2018's 18% — are **excluded as circular**, measured in populations conditioned on the outcome the model is scored on; Lopman 2014 (*Am J Epidemiol*, DOI 10.1093/aje/kwt287) and Teunis 2020 are **model outputs, not measurements** | ⊘ **no value licensed** — **no study measures this in adults under natural exposure**; sweep the two intervals separately, never a pooled central value, and declare which illness definition the `never_symptomatic` state means before adopting either. Boarding stays a load error | #45, #53 |
