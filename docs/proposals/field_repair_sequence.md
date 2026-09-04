# Field repair sequence: four defects, four different repairs, and only one is a curve

> **Status:** **R1 landed** (this branch: the fraction alias is deleted and both
> bundles are on `surface_decay_log10_per_day`); **R2–R5 proposed, and not
> implemented**. **No value is adopted** — R1 was a value-preserving unit
> migration, not a repair, so no register value, grade or interval moved with
> it. §1's account of the pre-R1 state is kept as the reason the migration was
> needed, not as a description of the tree.
> It sequences the field repairs that
> [`bayesian_inference_design.md`](bayesian_inference_design.md) §1 requires
> before any inference runs, and it **corrects that document's §1**, which
> described all four as the same defect. They are not. Every interval and
> citation below is already recorded in the
> [provenance register](../parameter_provenance_register.md) or in the
> literature tranches; this document re-reads them and proposes no new value.

## 0. The correction

`bayesian_inference_design.md` §1 listed four fields as instances of one class —
"the literature measures a function and the field holds one number". Checked row
by row against the register, that is right about **one** of them. The four are
four different defects with four different remedies, and two are not
curve-shaped at all:

| Field | Register state | Actual defect | Remedy |
|-------|----------------|---------------|--------|
| influenza `surface_decay_per_day` = 0.94 | `⊘ field` — confirmed by search | **A curve.** The measured quantity is a matrix- and RH-conditioned interval of half-lives | Covariate-indexed rate |
| influenza `illness_probability.eta` / `gamma` = 0.67 / 0.1 | `⊘ mech → refuted` | **A refuted form.** `1 − (1 + η·dose)^−γ` is strictly increasing in dose; the endpoint is flat over 4.2 orders | **Delete** the dose dependence — a simplification, not a curve |
| norovirus `airborne_emission_fraction` = 1e-4 | **not blocked**; `⊘ field` defect recorded **resolved** (#42), row unsourced | **A definition with the wrong conditioning** — and a candidate source exists under the right one | Redefine as emesis-event-conditioned |
| SARS-CoV-2 `dose_response.alpha` / `beta` = 0.18 / 58.0 | `⊘ joint, and ∅ null in copies` | **Unit incommensurability.** No ID50 in genome copies exists from any design; every independent dose measurement is in infectious units | Move the pipeline's unit, or source a conversion |

So the design document's §1 overstated two rows. In particular it said
`airborne_emission_fraction` has no referent "however it is phrased", and the
register says the opposite: there is a phrasing under which it is sourceable at
Grade B. That sentence should be read as corrected by this table.

**Two of the four repairs cost nothing to run.** `influenza_a` exists only in
`data/pathogens/edison_10pathogen_profiles.json`; `active_profiles.json` carries
`norwalk_gi` and `sars_cov2_resp` only. So both influenza repairs touch a bundle
that is never loaded — no golden moves, no harness re-run, and nothing to
attribute. That is the natural head of the sequence.

## 1. A fifth item, not previously on the list

Norovirus surface decay is recorded as **✓ adopted in sourced units** (#41):
`surface_decay_log10_per_day`, interval **[0.067, 0.79] log10/day**, Grade B,
with the conversion `f = 1 − 10^−k` happening in exactly one place
(`TransmissionCore._surface_survival`). The unit repair is real and it holds.
Two things behind it do not.

**The form was never checked.** Of the five surrogate studies in that interval,
the only one with an RH-and-temperature design — Kim et al. 2012,
*Environ Sci Technol* ([10.1021/es3032105](https://doi.org/10.1021/es3032105)) —
reports that **Weibull fits better than linear**, and Colas de la Noue 2014
([10.1128/aem.01871-14](https://doi.org/10.1128/aem.01871-14)) finds that low
*and* saturated absolute humidity both preserve infectivity better than
intermediate AH, i.e. the dependence is **non-monotone**. The field is a single
exponential rate. So the norovirus row is correctly *united* and still assumes a
*shape* the evidence does not confirm — the same archetype as the citation-with-
the-wrong-number, arriving one level up: the unit is right, the source is real,
and the functional form was never the thing anyone checked. This is a **weaker**
claim than the influenza row: Kim 2012's superiority-of-Weibull is read from its
abstract and its rate constants were never verified (tranche 5 §1 correction
(b)), so the form is *unconfirmed*, not refuted.

**And the sourced key was unexercised — this is what R1 fixed, and it is stated
here in the past tense because R1 has landed on this branch.** No shipped profile
set `surface_decay_log10_per_day`; both active profiles carried the deprecated
fraction alias `surface_decay_per_day`, so behaviour was bit-identical to
pre-#41 and the adopted interval reached nothing that ran. The
`model-parameter-provenance` skill's rule is explicit — *delete superseded
constants; never alias them*, because "a stale duplicate of a corrected constant
is how a correction silently fails to apply". That was the state precisely.
Migrating the two profiles onto the sourced key, and deleting the
alias, is a prerequisite for the influenza repair rather than a follow-up: the
influenza repair introduces the covariate-indexed version of the *same* field,
and doing that while a fraction-valued alias is still live gives the field three
spellings.

The migration is a value-preserving one and must be checked as such:
0.25 fractional ↔ `−log10(0.75)` = **0.125 log10/day** for norovirus, and 0.95
fractional ↔ **1.30 log10/day** for SARS-CoV-2. Those two conversions are the
whole diff, and a golden that moves under them is a defect, not a baseline
update.

## 2. Sequence

**R1 — Migrate the active profiles onto `surface_decay_log10_per_day` and delete
the fraction alias. Landed.** No behaviour change intended; the two conversions
above are the entire content. Attribution rule: any moved golden stops the
change — none moved. Prerequisite for R2, which is now unblocked.

**R2 — Influenza `surface_decay_per_day` becomes a covariate-indexed rate.**
The register's own evidence dictates the covariates, and it contains one
surprise that inverts the obvious parameterisation:

> Qian 2023 ([10.1128/aem.00633-23](https://doi.org/10.1128/aem.00633-23))
> measures half-life 4.5–5.9 h across steel, ABS, PS and glass in **human
> airway surface liquid** at 23% RH, 22–24 °C — and reports the
> **donor-culture spread at 3.2–8.1 h, wider than the between-material
> spread.**

So **matrix, not surface material, is the dominant covariate**, which is the
opposite of how a surface-decay field would naturally be indexed. The rest of
the conditioning is: absolute humidity (Perry 2016 significant at p<0.0001, and
non-monotone on steel per Qian), temperature, and — separately — the assay
endpoint, because Greatorex 2011 measures **0.06 log10 RNA loss against >4.2
log10 infectivity loss at 24 h on the same coupons**. Our pools are denominated
in genome copies and the dose-response consumes copies, so decaying a pool at
the RNA rate is dimensionally consistent and epidemiologically wrong by up to
four orders. Tranche 5 §1 already resolved this for norovirus in favour of the
infectivity rate; the influenza row inherits the same resolution and must state
it, because the influenza evidence base is where the gap is widest.

Strain is **not** a covariate: Perry 2016 finds strain not significant
(p = 0.45).

> **R2's scope is superseded on the environmental axes — see
> [`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md).** The
> covariate-indexed rate described above is kept as the record of what this
> sequence thought the repair was; the correction is recorded, not applied
> retroactively. Its finding is that material, RH and temperature largely
> collapse for an HVAC-pinned ship — none of the three is model state, and
> Qian's between-material spread is inside its between-donor spread — while
> matrix is a selection criterion for sourcing rather than a model covariate.
> The axis that does not collapse is **time since deposition**: decay is
> biphasic and the phase boundary is drying, which the field cannot express at
> all. So R2 and #60 are one question rather than two, and neither is a
> covariate index. The assay-endpoint resolution stated above — infectivity,
> not RNA — is unaffected and still holds. No value is proposed there either.

**R3 — Delete the influenza dose dependence in `illness_probability`.** Carrat
2008 (*Am J Epidemiol* 167:775–785,
[10.1093/aje/kwm375](https://doi.org/10.1093/aje/kwm375)) measures the
proportion of symptomatic infection at **66.9% (95% CI 58.3–74.5)** over
**522 infected individuals in 38 subgroups**, across inocula spanning
**3–7.2 log10 TCID50**, with no significant dose association (p = 0.12) — and
the one clinical dose association runs the wrong way (fever OR 0.56 per log10
TCID50, 0.42–0.73, p<0.001, which the authors call striking and unexplained).
The repair therefore *removes* a mechanism: presentation becomes a
dose-independent probability with a measured CI, and the `η`/`γ` pair is deleted
rather than re-sourced. Grade **B**, not A, because Carrat is a pooled
meta-regression across 56 volunteer challenge studies in clinical facilities —
an analogous setting and a cross-study regression, which is this register's
ceiling for the class. The only contrary claim, Teunis 2010, is an output of a
**fitted** hierarchical dose-response model and is therefore circular for an
attack-rate-scored model; it stays recorded and rejected.

This repair has a consequence worth stating before it is made: it removes a
dose-conditional pathway on the influenza arm, so an influenza fit loses a
degree of freedom. That is the intended direction.

**R4 — Redefine `airborne_emission_fraction` as emesis-event-conditioned.**
As a fraction of *continuous shedding* the quantity has no commensurable
numerator and denominator: shedding is measured in copies/g of stool or
vomitus, airborne virus in copies/m³ of room air, never in the same subjects
(tranche 13 §3.1, six unfiltered queries). Conditioned on an **emesis event** it
has a Grade B source — Tung-Thompson 2015, MS2 in simulated vomiting, n = 3 per
condition, 41 L chamber, corrected for 8.5% sampler efficiency:
**7.2×10⁻⁷ – 2.67×10⁻⁴**, whose denominator is the virus in one expelled bolus.
Two traps to carry with it: the paper's table is in **percent**, so reading it as
fractions overstates by two decades; and the shipped 1e-4 falling inside that
range is coincidence across incompatible denominators, not provenance.

The reason this is the *correct* repair rather than a convenient one is the
`model-parameter-provenance` skill's recurring archetype — *a well-mixed pool
standing in for a small number of concentrated events*, which has now failed in
five separate mechanisms. A fraction of continuous shedding is precisely the
smooth-flow representation of a process that is a small number of large
events, and vomiting has already been the instance of that archetype once
(#352). So R4 is the archetype fix, not a definition tidy.

The COVID arm's `airborne_emission_fraction` is a different case and is not
part of R4: the register records it as **derivable** — measured emission rate
(Alsved 2022, Zheng 2022) ÷ modelled specimen titre, both in copies — pending
the curve's units fix, and it is respiratory rather than emetic. It belongs
with #30.

**R5 — SARS-CoV-2 `dose_response` units.** This is the hardest and it is not a
field-shape repair: no SARS-CoV-2 ID50 in genome copies exists from any design
(tranche 15, eight unfiltered queries, including one written specifically to
characterise the Killingley inoculum in copies), while the pipeline's dose is in
copies. Two admissible routes, and the choice is a design decision rather than a
sourcing one:

1. **Rejected — move the arm's dose pipeline to infectious units**, and carry a
   copies↔infectious conversion only where a measurement supplies one.
2. **Selected — source the conversion**, which remains the SARS-CoV-2 question:
   no SARS-CoV-2 conversion is adopted, and the outstanding copies↔infectious
   conversion still belongs with the collaborator. The norovirus half of #43 is
   **narrowed, not closed**: the published exchange settles that the
   disagreement is statistical rather than biological and that the shipped
   norovirus pair is the non-aggregation genome-copy fit, while the unit of
   Teunis's 18 is not settled by any source held here. The aggregate reading and
   the ≈925
   copies-per-aggregate bridge remain unverified and circular, and Atmar's
   genomic-equivalents wording remains unreconciled; Teunis's own aggregation
   parameter or aggregate-size distribution would be needed to settle that
   question. R5 is not done; molecular detection is where the project's
   observational effort is concentrated, so the SARS-CoV-2 conversion is what
   still has to be found.

Neither may be settled by adopting a convenient ID50: the two available figures
(Prentiss 361–2,000 particles; Riediker 500/300/100 copies) are **fitted to
attack-rate data from high-attack-rate ship and superspreading events**, so
using them and then conditioning on Diamond Princess would put the same voyage
on both sides of the inference — barred by the per-fit circularity rule of
`bayesian_inference_design.md` §3. R5 gates #30, #33 and #34.

The conversion is likely covariate-dependent — by specimen, variant, and point
in the infection course — which is what the register's `∅ null in copies`
marker already says. Sourcing "a conversion" may therefore return a function
rather than a scalar, and the trap is adopting a single figure because it is
the only one that turned up. That would make R5 the second curve-valued repair,
so the same dimensional rule applies to it as to R2.

## 3. What this does to the register's counts

Nothing, until a repair lands. R1 is behaviour-preserving. R2 and R3 move two
`⊘`-marked influenza rows in a bundle that is not loaded. R4 changes a field
definition and *may* then admit a Grade B value, which would be the first
adoption on that row — and adoption is a separate decision, not part of the
repair. R5 admits none.

The register's headline stays **57 recorded / 21 blocked / 9
refuted-or-unmeasurable**, with in-tree adoption **8 / 6 / 2**, until a specific
change moves it and says which row it moved.

## 4. Open questions

1. **R2's functional form.** The covariates are dictated by the evidence; the
   form is not. Weibull (Kim 2012, both arms) against exponential-with-covariates
   is a choice, and it is the same choice §1 leaves open for norovirus. Deciding
   it once for both arms is cheaper than twice, and coupling them means the
   norovirus screen interval must be re-expressed in whatever form wins.
2. **Whether R1 deletes the alias or only stops using it.** The skill says
   delete, and the blast radius is small: only two files in `data/` carry the
   key at all — `active_profiles.json` (2 occurrences) and
   `edison_10pathogen_profiles.json` (5); the two `enterprise_*` bundles carry
   no surface-decay key and fall back to the engine default. The
   counter-argument is that two of those occurrences are inherited placeholders
   nobody has sourced — `vibrio_cholerae_parahaemolyticus` and
   `campylobacter_jejuni`, both a suspiciously round 0.5, the same value as the
   engine default — so deleting the alias forces a unit decision on two bacteria
   as collateral. Converting a placeholder is not a repair; dropping the key and
   letting them fall back to the default, as the other seven inherited pathogens
   already do, is the honest option.

**Decided:** R5 takes route 2 (source a copies conversion), as recorded in §2
R5; it is no longer an open question.
