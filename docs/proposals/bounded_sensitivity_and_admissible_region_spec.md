# Bounded sensitivity and the admissible region: parameters as intervals, not values

> **Status:** Partly implemented. The §2 screen exists as
> `telemetry_buffer/observation_model/bounded_screen.py` and its first pass over
> the §3.2 norovirus box is reported in
> [`norovirus/bounded_screen_results.md`](../norovirus/bounded_screen_results.md).
> The §2.3 admissible-region search does not exist, the §4 SARS-CoV-2 ledger is
> deferred behind task #30, and the §5 influenza box has not been run because
> `influenza_a` is not an active profile.

## 1. Why this replaces "fit one knob per pathogen"

Every calibration design in this repository so far has asked: *what value of
parameter X reproduces the anchors?* That question presumes X is free, and it is
the question the parameter-freedom audits
([norovirus](../norovirus/norovirus_parameter_freedom_audit.md),
[COVID](../covid/covid_parameter_provenance_audit.md)) showed we cannot answer
honestly — the knob is either inert (norovirus faecal release above 8) or
non-identifiable apart from an unsourced denominator (COVID emission scale
apart from β).

This document specifies the replacement question:

> Given that every parameter enters as a **sourced interval** rather than a
> value, does the image of that box contain the observed outcomes?

Three properties follow, and they are the reason to prefer it.

1. **There is no knob to turn.** A point inside a literature interval is not a
   fitted value; the interval is the claim, and it was fixed before the model
   ran. Overfitting requires freedom the design does not grant.
2. **Provenance work gets a priority order it does not currently have.** A
   Grade C parameter whose whole plausible range moves no scored output is not a
   liability. A Grade A central estimate with a wide interval and a large
   elementary effect is the real exposure. Our audit ordering assumes the
   opposite — it ranks by evidence grade, not by consequence.
3. **A miss is a result.** If no point in the box reproduces the anchors, the
   admissible set is empty, and that is a statement about the box or about a
   missing mechanism. It is not a residual to be absorbed.

## 2. Method

### 2.1 Screen: Morris elementary effects

Continuous factors are mapped to the unit hypercube, each with a declared
transform (linear or log10 — stated per factor in §3). Design:

| Setting | Value | Why |
|---|---|---|
| Levels `p` | 4 | Standard for elementary effects; 4 levels with Δ = p/(2(p−1)) = 2/3 gives a balanced sampling of the grid |
| Trajectories `r` | 10 | Runs = r(k+1); at k = 12 that is 130 design points |
| Seeds per point | 5, **the same five at every point** | Common random numbers. The elementary effect is a difference between two design points; sharing the seed set removes most of the stochastic variance from that difference |
| Statistic | μ* on the seed-mean output, and σ | μ* ranks influence; σ flags interaction or non-monotonicity, which is what tells us a one-at-a-time reading would have been wrong |

**Noise floor, and it is not optional.** Before the screen, run 20 seeds at the
box centre and record the seed-to-seed standard deviation of every scored
output. Any factor whose μ* falls below that floor is reported as
*indistinguishable from stochastic noise at this design size* — not as
"insensitive". The distinction matters because the second claim would license
freezing the parameter, and the first does not.

### 2.2 Structural uncertainty is not a continuous factor

Dose-response **model family** is categorical, and interpolating between
families is meaningless. Run the entire Morris design once per family (§3.1) and
report the between-family spread of each output as its own quantity. For
norovirus this is expected to dominate: Liu et al. 2026 fitted five families to
37 datasets and found the one-particle infection probability spanning 0.08% to
45.61% across them — roughly 2.7 log10 of structural uncertainty, against which
any within-family interval is narrow.

### 2.3 Feasibility: the admissible region

Only over the factors that cleared the noise floor:

1. Sample the box (Sobol' sequence, 2^10 points, all non-screened factors held
   at their sourced central estimate).
2. A point is **admissible** iff *every* anchor interval is covered
   simultaneously — norovirus incidence (A8) and posting probability (A9) and
   attack rate (A4) for both eras across all four classes, with the COVID and
   influenza anchors of §4–§5 for those arms.
3. Report the admissible volume fraction, the marginal admissible range of each
   factor, and — if the set is empty — which anchor pairs are jointly
   unsatisfiable. Pairwise incompatibility is the diagnostic that points at a
   missing mechanism rather than a wrong interval.

**Rule.** The marginal admissible range of a factor is an *output* of this
procedure. It may be reported, and it may not be written back into a profile as
a new central estimate; that would be fitting to the anchors by a longer route.

## 3. Norovirus factor ledger

Bounds are the measured spread across studies, materials, or populations for
Grade A/B factors, and an explicitly declared plausible range for Grade C. Where
the current profile value sits outside the sourced interval, that is flagged —
it is the same class of finding as §3 of the norovirus freedom audit.

### 3.1 Structural factor (categorical, per §2.2)

| Family | Parameters | Source |
|---|---|---|
| Beta-Poisson, disaggregated | α = 0.111, β = 32.81 (current profile) | Teunis et al. 2008 as inherited; see the open ledger — every dose figure is withdrawn |
| Fractional Poisson | Single susceptible-fraction parameter plus aggregation | Messner et al. 2014, *Risk Analysis* 34(10) — AIC favours it over beta-Poisson on the pooled challenge data |
| Multilevel by secretor status and genogroup | P(inf ǀ 1 GC) = 0.076 for GII in Se+ | Teunis et al. 2020, *Epidemics* 32:100401 |

Liu et al. 2026 (*Water Research*, DOI 10.1016/j.watres.2026.126482) is the
bound on this axis rather than a family in it: 37 dose-response datasets
extracted from 408 publications, GI and GII fitted separately, and the finding
that **aggregation parameters are model-dependent and function as fitting
parameters rather than measured properties**. That is an independent statement
of the identifiability problem we derived for the COVID emission scale, and it
means α and β must move together as a family choice, never as two continuous
factors.

### 3.2 Continuous factors

| Factor | Transform | Interval | Grade | Basis |
|---|---|---|---|---|
| `innate_nonsusceptible_fraction` | linear | 0.00 – 0.16 | B | See §3.3. The arm is GII (declared in `name`, `genotypes` and `incubation.notes`), so the GII partial-susceptibility ceiling governs and the screen's box was correct |
| `contact_transfer_fraction` | linear | 0.06 – 0.50 | B | Anderson et al. 2021, *AEM* 87(22): 360 fingerpad↔surface transfer events, 20 volunteers, MS2 (non-enveloped surrogate) mean 0.26, Phi6 0.17; surface type and transfer direction both significant, so the spread is the interval and a single number cannot be right for both directions |
| Emesis titre (GEC/mL) | log10 | Kirby 2016 measured range | B | Already sourced in-tree; carry the study spread, not the point |
| Emesis volume (mL) | log10 | 50 – 800 | B | Tung-Thompson et al. 2015, already bounded in-tree |
| Cabin-localization fraction `f` | linear | 0.80 – 0.99 | **C, declared** | No measurement exists. Wikswo 2009 is the nearest evidence and does not measure it; recorded as a null result. This factor was already shown to be the binding uncertainty for the Park anchor, so it is the one to watch |
| `environmental_faecal_release_log10_g_per_epoch` | linear | 4 – 24 | **D, construction** | Not a literature quantity. Included so the screen can confirm the inert-above-8 finding independently, not because a value will be selected |
| `surface_decay_per_day` | linear | 0.14 – 0.84 | B | Surrogate spread on non-porous surfaces, Fallahi 2011 to the Kim fast cell; recut in tranche 5. Sweeping fractional loss linearly under-covers the slow end — a rate-space sweep is queued |
| Reporting-probability scale | linear | 0.5 – 1.5 × | **C, declared** | The observation model's 15 assumed numbers are not independently identified (A3 circularity). Screen them as **one** multiplier on reporting probability, because that is the dimension the single empirical aggregate constrains |
| `shedding_variance_log10` | linear | study spread | C | Source or declare |

### 3.3 The FUT2 ceiling is genogroup-conditional, and the arm is GII

**Corrected twice — see
[`../literature/consensus_tranche_2.md`](../literature/consensus_tranche_2.md) §1
and [`../literature/consensus_tranche_3.md`](../literature/consensus_tranche_3.md)
§1.** The ceiling *is* genogroup-conditional, which tranche 2 established. What
tranche 2 then got wrong was which genogroup this arm is: it read the
`pathogen_id` and assumed GI.1, while the profile declares GII.4 in its `name`,
simulates `GII.4 / GII.17 / GII.2` in `strain_evolution.genotypes`, and carries
an `incubation.notes` line saying the distribution is "GII rather than the GI the
pathogen_id implies." **The GII interval governs, and the original 0.00 – 0.16
conclusion stands.**

Teunis et al. 2020 estimates infection risk at 1 genomic copy separately by
secretor status *and genogroup*, and the two genogroups are not alike:

| | Se+ | Se− | Se− / Se+ |
|---|---:|---:|---:|
| **GI** | 0.28 | **0.00007** | **0.00025** |
| GII | 0.076 | 0.015 | 0.197 |

For GII, non-secretors retain about 20% of Se+ per-copy risk — partial
susceptibility, so a fully removed fraction over-corrects and the ceiling is
about 0.2 × (1 − 0.2) ≈ 0.16. Rouphael et al. 2022 (*JID*, GII.2, 4 of 8 Se−
subjects ill at top dose against 10 of 12 Se+) and Frenck et al. 2012 (*JID*,
GII.4, 1 of 17 Se− ill against 13 of 23 Se+) bracket that partial susceptibility
from the two directions.

For **GI** the reduction is a factor of ~4,000, not ~5: Lindesmith et al. 2003
(*Nature Medicine*, GI.1 challenge) reports the FUT2 null allele as **fully
penetrant — no nonsecretor developed infection at any dose**, so a removed
fraction would be the right mechanism with a ceiling at the non-secretor
prevalence itself, 0.2 × (1 − 0.00025) ≈ 0.20. **That branch does not apply to
this arm**, and is retained here only because the inherited dose-response (α
0.111 / β 32.81, `Person.java`, fitted to oral Norwalk GI.1 inoculum) *is* GI —
so a future correction of the dose-response to GII, or of the arm to GI, would
switch which row applies. The two terms must move together or not at all.

Prevalence remains population-specific and is the real source of width: ~20% in
European-ancestry populations, 29% of the Lindesmith 2003 study sample, 19% in
the Rwandan cohort of Munyemana et al. 2025 (no norovirus association detected),
and genotype/population variation is itself an argument for an interval
(Nordgren & Sharma 2019, *Viruses* 11:226).

**Consequence for #21:** both the shipped 0.0 and Edison's 0.2 are outside the
governing 0.00 – 0.16 interval, in opposite directions, and the real defect is
the removed-fraction *mechanism* — a partial-susceptibility multiplier is the
right shape for GII. The larger question the genogroup work raises is not about
this parameter at all: a GI.1 infectivity curve is driving a GII strain set (§3.3
above, tranche 3 §1), which is Edison Q1 rather than a scope decision.

The screen in `../norovirus/bounded_screen_results.md` swept 0.00 – 0.16. Its
ranking is unaffected: extending the upper end to 0.20 can only increase the
elementary effects of the factor that already ranked first.

## 4. SARS-CoV-2 factor ledger

Not writable yet, and the reason is recorded in the
[COVID audit](../covid/covid_parameter_provenance_audit.md): the emission term
is a nasal concentration where the model needs a rate, and dose enters the
beta-Poisson only as D/β, so an interval on the emission scale is not
interpretable until β is fixed in the same unit system. Sourcing the intervals
before that repair would produce a box in unusable units.

Prerequisite: task #30. The ledger is written after it, not before.

## 5. Influenza factor ledger

Influenza is the arm where the respiratory emission interval can be **measured**
rather than reconstructed, which is why it is worth activating (`influenza_a`
exists in `data/pathogens/edison_10pathogen_profiles.json` and is already wired
as a campaign pathogen config, but is absent from `active_profiles.json`).

| Factor | Interval basis |
|---|---|
| Exhaled emission rate, fine aerosol | Yan et al. 2018, *PNAS* 115(5) (EMIT): 142 confirmed cases, 218 paired NP and 30-minute breath samples on days 1–3 post-onset. Geometric mean 3.8 × 10⁴ RNA copies per 30 min fine (≤5 µm) and 1.2 × 10⁴ coarse (>5 µm); infectious virus recovered from 52/133 (39%) of fine aerosols. This is an emission **rate**, in the units the model needs |
| Tidal-breathing emission, lower bound | Fabian et al. 2008, *PLoS ONE* 3(7): exhaled generation rates <3.2 to 20 RNA particles per minute, >87% of exhaled particles under 1 µm |
| Dose-response | Memoli et al. 2015 (*CID*, A(H1N1)pdm09 IND challenge): 10⁷ TCID50 intranasal produced mild-to-moderate disease in 69%. Han et al. 2019 (*CID*, A/Bethesda/MM1/H3N2): escalation 10⁴–10⁷ TCID50, MMID only at 10⁶ (44%) and 10⁷ (40%) |
| Presymptomatic window | Ip et al. 2017: shedding begins about 1 day before onset (already carried on the profile) |

**The measurement that matters most is a negative one.** Yan et al. found NP
swab viral load (geometric mean 8.2 × 10⁸ per swab) was **not** significantly
associated with fine- or coarse-aerosol viral RNA, and read upper- and
lower-airway shedding as compartmentalised and independent. That is direct
empirical refutation of the practice of driving a respiratory emission term from
a nasal viral-load curve — which is exactly what both the COVID and influenza
profiles do today. It converts the COVID audit's dimensional argument into a
measured one.

**Two cautions, both of which must be in the ledger before any flu fit.**

- *Route asymmetry in the challenge data.* The challenge studies above are
  intranasal instillation at 10⁶–10⁷ TCID50; that is not the aerosol dose, and
  the two differ by orders of magnitude in the classical literature. An
  intranasal ID50 must not be used as an aerosol dose-response denominator
  without an explicit, sourced route conversion. Absent one, this is the same
  D/β non-identifiability as COVID, and must be declared as such.
- *`base_susceptibility: 0.65` is prior immunity in disguise.* It is the one
  place a flu arm can quietly overfit, because it can absorb any level error.
  It must come from seroprevalence or vaccination coverage for the specific
  season and route, or be declared Grade C and screened across its full range.

### 5.1 Influenza anchors, and the co-circulation target

Respiratory illness is outside VSP, so there is no influenza analogue of the
37,258-voyage AGE denominator. Anchors are outbreak investigations, so N is
COVID-like rather than norovirus-like.

| Anchor | Observation |
|---|---|
| Levels, two Alaska hulls | Medically-attended ARI 3.7% passengers / 3.1% crew on one ship; reported respiratory illness 6.2% / 4.7% on the second (Rogers et al., via Young & Wilder-Smith 2018, *J Travel Med*) |
| **Co-circulation** | 2009 Sydney 10-day Pacific cruise, 1,970 passengers + 734 crew: 82 (3.0%) A/H1N1, 98 (3.6%) A/H3N2, **2 (0.1%) both** |
| High-contact subgroup | 20 of 45 children (44.4%) attending the ship's childcare centre infected with A/H1N1 on the same voyage |

The co-circulation row is the one that earns the strain machinery. Two subtypes
on one hull with a measured co-infection count and a measured high-contact
subgroup constrains `cross_immunity` and `superinfection_susceptibility`
jointly — both of which the profile currently carries as declared placeholders
(`docs/paper3/variant_surveillance_plan.md` §7). A single-strain attack rate
constrains neither.

## 6. What this document does not authorise

- No parameter may be set from the admissible region (§2.3).
- No interval may be narrowed because it makes the region non-empty.
- The screen reports a ranking; it does not select a value.
- An empty admissible set is published as an empty admissible set.
