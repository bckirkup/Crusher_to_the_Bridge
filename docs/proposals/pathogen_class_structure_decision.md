# The pathogen-class ruling: strain classes, not genotypes and not a scalar

> **Status:** Decision record, 2026-09-04. It settles how strain-level
> heterogeneity in the dose-response is *structured*, and it is the pathogen-side
> counterpart of [`fleet_emergence_decision.md`](fleet_emergence_decision.md).
> **Nothing here is implemented, no value is adopted, no register row is
> re-graded, and no interval is narrowed.** Every dose figure quoted is re-read
> from the [provenance register](../parameter_provenance_register.md) or the
> [norovirus ledger](../norovirus/norovirus_open_ledger.md) and every one of them
> remains void pending refit. Its purpose is to record which structure is chosen,
> which two are forbidden, and which quantities the choice makes load-bearing.

## 0. The ruling

The question:

> "Now we need to decide whether we think that 'norovirus' ID50 is really best
> described by a few lab experiments or that those are random draws from discrete
> options, or there is a cloud and we have some points in it (hopefully)."

The ruling:

> "This is the same principle that we are following with the ship models — we
> aren't going to make every single ship it's own perfect model, but we can't
> ignore giant swimming pools as a category."

So: **classes.** Not a per-genotype table (the pathogen equivalent of a perfect
model per hull), and not one scalar (the equivalent of one generic ship). A small
number of categories, each admitted because it behaves differently in a way that
cannot be averaged away, with the within-class spread left unresolved.

## 1. What the points we hold can and cannot support

Four measurements, all re-read from register §3.1:

| Source | Setting | ID50 | Unit |
|---|---|---|---|
| Atmar 2014, GI.1 | challenge, secretor-positive O/A | 1,320 | gEq |
| Atmar 2014, GI.1 | challenge, all secretor-positive | 2,800 | gEq |
| Guix 2020, GII | outbreak reconstruction, **illness** | 2,934 | gEq |
| Teunis 2008, GI.1 | challenge, disaggregated arm (shipped) | 16,644 | copies |
| Rouphael 2022, GII.2 | challenge | 5.1 × 10⁵ | gEq |

That is ~2.6 logs of spread, and **genotype does not sort it**. Rouphael's GII.2
and Guix's GII sit about two logs apart inside one genogroup, while the GI.1
figures straddle the middle of the range. Study design is confounded with strain
in every one of these comparisons at once: challenge inoculum versus outbreak
reconstruction, infection versus illness endpoint, aggregated versus
disaggregated dose unit. The genogroup contrast is not merely unmeasured here, it
is *unmeasurable from this table*.

Two structures are therefore ruled out before any modelling preference:

- **A per-genotype table is unidentifiable.** It would need one ID50 per
  genotype, and the observations cannot separate genotype from design. Worse, the
  anchor cannot either — see §5.
- **A single scalar is refuted.** 2.6 logs is not measurement error on one
  constant, and the register's own GII interval α ∈ [0.072, 0.161] already
  concedes the point by being an interval.

The cloud is real; our points are in it; we cannot resolve its shape. That is
exactly the situation the class construction is for.

## 2. Where the variability lives: between voyages, not between agents

This is the part that earns its parameter, and it is a mechanical claim rather
than a statistical preference.

A voyage is seeded by a small number of importations, so in the common case every
agent aboard faces **the same** draw from the cloud. Strain variability is
therefore between-voyage. It is *not* the same object as a wider dose-response
curve, and the two are not interchangeable:

- β already carries within-host and host-factor heterogeneity. Flattening it to
  represent strain spread double-counts, and it is also the half of the shipped
  pair whose provenance is least secure (ledger: β keeps no provenance at all if
  the Teunis fit is abandoned).
- A flat wide curve makes every ship average. A per-importation draw makes ships
  differ. The between-ship contrast is the entire fleet-as-sensor signal, so
  smearing it into an individual-level curve destroys the observable that
  [`fleet_emergence_decision.md`](fleet_emergence_decision.md) just made the
  likelihood.

A per-founder multiplier *m* on delivered dose divides that strain's effective
ID50 by exactly *m*, whatever the dose-response form: *P* reaches 0.5 where *mD*
reaches the base N50, that is at *D* = N50/*m*. For the **closed-form**
beta-Poisson this is also a literal reparameterisation, `P(mD; α, β) =
P(D; α, β/m)`, since that form depends on *D*/β. For the **exact**
confluent-hypergeometric form the live path uses it is not:
`1 − 1F1(α; α+β; −mD)` is not `1 − 1F1(α; α+β/m; −D)`, so *m* shifts the ID50
without being a β rescaling. Either way, a class difference in infectivity is
expressible with no new dose-response field. `StrainState`
already carries `transmissibility_multiplier` as a dose `emission_factor`
(`engines/transmission_core.py:883`, `engines/strain_dose_ledger.py`), and
shedding is a *separate* offset, so that multiplier is free to mean per-particle
infectivity rather than "sheds more".

**Consequence to watch, not resolved here:** `dose_reference_log10` on the
norovirus profile is that profile's own N50, used to condition incubation on
dose. A per-founder *m* moves the effective N50 while the reference stays fixed,
so the incubation dose term would silently become class-dependent. Either the
reference follows the class or the coupling is declared as accepted; picking one
is implementation work, and this document does not pick.

## 3. The class boundary, and why it is not chosen from the dose evidence

**The classes are GII.4 pandemic lineages versus non-GII.4 (GII.2/GII.17).**

The justification is deliberately *not* the ID50 table of §1, which cannot
support a split. It is that a second, independent quantity already demands the
same two categories. Register §3.1, `secretor_negative_relative_susceptibility`,
records Kambhampati 2015's pooled secretor:non-secretor odds ratios as 9.9
(3.9–24.8) for GII.4 and 2.2 (1.2–4.2) for GII non-4 — implying non-secretor
relative susceptibility of 0.10 (0.04–0.26) against 0.45 (0.24–0.83). That is a
4.5× difference in *who is even susceptible*, measured, on the same split.

Two independent quantities requiring the same boundary is the test for a category
that cannot be averaged away. It is the swimming pool. A finer split fails the
opposite test: nothing in the evidence or the anchor distinguishes GII.17 from
GII.2.

Three prohibitions follow, in the same spirit as the fleet ruling's:

1. **No genotype-indexed dose-response table.** The class is the unit. Adding a
   row per genotype adds parameters no datum can address.
2. **No class share fitted to VSP.** See §5; the anchor contains no genotypes at
   all, so such a fit would be estimating a quantity the likelihood is blind to,
   and the share would silently absorb every other misfit.
3. **No widening of β to stand in for strain spread.** §2. If strain
   heterogeneity is wanted, it enters at the founder, where it is mechanically
   what it claims to be.

## 4. What already exists, and the two numbers that are wrong for this purpose

In-tree, checked rather than assumed:

- **Genotype is currently a label with no physics.** `_founder_genotype`
  (`engines/transmission_core.py:896`) draws a founder genotype from
  `prior_genotype_distribution`, but every founder is registered with
  `phenotype=None` → `Phenotype()`, i.e. all four offsets at 1.0
  (`engines/strain_state.py`). The genotype axis feeds `cross_immunity` and
  escape lookups only. The class identity exists; the class *difference* does
  not.
- **The mutation window cannot generate the cloud, and should not be widened
  to.** `PhenotypeEffectRanges.transmissibility` is (0.80, 1.25) — about ±0.1
  log — against §1's ~2.6 logs. These are two different distributions: a narrow
  per-mutation effect and a wide founder draw. Only the narrow one is
  implemented. Enlarging it would make shipboard evolution do work that belongs
  to importation.
- **The dispersion parameter has precedent.** `shedding_variance_log10` already
  declares a per-agent lognormal spread rather than fitting one
  (`docs/SHEDDING_AND_CABINMATES.md`), which is the shape a declared,
  swept within-class dispersion would take.
- **`prior_genotype_distribution` is a uniform placeholder and this ruling makes
  it load-bearing.** The shipped norovirus block is GII.4/GII.17/GII.2 at 0.3333
  each (`data/pathogens/active_profiles.json`). Under §3 it becomes the class
  mixture, so it needs external typing provenance and currently has none. It is
  not in the register as a sourced row.

There is a corollary for the variant-surveillance goal: since mutation aboard
cannot move ID50 far, between-ship spread in attack rate is dominated by *which
class boarded*. That makes the fleet signal a **port** signal first, and a
shipboard-evolution signal only at much finer resolution.

## 5. The identifiability consequence, which is the whole reason for the ruling

The VSP series carries **no genotype information whatsoever**: across all 428
postings in `telemetry_buffer/observation_model/vsp_outbreak_series.csv` there
are 25 distinct `causative_agent` strings, 302 of them exactly `norovirus`, and
not one names a genogroup, let alone a genotype. The field is verbatim from the
CDC page, which reports agent at genus/species level; the vocabulary the
extractor validates against (`fetch_vsp_outbreaks.py`) is genus/species by
construction. So genotype was never published, not dropped in extraction.

Therefore:

- The **class shares** are a declared input, sourced from external typing
  surveillance and swept. They are never estimated from the postings.
- The **within-class dispersion** is declared and swept, not fitted: §1's points
  are too design-confounded to estimate a width.
- Only a **mixture-marginal location** is estimable from the anchor, and it is
  the marginal over the circulating mixture — which is the right target anyway,
  because the postings are themselves a mixture.

The degrees-of-freedom arithmetic that follows is the point of choosing classes
over genotypes: **one estimable quantity plus two declared ones**, against one
ID50 per genotype under the rejected structure. And it answers the
overspecification worry directly — the class structure is chosen so that the
number of *estimable* parameters does not grow at all with the number of strain
categories.

## 6. What this does not decide

- **Which genogroup the active arm declares.** Still open; the Atmar retarget
  was rejected on exactly this ground and the item was reclassified as a
  genogroup-declaration item, not a fit. Under this ruling the arm is naturally
  the pooled GII mixture, but the declaration is a separate change.
- **Any ID50 value.** Every dose figure in the repository remains void pending a
  validated refit. §1 is a table of evidence, not a set of candidates for
  adoption.
- **Whether the class difference enters as `transmissibility_multiplier` or a
  new founder-level field**, and how `dose_reference_log10` follows it (§2).
- **The class shares themselves.** They need typing provenance that no register
  row currently holds; until then the uniform 1/3 is a placeholder and must be
  labelled as one rather than treated as a mixture.
