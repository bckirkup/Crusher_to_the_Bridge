# CTB Incubation Period Model Spec
## Paper 3 Addendum: Stochastic Incubation, Dose-Dependent Onset, and Host Frailty

### Motivation

The current simulator uses a fixed `symptom_onset_day` (default 1.0 for all
pathogens) with an optional additive `strain_incubation_modifier` from the
variant surveillance system. This is inadequate for three reasons:

1. **No stochastic variation.** Every agent with the same strain gets symptoms
   on the same day post-infection. Real incubation periods have substantial
   person-to-person variability (CV 30-50% for most pathogens).
2. **No dose dependence.** Higher inocula shorten incubation — well-documented
   in human challenge studies — but the current model ignores acquired dose.
3. **No host heterogeneity.** Age, fitness, chronic disease, and prior immunity
   modify severity and susceptibility, but not the current onset timing. The
   wearable system tracks per-agent physiology that could reflect underlying
   susceptibility, creating a detection opportunity the model cannot currently
   explore.

This spec adds a three-layer incubation model: distributional draw → dose
shift → host modifier, with a latent frailty score that bridges the
epidemiological model to the wearable telemetry.

---

## 1. Incubation Period Distributions

### 1.1 Parameterization

Replace the fixed `symptom_onset_day` with a stochastic draw from a
pathogen-specific lognormal distribution. Convention: `log(T) ~ Normal(mu, sigma^2)`
on the natural-log scale; median = `exp(mu)`.

#### Real pathogens

| Pathogen | mu | sigma | Median (d) | 95% interval (d) | Source |
|---|---|---|---|---|---|
| Norovirus GII | 0.182 | 0.445 | 1.2 | 0.5–2.9 | Lee et al. 2013 [1] |
| Norovirus GI | 0.095 | 0.599 | 1.1 | 0.3–3.6 | Lee et al. 2013 [1] |
| SARS-CoV-2 (ancestral) | 1.758 | 0.450 | 5.8 | 2.3–14.6 | Wei et al. 2021 [2], sigma estimated |
| SARS-CoV-2 (Alpha) | — | — | ~4.4 | ~1–12 | Gamma(3.08, scale=1.58d); Manica et al. [3] |
| SARS-CoV-2 (Delta) | — | — | ~4.1 | ~1–10 | Gamma(4.43, scale=1.01d); Manica et al. [3] |
| SARS-CoV-2 (Omicron) | 1.253 | 0.400 | 3.5 | 1.5–8.2 | Xu et al. 2023 [4], sigma estimated |
| Influenza A (pooled) | 0.336 | 0.412 | 1.4 | 0.6–3.1 | Lessler et al. 2009 [5] |
| Influenza A (H1N1pdm) | 0.358 | 0.480 | 1.43 | 0.5–4.4 | Nishiura & Inaba 2011 [6]; Weibull(1.75, 1.85) converted |
| Influenza A (H3N2) | 1.137 | 0.505 | 3.1 | 1.2–8.4 | Liao et al. 2009 [7]; challenge data, higher uncertainty |
| Measles | 2.526 | 0.207 | 12.5 | 8.3–18.8 | Lessler et al. 2009 [5] |
#### Additional pathogens (Edison 10-pathogen profiles)

| Pathogen | mu | sigma | Median (d) | 95% interval (d) | Source |
|---|---|---|---|---|---|
| Influenza A | 0.336 | 0.412 | 1.4 | 0.6–3.1 | Lessler et al. 2009 [5] |
| Measles | 2.526 | 0.207 | 12.5 | 8.3–18.8 | Lessler et al. 2009 [5] |
| Legionella pneumophila | 1.723 | 0.420 | 5.6 | 2.2–14.0 | Lessler et al. 2009 [5]; median 5-6d, range 2-14d |
| Vibrio cholerae/parahaemolyticus | -0.288 | 0.600 | 0.75 | 0.2–2.8 | FDA BAM; median 15-24h for V. parahaemolyticus |
| Campylobacter jejuni | 1.099 | 0.400 | 3.0 | 1.2–7.3 | Silva et al. 2017 [21]; systematic review median 3.0d |
| Clostridioides difficile | 0.693 | 0.500 | 2.0 | 0.7–5.4 | Leffler & Lamont 2015 [22]; colonization-to-symptom ~2d, high uncertainty |
| Andes hantavirus | 2.890 | 0.300 | 18.0 | 9.8–33.0 | Vial et al. 2006 [23]; HPS median 18d, range 11-35d |
| Ebola virus | 2.197 | 0.340 | 9.0 | 4.6–17.7 | WHO Ebola Response Team 2014 [24]; gamma(1.6, 5.6d) or lognormal median 9.0d |

Notes:
- **Legionella**: environmental exposure pathogen (no person-to-person
  transmission in the real world, but the model uses it for Legionnaires'
  disease from shipboard water systems). Incubation is 2-14 days.
- **Vibrio**: very short incubation. V. parahaemolyticus (the cruise-relevant
  species) has median onset ~15-24h after contaminated seafood consumption.
  V. cholerae is shorter still (~1-3 days for cholera).
- **C. difficile**: complex pathogenesis — spore ingestion → colonization →
  toxin production → symptoms. The 2-day estimate is colonization-to-symptom;
  spore-to-symptom can be longer and highly variable. High sigma reflects this
  uncertainty.
- **Andes hantavirus**: only hantavirus with confirmed person-to-person
  transmission. Long incubation (11-35d), making it detectable by end-of-voyage
  wastewater monitoring but often not by clinical presentation during the voyage.
- **Ebola**: well-characterized from the 2014 West African outbreak. WHO EVD
  Response Team fitted gamma distributions; lognormal approximation shown here.

#### Dose-response parameters for additional pathogens

| Pathogen | dose_shift | dose_floor | ED50 | Notes |
|---|---|---|---|---|
| Legionella pneumophila | 0.10 | 0.4 | 100 CFU | Inhalation dose; within-host birth-death model supports dose dependence |
| Vibrio parahaemolyticus | 0.15 | 0.3 | 1e5 CFU | High infectious dose; dose-dependent onset documented |
| Campylobacter jejuni | 0.12 | 0.3 | 800 CFU | Black et al. 1988 challenge; dose-dependent attack rate, onset less characterized |
| Clostridioides difficile | 0.05 | 0.5 | N/A (spore) | Dose-incubation relationship poorly characterized; conservative |
| Andes hantavirus | 0.08 | 0.4 | unknown | No challenge data; conservative estimate |
| Ebola virus | 0.15 | 0.3 | ~1-10 PFU | Extremely low ID50; strong dose-dependent onset in NHP models |

Notes:
- SARS-CoV-2 Alpha/Delta are better fit by gamma than lognormal. The model
  should support both families; use gamma when published fits are gamma.
- No reliable genotype-specific fits exist within norovirus GII (GII.4 vs
  GII.17 vs GII.2). Use the pooled GII distribution for all genotypes unless
  future data warrant splitting.
- H3N2 challenge-study estimates (~3d) are longer than outbreak estimates
  (~1.4d), likely reflecting different symptom definitions and inoculation
  protocols. Use the Lessler pooled fit as the primary; offer the challenge
  values as a sensitivity option.

#### Trek pathogens

Trek incubation parameters are designed to span the parameter space for
interesting surveillance dynamics, not to match canon precisely. Each is
anchored to a real-pathogen analog with deliberate modifications.

| Pathogen | mu | sigma | Median (d) | 95% interval (d) | Rationale |
|---|---|---|---|---|---|
| Rigelian Fever | 1.386 | 0.500 | 4.0 | 1.5–10.5 | Analog: SARS-CoV-2 Delta with slightly wider dispersion. Systemic febrile illness with moderate incubation. |
| Psi-2000 Polywater | -0.223 | 0.600 | 0.8 | 0.2–3.0 | Analog: rapid-onset intoxication. Shorter than norovirus, high dispersion (behavioral modification varies greatly by individual susceptibility). The spec notes Psi-2000 has extreme adaptability (mutation_rate 0.10, phenotype_fraction 0.50), so fast + variable onset creates surveillance challenge. |
| Barclay Protomorphosis | 1.946 | 0.350 | 7.0 | 3.5–14.0 | Analog: slow-transforming retroviral infection. Long incubation with moderate variance — the surveillance value is detecting it before phenotypic changes are visible. |
| TNG Shipboard Influenza | 0.405 | 0.420 | 1.5 | 0.6–3.6 | Analog: influenza A with slight rightward shift. 24th-century strain with slightly longer incubation reflecting partial population immunity. |

### 1.2 Implementation

#### Pathogen profile schema

Add to each pathogen profile in `data/pathogens/*.json`:

```json
{
  "incubation_distribution": {
    "family": "lognormal",
    "mu": 0.182,
    "sigma": 0.445,
    "unit": "days"
  }
}
```

For gamma-distributed pathogens (SARS-CoV-2 Alpha/Delta):

```json
{
  "incubation_distribution": {
    "family": "gamma",
    "shape": 3.08,
    "scale": 1.58,
    "unit": "days"
  }
}
```

When `incubation_distribution` is absent, fall back to the legacy fixed
`symptom_onset_day` (default 1.0) for backward compatibility.

#### Draw timing

The incubation draw happens once per infection event, at the point the
infection is established (in `infect_with_pathogen` / dose-response success).
The drawn value is stored on the infection record as `incubation_days` and
replaces the role of `symptom_onset_day` in the progression logic
(`orchestrator_epoch.py:363`).

```python
# At infection establishment:
dist = pathogen_profile.get("incubation_distribution")
if dist and dist["family"] == "lognormal":
    T_base = rng.lognormal(dist["mu"], dist["sigma"])
elif dist and dist["family"] == "gamma":
    T_base = rng.gamma(dist["shape"], dist["scale"])
else:
    T_base = float(pathogen_profile.get("symptom_onset_day", 1.0))
```

---

## 2. Dose-Dependent Incubation Shortening

### 2.1 Evidence

Higher inocula shorten incubation across multiple pathogens:

- **Norovirus**: Ge et al. (2023) [8] showed median onset decreased from 1.5d
  at low dose to 0.8d at 4,800 RT-PCR units — approximately 0.23 days shorter
  per 10-fold dose increase across a 3-log range.
- **SARS-CoV-2**: Blaurock et al. (2022) [9] in Golden Syrian hamsters: weight
  loss onset at 2 dpi for >=100 TCID50 vs 5 dpi for 10 TCID50 — ~3 day shift
  over 1 log.
- **Influenza**: Fullen et al. (2016) [10]: peak symptoms advanced ~1 day per
  100-fold dose increase in H3N2 challenge.
- **Theory**: Target-cell-limited model predicts shortening of ln(10)/r per
  log10 dose, where r is the net viral growth rate. For influenza r ~ 4/day,
  this gives ~0.58 days/log10 (Baccam et al. 2006).

Convergent estimate: **0.2–0.7 days shorter per log10 dose increase**.

### 2.2 Implementation

After the base incubation draw, apply a dose-dependent multiplicative shift:

```python
# dose = acquired_particles from dose-response
# ED50 = pathogen-specific median effective dose
log_dose_ratio = math.log10(max(dose, 1.0) / ED50)
dose_modifier = max(dose_floor, 1.0 - dose_shift * log_dose_ratio)
T_inc = T_base * dose_modifier
```

#### Parameters per pathogen

| Pathogen | dose_shift | dose_floor | ED50 | Source |
|---|---|---|---|---|
| Norovirus GII | 0.12 | 0.3 | see note below — no assay figure is usable here | Atmar et al. 2014 (GI.1) [11]; corrected — see note |
| SARS-CoV-2 | 0.15 | 0.3 | ~100 TCID50 | Blaurock et al. 2022 [9] |
| Influenza A | 0.10 | 0.4 | ~1000 TCID50 | Memoli et al.; Fullen et al. [10] |
| Measles | 0.05 | 0.5 | ~0.2 TCID50 | No direct evidence; conservative |
| Rigelian Fever | 0.15 | 0.3 | 50 (model units) | Analog: SARS-CoV-2 |
| Psi-2000 Polywater | 0.20 | 0.2 | 10 (model units) | Aggressive: rapid intoxication |
| Barclay Protomorphosis | 0.08 | 0.4 | 30 (model units) | Conservative: retroviral |
| TNG Shipboard Influenza | 0.10 | 0.4 | 500 (model units) | Analog: influenza |

The `dose_floor` prevents unrealistically short incubation at extreme doses
(e.g., massive environmental exposure). `dose_shift` is dimensionless; it acts
on the fractional incubation. The recommended central value of ~0.12–0.15
produces ~0.5 day shortening per log10 dose for a pathogen with 4-day baseline,
consistent with the empirical range.

**The norovirus ED50 cell was wrong in three ways, and no shipped profile ever
used it.** It read "18 RT-PCR units, Atmar et al. 2014". (a) Atmar et al. 2014
measures **GI.1 Norwalk**, not GII. (b) Its HID50 is **3.3 RT-PCR units
(≈1,320 gEq)** for secretor-positive blood-group O or A subjects and **7.0
(≈2,800 gEq)** across all secretor-positive subjects — not 18. (c) **18 is a
different quantity in a different unit**: it is Teunis et al. 2008's Table III
figure, and it is not in RT-PCR units under either available reading of it — at
Atmar's own implied ≈400 gEq per RT-PCR unit, "18 RT-PCR units" would be ≈7,200
gEq, while the readings actually on offer are 18 aggregates (≈16,650 genome
copies) or 18 genomic equivalents, discussed below. Behaviour is unaffected,
because every shipped profile references its own beta-Poisson N50 in model units
and says why it refuses the literature assay figure
(`data/pathogens/active_profiles.json`, `norwalk_gi` notes) — the consequence
being that the incubation dose axis is referenced to the model's own N50 rather
than to any assay unit.

**A reconciliation is available but unverified and circular, so it is a
candidate reading rather than a finding:** 18 aggregates at ≈925 copies each
would put Teunis's figure on our own dose axis, at ≈16,650 copies, while
the live per-agent path draws `r ~ Beta(α, β)` and has an exact
confluent-hypergeometric N50 of **16,644 copies**. The closed-form helper
`1 − (1 + D/β)^−α` has an approximate N50 of **16,871 copies**; the ≈1.3%
gap is between the live per-agent mechanism and that test-only helper, not a
second biological dose figure. The trap is pairing the aggregate-unit 18 with
the non-aggregation alpha/beta: `P ≈ 0.047` at `D = 18` to three significant
figures under both forms, not 0.5. The bundle review already called the 925
bridge an unverified hypothesis — "16,644 / 18 ≈ 925 genome copies per
infectious aggregate" — so the collaborator's confirmation is circular rather
than independent: 16,643.78 / 18 = 924.65, and 18 × 925 agrees with the exact
N50 to ≈0.04%. The aggregate reading is therefore **unverified**, not
corroborated, and 925 remains unverified against the primary. What would settle
it is Teunis et al. 2008's own reported aggregation parameter or aggregate-size
distribution, read from Table III or the paper's text, independently of any ID50
held here. Atmar's reply describes the figure as "18 genomic equivalents ...
determined using assumptions about differing amounts of virus aggregation",
which remains unreconciled with the aggregate reading. Atmar's measured HID50 of
1,320–2,800 gEq is **5.9–12.6× below 16,644** under the nominally same
no-aggregation framing reported by Kirby, Teunis & Moe, so that comparison is an
open question attributed to the primary texts, not a value to adopt. The model
is internally consistent on its live dose axis; representing 18 as aggregates
would require an aggregation distribution step before the dose-response draw,
which `engines/transmission_core.py` does not have.

#### Pathogen profile schema

```json
{
  "incubation_dose_response": {
    "dose_shift": 0.12,
    "dose_floor": 0.3,
    "reference_dose": 18.0
  }
}
```

When absent, no dose adjustment (backward compatible).

---

## 3. Host Frailty Score

### 3.1 Architecture

The literature does not support a strong universal frailty effect on incubation
period [task:7f6f04c8-fa65-48c4-813a-dbe9397f7641]. Host factors primarily
modify **severity** and **susceptibility**, with at most ±10% effect on
incubation. Therefore:

- **Frailty modifies severity strongly, incubation weakly.**
- **Frailty is reflected in wearable baselines**, creating the detection
  opportunity that makes paper 3's wearable-stratified analysis possible.
- **Frailty and prior immunity are separate axes** — a fit vaccinated elderly
  person and a frail unvaccinated young person should not collapse to the same
  state.

### 3.2 Frailty score computation

At agent initialization, compute a latent `frailty_score` in [0, 1]:

```python
# Standardized components (0-1 scale):
A = age_risk(agent.age)         # nonlinear: 0 for 20-40, rising to 1 for 80+
C = chronic_burden(agent)       # 0 = none, 1 = severe multi-morbidity
F = fitness_deficit(agent)      # 0 = fit, 1 = sedentary
S = sleep_deficit(agent)        # 0 = >7h, 1 = <5h chronic

Z = 0.30 * A + 0.30 * C + 0.25 * F + 0.15 * S + Normal(0, 0.1)
frailty_score = 1 / (1 + exp(-Z))  # logistic transform to [0, 1]
```

Weights are a modeling proposal, not an estimated epidemiological equation.
They can be swept in sensitivity analysis.

### 3.3 Frailty effects on incubation (weak)

```python
# After dose modifier:
host_modifier = 1.0 + frailty_incubation_shift * (agent.frailty_score - 0.5)
# frailty_incubation_shift default = 0.1 → ±5% at the extremes
T_inc = T_base * dose_modifier * host_modifier
```

**Recommended default: `frailty_incubation_shift = 0.0`** (no effect). Enable
only in sensitivity analysis. The literature specifically warns against
inferring incubation effects from severity associations.

### 3.4 Frailty effects on severity (strong)

```python
# Modify illness probability:
severity_boost = frailty_severity_beta * (agent.frailty_score - 0.5)
ill_prob_modified = logistic(logit(ill_prob_base) + severity_boost)
# frailty_severity_beta default = 1.5 (strong effect)
```

### 3.5 Frailty effects on clearance

Immunocompromised agents (high chronic burden, specific conditions) get a
long-shedder component rather than a simple clearance multiplier:

```python
if agent.frailty_score > 0.8 and has_immunosuppressive_condition(agent):
    # 5-15% chance of extended shedding (SARS-CoV-2: up to 78 days)
    if rng.random() < long_shedder_probability:
        recovery_day *= long_shedder_multiplier  # 3-10x
```

This is based on Aydillo et al. (2020) [12]: profoundly immunocompromised
cancer patients shed viable SARS-CoV-2 for up to 61 days post-onset.

### 3.6 Frailty in wearable baselines

The frailty score modulates per-agent wearable baselines, creating a
pre-infection signal that a sufficiently sensitive algorithm could detect:

```python
# At wearable initialization (WearableMonitor._compute_baselines):
frailty = agent.frailty_score

# Heart rate: +4 to +8 bpm for high frailty
rhr_offset = 6.0 * (frailty - 0.3)  # 0 at frailty=0.3, +4.2 at frailty=1.0

# HRV: age-dependent decline + frailty reduction
# Base: SDNN ~ 54 - 0.5*age (Choi et al. 2020 [13])
# Frailty: additional -15% for metabolic/chronic disease
hrv_multiplier = 1.0 - 0.15 * max(0, frailty - 0.3)

# SpO2: minimal effect unless COPD/obesity
# Obesity: -0.4%; mild COPD: -1.5%; severe COPD: -3%
# (Vold et al. 2014 [14]; Kapur et al. [15])
spo2_offset = -0.4 * has_obesity - 1.5 * has_mild_copd - 3.0 * has_severe_copd

# Sleep: poorer baseline sleep for higher frailty
sleep_offset = -0.8 * max(0, frailty - 0.3)  # hours
```

These offsets are applied on top of the existing class/gender offsets in
`WearableMonitor._compute_baselines`. They are conservative — the ranges are
within the physiological variation already modeled by the wearable system.

### 3.7 Pre-symptomatic wearable anomaly

The wearable infection perturbation (`wearable_monitor.py:599`) already
applies infection-phase-dependent deltas. To support pre-symptomatic detection:

- **Lead time**: anomaly onset 0–4 days before symptoms (Stanford smartwatch
  study: 85% of cases showed changes at or before onset; TemPredict: mean
  2.75 days lead [16, 17]).
- **Signal magnitude**: HR peak increment ~+7 bpm; HRV decrement ~3 ms SDNN
  or 5-20% relative; temperature +0.2-1.0°C (Mitratza et al. 2022 [18]).
- **Frailty interaction**: `chronic_wearable_response_scale` (already wired)
  should scale with frailty — higher-frailty agents show larger perturbations
  but from a noisier baseline, making detection harder in some cases.

Existing implementation already handles this architecture. The addition is:
start the infection perturbation `wearable_lead_days` before `incubation_days`,
where `wearable_lead_days` is drawn per infection:

```python
wearable_lead_days = max(0, rng.normal(lead_mean, lead_sd))
# Default: lead_mean = 1.5, lead_sd = 1.0 (truncated at 0)
# → ~50% of infections detectable 1+ day before symptoms
```

---

## 4. Complete Incubation Pipeline

At infection establishment:

```
1. Draw T_base from pathogen incubation_distribution (lognormal or gamma)
2. Apply dose shift: T_dose = T_base * max(floor, 1 - shift * log10(dose/ED50))
3. Apply strain modifier: T_strain = T_dose + strain_incubation_modifier
4. Apply host modifier: T_inc = T_strain * (1 + frailty_shift * (frailty - 0.5))
5. Floor at minimum_incubation (0.1 days = 2.4 hours)
6. Draw wearable_lead_days for pre-symptomatic anomaly onset
7. Store T_inc and wearable_lead on the infection record
```

The strain modifier (step 3) is additive (days), matching the existing
`incubation_modifier` convention in `StrainState`. All other modifiers are
multiplicative on the base draw.

---

## 5. Config Schema

### Pathogen profile additions

```json
{
  "pathogen_id": "norwalk_gi",
  "incubation_distribution": {
    "family": "lognormal",
    "mu": 0.182,
    "sigma": 0.445,
    "unit": "days",
    "minimum": 0.1
  },
  "incubation_dose_response": {
    "dose_shift": 0.12,
    "dose_floor": 0.3,
    "reference_dose": 18.0
  },
  "wearable_lead": {
    "mean_days": 1.5,
    "sd_days": 1.0
  }
}
```

### Simulation config additions

```yaml
host_frailty:
  enabled: false          # default off for backward compatibility
  frailty_incubation_shift: 0.0   # default: no incubation effect
  frailty_severity_beta: 1.5
  long_shedder_probability: 0.05
  long_shedder_multiplier: 5.0
  wearable_frailty_coupling: true  # modulate wearable baselines
```

---

## 6. Backward Compatibility

- `incubation_distribution` absent → uses legacy `symptom_onset_day` (default 1.0)
- `incubation_dose_response` absent → no dose adjustment
- `host_frailty.enabled = false` → no frailty score, no wearable coupling
- `wearable_lead` absent → no pre-symptomatic anomaly shift

All existing tests and campaign outputs are unchanged with defaults.

---

## 7. Paper 3 Value

This parameterization enables the paper's central claim: **the cruise ship as a
facility for construction of a parameterized model of each new circulating
variant, stratified to demographics and wearable data.**

Specifically:

1. **Variant-specific incubation estimation**: with stochastic draws + strain
   modifier, different variants produce different onset distributions in the
   simulated cohort. The ship's closed denominator and known exposure times let
   you *estimate* these distributions from clinical and wearable data — a natural
   experiment that land-based surveillance cannot replicate.

2. **Dose-response recovery**: the dose-dependent shift creates a signal in
   the relationship between exposure intensity (inferable from spatial proximity,
   transmission route) and onset timing. Fleet-level pooling across voyages
   recovers this relationship.

3. **Wearable-stratified risk**: the frailty-wearable coupling means that
   pre-infection baseline readings carry information about severity risk. An
   onboard algorithm that personalizes detection thresholds to each agent's
   baseline can outperform population-level thresholds — and that advantage is
   measurable in the simulation.

4. **Pre-symptomatic detection**: the wearable lead time creates a window
   where the ship's telemetry knows about an infection before the agent reports
   to sick call. The value of this window is quantifiable per pathogen, per
   wearable deployment scenario.

---

## References

[1] Lee RM, Lessler J, Lee RA, et al. Incubation periods of viral
gastroenteritis: a systematic review. BMC Infect Dis. 2013;13:446.
doi:10.1186/1471-2334-13-446

[2] Wei Y, Wei L, Liu Y, et al. A systematic review and meta-analysis reveals
long and dispersive incubation period of COVID-19. medRxiv/Infection. 2021.
doi:10.1007/s15010-021-01682-x

[3] Manica M, et al. Estimation of the incubation period and generation time
of SARS-CoV-2 Alpha and Delta variants from contact tracing data. arXiv. 2022.
arXiv:2203.07063

[4] Xu M, Liu Q, Li Y, et al. Incubation period of COVID-19 from world wide
cases. BMC Med. 2023. doi:10.1186/s12916-023-03070-8

[5] Lessler J, Reich NG, Brookmeyer R, et al. Incubation periods of acute
respiratory viral infections: a systematic review. Lancet Infect Dis.
2009;9:291-300. doi:10.1016/S1473-3099(09)70069-6

[6] Nishiura H, Inaba H. Estimation of the incubation period of influenza A
(H1N1-2009) among imported cases. J Theor Biol. 2011.
doi:10.1016/j.jtbi.2010.12.017

[7] Liao CM, et al. Dose-response of influenza A virus. Epidemiol Infect.
2009. doi:10.1017/S0950268809991178

[8] Ge Y, Billings WZ, Opekun A, et al. Effect of norovirus inoculum dose on
virus kinetics, shedding, and symptoms. Emerg Infect Dis. 2023;29:1349-1356.
doi:10.3201/eid2907.230117

[9] Blaurock C, et al. SARS-CoV-2 dose-dependent infection in Golden Syrian
hamsters. Emerg Microbes Infect. 2022.

[10] Fullen DJ, et al. Human H3N2 challenge study. J Med Virol. 2016.

[11] Atmar RL, Opekun AR, Gilger MA, et al. Determination of the 50% human
infectious dose for Norwalk virus. J Infect Dis. 2014;209:1016-22.
doi:10.1093/infdis/jit620

[12] Aydillo T, et al. Shedding of viable SARS-CoV-2 after immunosuppressive
therapy for cancer. N Engl J Med. 2020;383:2586-2588.
doi:10.1056/NEJMc2031670

[13] Choi J, Cha W, Park MG. Declining trends of heart rate variability
according to aging. Front Aging Neurosci. 2020.
doi:10.3389/fnagi.2020.610626

[14] Vold M, Melbye H, Aasebo U. Low FEV1, smoking history, and obesity are
factors associated with oxygen saturation decrease. Int J COPD. 2014;9:1225.
doi:10.2147/copd.s69438

[15] Kapur VK, et al. Obesity is associated with a lower resting oxygen
saturation in the ambulatory elderly. Cardiovasc Health Study.

[16] Mishra T, et al. Early detection of COVID-19 using a smartwatch. medRxiv.
2020. doi:10.1101/2020.07.06.20147512

[17] Mason AE, et al. Detection of COVID-19 using multimodal data from a
wearable device: TemPredict study. Sci Rep. 2022.
doi:10.1038/s41598-022-07314-0

[18] Mitratza M, et al. The performance of wearable sensors in the detection
of SARS-CoV-2 infection: a systematic review. Lancet Digit Health.
2022;4:e370-383. doi:10.1016/S2589-7500(22)00019-X

[19] Prather AA, et al. Behaviorally assessed sleep and susceptibility to the
common cold. Sleep. 2015;38:1353-9. doi:10.5665/sleep.4968

[20] Devasia T, Lopman B, Leon J, Handel A.

[21] Silva J, Leite D, Fernandes M, et al. A systematic review and
meta-analysis on the incubation period of Campylobacteriosis. Epidemiol Infect.
2017. doi:10.1017/S0950268817001303

[22] Leffler DA, Lamont JT. Clostridium difficile infection. N Engl J Med.
2015;372:1539-1548. doi:10.1056/NEJMra1403772

[23] Vial PA, et al. Hantavirus pulmonary syndrome due to Andes virus:
clinical features and epidemiology. Rev Med Chile. 2006.

[24] WHO Ebola Response Team. Ebola virus disease in West Africa — the first 9
months of the epidemic and forward projections. N Engl J Med.
2014;371:1481-1495. doi:10.1056/NEJMoa1411100 Association of host, agent and
environment characteristics and the duration of incubation and symptomatic
periods of norovirus gastroenteritis. Epidemiol Infect. 2015;143:2308-2314.
doi:10.1017/S0950268814003288

---

## Files to modify

| File | Change |
|------|--------|
| `data/pathogens/*.json` | Add `incubation_distribution`, `incubation_dose_response`, `wearable_lead` per pathogen |
| `schemas/pathogen_profiles.schema.json` | Validate new blocks |
| `engines/infection_dynamics_bridge.py` | Draw incubation at infection; apply dose + host modifiers |
| `orchestrator_epoch.py` | Use `incubation_days` from infection record instead of fixed onset |
| `orchestrator_init.py` | Compute `frailty_score` per agent at initialization |
| `engines/wearable_monitor.py` | Frailty-coupled baseline offsets; pre-symptomatic anomaly lead |
| `engines/wearable_anomaly_scorer.py` | Frailty-aware threshold personalization |
| `crusher_labs/config.yaml` | `host_frailty` config block |
| `tools/sanity_checker.py` | Validate distribution params, dose-response bounds |
| `tests/` | Unit tests for each layer independently and combined |
