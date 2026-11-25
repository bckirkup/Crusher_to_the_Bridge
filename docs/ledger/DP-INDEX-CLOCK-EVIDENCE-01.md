# DP-INDEX-CLOCK-EVIDENCE-01
**Date:** 2026-11-25
**Commit:** cdbe1a8d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** cdbe1a8d

**DP-UNION-CLOCK-01 stopped at the evidence gate.** NIID explicitly corrected
the Hong Kong passenger's cough onset to **23 January 2020**. His treating
clinicians also place his first reported symptom on that date. The proposed
19 January canary required an absence of primary support for 23 January.

## Measured (what the primary sources report)

All dates concern the same passenger who boarded at Yokohama on 20 January
and disembarked in Hong Kong on 25 January, except the separate case in the
last row. Dates refer to 2020.

| Event | What the source says | Where read |
|---|---|---|
| Index cough, corrected official record | NIID identifies the passenger by his 25 January disembarkation and explicitly calls “cough since 19 Jan” incorrect. Its replacement date is 23 January. | NIID, *Field Briefing: Diamond Princess COVID-19 Cases*, **Corrigendum**, second bullet (the first bullet corrects a table denominator). [Agency text](https://id-info.jihs.go.jp/niid/en/2019-ncov-e/9407-covid-dp-fe-01.html) |
| Index cough, clinical history | The treating team describes a “mild dry cough on 23 January 2020” with no other symptoms then. | Leung et al., *Journal of Travel Medicine*, first patient narrative accompanying Fig. 1A. [Case report](https://doi.org/10.1093/jtm/taaa073) |
| Index cough, conflicting accounts | Hong Kong's initial case notice gives 19 January. Yamagishi et al. also say the cough started on 19 January. | Hong Kong CHP, 1 February case notice, patient history. Yamagishi et al., *Eurosurveillance*, “Outbreak detection”. [CHP notice](https://www.info.gov.hk/gia/general/202002/01/P2020020100795.htm) · [Outbreak study](https://doi.org/10.2807/1560-7917.ES.2020.25.23.2000272) |
| Fever and medical attendance | Leung et al. record feverishness on 29 January and a hospital visit on 30 January. CHP and Yamagishi et al. date fever onset to 30 January. | Clinical narrative, CHP patient history, and “Outbreak detection”, respectively. [Leung](https://doi.org/10.1093/jtm/taaa073) · [CHP](https://www.info.gov.hk/gia/general/202002/01/P2020020100795.htm) · [Yamagishi](https://doi.org/10.2807/1560-7917.ES.2020.25.23.2000272) |
| Diagnosis and reporting | The Hong Kong RT-PCR was positive on 1 February. CHP announced the case that day. Yamagishi et al. date the report to Japan's health ministry to 1 February and notification with the travel history to 2 February. | Clinical narrative, dated CHP notice, and “Outbreak detection”. [Leung](https://doi.org/10.1093/jtm/taaa073) · [CHP](https://www.info.gov.hk/gia/general/202002/01/P2020020100795.htm) · [Yamagishi](https://doi.org/10.2807/1560-7917.ES.2020.25.23.2000272) |
| Earliest other confirmed case | Yamagishi et al. report onset on **22 January**, explicitly excluding the Hong Kong index. The report establishes another person's symptom date. The transmission link is unknown. | Yamagishi et al., Abstract (earliest confirmed non-index onset). [Outbreak study](https://doi.org/10.2807/1560-7917.ES.2020.25.23.2000272) |

Tsuboi et al.'s Japanese quarantine study also describes this passenger as
“coughing since 23 January” in its Introduction. The NIID corrigendum is
the source that explicitly compares the two dates. [Quarantine study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7731102/)

## Inferred (mapping the record to the arm)

The clock uses the first reported symptom. With boarding as voyage day 0,
the corrected cough date maps to day +3. The frozen `union_niid` arm uses
+3.0 and infection age 2.8 days. The resulting 5.8-day incubation is a
model assumption. The case histories give no measured infection date.
[Frozen design](../../picard_framework/runs/covid_dp_union_01_design.json) ·
[Engine clock audit](COVID-INDEX-CLOCK-01.md)

The −1.0-day declaration in [SEED-ONSET-01](SEED-ONSET-01.md) accurately
represents the Yamagishi account. The NIID correction applies to its own
briefing. Kosmos's `THETA_AFTER_BEHAVIOR.md` was an external proposal. No
file of that name occurs in the checkout or its reachable Git history at
`cdbe1a8d`. The primary basis for +3 is the agency corrigendum and the
clinical history above.

## Hypothesis and disposition

Whether changing this clock alone would alter founder yield on the union
arm remains unmeasured. First diagnosis also leaves the identity of the
person who introduced the infection unresolved, as Leung et al. discuss.

The completed [DP-UNION-01 readout](../covid/covid_dp_union_01_readout.md)
found no consistent θ on the corrected clock. DP-UNION-CLOCK-01 submitted
zero jobs. Founder count and all seven contract outcomes are unmeasured
for the proposed arm. The decision for review is to close that canary on
the evidence gate and retain the 23 January clock for the reconstruction.
