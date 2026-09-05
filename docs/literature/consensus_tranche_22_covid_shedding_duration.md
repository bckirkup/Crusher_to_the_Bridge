# Tranche 22 — the SARS-CoV-2 shedding clock: two clocks are measured, the field can only carry one, and the one it carries is RNA


**Register rows fed / supersession.** This tranche feeds
`shedding_duration_days` in §3.2 of
[`docs/parameter_provenance_register.md`](../parameter_provenance_register.md),
the row [tranche 9](mql_tranche_9_sars_cov2.md) §5 opened as blocked. Tranche 9's
finding that the arm carries no value is superseded by A2 (#51), which adopts
one; tranche 9's evidence and arithmetic are unchanged.

**Status:** Evidence assembled and **one value adopted** —
`sars_cov2_resp.shedding_duration_days` = 15, interval [10.8, 18.4] — in the
same change as this document. Nothing else in the profile moves. The
authoritative per-quantity status is the register; this document reports what
was searched, including what was found and rejected.

**Scope:** task #51, item A2 of
[`../proposals/defect_resolution_plan.md`](../proposals/defect_resolution_plan.md).
The quantity is the **shedding period from symptom onset**, in days, for the
`sars_cov2_resp` arm: the field that ends the infection in
`engines/natural_history.clearance_days`, separately from `recovery_day`, which
ends the illness.

---

## 1. What the field is, which decides which quantity is admissible

`shedding_duration_days` bounds the infection, and while it runs the host emits
from `shedding_curve_log10`. That curve is a **nasal concentration in genome
copies** ([tranche 9](mql_tranche_9_sars_cov2.md) §1, which is also why its
magnitude is still blocked). So the clock and the curve are both RNA quantities,
and the quantity to source is the **duration of upper-respiratory RNA
positivity**, not the duration of culturable virus. Sourcing the infectious
duration into this field would shorten the *detectability* window — the thing
the COVID arm is scored on (#33, Diamond Princess, a repeat-testing series over
weeks) — to buy a dose correction worth 0.021% of the curve integral.

That trade is stated in the register row and in the profile note rather than
hidden, because it is the honest cost of one field serving two clocks: days 8–14
emit at 2.0–5.5 log10 as though infectious when the culture evidence says most
hosts are not. Splitting the clocks is a structural change, not a sourcing one,
and is not done here.

## 2. Method

Three unfiltered Consensus searches, full-text chunks requested on each. No
filters, no date restriction. Queries as issued:

| # | Query | Outcome |
|---|---|---|
| 1 | *SARS-CoV-2 duration of upper respiratory tract RNA shedding mean days meta-analysis viable virus isolation days* | Cevik 2020, Fontana 2020, Wu 2023 — the three pooled durations §3 adopts from, all with the RNA/viable split in body chunks |
| 2 | *duration PCR positivity days after symptom onset SARS-CoV-2 nasopharyngeal swab cohort median time to negative conversion* | Mancuso 2020, Mallett 2020 — corroboration, and the protocol-endpoint rejection of §4 |
| 3 | *duration of infectious viable virus culture positivity days after symptom onset SARS-CoV-2 longitudinal cohort* | Drain 2022 — both clocks measured in the same 95 subjects, §5 |

The ladder was not escalated past E0: every quantity below was returned in a
Results or Abstract chunk of the paper that reports it.

## 3. The RNA-positivity duration — three pooled estimates, ~7.6 days apart

| Source | Design | Pooled duration, URT | Section of origin |
|---|---|---|---|
| Cevik 2020, *Lancet Microbe*, DOI [10.1016/S2666-5247(20)30172-5](https://doi.org/10.1016/S2666-5247(20)30172-5) | Meta-analysis, 43 studies, 3,229 individuals, to June 2020 | **mean 17.0 d** (95% CI 15.5–18.6) | **R** |
| Fontana 2020, *Infect Control Hosp Epidemiol*, DOI [10.1017/ice.2020.1273](https://doi.org/10.1017/ice.2020.1273) | Meta-analysis, 28 studies, to 2020-09-08 | **median 18.4 d** (95% CI 15.5–21.3, I² = 98.9%) | **R** |
| Wu 2023, *Int J Infect Dis*, DOI [10.1016/j.ijid.2023.02.011](https://doi.org/10.1016/j.ijid.2023.02.011) | Meta-analysis, Omicron, URT, 2021-11 to 2022-12 | **mean 10.82 d** (95% CI 10.23–11.42) | **R** |

**Interval [10.8, 18.4].** Its width is variant and era — ancestral versus
Omicron, pre-vaccination versus post — not measurement error, so it must not be
collapsed on the argument that the estimates are imprecise. Fontana's own I² of
98.9% says the same thing inside a single pooling.

**Shipped 15.** It is the authored curve's own length, and it sits 0.4 d from the
interval midpoint (14.6). Both facts are stated because neither alone would be a
reason: the curve length is a model artefact and the midpoint is a convention.
What matters for the no-tuning rule is what 15 is *not* — it is not selected
against Diamond Princess, the passenger/crew ratio, or any other scored anchor,
and no anchor was evaluated at any candidate before it was chosen. Adopting
Cevik's 17.0 or Wu's 10.82 instead would require the curve to be extended or
truncated respectively, which is a curve change and belongs to #30.

**Where the value lands.** Both shipped bundles that carry this arm —
`data/pathogens/active_profiles.json` and
`data/pathogens/edison_10pathogen_profiles.json`, the latter being what the
mega-cruise campaign manifests run — get the same 15, since the campaign is what
the #36/#37 gate sweeps and a bundle left at 7 would sweep the defective arm.

## 4. Rejected: the clearance-protocol endpoints, which are 2–3× longer

Mancuso 2020 (*BMJ Open*, DOI [10.1136/bmjopen-2020-040380](https://doi.org/10.1136/bmjopen-2020-040380);
1,162 subjects, Reggio Emilia) reports median **30 days from diagnosis** and
**36 days from symptom onset** to first negative swab, IQR 28–45, rising with
age and severity. Mallett 2020 (*BMC Medicine*, DOI [10.1186/s12916-020-01810-8](https://doi.org/10.1186/s12916-020-01810-8);
IPD review, 32 studies, 1,023 participants) reports nasopharyngeal positivity
89% (83–93) at 0–4 d falling to 54% (47–61) at 10–14 d, with virus still
detectable at 46 d in some participants.

Neither is admitted into the interval, and not because they disagree with it.
Their endpoint is different: *time until a test-and-release protocol records a
negative*, in a cohort followed because it is being cleared, which mixes the
duration of positivity with the sampling schedule and the assay's false-negative
rate — Mancuso measures that rate directly at about one in five. They are
recorded as corroborating the **tail** (positivity past three weeks is common)
without moving the pooled central estimate.

## 5. The other clock, measured in the same subjects

Drain 2022 (*J Clin Virol*, DOI [10.1016/j.jcv.2023.105420](https://doi.org/10.1016/j.jcv.2023.105420);
95 ambulatory adults, serial nasal swabs with viral culture) is the cleanest
statement of the split, because one cohort carries both endpoints: median time
from symptom onset to first negative was **11 d [IQR 4] by culture** against
**>19 d by RT-PCR**; culture positivity was 41% (29/71) at 6–10 d and 8% (8/96)
at 11–15 d, while RNA remained positive in **26 of 51** participants tested
21–30 days out. Section of origin **R** (Results table and abstract).

Consistent with it: no live virus past day 9 of illness in any study Cevik
reviewed; Omicron viable-virus duration **5.16 d** (4.18–6.14) against 10.82 d
of PCR positivity in the same Wu meta-analysis; Keske 2023's culture positivity
83/52/13.5/8% at days 5/7/10/14 with 19% infectious after symptoms stop
([tranche 9](mql_tranche_9_sars_cov2.md) §5).

**So the infectious duration is ~5–11 d and the RNA duration ~11–18 d, in the
same populations.** That is a 2× separation measured within cohorts, not a
disagreement between them, and it is the reason the register carries the cost of
the choice in §1 rather than treating 15 as an infectious period.

## 6. What this tranche does not do

- It does not source the curve's magnitude or its shape (#30, still blocked on
  the emission/dose product).
- It does not add a second, infectious-duration field. That is a model change:
  it needs a separate clock, and the emission side would have to decide which
  clock each route reads.
- It does not touch `recovery_day` = 7, which stays the illness duration.
- It evaluates no anchor. #33 is unblocked by this change, not answered by it.
