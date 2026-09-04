# Consensus tranche 6 — is there a GII dose-response, and what the strain layer can carry


**Register rows fed / supersession.** This tranche feeds `dose_response.alpha` / `beta`, `illness_probability.eta` / `gamma`, and `secretor_negative_relative_susceptibility` in §3.1. No later withdrawal or supersession is recorded in the register or the norovirus open ledger.

**Status:** Evidence assembled and interpreted. **No pathogen-profile constant,
no engine constant and no screen interval changed by this document**; the two
changes it justifies are listed in §5 and are queued, not applied.
**Scope:** the Wave 3 question — whether a genogroup II dose-response exists to
adopt in place of the inherited GI.1 pair, or whether the honest outcome is a
declaration — plus the genotype dependence of the secretor term Wave 1 adopted
(#377).
**Method:** Consensus MCP searches on human GII challenge studies,
outbreak-fitted GII dose-response models and FUT2 genotype-specific
susceptibility, each read back into the shipped parameterisation before being
called usable.

The short answer to the question asked: **a GII dose-response does exist, in
three independent forms, and the declaration is not needed.** The longer answer
matters more, because reconciling those forms against our own field withdrew a
number I published two tranches ago and left the shipped value standing.

---

## 1. What the field is, stated precisely enough to test a citation against

`data/pathogens/active_profiles.json` ships

```json
"dose_response": {"model": "beta_poisson", "alpha": 0.111, "beta": 32.81}
```

consumed as a **beta-frailty** model (#370): a per-host susceptibility
`r ~ Beta(α, β)` is drawn and infection follows with probability
`1 − exp(−r·D)`, where `D` is the dose in **qPCR genome copies** accumulated by
the recipient over the epoch. In expectation this is the exact confluent
hypergeometric beta-Poisson, `P(D) = 1 − ₁F₁(α; α+β; −D)`, which is what makes
published fits comparable with the shipped pair at all.

Two consequences that decide most of what follows:

- The dose unit is **disaggregated genome copies**. A fit whose likelihood
  includes an aggregation parameter reports risk *per aggregate*, and its
  per-copy statistics are not in this unit even when the words are identical.
- The field is an **infection** curve. Illness is a separate composite
  (`illness_probability`, η/γ), so an illness ID50 bounds α from one side only.

Derived from the shipped pair, for reference below: **ID50 = 1.67 × 10⁴ genome
copies**, single-copy infection risk **0.0033**.

## 2. The GII measurements, mapped into the shipped family

Each row converts a published GII quantity into the α that reproduces it with
β held at 32.81 (the ratio β/α sets the frailty dispersion; holding β fixed and
moving α is the one-dimensional slice the screen can sweep). Arithmetic is the
₁F₁ form above, with the large-dose asymptote `P(D) → 1 − Γ(α+β)/Γ(β)·D^(−α)`
used for the ID50 root; asymptote and exact form agree to 0.3% at the shipped
pair, which is the check that the mapping is sound.

| Source | Setting and outcome | Reported | Implied α (β = 32.81) |
|---|---|---|---|
| Rouphael et al. 2022, *J Infect Dis* | **Human GII.2 (Snow Mountain) challenge**, 44 adults, 1.2×10⁴–1.2×10⁷ GEC, **infection** | ID50 = 5.1×10⁵ GEC | **0.072** |
| Guix et al. 2020, *Water Research* | GII waterborne outbreak, dose reconstructed from water, **illness** | ID50 ≈ 2,934 GC/day (95% CI 1,683–5,044) | **0.154** (lower bound on α, see below) |
| Ramesh et al. 2020, *Viruses* | GII.4/2003 Cin-2, **gnotobiotic pig**, infection | ID50 2,400–3,400 RNA copies | 0.149–0.161 (animal model, Grade C for humans) |
| Guix et al. 2020, same study, GI arm | GI outbreak, illness | ID50 ≈ 556 GC/day | 0.244 |
| **Shipped (Teunis 2008 GI.1 challenge, disaggregated)** | Human GI.1 challenge, infection | ID50 = 1.67×10⁴ | **0.111** |

The Guix row is a **lower bound on α**, not a point: an infection ID50 is below
the illness ID50 of the same exposure, so the α that reproduces GII illness at
2,934 copies understates GII infectivity. The direction is the safe one.

### The result

**The GII evidence brackets the shipped GI.1 value, and brackets it tightly:
α ∈ [0.072, 0.161], a factor of 2.2 end to end, with the shipped 0.111 inside
it and within 3% of its geometric centre (0.108).** In ID50 terms the interval
is 4.9×10⁵ down to 2.5×10³ copies, and the shipped 1.67×10⁴ sits in the middle
of it.

So the genogroup mismatch flagged in #372 and carried as blocked item 1 of the
register is real as a provenance defect and **small as a numerical one**. It
does not license a swap: replacing 0.111 with any single GII point estimate
would move the dose axis less than the width of the GII evidence itself, and
picking the endpoint that best reproduced an anchor would be fitting.

## 3. A withdrawal: the "3.7× per-copy genogroup difference" is a unit error, not a genogroup effect

In tranche 3 and again when Wave 3 was proposed I described the GI-versus-GII
difference as roughly 3.7× in infectivity per genome copy, from Teunis et al.
2020 (*Epidemics* 32:100401): single-copy infection risk 0.28 for GI against
0.076 for GII in secretor-positive hosts. **That figure cannot be carried into
this field, and the comparison it supported is withdrawn.**

Reproducing a single-copy risk of 0.076 in the shipped family requires
**α = 2.85**, which puts the ID50 at **≈ 10 genome copies** — five orders below
every challenge measurement in §2, including the GII.2 challenge in the same
genogroup. A two-parameter beta-Poisson cannot hold both statistics at once
because they are not statements about the same dose: Teunis 2020 and Teunis 2008
both model **aggregation explicitly**, so their high per-particle risks are risks
per *aggregate* of many copies, while the shipped pair is the disaggregated arm
of Teunis 2008 — the correct arm for a qPCR-copy dose axis, which is the one
thing about the inherited value that turns out to have been right.

Liu et al. 2026 (*Water Research*, 37 datasets from 408 publications) is the
independent statement of the same problem: aggregation parameters are
model-dependent and **behave as fitting parameters rather than measured
properties**. Quoting a per-copy risk across that boundary is the same class of
defect as taking the emesis titre from an abstract that pooled two genogroups
(#373) — the number is real, the unit is not ours.

This is also the answer to whether α and β can be swept independently: they
cannot. The family, its aggregation assumption and its dose unit are one choice,
which is why §5 sweeps α on a fixed β and records the family as a categorical
factor rather than opening β.

## 4. What *is* genotype-specific, and it is not infectivity per copy

This is the part that bears on the variant work, and it reverses the direction I
suggested when the question came up.

Kambhampati et al. 2015 (*Clin Infect Dis*, systematic review and meta-analysis,
random-effects pooling) measures secretor-positive versus non-secretor infection
odds **by genotype within genogroup II**:

| Comparison | Pooled OR (secretor : non-secretor) | Implied non-secretor relative susceptibility |
|---|---|---|
| **GII.4** | 9.9 (95% CI 3.9–24.8) | **0.10** (0.04–0.26) |
| **GII non-4** | 2.2 (95% CI 1.2–4.2) | **0.45** (0.24–0.83) |

Supporting the same split from independent designs: Lopman et al. 2014
(Ecuadorian birth cohort, 194 children) found *every* GII.4 infection in
secretor-positive children while **non-GII.4 infections were more frequent in
secretor-negative** children (RR 0.56, p = 0.029); Rouphael's GII.2 challenge
infected 4 of 8 non-secretors at top dose; Carlsson et al. 2009 documents
symptomatic GII.4 in a G428A homozygote, so the protection is strong and not
absolute even for GII.4; Larsson et al. 2006 reaches "relatively but not
absolutely resistant" from GII.4 antibody titres in 105 donors.

Our profile declares `genotypes` as **GII.4 / GII.17 / GII.2** — a mixture that
straddles both rows of that table. Wave 1 adopted
`secretor_negative_relative_susceptibility` = 0.20 from the Teunis 2020 GII
ratio (0.015/0.076), and 0.20 does sit between the GII.4 and GII-non-4 values,
so nothing adopted is refuted. But two things follow:

1. The screen interval **[0.05, 0.50]** under-covers the high end. Kambhampati's
   GII-non-4 CI reaches 0.83 and Rouphael's illness split is ≈ 0.6. The
   defensible interval is **[0.04, 0.83]**, and its width is *genotype
   composition*, not measurement error.
2. **This is the quantity the strain layer should carry**, not infectivity per
   copy. It is measured per genotype with an order-of-magnitude contrast inside
   one genogroup, it acts on the recipient at challenge time — where
   `immune_escape` is already read — and it does not touch the emission side, so
   it does not recreate the emission-scale degeneracy (#366) that rules out
   putting infectivity on `transmissibility_multiplier`. A GII.4→GII.2 strain
   replacement is, on this evidence, mostly a **change in who is susceptible**,
   not a change in dose per copy.

Two boundaries on that, recorded so the search is not repeated: Liu et al. 2026
finds the GII fully-immune fraction weak and model-dependent (essentially
0–0.02), which is consistent with partial susceptibility and against any
removed-fraction return; and Munyemana et al. 2025 (668 Rwandan children) found
**no** FUT2 association for norovirus overall while finding one for rotavirus —
a genotype-composition null that belongs in the interval's width rather than
against the mechanism.

## 5. What this licenses, and what it does not

**Two changes, both queued rather than applied here:**

1. `dose_response` α/β moves from *blocked by mechanism* to **declared and
   swept**: keep the shipped pair as the construction point, state in the profile
   and the register that it is the disaggregated GI.1 challenge arm, and sweep
   **α ∈ [0.072, 0.161] at fixed β = 32.81** as the GII interval it lies inside.
   The declaration Wave 3 was going to have to make gets narrower: not "a GI.1
   dose axis is scored against GII.4 observations" with an unquantified bias, but
   "the GI.1 pair is inside the human GII interval, near its centre, and the
   axis is swept over that interval".
2. `secretor_negative_relative_susceptibility` screen interval widens from
   [0.05, 0.50] to **[0.04, 0.83]**, and the register records that the quantity
   is genotype-specific with the two-row table in §4 as its basis.

**What it does not license.** No profile constant changes. β does not become a
factor. Teunis 2020's per-copy risks do not enter the field in any form. The
gnotobiotic-pig ID50 is corroboration, not an endpoint. And the interval in (1)
is a sweep, not a refit: per the admissible-region spec, a marginal admissible
range is an output and may not be written back as a new central estimate.

**Bias direction, since it was asked for and is now answerable.** Both endpoints
are reachable, so the honest statement is not a signed bias but a bound: the
dose axis is uncertain by **a factor of 2.2 in α**, i.e. ID50 anywhere from
2.5×10³ to 4.9×10⁵ copies, and the shipped value is not at either end. That is
narrower than the surface-decay interval (an order of magnitude, #375) and far
narrower than the COVID dose axis (1–2 orders, #366/#30) — the norovirus dose
axis is, unexpectedly, the best-constrained of the three.

## 6. Sources

- Rouphael, N. G. *et al.* (2022) Norovirus GII.2 (Snow Mountain virus) human
  challenge: 44 adults, 1.2×10⁴–1.2×10⁷ GEC, median infectious dose 5.1×10⁵ GEC,
  36 secretor-positive / 8 secretor-negative. Grade **B** (human challenge,
  correct genogroup, not this setting).
- Guix, S. *et al.* (2020) *Water Research* — GII and GI waterborne-outbreak
  dose-response; 50% illness doses 2,934 (GII) and 556 (GI) genome copies/day.
  Grade **B**.
- Teunis, P. F. M. *et al.* (2020) *Epidemics* 32:100401 — multilevel model by
  genogroup and secretor status; single-copy risks 0.28 (GI) and 0.076 (GII) in
  secretor-positive hosts, 0.015 GII in secretor-negative. **Aggregation
  modelled; per-copy statistics not in our dose unit** (§3).
- Teunis, P. F. M. *et al.* (2008) *J Med Virol* 80:1468 — GI.1 Norwalk
  challenge; the disaggregated arm is the shipped α/β.
- Liu, X. *et al.* (2026) *Water Research* — 37 dose-response datasets, GI and
  GII fitted separately; aggregation parameters function as fitting parameters;
  GII immune fraction ≈ 0–0.02.
- Ramesh, A. *et al.* (2020) *Viruses* — GII.4/2003 Cin-2 gnotobiotic pig ID50
  2,400–3,400 RNA copies. Grade **C** for human dose-response.
- Kambhampati, A. *et al.* (2015) *Clin Infect Dis* — FUT2 meta-analysis;
  secretors 9.9× (3.9–24.8) for GII.4 and 2.2× (1.2–4.2) for GII non-4. Grade
  **B**.
- Lopman, B. *et al.* (2014) *J Infect Dis* — Ecuadorian birth cohort; all GII.4
  infections secretor-positive, non-GII.4 more frequent in non-secretors
  (RR 0.56).
- Carlsson, B. *et al.* (2009) *PLoS ONE* — symptomatic GII.4 in a FUT2 G428A
  homozygote; protection strong, not absolute.
- Larsson, M. *et al.* (2006) *J Infect Dis* — GII.4 antibody prevalence and
  titre by FUT2; non-secretors relatively, not absolutely, resistant.
- Munyemana, J. B. *et al.* (2025) *Microorganisms* 13:1071 — 668 Rwandan
  children; FUT2 stop variant associated with rotavirus, **not** with norovirus.
- Thébault, A. *et al.* (2013) — oyster-associated GI/GII outbreak fits, high
  per-particle infectivity. Read but **not used**: same aggregation-unit
  boundary as Teunis 2020 (§3).
- Messner, M. J. *et al.* (2014) *Risk Analysis* 34(10); Abel, N. *et al.* (2017)
  — alternative families (fractional Poisson, model-dependence of the commonly
  quoted α = 0.04 / β = 0.055). Already recorded in the bounded-sensitivity spec
  as the structural axis.
