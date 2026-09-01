# Bounded sensitivity and the admissible region: parameters as intervals, not values

> **Status:** Proposed. Nothing in this document is implemented. The harness it
> specifies (`telemetry_buffer/observation_model/bounded_screen.py`) does not
> exist.

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
| `innate_nonsusceptible_fraction` | linear | 0.00 – 0.16 | B | See §3.3; the 0.2 in `norovirus_gii4` is **above** the sourced ceiling |
| `contact_transfer_fraction` | linear | 0.06 – 0.50 | B | Anderson et al. 2021, *AEM* 87(22): 360 fingerpad↔surface transfer events, 20 volunteers, MS2 (non-enveloped surrogate) mean 0.26, Phi6 0.17; surface type and transfer direction both significant, so the spread is the interval and a single number cannot be right for both directions |
| Emesis titre (GEC/mL) | log10 | Kirby 2016 measured range | B | Already sourced in-tree; carry the study spread, not the point |
| Emesis volume (mL) | log10 | 50 – 800 | B | Tung-Thompson et al. 2015, already bounded in-tree |
| Cabin-localization fraction `f` | linear | 0.80 – 0.99 | **C, declared** | No measurement exists. Wikswo 2009 is the nearest evidence and does not measure it; recorded as a null result. This factor was already shown to be the binding uncertainty for the Park anchor, so it is the one to watch |
| `environmental_faecal_release_log10_g_per_epoch` | linear | 4 – 24 | **D, construction** | Not a literature quantity. Included so the screen can confirm the inert-above-8 finding independently, not because a value will be selected |
| `surface_decay_per_day` | linear | study spread | B | Norovirus surface persistence; source the spread across materials before the run |
| Reporting-probability scale | linear | 0.5 – 1.5 × | **C, declared** | The observation model's 15 assumed numbers are not independently identified (A3 circularity). Screen them as **one** multiplier on reporting probability, because that is the dimension the single empirical aggregate constrains |
| `shedding_variance_log10` | linear | study spread | C | Source or declare |

### 3.3 The FUT2 ceiling is lower than we have been calling the literature value

Task #21 says to correct `innate_nonsusceptible_fraction` from 0.0 to the
literature 0.2. That target is wrong, and the interval framing is what exposes
it.

Teunis et al. 2020 estimates infection risk at 1 genomic copy separately by
secretor status: 0.076 for GII in Se+ subjects, and **0.015 in Se−** — a
five-fold reduction, not protection. Rouphael et al. 2022 (*JID*, GII.2 Snow
Mountain virus challenge, 44 adults) is the direct test: at the highest dose,
4 of 8 secretor-negative subjects became ill, against 10 of 12 secretor-positive.
Non-secretors are partially susceptible to GII.

So a fully non-susceptible fraction equal to non-secretor prevalence
over-corrects. With prevalence around 0.2 and Se− retaining roughly 0.015/0.076
≈ 20% of Se+ per-copy risk, the defensible ceiling on a *fully* non-susceptible
fraction is about 0.2 × (1 − 0.2) ≈ 0.16, and lower for a mixed-genotype
profile, since GII.2 and GII.17 are less secretor-restricted than GII.4
(Nordgren & Sharma 2019, *Viruses* 11:226 — susceptibility is genotype-dependent
and HBGA expression varies substantially between populations, which is itself an
argument for an interval). Prevalence is population-specific: 19% in the
Rwandan cohort of Munyemana et al. 2025, with no norovirus association detected.

**Consequence for #21:** the correct change is not 0.0 → 0.2. It is 0.0 → an
interval of 0.00 – 0.16 whose upper end is a partial-susceptibility
approximation, with the mechanism ideally re-expressed as reduced susceptibility
in Se− hosts rather than a removed fraction. Both the shipped 0.0 and the
"literature" 0.2 are outside the defensible range, in opposite directions.

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
