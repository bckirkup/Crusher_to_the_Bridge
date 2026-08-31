# CTB Incubation Period Model — Devin Implementation Brief

> **Status:** Complete — implementation brief for ../ctb_incubation_spec.md, which is implemented

## Summary

Add stochastic incubation period draws with dose-dependent shortening and
optional host frailty modifiers to the CTB simulator. All 14 pathogens
parameterized. Branch: `paper3-variant-surveillance`.

## Spec document

Full spec with all parameters, literature citations, and code snippets:
`/workspace/ctb_incubation_spec.md`

## Changes in priority order

### Change 1: Stochastic incubation distribution per pathogen

**What**: Replace fixed `symptom_onset_day` (default 1.0) with a per-infection
lognormal or gamma draw from pathogen-specific parameters.

**Where the draw happens**: At infection establishment, when dose-response
succeeds. Store the drawn value as `incubation_days` on the infection record.

**Files to modify**:
- `data/pathogens/active_profiles.json` — Add `incubation_distribution` block to `norwalk_gi` and `sars_cov2_resp`
- `data/pathogens/edison_10pathogen_profiles.json` — Add to all 10 pathogens
- `data/pathogens/enterprise_tos_profiles.json` — Add to Rigelian Fever, Psi-2000
- `data/pathogens/enterprise_tng_profiles.json` — Add to Barclay Protomorphosis, TNG Shipboard Influenza
- `schemas/pathogen_profiles.schema.json` — Validate `incubation_distribution` block
- `engines/infection_dynamics_bridge.py` — At infection establishment, draw from distribution and store as `incubation_days` on infection record
- `orchestrator_epoch.py` — Replace `float(prof.get("symptom_onset_day", ONSET_DAY))` (line 365) with `float(inf.get("incubation_days", prof.get("symptom_onset_day", ONSET_DAY)))`

**Schema for pathogen profile**:
```json
"incubation_distribution": {
  "family": "lognormal",
  "mu": 0.182,
  "sigma": 0.445,
  "unit": "days",
  "minimum": 0.1
}
```

**Parameters (all 14 pathogens)**:

| Pathogen ID | Family | Param 1 | Param 2 | Median (d) |
|---|---|---|---|---|
| norwalk_gi / norovirus_gii4 | lognormal | mu=0.182 | sigma=0.445 | 1.2 |
| sars_cov2_resp | lognormal | mu=1.758 | sigma=0.450 | 5.8 |
| influenza_a | lognormal | mu=0.336 | sigma=0.412 | 1.4 |
| measles_virus | lognormal | mu=2.526 | sigma=0.207 | 12.5 |
| legionella_pneumophila | lognormal | mu=1.723 | sigma=0.420 | 5.6 |
| vibrio_cholerae_parahaemolyticus | lognormal | mu=-0.288 | sigma=0.600 | 0.75 |
| campylobacter_jejuni | lognormal | mu=1.099 | sigma=0.400 | 3.0 |
| clostridioides_difficile | lognormal | mu=0.693 | sigma=0.500 | 2.0 |
| andes_hantavirus | lognormal | mu=2.890 | sigma=0.300 | 18.0 |
| ebola_virus | lognormal | mu=2.197 | sigma=0.340 | 9.0 |
| rigelian_fever | lognormal | mu=1.386 | sigma=0.500 | 4.0 |
| psi_2000_polywater | lognormal | mu=-0.223 | sigma=0.600 | 0.8 |
| barclay_protomorphosis | lognormal | mu=1.946 | sigma=0.350 | 7.0 |
| tng_shipboard_influenza | lognormal | mu=0.405 | sigma=0.420 | 1.5 |

**Backward compat**: When `incubation_distribution` is absent, fall back to
`symptom_onset_day` (default 1.0). Existing behavior preserved.

**Interaction with strain system**: The existing `strain_incubation_modifier`
(additive, in days) is applied AFTER the base draw, as already wired in
`orchestrator_epoch.py:366`. No change needed to the strain modifier logic.

### Change 2: Dose-dependent incubation shortening

**What**: Higher inoculum shortens the drawn incubation period.

**Key equation**:
```python
log_dose_ratio = math.log10(max(dose, 1.0) / reference_dose)
dose_modifier = max(dose_floor, 1.0 - dose_shift * log_dose_ratio)
incubation_days *= dose_modifier
```

**Files to modify**:
- `data/pathogens/*.json` — Add `incubation_dose_response` block per pathogen
- `schemas/pathogen_profiles.schema.json` — Validate new block
- `engines/infection_dynamics_bridge.py` — Apply dose modifier after incubation draw, before storing on infection record

**Schema**:
```json
"incubation_dose_response": {
  "dose_shift": 0.12,
  "dose_floor": 0.3,
  "reference_dose": 18.0
}
```

**Parameters per pathogen** (see spec for full table; key ones):

| Pathogen | dose_shift | dose_floor | reference_dose |
|---|---|---|---|
| norwalk_gi | 0.12 | 0.3 | 18.0 |
| sars_cov2_resp | 0.15 | 0.3 | 100.0 |
| influenza_a | 0.10 | 0.4 | 1000.0 |
| measles_virus | 0.05 | 0.5 | 0.2 |
| rigelian_fever | 0.15 | 0.3 | 50.0 |
| psi_2000_polywater | 0.20 | 0.2 | 10.0 |
| barclay_protomorphosis | 0.08 | 0.4 | 30.0 |
| tng_shipboard_influenza | 0.10 | 0.4 | 500.0 |
| ebola_virus | 0.15 | 0.3 | 5.0 |

**Backward compat**: When `incubation_dose_response` is absent, no adjustment.

### Change 3: Host frailty score (optional, lower priority)

**What**: A latent per-agent `frailty_score` in [0,1] that modifies severity
(strongly), wearable baselines (moderately), and incubation (weakly/not at all
by default).

**Files to modify**:
- `crusher_labs/config.yaml` — Add `host_frailty` config block
- `orchestrator_init.py` — Compute `frailty_score` per agent at initialization
- `engines/infection_dynamics_bridge.py` — Optional frailty modifier on incubation
- `engines/wearable_monitor.py` — Frailty-coupled baseline offsets in `_compute_baselines`
- `orchestrator_epoch.py` — Frailty modifier on illness probability

**Frailty score** (at agent init):
```python
A = age_risk(age)  # 0 for 20-40, rising to 1 for 80+
C = chronic_burden  # from chronic_diseases config
F = fitness_deficit  # 0=fit, 1=sedentary
S = sleep_deficit    # 0=>7h, 1=<5h
Z = 0.30*A + 0.30*C + 0.25*F + 0.15*S + Normal(0, 0.1)
frailty_score = 1 / (1 + exp(-Z))
```

**Wearable baseline offsets**:
- RHR: `+6.0 * (frailty - 0.3)` bpm
- HRV: `* (1.0 - 0.15 * max(0, frailty - 0.3))`
- Sleep: `-0.8 * max(0, frailty - 0.3)` hours

**Pre-symptomatic wearable lead** (per infection):
```python
wearable_lead_days = max(0, rng.normal(1.5, 1.0))
```
Start infection perturbation this many days before `incubation_days`.

**Default**: `host_frailty.enabled = false` (off, no effect).

## Complete incubation pipeline (at infection)

```
1. Draw T_base from incubation_distribution (lognormal or gamma)
2. Apply dose: T_dose = T_base * max(floor, 1 - shift * log10(dose/ED50))
3. Apply strain: T_strain = T_dose + strain_incubation_modifier  [existing]
4. Apply host: T_inc = T_strain * (1 + frailty_shift * (frailty - 0.5))
5. Floor at minimum (0.1 days)
6. Store T_inc on infection record as incubation_days
7. Draw wearable_lead_days for pre-symptomatic anomaly
```

## Test plan

1. **Distribution draws**: Run 1000 infections, verify drawn incubation
   distribution matches specified lognormal parameters (KS test).
2. **Dose effect**: Same pathogen at 1x, 10x, 100x dose → verify monotonic
   shortening and floor behavior.
3. **Strain modifier**: Verify additive strain shift applied correctly on top
   of stochastic draw.
4. **Backward compat**: With no `incubation_distribution`, verify behavior
   identical to current fixed-onset model.
5. **Flag-off identity**: With `host_frailty.enabled = false`, no RNG draws
   change, all existing golden tests pass.
