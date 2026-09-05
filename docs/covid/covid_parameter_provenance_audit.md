# SARS-CoV-2 parameter provenance audit

> **Status:** Findings, 2026-09-01. Audits the provenance of every scalar in the
> active `sars_cov2_resp` profile (`data/pathogens/active_profiles.json`) and in
> `docs/formal_spec_v2.md` Appendix A.2. **No constant was changed by this
> audit.** It records what is sourced, what is inherited, what is assumed, and
> which quantities are identifiable from the Diamond Princess training data
> fixed in `docs/proposals/covid_trajectory_fit_spec.md`.

> Per-quantity status now lives in the fleet-wide register
> [`../parameter_provenance_register.md`](../parameter_provenance_register.md),
> which carries the SARS-CoV-2 rows; this audit holds the evidence and the
> arguments behind them.

## Why this exists

The trajectory-fit proposal declared **one** fitted parameter — the respiratory
emission scale — on the implicit premise that the rest of the COVID profile is
parameterised from the literature. That premise was not checked. It is false in
the aggregate: of 25 scalars in Appendix A.2, **five carried a citation** before
this audit, and the two quantities that most decide whether the arm transmits at
all — the emission magnitude and the dose-response denominator — were among the
unsourced ones.

The norovirus lesson applies verbatim
(`.agents/skills/model-parameter-provenance/SKILL.md`): one free scalar sitting
on top of several unsourced mechanisms does not measure the scalar, it absorbs
their error. Section 4 shows the COVID arm has that structure exactly, and that
the errors run in *opposite* directions, which is the configuration in which a
fit looks best and means least.

## 1. Classification of every Appendix A.2 scalar

Classes: **M** measured (direct citation, quantity and units check out) ·
**B** analogous measurement · **I** inherited (carried from the upstream Java
model or another pathogen) · **C** assumption, no source · **D** derived
internally from another profile value.

| Parameter | Value | Class before | Class after | Source status |
|---|---|---|---|---|
| `incubation.distribution` / `median_days` / `dispersion` | lognormal, 5.8 d, GSD 1.57 | M | M | Wei et al. 2021, ancestral lineage. Holds for Diamond Princess; wrong for Omicron |
| `presymptomatic_shedding_days` | 2.0 | M | M | He et al. 2020 (infectiousness from ~2.3 d before onset); profile note records the 2.0 vs 2.3 rounding |
| `airborne_half_life_hours` | 1.1 | M | M | van Doremalen et al. 2020, NEJM median 1.1 h. Note the preprint reports 2.7 h; the profile uses the peer-reviewed figure |
| `incubation.dose_reference_log10` | 3.43 | D | D | $\log_{10}$ of the profile's own $N_{50}$ — inherits whatever error the dose-response carries (§2) |
| `incubation.dose_log10_shortening` / `dose_floor` | 0.15 / 0.3 | C | C | `ctb_incubation_spec.md` is an in-repo spec, not a measurement |
| `surface_decay_per_day` | 0.95 | C | **M** | Newly sourced by this audit — §3 |
| `recovery_day` | 7 | C | **B** | Newly sourced by this audit — §3 |
| `shedding_curve_log10` (shape) | peak at index 4 | C | **B** (shape only) | Newly sourced by this audit — §3. Magnitude remains C and mis-dimensioned (§4) |
| `dose_response.model` / `alpha` / `beta` | beta_poisson, 0.18, 58.0 | C (spec) / M (notes) | **C** | Attribution is wrong and the two documents disagree — §2 |
| `shedding_curve_log10` (magnitude) | peak $10^{9}$ | C | C | Two to four orders above measured respiratory emission — §4 |
| `asymptomatic_shedding_log10` | peak $10^{7.5}$ | C | C | The 1.5-log10 symptomatic/asymptomatic offset has no source; measured URT loads are *similar* between the two |
| `illness_probability.eta` / `gamma` | 0.4 / 0.12 | C | C | Norovirus's are `Person.java` (0.508 / 0.095). COVID's are unattributed near-neighbours of them — §5 |
| `shedding_variance_log10` | 1.2 | C | C | No source. Individual-variation evidence exists and is larger (§4) but was not the basis of this value |
| `transmission_route_weights` | 6 values | C | C | No source, and they are independent multipliers rather than realised shares (norovirus audit §9) |
| `surface_deposition_fraction` | 5e-05 | C | **I** | Norovirus's 1e-4 is `ViralParticle.java`; COVID's is that value halved, with no stated reason |
| `recovery`/`incubation` bounds `min_days` 0.5, `max_days` 21.0 | — | C | C | Truncation convention, not measurement |
| `base_susceptibility` | 1.0 | C | C | Construction constraint (the unit against which modifiers act), not a measurable |
| `innate_nonsusceptible_fraction` | 0.0 | C | C (defensible) | Unlike norovirus FUT2, there is no known innate-resistance locus. Correct-by-argument for a naive 2020 population; still a declaration |
| `transmission_routes`, `category`, `pathogen_id`, `name` | — | — | — | Structural, not parameters |

**Count after the audit: 8 sourced of 25.** Seventeen remain Grade C or
inherited. The proposal's premise was wrong by roughly a factor of three.

## 2. The dose-response attribution is wrong in three ways

`docs/pathogen_notes.md` §2 attributes $\alpha = 0.18$, $\beta = 58.0$ to
"Watanabe 2020 derived models for SARS-CoV-1 and adapted for CoV-2".
`formal_spec_v2.md` Appendix A.2 lists the same two values with source "—". The
documents contradict each other, and the citation is wrong regardless:

1. **The paper is 2010, not 2020.** Watanabe et al., *Risk Analysis*
   30(7):1129–1138, [10.1111/j.1539-6924.2010.01427.x](https://doi.org/10.1111/j.1539-6924.2010.01427.x).
2. **It rejected the beta-Poisson form.** Its own abstract: the exponential
   model ($k = 4.1 \times 10^{2}$) described the pooled data, and "the
   beta-Poisson model did not provide a statistically significant improvement in
   fit." The profile uses the form the source declined to adopt, with parameters
   that appear nowhere in it.
3. **The data are murine.** Transgenic mice susceptible to SARS-CoV, pooled with
   murine hepatitis virus strain 1. Its human-relevant outputs are $ID_{10} = 43$
   and $ID_{50} = 280$ **PFU**, not RNA copies.

So $\alpha$ and $\beta$ are Grade C: unsourced values in a functional form their
nominal source rejected, on a different virus in a different host, quoted in
units the model does not use.

### What the literature does offer

| Source | Form | Parameter | $N_{50}$ equivalent | Units |
|---|---|---|---|---|
| Watanabe 2010 (mice, SARS-CoV-1) | exponential | $k = 4.1\times10^{2}$ | 280 (illness) | PFU |
| Zhang & Wang 2020, *Clin Infect Dis* [10.1093/cid/ciaa1675](https://doi.org/10.1093/cid/ciaa1675) | exponential | $k = 6.4\times10^{4}$–$9.8\times10^{5}$ | $4.4\times10^{4}$–$6.8\times10^{5}$ | **RNA copies** |
| Killingley 2022, *Nat Med* [10.1038/s41591-022-01780-9](https://doi.org/10.1038/s41591-022-01780-9) | human challenge | 10 TCID50 infected 18/36 (~53%) | ~10 | TCID50, intranasal |
| Miura 2023, *Epidemics* [10.1016/j.epidem.2023.100691](https://doi.org/10.1016/j.epidem.2023.100691) (published form of the 2022 preprint) | beta-Poisson with individual variation | **not fitted to Killingley** — the paper's own point is that a single dose level cannot identify the individual-variation parameters | — | TCID50 |

The active profile's $N_{50}$ is **2,670 model units**. If model units are RNA
copies — which is what the shedding curve's $10^{9}$ implies — the profile is
**17–254× more sensitive** than the only human-deduced copy-based dose-response.
Zhang & Wang was recorded here as the natural replacement candidate because it
is the one stated in the same units as our emission term. **That candidacy is
withdrawn** by
[`../literature/consensus_tranche_25_covid_emission_beta_alias.md`](../literature/consensus_tranche_25_covid_emission_beta_alias.md)
§3: its human calibration runs through an infection-risk meta-analysis and its
dose term through exhaled shedding, so adopting it would fix one factor of the
emission × susceptibility product from data about the product. Killingley is the
harder anchor but is in TCID50 by the intranasal route, and converting it needs a
copies-per-TCID50 factor that is itself a sourced quantity — measured, and 2.7
logs wide (tranche 15). Neither endpoint survives, so there is no span to sweep
and the denominator is refused rather than replaced.

**Update (Consensus tranche 4).** The other half of the pair — an emission
*rate* in the same units — now has candidates, so §4's non-identifiability can
be broken from the emission side rather than only from β:
Lane et al. 2023 measured exhaled SARS-CoV-2 at a mean **80 RNA copies/min**
over 312 serial breath specimens, and Coleman et al. 2021 measured **63–5,821
copies per expiratory activity** (≈2–200 copies/min) with 85% of the load in
fine aerosol and 94% emitted by talking and singing. Ma et al. 2020's exhaled
breath *condensate* estimate is 10³–10⁵ copies/min — 1–3 orders higher, and the
gap is method, not variant, which is why the emission term has to enter as an
interval. Sources, grades and the three caveats that keep Zhang & Wang Grade C
are in [`../literature/consensus_tranche_4.md`](../literature/consensus_tranche_4.md)
§2. Nothing is adopted; task #30 remains open.

## 3. Three values that turn out to be defensible

Sourcing found in the model's favour, which is worth recording as carefully as
the misses:

**`surface_decay_per_day = 0.95` is right, and was unsourced by accident.** The
key is a *fractional loss per day*, converted per epoch in
`TransmissionCore._surface_survival` via `SimClock.decay_per_epoch`. At 0.95/day
the per-epoch loss is 0.117, i.e. a **5.55-hour half-life** — against van
Doremalen's NEJM 5.6 h on stainless steel and 6.8 h on polypropylene. Grade A
for those two surfaces, and for lit conditions. Report the other end honestly:
Riddell 2020 (*Virol J*, 20 °C, in the dark) measured half-lives of 1.7–2.7
**days**, 7–12× longer, so a single fleetwide 0.95 sits at the fast end of the
measured range and is not conservative for dark interiors.

**`recovery_day = 7` from onset is a defensible central value.** Oordt-Speets
2024 (*J Glob Health*, 14 culture studies) puts daily culture positivity at
44–50% from day −1 to 5, 28% at day 7, 11% at day 9, and 0–8% over days 10–17;
Wu 2023 pools Omicron viable shedding at 5.16 d (95% CI 4.18–6.14). Grade B: the
*duration* is sourced, the *deterministic* clearance at exactly onset + 7 is
still a modelling convention (`formal_spec_v2.md` §645).

**The shedding-curve shape is approximately right.** Killingley 2022 measured
nasal viral load peaking ~5 d after inoculation at 8.87 log10 copies/mL (95% CI
8.41–9.53), with viable virus recoverable to ~10 d; Pan 2020 (*Lancet Infect
Dis*) puts the throat/sputum peak at 5–6 d after onset. The profile's 15-point
curve peaks at index 4 and declines over ~14 d, which matches. The *magnitude*
does not — see below.

## 4. The structural finding: the emission scalar is not identifiable alone

Two independent problems, and they point in opposite directions.

**The emission magnitude is too high, not too low.** Emission per epoch is
$10^{(\text{curve} - \text{adj})}$, so at peak with `dose_adjustment = 3.0` the
model emits $10^{6}$ units per hour. Coleman 2021 (*Clin Infect Dis*
[10.1093/cid/ciab691](https://doi.org/10.1093/cid/ciab691)) measured actual
emitted respiratory aerosol from COVID patients with a G-II sampler: **63–5,821
N-gene copies per expiratory activity per participant** (30 min breathing, 15
min talking, 15 min singing), 85% of it in fine aerosol, 94% from talking and
singing, and two patients on illness day 3 accounted for 52% of the total. That
is $10^{2}$–$10^{4}$ copies per activity period against the model's $10^{6}$ per
hour: **two to four orders of magnitude high** on the aerosol channel. The
curve's $10^{9}$ is a *concentration* (copies per mL of nasal fluid, per
Killingley) being used as a *rate* (units emitted per epoch). That is a
dimensional error, not a calibration offset.

**The dose-response is too sensitive** by 1.2–2.4 orders (§2). So the arm is
built from a high emission and a low threshold, which is exactly the
configuration in which a scalar fit succeeds while both components stay wrong.

**And the fit cannot decompose them.** The beta-Poisson probability is
$1 - (1 + D/\beta)^{-\alpha}$: the delivered dose $D$ and the denominator
$\beta$ enter only as the ratio $D/\beta$. The emission scale multiplies $D$.
Therefore **no amount of Diamond Princess data can separate the emission scale
from $\beta$** — a trajectory pins the composite
$(\text{emission} \times \text{route multiplier} \times \text{transfer}) / \beta$
and nothing else. Two consequences:

1. Fitting "one scalar" is honest as a count and misleading as a claim. The
   fitted quantity is a composite of at least four unsourced numbers (emission
   magnitude, $\beta$, the route multipliers, the deposition fraction), and a
   good fit is not evidence about any one of them.
2. $\beta$ must therefore be **fixed from an independent source before the fit**,
   not left free and not "checked afterwards". Fixing it to Zhang & Wang would
   have made the fitted emission scale interpretable as copies emitted per hour
   and comparable against Coleman — which is what would turn the fit into a
   test. **That route is closed** (§2, tranche 25 §3): Zhang & Wang's copies
   denominator is not independent of the emission factor it would license. No
   admissible independent source for the denominator has been found, so the
   composite $\Theta$ stays the fitted quantity and must be reported as a
   composite. Note also that the per-host path is stronger than the ratio
   $D/\beta$ above: `_dose_response_hazard` reads
   `susceptibility × effective_dose`, so the aliasing is exact for a fixed host
   and not an artefact of the closed form.

## 5. Two quantities that must not be fitted, because they are scored

- **`illness_probability.eta` / `gamma`.** These set the asymptomatic fraction,
  and they set it *dose-dependently*: at the profile's own $N_{50}$ the illness
  probability is 0.567 (43% asymptomatic), at dose 100 it is 0.36 (64%), at dose
  10 it is 0.176 (82%). Measured fractions: Buitrago-García 2020 (*PLoS Med*, 79
  studies) 20% (95% CI 17–25) overall and 31% (26–37) in screened-and-followed
  cohorts; Sah 2021 (*PNAS*, 350+ studies) 35.1% (30.7–39.9). The held-out Greg
  Mortimer anchor is 81% asymptomatic among positives. The 43%-at-$N_{50}$
  coincidence with Sah is not evidence: the dose-dependence itself is unmeasured,
  and the asymptomatic fraction is a **scored output** of the held-out hull. No
  value in `illness_probability` may be moved to improve it.
- **`shedding_variance_log10`.** It is the model's only superspreading control,
  and the skewed cross-ship distribution (Willebrand 2022: median attack rate
  0.2%, mean 3.7%) is a held-out score. Coleman's "two patients gave 52% of the
  load" is independent evidence that person-to-person variation is large, and
  should be used to *source* this value, not to tune the distribution it is
  scored against.

## 6. What this changes about the fit plan

The four prerequisites in `docs/proposals/covid_trajectory_fit_spec.md` §7 stand,
with one added and one sharpened:

1. **Re-source $\beta$ and the emission scale together, in one unit system**
   (RNA copies). Sharpened: this is not optional tidying, it is the condition
   under which the fit is identifiable at all (§4). **Attempted and refused**
   (tranche 25): the emission side is bounded by measurement at
   $[4.2\times10^{3}, 5.8\times10^{7}]$ copies per hour-equivalent, but no
   admissible copies-denominated dose-response exists, so this prerequisite is
   currently *unmeetable* rather than outstanding. The consequence is that the
   fit remains a fit of the composite, and (per the closing paragraph) its output
   must not be reported as an emission rate.
2. **Re-derive the emission term as a rate,** not as a nasal-fluid concentration,
   against Coleman 2021 for the aerosol fraction. The current $10^{9}$ peak is a
   dimensional error.
3. **Source `shedding_variance_log10`** from measured emission variation before
   the cross-ship distribution is scored (new).
4. Severity and observation models, the two scenarios, and the testing-campaign
   replica, as already specified.

Until (1) and (2) are done, any number produced by fitting the emission scale is
a composite with no physical interpretation, and should not be reported as an
emission rate.
