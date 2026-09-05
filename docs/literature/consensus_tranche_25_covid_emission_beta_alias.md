# Tranche 25 — emission scale and β are one axis in this tree, not two, and the only copies-denominated β candidate is attack-rate-derived: #30 refused on evidence


**Register rows fed / supersession.** This tranche feeds §3.2's
`shedding_curve_log10` (magnitude) and `dose_response.alpha` / `beta` rows and
**supersedes §4 item 4's instruction** to sweep β "over the Killingley-to-Zhang &
Wang span": one endpoint of that span is not admissible under this repository's
own no-attack-rate-fitting rule (§3), and the two named factors are not two
sweepable axes in the shipped establishment step (§1). No later withdrawal is
recorded in the register or the norovirus open ledger.

**Status:** Evidence assembled and interpreted, plus one in-tree derivation.
**No pathogen-profile constant, no engine constant and no screen interval changes
in this document.** The arithmetic in §1 is reproducible from the shipped profile
and is locked by `tests/test_dose_pathway_invariants.py`
(`test_dose_and_susceptibility_enter_only_as_a_product`,
`test_beta_rescales_the_susceptibility_draw`).

**Scope:** item #30 — SARS-CoV-2 emission scale **and** `dose_response.beta`,
taken jointly, which is the only way they can be taken. Track C item C2.

**Method:** five Consensus MCP `search` queries, unfiltered except where noted,
on top of the recall already established for this item by
[tranche 4](consensus_tranche_4.md) §2 (both halves in copies),
[tranche 9](mql_tranche_9_sars_cov2.md) §1–2 (the emission bracket, and the three
MQL denominator candidates) and
[tranche 15](consensus_tranche_15_covid_dose_denominator.md) (eight queries: no
ID50 in copies exists, and the copies-per-infectious-unit bridge is ~2.7 logs
wide). This unit does not re-run that recall; it asks the one question those three
left open — **whether the copies-denominated denominator that #30 was told to
sweep to is admissible at all** — and settles what the sweep axis is.

**No candidate was selected, ranked or rejected by what its value would do to
VSP, the Diamond Princess, the Greg Mortimer or any anchor in `docs/anchors/`.**
That comparison was not computed at any point in this unit, and §1's conclusion is
that it *could* not have been informative about either factor separately.

---

## 1. What "jointly" means in this tree, derived rather than asserted

The register has said since #366 that emission scale and β "enter the beta-frailty
law strictly as a product". That is the right conclusion and it was never shown
against the shipped code. It is stronger than the register states.

The per-host establishment step is `TransmissionCore._dose_response_hazard`:

```python
susceptibility = self._dose_response_susceptibility(agent, pathogen_id)  # ~ Beta(α, β), drawn once, persistent
return -math.expm1(-susceptibility * effective_dose)
```

Two consequences, computed at the shipped `sars_cov2_resp` pair
(α = 0.18, β = 58.0):

1. **The hazard is a function of the product `susceptibility × effective_dose`
   and of nothing else.** Halving the emission scale and doubling susceptibility
   is not *approximately* the same run, it is bit-for-bit the same hazard: over
   2 × 10⁶ Beta draws, `max|h(s, D) − h(s/c, cD)| = 1.1 × 10⁻¹⁶` for
   c ∈ {10, 10², 10³}, i.e. floating-point noise.
2. **β is a scale parameter on the susceptibility draw over the whole range a
   sweep would use.** `Beta(α, βc) ≈ Beta(α, β) / c` to within **0.7%** on every
   quantile from the 5th to the 95th, and 0.31% on the mean, for
   c up to 10⁴ (exact Beta quantiles, not sampling). β⁻¹ is therefore a
   multiplier on dose, and α — not β — is what carries the *shape* of host
   heterogeneity.

So a sweep over β and a sweep over the emission scale traverse the same
one-dimensional family of models. **The identified composite is**

```
Θ  =  (copies emitted per epoch at peak shedding)  ×  (per-copy infection risk)
```

and the shipped arm's Θ, on the airborne path, is

```
10**9.0 × 5e-5  copies/epoch          = 5.0 × 10⁴      (tranche 9 §1)
E[s] = α/(α+β) = 0.18/58.18           = 3.09 × 10⁻³ per copy
```

before route multipliers and room dilution. **Nothing in outbreak data, and
nothing in either half's literature, can separate the two factors of Θ.** Fixing
one from measurement is the *only* way to make the other mean anything, which is
exactly what #30 was written to do — and §3 is why it cannot be done on the β
side.

**This is a live warning for #36.** A Morris screen that carries
`shedding_curve_log10` magnitude (or `airborne_emission_fraction`) *and*
`dose_response.beta` as separate factors is screening one factor twice: their
elementary effects are aliased by construction, so the screen would report a
spurious pair of large main effects with a perfect interaction between them, and
the pair's apparent importance would be split arbitrarily by the sampling. The
screen must carry **one** factor for Θ, or hold β fixed and vary emission alone.

## 2. Queries, verbatim

Run against `mcp_tool(server="consensus", tool_name="search")`.

1. `dose-response relation deduced for coronaviruses SARS-CoV-2 exponential model virus RNA copies meta-analysis infection risk assessment aerosol transmission` — unfiltered; written to retrieve Zhang & Wang 2020's own statement of its design.
2. `SARS-CoV-2 dose-response model infectious dose in genome copies human challenge inoculum quantified RNA copies naive host` — `year_min=2023`, to test whether anything published after tranche 15's recall closes the copies-denominated null.
3. `Miura individual variation susceptibility human challenge beta-Poisson dose-response SARS-CoV-2 HCoV-229E estimated parameters TCID50` — unfiltered; the engine's functional form is beta-frailty, so a challenge-fitted *beta-Poisson* pair would be the one candidate worth composing through the copies bridge.
4. `measured exhaled SARS-CoV-2 RNA emission rate copies per minute breath aerosol sampling infected individuals quantified` — `year_min=2023`, to test the emission half of Θ for new measurement.
5. `beta-Poisson dose-response parameters alpha beta SARS-CoV-2 quantitative microbial risk assessment RNA genome copies N50 estimate` — unfiltered.

## 3. The β side: the copies-denominated candidate is attack-rate-derived, and it is not independent of the emission side either

Zhang & Wang 2020 (*Clin Infect Dis*, DOI
[10.1093/cid/ciaa1675](https://doi.org/10.1093/cid/ciaa1675)) is the only
dose-response relation for SARS-CoV-2 stated in genome copies:
an exponential form with **k ≈ 6.4 × 10⁴ – 9.8 × 10⁵ virus copies**, i.e. a
per-copy infection risk of **10⁻⁶ – 10⁻⁵**. Its Methods, in its own abstract
(query 1, read from the returned abstract — **Ab**):

> "We developed a simple framework to integrate the a priori dose-response
> relation for SARS-CoV-2 **based on mice experiments**, the recent data on
> **infection risk from a meta-analysis**, and **respiratory virus shedding in
> exhaled breath** to shed light on the dose-response relation for humans."

Three defects, and each one alone is disqualifying under a rule this repository
already applies elsewhere:

1. **Its prior is the murine dose-response.** That is the same
   transgenic-mouse/MHV-1 basis (Watanabe 2010) whose attribution for the shipped
   α/β pair the register has already withdrawn twice, on the grounds that the
   data are murine and the units are PFU. Re-entering it as a *prior* does not
   make it a human measurement.
2. **Its human calibration is a meta-analysis of observed infection risk** — i.e.
   attack rates. This is the defect for which tranche 9 and tranche 15 rejected
   Prentiss 2022, Riediker 2022, Marc 2021, Iyaniwura 2024 and Xu 2025.
   Consistency is not optional: a value fitted to observed infection risk cannot
   be adopted into a model whose scored anchors *are* observed infection risk,
   however it is denominated. **Which** infection-risk meta-analysis, and whether
   its inputs include the cruise-ship series this model is scored against, could
   not be read from the retrieved abstract and is recorded as **unverified** —
   but the rule does not depend on the answer.
3. **Its third input is exhaled-breath shedding**, which is the *other* factor of
   Θ. Fixing β from Zhang & Wang and then comparing the emission scale against
   Alsved/Zheng/Lane/Coleman would be checking a measurement against a quantity
   partly derived from it. The one thing §1 says is required of the pair — that
   the fixed factor be independent of the free one — is exactly what this
   candidate does not offer.

**β is therefore refused on evidence, in copies, and the register's sweep
instruction is retired.** The Killingley endpoint stays what tranche 15 made it:
a real measured naive-human dose point in **TCID50**, reachable only through a
~2.7-log copies-per-infectious-unit bridge and a 0.59–0.96 log10 TCID50→PFU
offset, and at one dose level, which cannot identify a two-parameter
dose-response. The other endpoint is not admissible at all. A span needs two
endpoints.

**What that leaves is a null on Θ, not an interval.** The emission factor is
bounded by measurement (§4, grade B, ~4 logs). The per-copy factor has **no
admissible source in copies**, so their product is unbounded, and the honest
register state for both rows is ⊘ joint with **∅ null on the susceptibility
factor** — not "β identifiable given the bracket", which is what §3.2 currently
claims and which was true only if Zhang & Wang were usable.

## 4. The emission side: unchanged in interpretation, one new datum in the middle of the gap

Tranche 9 §1 bracketed peak emission at **4.2 × 10³ – 5.8 × 10⁷ copies per
epoch** (Alsved 2022's 70/110/80 copies min⁻¹ breathing/talking/singing, n = 38,
against Zheng 2022's 4.4–5.8 × 10⁷ copies h⁻¹ in 11 of 25 Omicron patients),
with the shipped arm's 5 × 10⁴ inside it. Query 4 adds one measurement inside the
4.1-log gap and no measurement outside the bracket:

| Source | Setting | Measured | In copies/epoch (1 h) | Grade |
|---|---|---|---|---|
| Malik 2023, *Infect Prev Pract*, DOI [10.1016/j.infpip.2023.100299](https://doi.org/10.1016/j.infpip.2023.100299) | Filter-based exhaled-breath device, hospitalised patients sampled on days 1/3/5/7/10/12/14, RT-qPCR | Symptomatic case **8.6 × 10³ – 4.1 × 10⁴ copies h⁻¹**, near-constant over the trajectory; **asymptomatic case up to 2 × 10⁵ copies h⁻¹**, ~10× the symptomatic one | **8.6 × 10³ – 2 × 10⁵** | **C** — right quantity, right units, direct measurement, but **n = 2** (a case report) |
| Lane 2023 (preprint), DOI [10.1101/2023.09.06.23295138](https://doi.org/10.1101/2023.09.06.23295138) | 312 breath specimens, natural breathing, multiple times daily | mean **80 copies min⁻¹** days 1–8 from onset, individual spikes > 800 min⁻¹, steep drop after day 8 | **4.8 × 10³** (mean), 4.8 × 10⁴ at the spikes | **B** design, **preprint** — carried as it was in tranche 4, not upgraded |

Malik's ordering — asymptomatic above symptomatic — is a second, independent
corroboration of the direction §3.2 already records as refuting
`asymptomatic_shedding_log10`'s −1.5-log offset. It is not adopted here (that
field is #31's), and at n = 2 it could not be.

**The bracket does not narrow.** Its width is method (breath condensate vs
aerosol sampler vs filter device) and host, not uncertainty about a single true
value, and Malik lands where a middle-of-the-gap measurement should if that
reading is right.

## 5. Rejected and non-adoptable candidates, with the reason

| Candidate | Reason |
|---|---|
| Cheng 2024, *Build Environ*, DOI [10.1016/j.buildenv.2024.112256](https://doi.org/10.1016/j.buildenv.2024.112256) — power-law quanta generation for the top 30% of cases | **Quanta are the composite Θ, back-calculated.** The paper states its two available methods are the viral-load method (which needs dose-response parameters as input — the thing we are trying to source) and the outbreak method (Wells-Riley on observed attack rates — circular). Either way it cannot separate §1's factors, which is the same finding as §1 arrived at independently |
| Aganovic 2023, *Risk Analysis*, DOI [10.1111/risa.14178](https://doi.org/10.1111/risa.14178) — four dose-response models compared on human challenge data | The **only** challenge-fitted coronavirus dose-response found: exponential **k = 0.054 for HCoV-229E** best-fitting, with Laplace-approximated beta-Poisson preferred for rhinovirus (α = 0.152, β = 0.021 for HRV-16). Not adoptable: **different virus**, and the dose axis is TCID50 for a virus with no copies bridge measured here. Recorded because it is the closest thing in the literature to the object #30 wants, and because it is direct evidence that the *functional form* is not settled by the data even where challenge doses exist |
| Miura 2023, *Epidemiology*, DOI [10.1097/ede.0000000000001679](https://doi.org/10.1097/ede.0000000000001679) — peer-reviewed successor to the Miura 2022 preprint the audit cited | A **framework** for reading challenge trials with individual variation in susceptibility — the same beta-frailty shape this engine uses — fitted for HCoV-229E, where several dose levels exist. For SARS-CoV-2 it presents "plausible infection risks over multiple orders of magnitude of the infectious dose" rather than a fitted pair, because Killingley has **one** dose level. Supersedes the preprint citation in `docs/covid/covid_parameter_provenance_audit.md` §2; adopts nothing |
| Xu 2025 (*Epidemics*), Iyaniwura 2024 (*PNAS*) | Already rejected in tranche 15 as within-host models fitted to the Killingley data. Query 2 returned both again at the top of the ranking, which is the recall check working: the corpus's answer to "dose-response in copies" is still *fitted to the one challenge study* |
| Xie 2017, *Risk Analysis*, DOI [10.1111/risa.12682](https://doi.org/10.1111/risa.12682); Schmidt 2013, DOI [10.1111/risa.12006](https://doi.org/10.1111/risa.12006) | Methodological, not sources for a value, and both bear on §1. Xie's validity rule of thumb for the *approximate* beta-Poisson form is β̂ > (22α̂)^0.5 for 0.02 < α̂ < 2: at the shipped COVID pair that is 58.0 > 1.99, and at the norovirus pair 32.81 > 1.56, so both shipped pairs satisfy it — and the engine's establishment step uses the exact beta mixture regardless (`formal_spec_v2.md` §A.2). Schmidt establishes that the Beta term in this model "cannot address variation among individual pathogens", i.e. it is **host** heterogeneity, which is how `_dose_response_susceptibility` draws it — one draw per agent, persistent |
| Malik 2023 as an emission *value* | Kept as an interval datum only (§4); n = 2 |

## 6. What this tranche licenses

**Licensed:**

1. **A refusal.** `dose_response.beta` for `sars_cov2_resp` cannot be adopted in
   genome copies: the only copies-denominated candidate is attack-rate-calibrated
   on a murine prior and shares its exhaled-shedding input with the other factor
   of Θ. §4 item 4's "β swept over the Killingley-to-Zhang & Wang span" is
   withdrawn as an instruction.
2. **A restatement of the axis, for #36 and #37.** Emission scale and β are one
   factor, to within 0.7% across a 4-log rescaling of β, and the screen must not
   carry them as two.
3. **The emission bracket stands** at 4.2 × 10³ – 5.8 × 10⁷ copies/epoch, grade
   B, with Malik 2023 as a grade-C datum inside it.

**Not licensed, and deliberately not done:**

- No composition of Killingley through the copies bridge (tranche 15 §6.4 states
  what it would cost: > 3 logs, wider than the sweep already carried).
- No refit of α/β, and no selection of a point inside any span. The standing rule
  that every dose figure is void pending a refit is unaffected — this unit removes
  a sweep endpoint, it does not move a value.
- No change to `airborne_emission_fraction` (#42's field, C4): it remains
  derivable as measured rate ÷ modelled titre once the curve's units are fixed,
  and §1 is the reason the derivation must be booked against Θ rather than
  treated as an independent third quantity.

## 7. The nulls, stated plainly

- **No admissible copies-denominated dose-response for SARS-CoV-2 exists.**
  Tranche 15 established that no *measured* ID50 in copies exists; this unit adds
  that the one *derived* relation in copies fails the non-circularity rule, so the
  null is complete rather than partial.
- **No challenge-fitted beta-Poisson pair for SARS-CoV-2 exists**, because
  Killingley used a single dose level (Miura 2023 is explicit about the
  consequence). The only challenge-fitted coronavirus pair in the literature is
  for HCoV-229E, in TCID50 (Aganovic 2023).
- **No measurement separates emission scale from susceptibility**, and after §1
  that is a statement about the model's identifiability rather than a gap in the
  literature: no attack-rate observation could.
