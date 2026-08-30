# Crusher-to-the-Bridge Within-Host Infection Dynamics — Formal Specification v2.0

| Field | Value |
|---|---|
| **Canonical SHA** | `d557f39f1692f72ff26b67b4074a5ae68e03b4c2` |
| **Version** | 2.0 |
| **Date** | 2026-08-30 |
| **Status** | Final — implementer-ready |
| **Supersedes** | v1.0-draft (2026-08-30) |
| **Authors** | Auto-generated from code audit, literature reviews, gap analysis, acceptance tests, and canonical source |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Definitions and Notation](#2-definitions-and-notation)
3. [Per-Pathogen Per-Host Pre-Establishment Inoculum Clearance](#3-per-pathogen-per-host-pre-establishment-inoculum-clearance)
4. [Cumulative Exposure and Infection Establishment](#4-cumulative-exposure-and-infection-establishment)
5. [Established-Infection Clearance](#5-established-infection-clearance)
6. [Shedding Dynamics](#6-shedding-dynamics)
7. [Clinical Presentation](#7-clinical-presentation)
8. [Optional Tissue Tropism](#8-optional-tissue-tropism)
9. [Timestep Invariance](#9-timestep-invariance)
10. [Configuration Schema](#10-configuration-schema)
11. [Telemetry](#11-telemetry)
12. [Migration](#12-migration)
13. [Acceptance Tests](#13-acceptance-tests)
14. [Appendices](#14-appendices)
15. [Changelog](#15-changelog-v10-draft-to-v20)

---

## 1. Overview

### 1.1 Purpose

This specification defines the within-host infection dynamics module for the Crusher-to-the-Bridge (CtB) multi-pathogen shipboard agent-based model. It covers the full lifecycle of a pathogen inside one host agent, from initial dose delivery through establishment, shedding, clinical presentation, and clearance. The module must support:

- Multiple concurrent pathogens (currently `norwalk_gi` and `sars_cov2_resp`; extensible to ≥10).
- Co-infection with multiple strains of the same pathogen (variant surveillance).
- Timestep-invariant operation across epoch durations from 0.5 hours to 24 hours (legacy).
- Deterministic reproducibility given a seeded PRNG.

### 1.2 Scope

**In scope:** Dose delivery to a susceptible host, pre-establishment clearance, cumulative dose tracking, establishment via dose-response, incubation, symptom onset and severity, shedding dynamics, within-host recovery/clearance, immunity acquisition.

**Out of scope:** Transmission pathways (direct contact, droplet, HVAC, fomite — see `transmission_core.py`), environmental contamination/persistence, spatial movement, diagnostic observation mechanics, containment interventions, strain mutation/recombination. These systems consume the interfaces defined here but are specified separately.

### 1.3 Source Materials

| Source | Location |
|---|---|
| Code audit (SHA d557f39) | `/workspace/478cd23a-468e-4074-bc13-d6a5b8938ee3.md` |
| Within-host literature review | `/workspace/6a207fd3-eb39-4f2e-9dc4-e7aed6defe1c.md` |
| Cumulative exposure literature review | `/workspace/26b414e0-180f-4654-bdeb-b5aa675bb5d9.md` |
| Codebase contracts | `/workspace/codebase_contracts.md` |
| Acceptance test design | `/workspace/acceptance_tests.md` |
| Gap analysis | `/workspace/spec_gap_analysis.md` |
| Canonical repository | `/workspace/Crusher_to_the_Bridge_canonical` (SHA `d557f39f`) |

---

## 2. Definitions and Notation

### 2.1 Variables

| Symbol | Type | Unit | Description |
|---|---|---|---|
| $$dt$$ | `float` | days | Duration of one epoch in natural-history time. `dt = epoch_duration_hours / 24`. |
| $$D_{i,p}(t)$$ | `float` | particles | Raw dose delivered to agent $$i$$ for pathogen $$p$$ in epoch $$t$$, summed over all pathways. |
| $$D^{\text{eff}}_{i,p}(t)$$ | `float` | particles | Effective dose after protection and susceptibility scaling: $$D^{\text{eff}} = D \cdot (1 - \pi) \cdot s_{\text{super}}$$. |
| $$C_{i,p}(t)$$ | `float` | particles | Cumulative effective dose for agent $$i$$, pathogen $$p$$, since last establishment or recovery. |
| $$r_{i,p}$$ | `float` | dimensionless | Persistent host-specific dose-response susceptibility. Drawn once per (agent, pathogen) pair; never redrawn. |
| $$\pi_{i,p}(t)$$ | `float` | $$[0, 1]$$ | Immune protection of agent $$i$$ against pathogen $$p$$ at epoch $$t$$. |
| $$s_{\text{super},p}$$ | `float` | $$[0, 1]$$ | Superinfection susceptibility for pathogen $$p$$ (0 = complete homotypic interference; default 0 without strain tracking). |
| $$\tau_{\text{inc},i,p}$$ | `float` | days | Drawn incubation period for agent $$i$$, pathogen $$p$$. |
| $$\tau_{\text{rec},p}$$ | `int` | days | Recovery duration for pathogen $$p$$, measured from onset. Fixed per pathogen profile. |
| $$\sigma_{i,p}(t)$$ | `float` | particles/epoch | Shedding rate of agent $$i$$ for pathogen $$p$$ at epoch $$t$$. |
| $$m_{i,p}$$ | `float` | dimensionless | Persistent per-agent shedding multiplier drawn from $$\text{LogNormal}(0, \sigma_{\text{shed}})$$ in $$\log_{10}$$ space. |

### 2.2 Enumerations

**`InfectionStatus`** (per-pathogen, source: `infection_dynamics_bridge.py`):

| Value | Semantics |
|---|---|
| `SUSCEPTIBLE` (0) | No active infection; may receive dose. |
| `INFECTED` (1) | Established infection; shedding and progressing. |
| `RECOVERED` (2) | Post-clearance; immune memory acquired. |
| `DEAD` (3) | Reserved. Not currently assigned (gated by `NotImplementedError`). |
| `IMMUNE` (4) | Pre-existing immunity at embarkation. |

**`IllnessStatus`** (per-pathogen, source: `infection_dynamics_bridge.py`):

| Value | Semantics |
|---|---|
| `NOT_ILL` (0) | No symptoms (pre-onset or asymptomatic infection). |
| `SYMPTOMATIC` (1) | Clinically presenting. |
| `RECOVERED` (2) | Post-recovery. |

**Severity States** (per-pathogen, 5-state ordered vector):

| Index | State | Semantics |
|---|---|---|
| 0 | `asymptomatic` | No clinical signs. |
| 1 | `subclinical` | Mild malaise; below reporting threshold for most observation systems. |
| 2 | `mild` | Recognizable illness; self-limiting. |
| 3 | `moderate` | Requires medical attention. |
| 4 | `severe_critical` | Requires intensive care or hospitalization. |

**Transmission Routes** (enum, source: `pathogen_profiles.schema.json`):

`direct_contact`, `fomite`, `droplet`, `hvac_airborne`, `water_aerosol`, `food`, `water`, `bodily_fluids`

> **Note:** The `transmission_routes` array on a pathogen profile uses the 8-value enum above. The `transmission_route_weights` dict uses a different key set: `direct_contact`, `droplet`, `hvac_airborne`, `fomite`, `food_contamination`, `environmental_source`. These keys map to `TransmissionCore` internal pathways and do not correspond 1:1 to the route enum. The distinction exists because the transmission engine aggregates several schema-level routes into pathway-level dose accumulators.

### 2.3 Type Aliases

```
PathogenId      = str           # e.g. "norwalk_gi"
StrainId        = str           # e.g. "GII.4-m0001"
AgentId         = int
EpochIndex      = int
DayCount        = float
Particles       = float
Probability     = float         # [0, 1]
```

---

## 3. Per-Pathogen Per-Host Pre-Establishment Inoculum Clearance

### 3.1 Rationale

In the current codebase (SHA d557f39), there is **no explicit pre-establishment clearance model**. Dose delivered in one epoch is immediately evaluated for establishment in that same epoch's dose-response draw. The cumulative-exposure mechanism (§4) implicitly allows subinfectious doses to accumulate across epochs, but no mucosal or innate-immune clearance reduces the retained viable inoculum between epochs.

The literature review (cumulative exposure report §1, §5) documents that fractionated exposures can substantially reduce infection risk compared to bolus exposures of equal total dose, due to immune clearance between sub-doses. For example, spreading 313 *Cryptosporidium* organisms across a 100-fold longer window reduced predicted risk from 0.66 to 0.09.

### 3.2 Mathematical Model

**NEW — not yet implemented in SHA d557f39.**

Between epochs, retained viable inoculum decays exponentially:

$$
C_{i,p}(t+1) = \bigl[C_{i,p}(t) + D^{\text{eff}}_{i,p}(t)\bigr] \cdot \exp(-\lambda_{\text{clear},p} \cdot dt)
$$

where $$\lambda_{\text{clear},p}$$ is the per-pathogen mucosal/innate clearance rate (day$$^{-1}$$).

This is a continuous exponential decay applied as a multiplicative factor each epoch. It is **not** an all-or-nothing clearance event. The exponential form ensures timestep invariance: splitting one epoch of duration $$dt$$ into $$n$$ sub-epochs of duration $$dt/n$$ with no new dose between them yields the same retained inoculum:

$$
C \cdot \bigl(\exp(-\lambda \cdot dt/n)\bigr)^n = C \cdot \exp(-\lambda \cdot dt)
$$

When `inoculum_clearance_rate_per_day` > 0, stale dose decays naturally without requiring a separate timeout mechanism. A dose that has not been refreshed for $$t$$ days is attenuated by $$\exp(-\lambda t)$$. For example, with $$\lambda = \ln(2)/2$$ day$$^{-1}$$ (half-life 2 days), after 10 days of no new exposure the retained dose is 0.3% of its original value — effectively negligible. This eliminates the need for a separate configurable "no-dose window" timeout (resolving the v1.0-draft §3.6 TODO-1).

### 3.3 Parameters

| Parameter | Key | Type | Default | Valid Range | Description |
|---|---|---|---|---|---|
| Inoculum clearance rate | `inoculum_clearance_rate_per_day` | `float` | 0.0 | $$[0, \infty)$$ | Pre-establishment mucosal clearance rate (day$$^{-1}$$). 0 = no clearance (current behaviour). |

### 3.4 Pseudocode

```python
def update_cumulative_exposure(agent, pathogen_id, effective_dose, dt, profile):
    """Update retained viable inoculum with new dose and clearance decay."""
    clearance_rate = profile.get("inoculum_clearance_rate_per_day", 0.0)

    # Accumulate new dose
    cumulative = agent.cumulative_exposure.get(pathogen_id, 0.0) + effective_dose

    # Apply exponential clearance
    if clearance_rate > 0.0:
        cumulative *= math.exp(-clearance_rate * dt)

    agent.cumulative_exposure[pathogen_id] = cumulative
    return cumulative
```

### 3.5 Current Behaviour Preservation

When `inoculum_clearance_rate_per_day = 0.0` (default), this reduces to the current additive-only accumulation in `transmission_core.py:1520-1524`.

### 3.6 Cumulative Exposure Reset Policy

The current codebase does **not** clear `cumulative_exposure` on recovery without establishment (audit finding 8.3, MODERATE). This specification requires:

> **SPEC-CLEAR-01**: `cumulative_exposure[pathogen_id]` MUST be reset to 0.0 when:
> 1. An infection establishes (already implemented, `transmission_core.py:1539`).
> 2. The agent transitions to `RECOVERED` for this pathogen (new requirement).
> 3. The agent's immune protection $$\pi_{i,p}$$ reaches 1.0 (full immunity acquired via other means).
>
> **Rationale:** When `inoculum_clearance_rate_per_day` > 0, the exponential decay naturally eliminates stale dose over time, making an explicit timeout unnecessary. When clearance rate = 0 (current default), SPEC-CLEAR-01 prevents residual dose from the previous susceptible window from carrying across a recovery boundary. The permanent host susceptibility (`dose_response_susceptibility`) is NOT reset.

---

## 4. Cumulative Exposure and Infection Establishment

### 4.1 Overview

Each epoch, a susceptible agent may receive dose from one or more transmission pathways. The combined dose is scaled by protection and susceptibility, then evaluated against a dose-response function to determine whether infection establishes. The model supports two dose-response families: **Beta-Poisson** (default) and **Exponential**.

### 4.2 Dose Delivery Pipeline

Per epoch, for each active pathogen:

1. **Pathway accumulation**: Six transmission pathways (`direct_contact`, `droplet`, `hvac_airborne`, `fomite`, `food_contamination`, `environmental_source`) each contribute a dose to agent $$i$$. These pathway keys are internal to `TransmissionCore` and map from the schema-level `transmission_routes` enum.
2. **Susceptibility scaling**: Total pathway dose is multiplied by the agent's per-pathogen `susceptibility_multiplier` (default 1.0; modified by chronic disease via `base_susceptibility`).
3. **Protection scaling**: Effective dose is $$D^{\text{eff}} = D \cdot (1 - \pi)$$, where $$\pi$$ is the agent's immune protection from `_challenge_protection()`.
4. **Superinfection scaling**: If the agent is already infected with this pathogen and strain tracking is active, effective dose is further multiplied by $$s_{\text{super},p}$$ (from `StrainEvolutionConfig.superinfection_susceptibility`). Without strain tracking, superinfection is blocked entirely.

> **Key invariant:** Protection and superinfection susceptibility scale the **dose**, not the probability. This is required for timestep invariance (§9).

### 4.3 Dose-Response Models

#### 4.3.1 Beta-Poisson (default)

The implementation uses a **persistent beta-frailty** model: a per-host susceptibility $$r_{i,p}$$ is drawn once from $$\text{Beta}(\alpha_p, \beta_p)$$ and stored permanently in `agent.dose_response_susceptibility[pathogen_id]`:

$$
r_{i,p} \sim \text{Beta}(\alpha_p, \beta_p) \quad \text{(drawn once, stored permanently)}
$$

The per-epoch establishment probability given the host's susceptibility and the epoch's effective dose:

$$
P(\text{establish in epoch}) = 1 - \exp(-r_{i,p} \cdot D^{\text{eff}}_{i,p}(t))
$$

This is the **epoch-invariant** formulation introduced in PR #346. The establishment draw uses only the **current epoch's** effective dose, not the cumulative total. The cumulative dose is tracked separately and transferred as `acquired_particles` upon establishment.

**Mathematical relationship to the classic approximate beta-Poisson:** The population-level (pre-draw) CDF for a single bolus dose $$D$$ under this model is:

$$
P_{\text{pop}}(D) = 1 - {}_1F_1(\alpha; \alpha + \beta; -D)
$$

This is the **exact** beta-mixture CDF, not the classic approximation $$1 - (1 + D/\beta)^{-\alpha}$$, which corresponds to a Gamma (not Beta) frailty. At shipped norovirus parameters ($$\alpha = 0.111$$, $$\beta = 32.81$$), the numerical difference between these two forms is < 0.001 across four orders of magnitude (audit finding 8.4). The codebase also contains `_dose_response()` (`transmission_core.py:1111-1118`) which uses the classic approximation for population-level calculations; this function is NOT used in the per-host establishment pipeline.

**Shipped parameters:**

| Pathogen | $$\alpha$$ | $$\beta$$ | $$N_{50}$$ (particles) |
|---|---|---|---|
| `norwalk_gi` | 0.111 | 32.81 | ~16,871 |
| `sars_cov2_resp` | 0.18 | 58.0 | ~2,670 |

#### 4.3.2 Exponential

For pathogens without host heterogeneity:

$$
r_{i,p} = k_p \quad \text{(constant, stored as dose\_response\_susceptibility)}
$$

$$
P(\text{establish in epoch}) = 1 - \exp(-k_p \cdot D^{\text{eff}}_{i,p}(t))
$$

The exponential model is selected when `dose_response.model = "exponential"`. The rate parameter `k` defaults to 0.01 if omitted.

#### 4.3.3 Epoch Invariance of the Dose-Response

The establishment probability over $$n$$ sub-epochs (each of duration $$dt/n$$ delivering $$D/n$$ particles) must equal the single-epoch probability (delivering $$D$$ particles in $$dt$$). This is satisfied because:

$$
P(\text{no establishment in } n \text{ sub-epochs}) = \prod_{j=1}^{n} \exp(-r \cdot D/n) = \exp(-r \cdot D)
$$

This invariance was validated by the PR #346 test suite (1/24/168 epoch slices agree within 0.04).

### 4.4 Cumulative Dose Tracking

```python
# From transmission_core.py lines 1520-1539
cumulative_dose = agent.cumulative_exposure.get(pathogen_id, 0.0) + effective_dose
agent.cumulative_exposure[pathogen_id] = cumulative_dose

inf_prob = 1 - exp(-r_ip * effective_dose)  # per-epoch hazard uses THIS epoch's dose

if rng.random() < inf_prob:
    establish(agent, pathogen_id, strain_id, dose=cumulative_dose, epoch=epoch)
    agent.cumulative_exposure[pathogen_id] = 0.0  # reset on establishment
```

> **Semantic distinction:** The per-epoch establishment probability uses `effective_dose` (this epoch only). The `cumulative_dose` is bookkeeping for the `acquired_particles` field at establishment. These serve different purposes: the probability drives the stochastic event; the cumulative total characterizes the infection for downstream dose-conditioning (incubation, severity).

### 4.5 Establishment Side Effects

When `_establish()` succeeds:

1. Creates `infections[pathogen_id]` dict with:
   - `status`: `InfectionStatus.INFECTED`
   - `illness`: `IllnessStatus.NOT_ILL`
   - `time_infected`: 0
   - `acquired_particles`: cumulative dose at establishment
   - `infection_epoch`: current epoch
   - `shedding_multiplier`: drawn from $$10^{N(0, \sigma_{\text{shed}})}$$ where $$\sigma_{\text{shed}}$$ = `shedding_variance_log10`
2. Resets `cumulative_exposure[pathogen_id]` to 0.
3. Sets agent-level `infection_status` to `INFECTED` and `illness_status` to `NOT_ILL` (legacy projection).
4. If strain tracking is active, records strain ID and phenotype on the infection record.
5. For superinfection (resident=True): `superinfect_with_strain()` adds a co-resident `StrainInfection` with its own clock.

### 4.6 Pseudocode: Full Establishment Pipeline

```python
def try_establish(agent, pathogen_id, epoch, effective_dose, rng, profile, clock):
    """One epoch's establishment attempt for one agent and one pathogen."""
    # Skip if already infected and superinfection is closed
    if agent.is_infected_with(pathogen_id) and not superinfection_open(pathogen_id):
        return False

    if effective_dose <= 0:
        return False

    # Immune protection
    protection = challenge_protection(agent, pathogen_id, epoch)
    if protection >= 1.0:
        return False

    effective_dose *= (1.0 - protection)

    # Superinfection discount
    if agent.is_infected_with(pathogen_id):
        effective_dose *= superinfection_susceptibility(pathogen_id)

    if effective_dose <= 0:
        return False

    # Accumulate with optional clearance (§3)
    dt = clock.day_fraction_per_epoch
    cumulative = update_cumulative_exposure(agent, pathogen_id, effective_dose, dt, profile)

    # Host-specific dose-response hazard
    r = get_or_draw_susceptibility(agent, pathogen_id, profile, rng)
    p_establish = -math.expm1(-r * effective_dose)  # = 1 - exp(-r * effective_dose)

    if rng.random() < p_establish:
        establish(agent, pathogen_id, cumulative, epoch, rng, profile)
        agent.cumulative_exposure[pathogen_id] = 0.0
        return True

    return False
```

---

## 5. Established-Infection Clearance

### 5.1 Overview

Once an infection is established, the agent progresses through an incubation period, potential symptom onset, and eventual clearance. The total infection course is:

$$
\tau_{\text{total}} = \tau_{\text{inc}} + \tau_{\text{rec}}
$$

where $$\tau_{\text{inc}}$$ is the drawn incubation period and $$\tau_{\text{rec}}$$ is the configured recovery duration (from symptom onset, whether or not symptoms actually occur).

### 5.2 Incubation Period

The incubation period is drawn once per infection from a distribution conditioned on the inoculum dose and host biology. The implementation is in `engines/incubation.py` via the `IncubationModel` dataclass.

#### 5.2.1 Distribution Families

| Distribution | Parameterization | Dispersion semantics | Schema constraint |
|---|---|---|---|
| **Lognormal** (default) | $$\mu = \ln(\text{median})$$, $$\sigma = \ln(\text{dispersion})$$ | Geometric standard deviation; must be > 1 | `dispersion > 1` enforced by schema |
| **Gamma** | shape $$k = 1/\text{dispersion}^2$$, scale $$\theta = \text{median} \cdot \text{dispersion}^2$$ | Coefficient of variation | `dispersion > 0` |

#### 5.2.2 Dose Conditioning

The median incubation is shifted by the log-dose relative to a reference:

$$
\text{dose\_factor} = \text{clamp}\bigl(1 - s_d \cdot (\log_{10}(D_{\text{acq}}) - \log_{10}(D_{\text{ref}})),\ f_{\text{floor}},\ 2.5\bigr)
$$

where:
- $$s_d$$ = `dose_log10_shortening` (fractional reduction per log10 unit above reference; default 0.0 = no dose effect)
- $$D_{\text{ref}}$$ = $$10^{\text{dose\_reference\_log10}}$$ (inoculum at which the literature median applies; default $$10^{4.0}$$)
- $$f_{\text{floor}}$$ = `dose_floor` (minimum multiplier; prevents zero incubation; code default 0.4, shipped profiles use 0.3)
- 2.5 = upper clamp (prevents unreasonably long incubation at very low doses)

#### 5.2.3 Host Conditioning

$$
\text{median}_{\text{conditional}} = \text{median}_{\text{base}} \times \text{dose\_factor} \times \prod_{j \in \text{host\_axes}} h_j
$$

Host factor multipliers (all > 0; default 1.0 = no effect; absent from shipped profiles):

| Axis | Config key | Effect when > 1 |
|---|---|---|
| Immunocompromised | `host_factors.immunocompromised` | Longer incubation (delayed presentation while shedding) |
| Prior immunity | `host_factors.prior_immunity` | Longer incubation (partial immunity blunts onset) |
| Age band | `host_factors.age_bands.<band>` | Age-specific shift |

#### 5.2.4 Strain Modification

A strain's `incubation_modifier` (positive or negative float, default 0.0) shifts the drawn incubation period additively after the host-conditioned draw:

$$
\tau_{\text{inc}} = \max\bigl(0,\ \tau_{\text{drawn}} + \delta_{\text{strain}}\bigr)
$$

#### 5.2.5 Truncation

The raw draw is clamped to $$[\text{min\_days}, \text{max\_days}]$$ **before** the strain modifier is applied:

$$
\tau_{\text{drawn}} = \text{clamp}(\tau_{\text{raw}}, \text{min\_days}, \text{max\_days})
$$

Code defaults: `min_days = 0.5`, `max_days = 30.0`. Shipped profiles override these (e.g., norwalk: 0.1–6.0 days; SARS-CoV-2: 0.5–21.0 days).

#### 5.2.6 Pseudocode

```python
def sample_incubation(agent, pathogen_id, infection, profile, rng):
    """Draw incubation period; cached once per infection."""
    stored = infection.get("incubation_days")
    if stored is not None:
        return stored

    model = IncubationModel.from_mapping(profile.get("incubation"))
    if model is None:
        # Legacy fixed onset day
        return profile.get("symptom_onset_day", 1)

    dose = infection["acquired_particles"]
    host = HostIncubationState(
        age_band=agent.age_band,
        immunocompromised=agent.immunocompromised,
        prior_immunity=bool(agent.immune_genotypes(pathogen_id)),
    )

    # Conditional median
    dose_factor = clamp(
        1.0 - model.dose_log10_shortening * (log10(max(dose, 1e-9)) - model.dose_reference_log10),
        model.dose_floor, 2.5
    )
    median = model.median_days * dose_factor * host_multiplier(host, model.host_factors)

    # Draw from selected distribution
    if model.distribution == "lognormal":
        drawn = rng.lognormal(log(median), log(model.dispersion))
    elif model.distribution == "gamma":
        shape = 1.0 / (model.dispersion ** 2)
        drawn = rng.gamma(shape, median / shape)

    # Truncate
    drawn = clamp(drawn, model.min_days, model.max_days)

    infection["incubation_days"] = drawn
    return drawn
```

### 5.3 Recovery / Clearance

Recovery duration is a **fixed integer** (`recovery_day`) measured in days from symptom onset (virtual or realized), consistent with the current codebase at SHA d557f39.

Clearance occurs when:
1. The infection has lasted at least $$\tau_{\text{inc}} + \tau_{\text{rec}}$$ days, **AND**
2. All co-resident strain lineages have individually exceeded their clearance threshold (residents_left == 0).

$$
\text{clear if:} \quad \text{days\_elapsed}(\text{epochs\_infected}) \geq \tau_{\text{inc}} + \tau_{\text{rec}} \quad \land \quad |\text{residents}| = 0
$$

#### 5.3.1 Per-Strain Clearance

Each co-resident strain (`StrainInfection`) maintains its own `time_infected` counter. The strain clears when:

$$
\text{clock.days\_elapsed}(\text{strain.time\_infected}) \geq \tau_{\text{inc}} + \tau_{\text{rec}}
$$

When the last strain clears, the pathogen-level infection transitions to `RECOVERED`.

#### 5.3.2 Chronic Disease Extension

The recovery duration can be extended by chronic diseases:

$$
\tau_{\text{rec,adjusted}} = \tau_{\text{rec,base}} + \sum_d \text{recovery\_day\_extension}_d
$$

where $$d$$ ranges over the agent's active chronic diseases. The extension is **unbounded** (audit finding 8.7). The `illness_probability_boost` from chronic diseases is separately capped at 0.5.

#### 5.3.3 Recovery Side Effects

When the infection transitions to `RECOVERED`:

1. `infection["status"]` → `InfectionStatus.RECOVERED`
2. `infection["illness"]` → `IllnessStatus.RECOVERED`
3. `cumulative_exposure[pathogen_id]` → 0.0 (SPEC-CLEAR-01, new requirement)
4. `_project_legacy_illness(agent)` updates agent-level fields (§12)
5. Per-cleared-strain: one `ImmuneRecord` is created (§5.4)

#### 5.3.4 Pseudocode

```python
def advance_infection(agent, pathogen_id, infection, profile, rng, strain_registry, epoch):
    """One epoch of infection progression."""
    clock = agent.clock

    infection["time_infected"] += 1
    epochs_infected = infection["time_infected"]
    days_infected = clock.days_elapsed(epochs_infected)

    onset_day = sample_incubation(agent, pathogen_id, infection, profile, rng)
    onset_day += infection.get("strain_incubation_modifier", 0.0)
    onset_day = max(0.0, onset_day)

    # Symptom onset: one draw per day boundary crossed
    if (infection["illness"] == IllnessStatus.NOT_ILL
        and crossed_day_boundary(clock, epochs_infected, onset_day)):
        draw_symptom_onset(agent, pathogen_id, infection, profile, rng, epoch)

    recovery_day = agent.get_chronic_recovery_day(pathogen_id, profile.get("recovery_day", 3))
    clearance_day = onset_day + recovery_day

    # Clear co-resident strains on their own clocks
    cleared = []
    residents_left = agent.advance_resident_strains(pathogen_id, clearance_day, cleared)
    record_cleared_immunity(agent, pathogen_id, cleared, strain_registry, epoch)

    # Pathogen-level clearance
    if days_infected >= clearance_day and residents_left == 0:
        infection["status"] = InfectionStatus.RECOVERED
        infection["illness"] = IllnessStatus.RECOVERED
        agent.cumulative_exposure[pathogen_id] = 0.0  # SPEC-CLEAR-01
```

### 5.4 Immunity Acquisition

Upon clearance of a strain, an `ImmuneRecord` is created with:
- `pathogen_id`, `genotype`, `strain_id`, `epoch`, `immune_escape`

These records feed the genotype-aware cross-immunity system (`_challenge_protection`), allowing partial or full protection against re-challenge depending on antigenic distance.

### 5.5 Design Decision: Fixed vs. Drawn Recovery Duration

The v1.0-draft TODO-2 asked whether to replace the fixed `recovery_day` with a drawn distribution (lognormal or gamma). **Decision: retain fixed `recovery_day` in v2.0.** Rationale:

1. The current codebase and all 388 tests use a fixed integer. All shipped profiles define `recovery_day` as an integer.
2. The literature supports heterogeneous infectious periods (Milbrath et al. 2013, Teunis et al. 2015), but no shipped profiles supply distribution parameters.
3. Backward compatibility: switching to a drawn duration would change attack rates and outbreak timing in all existing campaigns.
4. **Future extension path:** When evidence-based distribution parameters are available, add an optional `recovery_distribution` block to the pathogen profile (analogous to `incubation`). When present, the drawn duration replaces the fixed `recovery_day`. When absent, the fixed value governs. This is schema-compatible and default-off.

---

## 6. Shedding Dynamics

### 6.1 Overview

Shedding rate determines how much pathogen mass an infected agent emits per epoch. It is computed from a day-indexed shedding curve, adjusted by a dose offset, and scaled by persistent host and strain multipliers.

### 6.2 Shedding Curve

Two shedding curves are defined per pathogen profile, indexed by days since symptom onset:

- `shedding_curve_log10`: symptomatic hosts (or hosts before severity is determined)
- `asymptomatic_shedding_log10`: asymptomatic hosts

Each entry is $$\log_{10}(\text{copies/g})$$. Both shipped pathogen profiles have 15 entries (days 0–14).

### 6.3 Shedding Rate Computation

For a single-strain infection:

$$
\sigma_{i,p}(t) = \text{amount\_per\_epoch}\bigl(10^{C[d] - A} \cdot m_{i,p} \cdot m_{\text{strain}}\bigr)
$$

where:
- $$C[d]$$ = curve value at day index $$d$$ since onset (clamped to $$[0, \text{len}(C) - 1]$$)
- $$A$$ = `dose_adjustment` (log10 offset; 4.0 for `norwalk_gi`, 3.0 for `sars_cov2_resp`)
- $$m_{i,p}$$ = host shedding multiplier (drawn at infection: $$10^{N(0, \sigma_{\text{shed}})}$$ where $$\sigma_{\text{shed}}$$ = `shedding_variance_log10`)
- $$m_{\text{strain}}$$ = heritable strain shedding multiplier (from `Phenotype.shedding_multiplier`, default 1.0)
- `amount_per_epoch(x)` = $$x \cdot dt$$ (scales daily amount to epoch fraction; in `LEGACY_EPOCH_DAY` mode, returns $$x$$ unchanged)

### 6.4 Day-Since-Onset Calculation

The shedding curve is anchored to **symptom onset**, not infection establishment:

1. If `onset_time_infected` is set (symptoms occurred): elapsed = `epochs_infected − onset_epoch`.
2. If `incubation_days` is drawn (no symptoms yet): `days_since_onset = days_elapsed − incubation_days` (virtual onset).
3. Fallback: uses `symptom_onset_day` from profile (legacy, default 1 day).

The day index is $$\lfloor \text{days\_since\_onset} \rfloor$$, clamped to $$[0, \text{len}(C) - 1]$$.

### 6.5 Presymptomatic Shedding

Hosts shed for up to `presymptomatic_shedding_days` before onset, using the first curve value (index 0). If `days_since_onset < −presymptomatic_shedding_days`, shedding is zero.

| Pathogen | `presymptomatic_shedding_days` |
|---|---|
| `norwalk_gi` | 0.5 |
| `sars_cov2_resp` | 2.0 |

### 6.6 Co-Resident Strain Shedding

When multiple strains co-reside, shedding is partitioned by inoculum share:

$$
\text{share}_s = \frac{\text{acquired\_particles}_s}{\sum_{s'} \text{acquired\_particles}_{s'}}
$$

Each strain reads its own onset-anchored curve at its own acquisition time:

$$
\sigma_{\text{total}} = m_{\text{host}} \cdot \sum_s \text{amount\_per\_epoch}\bigl(\text{share}_s \cdot 10^{C[d_s] - A} \cdot m_{\text{strain},s}\bigr)
$$

This ensures co-infection **redistributes** emission rather than multiplying it. Total shedding from a co-infected host does not exceed what a single-strain host with the same total inoculum would produce (conservation invariant).

### 6.7 Route-Specific Shedding

Shedding is a **scalar** per-agent per-pathogen. Route-specific weighting is handled downstream by `transmission_route_weights` in `TransmissionCore`, not in the shedding computation itself.

**Shipped `transmission_route_weights`:**

| Pathogen | `direct_contact` | `droplet` | `hvac_airborne` | `fomite` | `food_contamination` | `environmental_source` |
|---|---|---|---|---|---|---|
| `norwalk_gi` | 0.35 | 0.10 | 0.05 | 0.30 | 0.20 | 0.00 |
| `sars_cov2_resp` | 0.25 | 0.30 | 0.30 | 0.10 | 0.00 | 0.05 |

> **Design decision (v1.0-draft TODO-3):** Route-specific shedding curves (e.g., separate fecal and respiratory curves) are **not** in scope for v2.0. The current architecture of scalar shedding multiplied by downstream route weights is sufficient for shipped pathogens. Norovirus dual transmission (fecal-oral + vomitus-aerosol) is adequately represented by the `transmission_route_weights` split. Route-specific curves are a future extension that would require the tissue tropism framework (§8).

### 6.8 Pseudocode

```python
def get_pathogen_shedding(agent, pathogen_id, profile, clock):
    """Compute shedding for one pathogen in one epoch."""
    inf = agent.infections.get(pathogen_id)
    if inf is None or inf["status"] != InfectionStatus.INFECTED:
        return 0.0

    epochs_infected = inf["time_infected"]
    is_symptomatic = inf["illness"] == IllnessStatus.SYMPTOMATIC

    # Select curve
    curve = profile.get("shedding_curve_log10")
    if not is_symptomatic:
        curve = profile.get("asymptomatic_shedding_log10", curve)

    if not curve:
        return 0.0

    adj = profile.get("dose_adjustment", 4.0)
    host_mult = inf.get("shedding_multiplier", 1.0)

    # Onset-anchored age
    days_since_onset, curve_index = shedding_age(epochs_infected, inf, profile, clock)

    # Presymptomatic window
    presymp = profile.get("presymptomatic_shedding_days", 0.0)
    if days_since_onset < -presymp:
        return 0.0

    idx = clamp(curve_index, 0, len(curve) - 1)

    return clock.amount_per_epoch(
        pow(10, curve[idx] - adj) * host_mult * inf.get("strain_shedding_multiplier", 1.0)
    )
```

---

## 7. Clinical Presentation

### 7.1 Overview

Clinical presentation maps the within-host infection state to observable clinical categories. This occurs in two stages: (1) an illness draw at incubation completion, and (2) a severity assignment for symptomatic cases. Shedding and clinical presentation are **orthogonal**: an asymptomatic agent can shed, and severity does not control infectiousness.

### 7.2 Illness Probability

At the epoch when the infection crosses the drawn incubation period (detected by `crossed_day_boundary()`), a single dose-conditioned draw determines whether the host becomes symptomatic:

$$
P(\text{symptomatic}) = \min\Bigl(1,\ 1 - (1 + \eta \cdot D_{\text{acq}})^{-\gamma} + \text{chronic\_boost}\Bigr)
$$

where:
- $$\eta$$, $$\gamma$$ are per-pathogen illness probability parameters (both > 0; not restricted to [0,1])
- $$D_{\text{acq}}$$ = `acquired_particles` at establishment (cumulative effective dose)
- `chronic_boost` = additive probability boost from chronic diseases (capped at 0.5 by `illness_probability_boost`)

The draw happens **once per day boundary** (not once per epoch), enforced by `crossed_day_boundary()`. This ensures the illness decision does not depend on epoch granularity.

**Shipped parameters:**

| Pathogen | $$\eta$$ | $$\gamma$$ |
|---|---|---|
| `norwalk_gi` | 0.508 | 0.095 |
| `sars_cov2_resp` | 0.4 | 0.12 |

### 7.3 Severity Assignment

If the illness draw succeeds and the pathogen has a `severity_model`, a severity state is drawn from the symptomatic portion of the 5-state vector:

```python
# Exclude asymptomatic (index 0); renormalize over states 1-4
symptomatic_states = severity_model["states"][1:]  # ["subclinical","mild","moderate","severe_critical"]
symptomatic_probs = normalize(severity_model["base_probabilities"][1:])
severity = rng.choice(symptomatic_states, p=symptomatic_probs)
```

If the illness draw fails, `symptom_severity` is set to `"asymptomatic"`.

If the pathogen has **no** `severity_model` (e.g., `sars_cov2_resp` at SHA d557f39), symptomatic agents receive a default severity and all observation falls through to a flat base rate.

**Shipped severity vectors (`norwalk_gi`):**

| State | Base probability | Conditional (symptomatic) |
|---|---|---|
| asymptomatic | 0.25 | — |
| subclinical | 0.55 | 0.733 |
| mild | 0.19 | 0.253 |
| moderate | 0.009 | 0.012 |
| severe_critical | 0.001 | 0.0013 |

### 7.4 Chronic Disease Severity Escalation

Symptomatic agents with chronic diseases may be escalated to `SEVERE` presentation:

$$
P(\text{escalate to severe}) = \text{probability\_per\_epoch}\bigl(\min(1, \max(0, s_{\text{chronic}} - 1))\bigr)
$$

where $$s_{\text{chronic}}$$ is the maximum chronic severity multiplier across active pathogens.

### 7.5 Observation Model

The observation model (per-pathogen) controls the visibility of infections to the surveillance system. It is indexed by the 5-state severity vector:

| Field | Shape | Required | Description |
|---|---|---|---|
| `system` | `string` | yes | Observation system identifier (e.g., `"VSP_AGE"`) |
| `syndrome_case_eligibility_by_severity` | `float[5]` | yes | Probability that severity state qualifies as a syndrome case |
| `reporting_probability_by_severity_pre_recognition` | `float[5]` | yes | Probability of reporting before outbreak recognized |
| `reporting_probability_by_severity_post_recognition` | `float[5]` | yes | Probability of reporting after outbreak recognized |
| `lab_sampling_probability_by_severity` | `float[5]` | no | Probability of lab sample collection |
| `active_screening` | `object \| null` | no | Active screening configuration |
| `assay_sensitivity_by_time_since_infection` | `any` | no | Time-dependent assay sensitivity |
| `episode_reporting_window_days` | `float > 0` | yes | Window during which an episode can be reported |

All array elements MUST be in $$[0, 1]$$. The `observation_model` block is optional: when absent, the pathogen has no structured observation pathway.

### 7.6 Clinical Presentation Metadata

Each pathogen profile carries a `clinical_presentation` block defining:

- **Syndromes**: `["gastrointestinal"]` for norwalk, `["respiratory"]` for SARS-CoV-2
- **Sample types**: `["stool"]` for norwalk, `["np_swab"]` for SARS-CoV-2
- **Phases**: Time-dependent clinical feature phases (e.g., acute → resolving) with feature lists

These metadata are consumed by the diagnostic cascade, not by the within-host model itself.

---

## 8. Optional Tissue Tropism

> **STATUS: OPTIONAL EXTENSION — not implemented in SHA d557f39. Default-off.**

### 8.1 Current State

The code audit confirmed that **no tissue compartments exist** in the current model. The `compartment` keyword appears only in the spatial/architectural sense (ship zones). Infection is a scalar per-pathogen state on a whole-agent. The `microflora_disruption` system tracks disruption magnitude by kingdom but does not partition infection into anatomical sites.

### 8.2 Design Decision: Shipped Pathogens and Tropism

The v1.0-draft TODO-4 asked which shipped pathogens require dual-tropism modeling. **Decision: no shipped pathogens require explicit tissue tropism in v2.0.**

- **Norovirus** (`norwalk_gi`): Has both fecal-oral and vomitus-aerosol transmission routes. These are adequately handled by `transmission_route_weights` (fomite 0.30 + food_contamination 0.20 for enteric; droplet 0.10 + hvac_airborne 0.05 for vomitus-aerosol). Separate tissue compartments would add complexity without improving epidemiological fidelity at the shipping-population scale.
- **SARS-CoV-2** (`sars_cov2_resp`): Single primary tropism (respiratory). No dual-tissue modeling needed.

### 8.3 Design Intent

If tissue tropism were implemented in a future version, it would:

1. **Tag each infection** with a primary tissue/portal (e.g., `respiratory`, `gastrointestinal`, `systemic`).
2. **Route-specific shedding**: Different shedding curves per tissue.
3. **Portal-specific establishment**: Different dose-response parameters per entry portal.
4. **Clinical presentation**: Tissue-specific symptom profiles.

### 8.4 Minimal Extension Schema

```yaml
tissue_tropism:                        # OPTIONAL block on PathogenProfile
  enabled: false                       # DEFAULT: false. Must be explicitly true.
  portals:
    - portal_id: "gastrointestinal"
      dose_response: {model: "beta_poisson", alpha: 0.111, beta: 32.81}
      shedding_curve_log10: [7.75, 9.0, ...]
      shedding_routes: ["fomite", "food_contamination"]
    - portal_id: "respiratory"
      dose_response: {model: "exponential", k: 0.01}
      shedding_curve_log10: [5.0, 6.0, ...]
      shedding_routes: ["droplet", "hvac_airborne"]
```

### 8.5 Default-Off Migration Gate

When `tissue_tropism` is absent or `tissue_tropism.enabled = false`, the model MUST reproduce the scalar per-pathogen behavior exactly. This is tested by acceptance test TRP-01 (§13).

### 8.6 Evidence Grade

**D (modeling/expert consensus)**: Limited empirical data for optimal tissue compartmentalization in ABM context. The within-host literature review rates tissue tropism at Evidence Grade C–D.

---

## 9. Timestep Invariance

### 9.1 Principle

All transition probabilities and rate-based quantities MUST use exact exponential forms that are invariant to the choice of epoch duration $$dt$$. No within-host quantity may use a naked epoch counter or raw `* 24` conversion outside of `SimClock`.

### 9.2 Required Forms

#### 9.2.1 Transition Probabilities (Hazard-Based)

For any per-day rate $$\lambda$$:

$$
P(\text{event in one epoch}) = 1 - \exp(-\lambda \cdot dt)
$$

**Implemented via**: `SimClock.probability_per_epoch(p_per_day)` which computes $$1 - (1 - p)^{dt}$$ for probability-parameterized inputs. For rate-parameterized inputs, use direct `exp(-rate * dt)`.

> **Implementation note:** `probability_per_epoch` takes a **per-day probability** (not a rate) and converts using $$1 - (1-p)^{dt}$$. This is the discrete-time complement formula, which is equivalent to $$1 - \exp(-\lambda \cdot dt)$$ when $$p = 1 - e^{-\lambda}$$. The dose-response hazard uses the rate form directly: `1 - exp(-r * dose)`.

#### 9.2.2 Competing Hazards

When multiple mutually exclusive outcomes have rates $$\lambda_1, \lambda_2, \ldots, \lambda_k$$:

$$
P(\text{any event}) = 1 - \exp\Bigl(-\sum_{j=1}^{k} \lambda_j \cdot dt\Bigr)
$$

Conditional on an event occurring, the probability it is outcome $$j$$:

$$
P(j \mid \text{event}) = \frac{\lambda_j}{\sum_{j'} \lambda_{j'}}
$$

#### 9.2.3 Cumulative Quantities

Dose accumulation with clearance uses dt-scaled decay:

$$
C(t + dt) = \bigl[C(t) + D^{\text{eff}}(t)\bigr] \cdot \exp(-\lambda_{\text{clear}} \cdot dt)
$$

Shedding emission per epoch:

$$
\sigma_{\text{epoch}} = \sigma_{\text{day}} \cdot dt
$$

**Implemented via**: `SimClock.amount_per_epoch(amount_per_day)`.

#### 9.2.4 Day-Boundary Events

Events that MUST occur at most once per natural-history day (e.g., illness onset draw) use `crossed_day_boundary(clock, epochs, offset)` to fire exactly once regardless of how many epochs span a day.

### 9.3 Conversion Functions (SimClock)

| Method | Input | Output | Formula |
|---|---|---|---|
| `days_elapsed(epochs)` | epoch count | days | $$\text{epochs} \cdot dt$$ |
| `day_index(epochs)` | epoch count | integer day | $$\lfloor \text{days\_elapsed} \rfloor$$ |
| `amount_per_epoch(x)` | per-day amount | per-epoch amount | $$x \cdot dt$$ |
| `probability_per_epoch(p)` | per-day probability | per-epoch probability | $$1 - (1 - p)^{dt}$$ |
| `decay_per_epoch(d)` | per-day fractional loss | per-epoch loss | $$1 - (1 - d)^{dt}$$ |
| `survival_from_half_life(h)` | half-life (hours) | per-epoch survival | $$0.5^{(\text{hours\_per\_epoch} / h)}$$ |

All methods return the input unchanged in `LEGACY_EPOCH_DAY` mode (where $$dt = 1.0$$).

### 9.4 Clock Modes

| Mode | Semantics | $$dt$$ |
|---|---|---|
| `HOURS` (production) | $$dt = \text{epoch\_duration\_hours} / 24$$ | Typically $$1/24$$ |
| `LEGACY_EPOCH_DAY` | One epoch = one natural-history day | $$1.0$$ |

All new code MUST function correctly under both modes. The clock refuses conflicting top-level and voyage `epoch_duration_hours` or `natural_history_clock` values (`sim_clock.py:102-148`).

---

## 10. Configuration Schema

### 10.1 Pathogen Profile Schema

The per-pathogen configuration is defined in `schemas/pathogen_profiles.schema.json` (166 fields, 23 required). The within-host-relevant portion is reproduced below with exact types, defaults, and constraints matching the schema at SHA d557f39:

```jsonc
{
  "pathogens": [
    {
      // ── Identity ──
      "pathogen_id": "string (REQUIRED)",
      "name": "string (REQUIRED)",
      "category": "string",
      "transmission_routes": ["string (REQUIRED, minItems 1)"],
      //   enum: direct_contact, fomite, droplet, hvac_airborne,
      //         water_aerosol, food, water, bodily_fluids

      // ── Dose Response ──
      "dose_response": {
        "model": "beta_poisson | exponential (REQUIRED)",
        "alpha": "number, exclusiveMinimum 0",  // REQUIRED when model=beta_poisson
        "beta": "number, exclusiveMinimum 0",   // REQUIRED when model=beta_poisson
        "k": "number, exclusiveMinimum 0"       // REQUIRED when model=exponential
      },

      // ── Illness ──
      "illness_probability": {
        "eta": "number > 0",
        "gamma": "number > 0"
      },

      // ── Severity ──
      "severity_model": {                        // OPTIONAL; null on sars_cov2_resp
        "states": ["string × 5 (REQUIRED)"],
        "base_probabilities": ["number[0,1] × 5 (REQUIRED)"],
        "prior": {
          "type": "dirichlet | logistic_normal | scenario_set (REQUIRED)",
          "parameters": "object (REQUIRED)"
        },
        "fatality_probability_by_severity": "array | null",
        "evidence_grade": "string"
      },

      // ── Observation ──
      "observation_model": {                     // OPTIONAL; null on sars_cov2_resp
        "system": "string (REQUIRED)",
        "syndrome_case_eligibility_by_severity": ["number[0,1] × 5 (REQUIRED)"],
        "reporting_probability_by_severity_pre_recognition": ["number[0,1] × 5 (REQUIRED)"],
        "reporting_probability_by_severity_post_recognition": ["number[0,1] × 5 (REQUIRED)"],
        "active_screening": "object | null",
        "lab_sampling_probability_by_severity": ["number[0,1] × 5"],
        "assay_sensitivity_by_time_since_infection": "any",
        "episode_reporting_window_days": "number, exclusiveMinimum 0 (REQUIRED)"
      },

      // ── Incubation ──
      "incubation": {                            // OPTIONAL; absent → use symptom_onset_day
        "distribution": "lognormal | gamma",     // Default: lognormal
        "median_days": "number, exclusiveMinimum 0 (REQUIRED)",
        "dispersion": "number, exclusiveMinimum 0",  // Default: 1.5. For lognormal: must be > 1.
        "min_days": "number >= 0",               // Default: 0.5
        "max_days": "number, exclusiveMinimum 0", // Default: 30.0. Must > min_days.
        "dose_reference_log10": "number",         // Default: 4.0
        "dose_log10_shortening": "number >= 0",   // Default: 0.0
        "dose_floor": "number, exclusiveMinimum 0, maximum 1", // Default: 0.4
        "host_factors": {
          "immunocompromised": "number, exclusiveMinimum 0",
          "prior_immunity": "number, exclusiveMinimum 0",
          "age_bands": {"<band>": "number, exclusiveMinimum 0"}
        },
        "notes": "string, minLength 1 (REQUIRED)"
      },
      "symptom_onset_day": "number >= 0",         // Legacy fallback if no incubation block

      // ── Shedding ──
      "shedding_curve_log10": ["number >= 0 × N"],
      "asymptomatic_shedding_log10": ["number >= 0 × N"],
      "dose_adjustment": "number >= 0",
      "shedding_variance_log10": "number >= 0",
      "presymptomatic_shedding_days": "number >= 0",

      // ── Recovery ──
      "recovery_day": "integer >= 0",             // Days of symptomatic duration from onset

      // ── Transmission Route Weights ──
      "transmission_route_weights": {
        "direct_contact": "number >= 0",
        "droplet": "number >= 0",
        "hvac_airborne": "number >= 0",
        "fomite": "number >= 0",
        "food_contamination": "number >= 0",
        "environmental_source": "number >= 0"
      },
      // additionalProperties: false on this object.
      // Weights typically sum to 1.0; absent → identity (all 1.0).

      // ── Environmental ──
      "surface_deposition_fraction": "number",
      "surface_decay_per_day": "number [0,1]",
      "airborne_half_life_hours": "number > 0",
      "contact_transfer_fraction": "number [0,1], default 1.0",
      "base_susceptibility": "number",
      "innate_nonsusceptible_fraction": "number",

      // ── New (§3) — not yet in schema at SHA d557f39 ──
      "inoculum_clearance_rate_per_day": "number >= 0"  // Default: 0.0
    }
  ]
}
```

### 10.2 Shipped Parameter Values

See **Appendix A** for the complete parameter tables for `norwalk_gi` and `sars_cov2_resp`, verified against `data/pathogens/active_profiles.json` at SHA d557f39.

---

## 11. Telemetry

### 11.1 Required Output Events

The ground-truth telemetry payload (one per epoch per agent) MUST include:

| Field | Level | Type | Description |
|---|---|---|---|
| `infection_state` | per-agent | `string` | `susceptible`, `infected`, `recovered`, `immune` |
| `symptom_presentation` | per-agent | `string` | `asymptomatic`, `symptomatic`, `severe` |
| `shedding_rate` | per-agent | `float` | Aggregate shedding rate this epoch |
| `pathogen_infections` | per-agent | `dict[str, dict]` | Per-pathogen infection records |
| → `status` | per-pathogen | `string` | InfectionStatus name |
| → `illness` | per-pathogen | `string` | IllnessStatus name |
| → `days_post_infection` | per-pathogen | `int \| null` | Days since establishment |
| → `days_since_symptom_onset` | per-pathogen | `int \| null` | 1-based symptom days |
| → `symptom_severity` | per-pathogen | `string` | Severity state name or empty |
| → `cumulative_exposure` | per-pathogen | `float` | Current retained inoculum (pre-establishment agents only) |
| → `acquired_particles` | per-pathogen | `float \| null` | Cumulative dose at establishment |
| → `shedding_this_epoch` | per-pathogen | `float` | Per-pathogen shedding rate |

### 11.2 Transmission Events

Each establishment produces a `TransmissionEvent`:

| Field | Type | Description |
|---|---|---|
| `epoch` | `int` | When transmission occurred |
| `pathway` | `string` | Dominant pathway (by dose contribution) |
| `source_agent_id` | `int \| None` | Source agent (if attributable) |
| `target_agent_id` | `int` | Newly infected agent |
| `zone` | `string` | Location at time of establishment |
| `dose` | `float` | Total pathway dose (before protection scaling) |
| `source_strain_id` | `string \| None` | Strain of the source agent |

### 11.3 Contact Tracing Matrix

Per-epoch tracing data including per-zone occupancy, dose breakdown by pathway and pathogen, food contamination exposures, and superinfection flag.

### 11.4 Simulation History

End-of-run summary includes:
- `infection_attack_rate_passenger` and `infection_attack_rate_crew`
- `infection_counters` per pathogen
- Per-agent final state records
- Model version and clock metadata

### 11.5 JSON Safety

All telemetry output MUST pass `json.dumps(..., allow_nan=False)`. Non-finite values (NaN, Infinity) MUST raise before writing. Physical times MUST be reconstructable from epoch indices and clock metadata.

---

## 12. Migration

### 12.1 Strategy

Migration from the current codebase to this spec is **incremental and backwards-compatible**. The five integration seams identified in the code audit provide natural insertion points:

| Seam | Current location | Replacement contract |
|---|---|---|
| **Dose delivery** | Exit of `execute_transmission()` → `agent_pathogen_doses` | No change needed; provides the input $$D_{i,p}(t)$$. |
| **Establishment** | `_establish()` in `transmission_core.py` | Replace with `challenge(dose, strain) → (bool, float)` conforming to §4. |
| **Progression** | `_advance_agent_pathogen_infections()` in `orchestrator_epoch.py` | Must emit `cleared` list for immune memory (already does). |
| **Shedding** | `get_pathogen_shedding()` in `infection_dynamics_bridge.py` | Must remain clock-scaled via `amount_per_epoch()` (already does). |
| **Immunity** | `_challenge_protection()` in `transmission_core.py` | Must remain genotype-aware; `ImmuneRecord` contract is stable. |

### 12.2 Migration Steps

1. **SPEC-CLEAR-01** (§3.6): Add `cumulative_exposure` reset on recovery. Low risk; additive change. Fixes audit finding 8.3 (MODERATE).
2. **Pre-establishment clearance** (§3): Add `inoculum_clearance_rate_per_day` parameter, defaulting to 0.0. Modify `update_cumulative_exposure` in the establishment pipeline. Zero-default preserves current behavior.
3. **Agent-level field projection** (audit finding 8.1): The per-pathogen `infections` dict is the **single source of truth**. The agent-level `infection_status` / `illness_status` / `time_infected` fields are **read-only computed projections** maintained by `_project_legacy_illness()` (`orchestrator_epoch.py:500-530`). New code MUST NOT write to agent-level infection fields directly; it MUST update the per-pathogen record and call the projection function.

> **Design decision (v1.0-draft TODO-5):** Agent-level infection fields (`infection_status`, `illness_status`, `time_infected`) are retained as **computed projections** in v2.0. They are marked `@deprecated` in documentation. Downstream consumers (VSP thresholds, telemetry, dashboards, observation engine, counter confinement) currently read these fields directly. A deprecation timeline follows:
> - **v2.0**: Fields are documented as projections, not sources of truth. New code must not write to them. `_project_legacy_illness()` remains the sole writer.
> - **v3.0 (future)**: Consumers are migrated to read from `infections[pid]` directly. Agent-level fields may be removed.

4. **Schema extension**: Add `inoculum_clearance_rate_per_day` to `pathogen_profiles.schema.json` with default 0.0.

### 12.3 Backwards Compatibility Invariants

All migrations MUST preserve:

1. Per-pathogen `infections` dict as the source of truth.
2. The legacy projection for downstream consumers (VSP thresholds, telemetry, observation engine).
3. Clock invariance for all time thresholds.
4. Deterministic reproducibility at the same seed and clock mode (unless a new stochastic draw is explicitly enabled by a non-default parameter).
5. Existing test suite passes without modification (388 focused tests at SHA d557f39).
6. RNG call order is preserved when new optional modules are absent or disabled.

---

## 13. Acceptance Tests

### 13.1 Statistical Conventions

All acceptance tests follow these conventions unless a specific test states otherwise:

1. **Deterministic tests** use relative tolerance $$10^{-10}$$ and absolute tolerance $$10^{-12}$$.
2. **Stochastic probability tests** use $$N = 100{,}000$$ agents. Pass if both (a) the analytic target lies in the two-sided Wilson 99% confidence interval and (b) absolute error ≤ 0.01.
3. **Time-to-event distribution tests** use $$N = 10{,}000$$, one-sample KS test at $$\alpha = 0.01$$, with effect-size bounds per test.
4. **Timestep equivalence tests** use two arms with independent seeds. Binary outcomes compared by two-proportion equivalence test; continuous outcomes by bootstrap CIs; event-time distributions by two-sample KS. Equivalence bounds are stated per test.
5. Fix and log: PRNG seed, code SHA, complete resolved configuration, clock mode, epoch duration, and replicate count.
6. Run statistical tests at $$\alpha = 0.01$$; within each section control the false-discovery rate at 1% by Benjamini–Hochberg. Deterministic invariants are not multiplicity-adjusted.

### 13.2 Pre-Establishment Clearance

| ID | Description | Pass criterion |
|---|---|---|
| **PEC-01** | Exact decay of retained inoculum: $$R_0 = 10^6$$, $$\mu \in \{0, 0.25, 2\}$$ day$$^{-1}$$, establishment disabled, multiple $$\Delta t$$. | At every observation, $$R(t) = R_0 e^{-\mu t}$$ within relative $$10^{-10}$$. Two clocks agree within relative $$10^{-10}$$. |
| **PEC-02** | Half-life interpretation and units: $$R_0 = 10^6$$, half-life 6 h, clocks 1 h and 0.5 h. | At 6, 12, 24 h: retained fractions are 0.5, 0.25, 0.0625 each within relative $$10^{-10}$$. |
| **PEC-03** | Competing clearance/establishment exact hazard: $$R_0 = 100$$, $$r = 0.02$$, $$\mu = 1$$, $$N = 100{,}000$$. Analytic $$P_{\text{est}} = 1 - \exp[-rR_0(1-e^{-\mu T})/\mu]$$. | Simulated fraction meets Wilson criterion and absolute error ≤ 0.01. |
| **PEC-04** | Limiting cases: $$R_0 = 0$$; $$r = 0$$; $$\mu = 0$$; $$\mu = 10^6$$; protection = 1. | Zero inoculum/rate/full-protection gives exactly zero establishment. With $$\mu = 0$$, hazard = $$rR_0T$$ within $$10^{-10}$$. |
| **PEC-05** | Portal-specific clearance isolation (when tropism enabled): two portals with different $$\mu$$. | Each portal follows its own analytic target. Swapping labels swaps results exactly. |
| **PEC-06** | Failed-challenge state cleanup: force establishment failure, advance, then reset. | Retained inoculum below $$R_0 e^{-10}$$. After reset, inoculum and hazard are exactly 0; susceptibility unchanged. |

### 13.3 Cumulative Exposure and Establishment

| ID | Description | Pass criterion |
|---|---|---|
| **CEX-01** | Repeated-dose composition: doses (3,7,11) vs bolus 21; $$N = 100{,}000$$. | Both arms match $$1 - e^{-r \sum D_i}$$ within Wilson criterion and absolute 0.01. Arm-to-arm risk difference 99% CI inside $$[-0.01, 0.01]$$. |
| **CEX-02** | Persistent beta frailty: $$\alpha = 0.111$$, $$\beta = 32.81$$; doses $$\{1, 100, 10^4\}$$; $$N = 200{,}000$$. | Matches exact beta-mixture CDF $$1 - {}_1F_1(\alpha; \alpha+\beta; -D)$$ within Wilson 99% CI and absolute 0.01. Each host has exactly one $$r$$ draw, unchanged across exposures. |
| **CEX-03** | Beta-frailty vs classic approximation consistency: 50-point log grid $$10^{-2}$$ to $$10^5$$; $$N = 200{,}000$$ per benchmark. | Implementation matches the analytic CDF declared by the specification within absolute 0.01. |
| **CEX-04** | Accumulator conservation: deterministic doses 1, 2, 4; force failure then establishment. | Pre-establishment cumulative = 7 within $$10^{-12}$$. `acquired_particles` = 7. Accumulator resets to 0. |
| **CEX-05** | Protection and superinfection scale dose, not probability: $$D = 100$$, $$r = 0.02$$, $$q = 0.4$$, $$s = 0.25$$. | Naive: $$1 - e^{-rD(1-q)}$$; resident: $$1 - e^{-rD(1-q)s}$$. Each within $$10^{-12}$$ at function level. |
| **CEX-06** | Fractionated exposure with clearance: bolus 100 vs ten doses of 10 q12h; $$\mu = 1$$. | Each arm matches its analytic risk within 0.01. With clearance, fractionated risk is strictly lower. |
| **CEX-07** | Route aggregation: doses 1, 3, 6 by three routes; force establishment. | Total dose = 10 within $$10^{-12}$$. Route ledger sums to 10. Dominant route is correct. Permutation-invariant. |
| **CEX-08** | Monotonicity and saturation: 101 doses 0–$$10^6$$ on log grid. | Probabilities in $$[0,1]$$, non-decreasing to $$10^{-12}$$, $$P(0) = 0$$ exactly, $$P(10^6) > 0.99$$. |

### 13.4 Established-Infection Clearance

| ID | Description | Pass criterion |
|---|---|---|
| **EIC-01** | Fixed recovery: incubation = 1.2 d, recovery_day = 3. Total course 4.2 d. $$\Delta t = 1/24$$. | Clearance at epoch $$\geq \lceil 4.2 \times 24 \rceil = 101$$ and ≤ 102. |
| **EIC-02** | Cumulative exposure reset on recovery (SPEC-CLEAR-01). | `cumulative_exposure[pathogen_id]` = 0.0 exactly after recovery. `dose_response_susceptibility` unchanged. |
| **EIC-03** | Co-resident strain independent clearance: Strain A at epoch 0, strain B at epoch 48. Recovery 3 d, incubation 1 d. | Strain A clears by epoch 97. Infection remains INFECTED until epoch 144. RECOVERED at 144. |
| **EIC-04** | Chronic disease recovery extension: base 3 d + extension 2 d = 5 d total recovery. | Clearance day shifts by exactly 2 days. |
| **EIC-05** | Host modifier on incubation: immunocompromised multiplier 1.5. | Median incubation shifts by factor 1.5 (within 5% of analytic, KS $$D < 0.02$$, $$N = 10{,}000$$). |
| **EIC-06** | Co-resident final-clearance rule: pathogen stays INFECTED until last lineage clears. Each cleared lineage creates exactly one `ImmuneRecord`. | Event-sequence and cardinality assertions. |
| **EIC-07** | Recovery reset and episode independence: residual exposure from prior episode is zero. New episode accumulates only new dose. | `cumulative_exposure` = 0 at recovery. New episode `acquired_particles` excludes prior exposure within $$10^{-12}$$. Permanent frailty unchanged. |

### 13.5 Shedding Correctness

| ID | Description | Pass criterion |
|---|---|---|
| **SHD-01** | Day-0 shedding: curve[0] = 7.75, adj = 4.0, multipliers = 1.0. Expected per-day: $$10^{3.75} \approx 5{,}623$$. | Computed value within 1% of expected. Per-epoch = daily × $$dt$$. |
| **SHD-02** | Presymptomatic window boundary: days_since_onset = −0.4 (inside 0.5 d window) → shedding > 0. days_since_onset = −0.6 (outside) → shedding = 0. | Exact match at boundaries. |
| **SHD-03** | Clinical-shedding orthogonality: identical burdens, one asymptomatic and four symptomatic categories. | With distinct curves: each state follows its own curve. With identical curves: all five totals equal within $$10^{-10}$$. Asymptomatic shedding > 0. |
| **SHD-04** | Integrated shedding conservation: 3.25 d infection, multiple $$\Delta t$$. | Sum equals exact piecewise integral within relative $$10^{-8}$$. No emission after clearance. |
| **SHD-05** | Host shedding-variance distribution: `shedding_variance_log10 = 0.5`, $$N = 20{,}000$$. $$X = \log_{10}(\text{multiplier})$$. | Mean of $$X$$ within 0.02 of 0; SD within 5% of 0.5. Multiplier persistent across episode. KS $$D < 0.02$$. |
| **SHD-06** | Co-resident partition conservation: two strains, inocula 30 and 70. | Shares 0.3 and 0.7 within $$10^{-12}$$, sum to 1. Total equals single-strain total within $$10^{-12}$$. Permutation-invariant. |
| **SHD-07** | Clock scaling: curve [2, 3, 4], clocks 24 h, 1 h, 0.5 h. | Integrated emission on each natural-history day identical within $$10^{-10}$$ across clocks. |

### 13.6 Clinical Presentation

| ID | Description | Pass criterion |
|---|---|---|
| **CLN-01** | Dose-to-illness probability: dose $$D \in \{0, 1, 100, 10^4\}$$, $$\eta = 0.508$$, $$\gamma = 0.095$$, $$N = 100{,}000$$. | Matches $$1 - (1 + \eta D)^{-\gamma}$$ by Wilson criterion and absolute ≤ 0.01. Non-decreasing. |
| **CLN-02** | Five-state categorical calibration: base probabilities $$(0.3, 0.1, 0.3, 0.2, 0.1)$$, $$N = 100{,}000$$. | Each proportion within 0.01 of target. Multinomial $$p > 0.01$$. Exactly one category per infection. |
| **CLN-03** | Symptomatic severity renormalization: base $$(0.4, 0.1, 0.2, 0.2, 0.1)$$, $$N = 100{,}000$$ symptomatic. | No asymptomatic draw. Proportions match $$(1/6, 2/6, 2/6, 1/6)$$ within 0.01. Multinomial $$p > 0.01$$. |
| **CLN-04** | Onset and clearance clocks: fixed onset 1.25 d, duration 3 d, $$\Delta t = 1$$ h. | Symptom draw at first epoch crossing 1.25 d. Clearance at 4.25 d with error < $$\Delta t$$. |
| **CLN-05** | Presentation does not control infectiousness: 50% asymptomatic with nonzero curve. | ≥ 99% of asymptomatic hosts emit > 0. Toggling clinical label does not change burden. |
| **CLN-06** | Observation monotonicity: severity-conditioned reporting affects observation, not biology. $$N = 50{,}000$$. | Reporting fractions non-decreasing. Burden, clearance, shedding unchanged across severity categories. |

### 13.7 Tissue Tropism (Conditional)

| ID | Description | Pass criterion |
|---|---|---|
| **TRP-01** | Disabled-module scalar equivalence: absent/disabled tropism reproduces scalar model. | Serialized state identical after removing additive null fields. Stochastic results bit-for-bit equal under same RNG. |
| **TRP-02** | Route-to-portal mapping (when enabled): inject dose by each route separately. | 100% appears in configured portal, 0 in others. Invalid routes fail validation. |
| **TRP-03** | Deposition-fraction conservation (when enabled). | Portal amounts sum correctly. Total retained + discarded = input within $$10^{-12}$$. |
| **TRP-04** | Independent portal decay (when enabled): different clearance rates per tissue. | Each portal matches own analytic trajectory. Changing one leaves others unchanged. |
| **TRP-05** | Competing portal establishment attribution (when enabled): $$\lambda_1 = 0.3$$, $$\lambda_2 = 0.1$$, $$N = 50{,}000$$. | Mean time within 5% of $$1/0.4$$. Attribution proportions within 0.01 of 0.75/0.25. |

### 13.8 Timestep Invariance

| ID | Description | Pass criterion |
|---|---|---|
| **DTI-01** | Deterministic state refinement: scripted exposure, $$\Delta t = 1, 0.5, 0.25$$ h. | Common-time retained inoculum and burden differ by relative < $$10^{-8}$$. Integrated shedding differs by relative < $$10^{-8}$$. |
| **DTI-02** | Establishment probability refinement: $$\Delta t = 1$$ h and 0.5 h, $$N = 100{,}000$$. | Risk difference 99% CI in $$[-0.01, 0.01]$$. Each arm matches analytic target within 0.01. |
| **DTI-03** | Clearance distribution refinement: $$N = 10{,}000$$, 1 h and 0.5 h. | Mean clearance time difference < 2%. Two-sample KS $$D < 0.02$$. |
| **DTI-04** | Full pipeline joint outcome: $$N = 20{,}000$$, 1 h and 0.5 h. | Establishment and symptomatic fraction differences ≤ 0.01. Mean clearance and shedding differ ≤ 3%. |
| **DTI-05** | Non-grid-aligned event boundaries: events at 1.2, 1.25, 1.9 d. | Event occurs in first epoch crossing scheduled time. Error in $$[0, \Delta t)$$. Errors shrink under refinement. |
| **DTI-06** | No naked epoch constants: static scan of new modules. | No arithmetic literal 24/168 or raw `*_day * 24` conversion outside `SimClock`. Zero unallowlisted findings. |

### 13.9 Configuration Validation

| ID | Description | Pass criterion |
|---|---|---|
| **CFG-01** | Valid minimal and maximal profiles. | Both validate with zero errors. Round-trip serialization valid. |
| **CFG-02** | Rate, duration, fraction bounds: negative, zero, NaN, Infinity, `max_days ≤ min_days`. | All invalid cases fail with field-path error. Adjacent valid boundary cases pass. |
| **CFG-03** | Dose-response discriminated union: beta-Poisson without $$\alpha$$; exponential without $$k$$; unknown model. | Every incomplete/unknown case fails. Complete cases pass. |
| **CFG-04** | Severity simplex: sum to 1 within $$10^{-8}$$. Duplicate/reordered/negative states. | Canonical simplex passes. Each malformed case fails. |
| **CFG-05** | Observation vector pairing: missing block, wrong length, values outside $$[0,1]$$. | All malformed cases fail with specific error. Valid paired blocks pass. |
| **CFG-06** | Clock conflict: differing top-level and voyage clocks; zero/negative epoch duration. | Every conflict fails before agent creation. Matching values pass. |
| **CFG-07** | Unknown keys and retired fields. | Unknown keys fail. Retired-only fields emit `DeprecationWarning` and map correctly. Old+new conflict fails. |
| **CFG-08** | Shipped-profile validation: every pathogen in `active_profiles.json`. | Zero errors. Unique IDs. All shedding arrays non-empty. |

### 13.10 Telemetry Output

| ID | Description | Pass criterion |
|---|---|---|
| **TEL-01** | Per-pathogen state completeness: one agent in each lifecycle state. | Every required key present. Schema validation passes. |
| **TEL-02** | Aggregate/per-pathogen reconciliation. | Agent aggregate state matches documented projection. Total shedding = sum of per-pathogen within 0.01. |
| **TEL-03** | Exposure and establishment event ledger: multi-route challenge. | Event contains all required fields. Route sums reconcile within $$10^{-8}$$. Exactly one establishment event per founding episode. |
| **TEL-04** | Clearance and clinical event timing. | Each transition emits exactly one event. Timestamps non-decreasing. No shedding after clearance. |
| **TEL-05** | JSON safety: `json.dumps(..., allow_nan=False)` passes. Non-finite input raises. | Strict round-trip. Zero non-standard JSON tokens. |
| **TEL-06** | Clock metadata: run metadata contains epoch duration, clock mode, and rate/amount units. | Physical times reconstructed from telemetry match internal within $$10^{-12}$$ days. |

### 13.11 Migration and Backward Compatibility

| ID | Description | Pass criterion |
|---|---|---|
| **MIG-01** | Default-off golden equivalence: baseline vs candidate with new blocks absent/disabled. | Deterministic fixtures bit-for-bit equal. Stochastic: attack rate ±0.01, peak prevalence ±0.01, peak timing ±1 epoch. |
| **MIG-02** | Per-pathogen source of truth: zero new writes to legacy fields outside projection allowlist. | All aggregate fields equal documented projection. Static AST scan clean. |
| **MIG-03** | Current establishment seam: `TransmissionCore.execute_transmission()` with known doses. | Adapter preserves establishment, acquired particles, strain ID, source agent, dominant pathway, dose ledger. |
| **MIG-04** | Progression and immune-memory: named lineage through clearance with `StrainRegistry`. | Exact cleared lineage IDs, one `ImmuneRecord` per cleared lineage, episode active until last lineage clears. |
| **MIG-05** | Shedding seam: daily trajectory through new model and current transmission at 1 h clock. | `get_pathogen_shedding()` adapter equals new model within $$10^{-12}$$. Mass ledger reconciles within $$10^{-8}$$. |
| **MIG-06** | Cumulative-state reset fix: accumulate, recover, reopen susceptibility. | `cumulative_exposure` = 0 at recovery. `dose_response_susceptibility` unchanged. New episode excludes prior dose within $$10^{-12}$$. |
| **MIG-07** | Legacy telemetry consumer compatibility. | Existing counters and VSP eligibility equal per-pathogen truth at every epoch. Legacy keys retain type and meaning. |
| **MIG-08** | RNG-stream isolation: disabled modules consume zero draws. | Event sequence and random outcomes bit-for-bit identical with modules absent vs disabled. |
| **MIG-09** | Production smoke and performance guard: standard short scenario. | Zero exceptions. Disabled candidate runtime ≤ 115% of baseline. Enabled ≤ 150% of baseline. |

### 13.12 Release Gates

**Pull-request gate:** All deterministic tests; stochastic unit tests CEX-01/02, EIC-01, SHD-05, CLN-01/02/03, DTI-02/03 at stated sample sizes; all schema tests; TEL-01 through TEL-06; MIG-01 through MIG-08.

**Nightly/full acceptance gate:** Every test, including all supported distribution families, all shipped profiles, 100-seed migration regression, complete timestep matrix, and performance guard.

**Failure interpretation:**
- A failed analytic identity is a correctness failure, not a calibration issue.
- A confidence interval outside an equivalence margin is a timestep/migration failure even if a null-hypothesis test has $$p > 0.01$$.
- A statistically significant but practically tiny difference inside the stated equivalence bound passes.
- A production profile that lacks an optional block may pass only through a documented fallback/default-off path.
- Tests for unsupported optional features are reported as **not applicable**, never silently skipped.

---

## 14. Appendices

### Appendix A: Shipped Pathogen Parameter Tables

All values verified against `data/pathogens/active_profiles.json` at SHA d557f39.

#### A.1 norwalk_gi (Norovirus GII.4)

| Parameter | Value | Source |
|---|---|---|
| `pathogen_id` | `norwalk_gi` | — |
| `name` | Norwalk Virus (Norovirus GII.4) | — |
| `category` | `enteric_viral` | — |
| `transmission_routes` | `[direct_contact, fomite, droplet, hvac_airborne, food]` | — |
| `dose_response.model` | `beta_poisson` | Teunis et al. 2008 |
| `dose_response.alpha` | 0.111 | Person.java |
| `dose_response.beta` | 32.81 | Person.java |
| `illness_probability.eta` | 0.508 | Person.java |
| `illness_probability.gamma` | 0.095 | Person.java |
| `incubation.distribution` | `lognormal` | Lee et al. 2013 |
| `incubation.median_days` | 1.2 | Lee et al. 2013 (GII pooled) |
| `incubation.dispersion` (GSD) | 1.56 | Lee et al. 2013 |
| `incubation.min_days` | 0.1 | — |
| `incubation.max_days` | 6.0 | — |
| `incubation.dose_reference_log10` | 4.23 | Beta-Poisson $$N_{50}$$, model units |
| `incubation.dose_log10_shortening` | 0.12 | ctb_incubation_spec |
| `incubation.dose_floor` | 0.3 | ctb_incubation_spec |
| `recovery_day` | 3 (days from onset) | Person.java |
| `shedding_variance_log10` | 1.0 | — |
| `presymptomatic_shedding_days` | 0.5 | Atmar et al. 2008 |
| `dose_adjustment` | 4.0 | Person.java |
| `shedding_curve_log10` | `[7.75, 9.0, 11.0, 11.0, 11.0, 10.0, 10.0, 9.5, 9.0, 9.0, 8.0, 8.0, 8.0, 8.0, 8.0]` | — |
| `asymptomatic_shedding_log10` | `[7.75, 9.5, 10.5, 10.0, 9.0, 8.0, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75, 7.75]` | — |
| `severity_model.states` | `[asymptomatic, subclinical, mild, moderate, severe_critical]` | — |
| `severity_model.base_probabilities` | `[0.25, 0.55, 0.19, 0.009, 0.001]` | — |
| `severity_model.prior` | Dirichlet, concentration 80 | — |
| `severity_model.evidence_grade` | `M/A` | — |
| `observation_model.system` | `VSP_AGE` | — |
| `observation_model.syndrome_case_eligibility_by_severity` | `[0, 0.55, 0.98, 1, 1]` | — |
| `observation_model.reporting_probability_by_severity_pre_recognition` | `[0, 0.45, 0.7, 0.94, 1]` | — |
| `observation_model.reporting_probability_by_severity_post_recognition` | `[0, 0.5, 0.76, 0.96, 1]` | — |
| `observation_model.lab_sampling_probability_by_severity` | `[0, 0.05, 0.2, 0.6, 0.9]` | — |
| `observation_model.episode_reporting_window_days` | 2.0 | — |
| `transmission_route_weights` | `{direct_contact: 0.35, droplet: 0.10, hvac_airborne: 0.05, fomite: 0.30, food_contamination: 0.20, environmental_source: 0.00}` | — |
| `surface_deposition_fraction` | 0.0001 | ViralParticle.java |
| `surface_decay_per_day` | 0.25 | — |
| `airborne_half_life_hours` | 1.1 | van Doremalen et al. 2020 |
| `base_susceptibility` | 1.0 | — |
| `innate_nonsusceptible_fraction` | 0.0 | — |

#### A.2 sars_cov2_resp (SARS-CoV-2 Respiratory)

| Parameter | Value | Source |
|---|---|---|
| `pathogen_id` | `sars_cov2_resp` | — |
| `name` | SARS-CoV-2 (Respiratory) | — |
| `category` | `respiratory_viral` | — |
| `transmission_routes` | `[droplet, hvac_airborne, direct_contact, fomite]` | — |
| `dose_response.model` | `beta_poisson` | — |
| `dose_response.alpha` | 0.18 | — |
| `dose_response.beta` | 58.0 | — |
| `illness_probability.eta` | 0.4 | — |
| `illness_probability.gamma` | 0.12 | — |
| `incubation.distribution` | `lognormal` | Wei et al. 2021 |
| `incubation.median_days` | 5.8 | Wei et al. 2021 (ancestral) |
| `incubation.dispersion` (GSD) | 1.57 | Wei et al. 2021 |
| `incubation.min_days` | 0.5 | — |
| `incubation.max_days` | 21.0 | — |
| `incubation.dose_reference_log10` | 3.43 | Beta-Poisson $$N_{50}$$, model units |
| `incubation.dose_log10_shortening` | 0.15 | ctb_incubation_spec |
| `incubation.dose_floor` | 0.3 | ctb_incubation_spec |
| `recovery_day` | 7 (days from onset) | — |
| `shedding_variance_log10` | 1.2 | — |
| `presymptomatic_shedding_days` | 2.0 | He et al. 2020 |
| `dose_adjustment` | 3.0 | — |
| `shedding_curve_log10` | `[3.0, 5.0, 7.0, 8.5, 9.0, 8.5, 7.5, 6.5, 5.5, 4.5, 3.5, 3.0, 2.5, 2.0, 2.0]` | — |
| `asymptomatic_shedding_log10` | `[3.0, 4.5, 6.0, 7.0, 7.5, 7.0, 6.0, 5.0, 4.0, 3.5, 3.0, 2.5, 2.0, 2.0, 2.0]` | — |
| `severity_model` | `null` (absent) | audit finding 8.6 |
| `observation_model` | `null` (absent) | audit finding 8.6 |
| `transmission_route_weights` | `{direct_contact: 0.25, droplet: 0.30, hvac_airborne: 0.30, fomite: 0.10, food_contamination: 0.00, environmental_source: 0.05}` | — |
| `surface_deposition_fraction` | 5e-05 | — |
| `surface_decay_per_day` | 0.95 | — |
| `airborne_half_life_hours` | 1.1 | van Doremalen et al. 2020 |
| `base_susceptibility` | 1.0 | — |
| `innate_nonsusceptible_fraction` | 0.0 | — |

### Appendix B: Glossary

| Term | Definition |
|---|---|
| **Agent** | One simulated individual (passenger or crew member) on the vessel. |
| **Epoch** | One discrete simulation timestep. Duration configured by `epoch_duration_hours` (default 1 hour). |
| **Establishment** | The stochastic event when delivered pathogen particles successfully initiate a replicating infection. |
| **Inoculum** | The viable pathogen particles delivered to a host in one or more exposure events. |
| **Natural-history day** | One day of biological time. Maps to $$24 / \text{epoch\_duration\_hours}$$ epochs. |
| **Onset** | The epoch at which symptoms first appear (drawn or virtual). |
| **Shedding curve** | Per-pathogen lookup table giving $$\log_{10}$$ shedding rate indexed by days since onset. |
| **Superinfection** | Establishment of a second strain of the same pathogen in an already-infected host. |
| **VSP** | CDC Vessel Sanitation Program; the surveillance system modeled for cruise-ship AGE outbreaks. |
| **Beta-frailty model** | The persistent-susceptibility dose-response implementation: $$r \sim \text{Beta}(\alpha, \beta)$$ drawn once per host per pathogen. Distinct from the classic approximate beta-Poisson CDF. |
| **Projection** | A computed summary of per-pathogen state written to agent-level fields for legacy consumers. Not a source of truth. |

---

## 15. Changelog: v1.0-draft to v2.0

### TODO Resolutions

| ID | Section | Resolution |
|---|---|---|
| TODO-1 | §3.6 | **Resolved:** Exponential decay via `inoculum_clearance_rate_per_day` (§3.2) naturally eliminates stale dose without a separate timeout. SPEC-CLEAR-01 reset on recovery handles the edge case. No additional "no-dose window" parameter needed. |
| TODO-2 | §5.5 | **Resolved:** Retain fixed `recovery_day` in v2.0. Future extension path defined for optional `recovery_distribution` block (§5.5). |
| TODO-3 | §6.7 | **Resolved:** Route-specific shedding curves are out of scope for v2.0. The existing scalar shedding + `transmission_route_weights` architecture is sufficient for shipped pathogens (§6.7). |
| TODO-4 | §8.2 | **Resolved:** No shipped pathogens require explicit tissue tropism. Norovirus dual transmission is handled by route weights. Tissue tropism remains optional and default-off (§8.2). |
| TODO-5 | §12.2 | **Resolved:** Agent-level infection fields retained as computed projections via `_project_legacy_illness()`. Marked deprecated with v3.0 removal timeline (§12.2). |

### Parameter and Schema Corrections

| Change | Section | Detail |
|---|---|---|
| Fixed `transmission_route_weights` key names | §6.7 | v1 used `food`; actual key is `food_contamination`. Added `environmental_source`. Updated table to match `pathogen_profiles.schema.json` exactly. |
| Added SARS-CoV-2 `environmental_source` weight | §6.7, A.2 | v1 showed only 5 routes; actual profile has 6 including `environmental_source: 0.05`. |
| Clarified `eta`/`gamma` range | §7.2 | v1 implied $$[0,1]$$; both parameters are positive reals (not probabilities). |
| Added `dose_response.k` default | §4.3.2 | Code default is 0.01 when `k` omitted from exponential model. |
| Corrected `dose_floor` default | §5.2.2 | Code default (`MIN_DOSE_FACTOR`) = 0.4; shipped profiles use 0.3. Both values documented. |
| Added shedding curves to Appendix A | A.1, A.2 | v1 omitted the actual curve values. Added complete 15-entry curves from `active_profiles.json`. |
| Added observation model values to Appendix A | A.1 | v1 omitted shipped observation model arrays. Added complete values. |
| Noted `severity_model`/`observation_model` null for SARS-CoV-2 | A.2 | Explicit documentation of audit finding 8.6. |
| Added `contact_transfer_fraction` | §10.1 | Schema-defined field with default 1.0. Omitted in v1. |

### Mathematical Clarifications

| Change | Section | Detail |
|---|---|---|
| Distinguished per-host hazard from population CDF | §4.3.1 | v1 ambiguously described "the Beta-Poisson model." v2 explicitly separates the per-host `1 - exp(-r * dose)` from the population-level $$1 - {}_1F_1$$ and the classic approximation $$1 - (1+D/\beta)^{-\alpha}$$. |
| Clarified dose used in establishment draw | §4.4 | v1 was ambiguous. v2 explicitly states: per-epoch establishment probability uses THIS epoch's effective dose. Cumulative dose is bookkeeping for `acquired_particles`. |
| Added `expm1` implementation note | §4.6 | Pseudocode uses `math.expm1` for numerical precision at small doses. |
| Corrected transition probability formula attribution | §9.2.1 | v1 conflated `probability_per_epoch` with rate-based formulas. v2 distinguishes probability-parameterized and rate-parameterized inputs. |

### Structural Changes

| Change | Section | Detail |
|---|---|---|
| Added §2.2 Note on route enum vs weight keys | §2.2 | Explicit documentation that `transmission_routes` enum and `transmission_route_weights` keys differ. |
| Added §5.3.3 Recovery Side Effects | §5.3.3 | Explicit enumeration of what happens at recovery, including SPEC-CLEAR-01. |
| Expanded §10.1 schema | §10.1 | Added `transmission_route_weights` structure with `additionalProperties: false`. Added `contact_transfer_fraction`. Corrected constraint annotations to match `pathogen_profiles.schema.json`. |
| Added §11.5 JSON Safety | §11.5 | Explicit NaN/Infinity rejection requirement. |
| Added per-pathogen telemetry fields | §11.1 | Added `cumulative_exposure`, `acquired_particles`, `shedding_this_epoch` to required telemetry. |
| Expanded §12.3 Backwards Compatibility | §12.3 | Added RNG isolation invariant and deterministic reproducibility constraint. |
| Replaced Appendix C (TODOs) | §15 | Appendix C eliminated. All open questions resolved. Replaced by this changelog. |

### Acceptance Test Integration

| Change | Section | Detail |
|---|---|---|
| Integrated 76 acceptance tests | §13 | Tests from `/workspace/acceptance_tests.md` reorganized into 11 sections matching spec structure. Test IDs standardized. Statistical conventions consolidated into §13.1. |
| Added release gates | §13.12 | PR-gate and nightly-gate test selections defined. Failure interpretation rules specified. |

---

*End of specification.*
