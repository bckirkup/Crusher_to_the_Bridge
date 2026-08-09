# Campaign Analysis Bundle and Stan Calibration Layer — Spec v1

## Purpose

Add an adjacent analysis toolchain to Crusher to the Bridge (CTB) that converts
campaign outputs into standardized statistical datasets and fits Bayesian
trajectory-level models using Stan.

This is **not** a replacement for the agent-based model (ABM). The ABM remains
the mechanistic simulator. Stan consumes ABM outputs as data and estimates
posterior distributions for latent growth, platform effects, dose-response
uncertainty, intervention timing, and VSP threshold compression.

## Rationale

Recent critique identified a valid vulnerability: point calibration of
`dose_adj=10.6` and isolated one-factor sweeps do not fully address parameter
non-identifiability. The correct next step is to treat large campaign outputs
as structured observations and fit a Bayesian model to the full time series,
not just final attack rates.

The key scientific questions are:

1. What posterior distribution over norovirus `dose_adj` is compatible with
   observed VSP-like attack rates?
2. How much platform-specific latent epidemic potential remains after
   accounting for VSP response?
3. How much does the VSP threshold compress epidemic curves?
4. Do advanced surveillance modalities shift detection earlier even when final
   attack rate barely changes?
5. Which parameters are identifiable from available campaign outputs?

## Directory Structure

Add a new adjacent package:

```text
picard_framework/analysis/
  __init__.py
  campaign_bundle.py          # creates standardized analysis bundle
  parse_run_id.py             # factor parser for run IDs + campaign params
  metrics.py                  # derived scalar metrics (incl. coerce_bool)
  pairwise.py                 # native vs CONTAM / baseline vs intervention deltas
  figures.py                  # standard plots
  report.py                   # HTML/Markdown report generation
  stan/
    _data.py                  # shared outbreak/trajectory data builders
    norovirus_outbreak.stan   # Stage A: P(outbreak)
    norovirus_trajectory.stan # Stage B: trajectory | outbreak (reduce_sum)
    fit_norovirus_outbreak.py
    fit_norovirus_trajectory.py
    fit_norovirus_hurdle.py   # runs Stage A then Stage B
    posterior_summaries.py
    README.md
```

CLI entry points:

```text
python -m picard_framework.analysis.campaign_bundle RESULTS_DIR --out analysis/
python -m picard_framework.analysis.stan.fit_norovirus_hurdle analysis/ --out-dir hurdle_fit/
python -m picard_framework.analysis.stan.fit_norovirus_outbreak analysis/ --out stan_fit_outbreak/
python -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit_trajectory/
python -m picard_framework.analysis.report analysis/ stan_fit_trajectory/ --out report.html
python scripts/build_stan_step2_bundle.py   # merge C12c + C14/C14b bundles
```

## Campaign Analysis Bundle

### Input

A directory of zipped campaign outputs:

```text
<run_id>.zip
  timeseries.json
  summary.json
  run_spec.json
```

### Output

```text
analysis/
  run_summary.csv
  epoch_timeseries.parquet
  epoch_timeseries.csv.gz     # fallback if pyarrow unavailable
  pairwise_deltas.csv         # optional, if paired engines or baselines present
  factor_dictionary.json
  aggregate_metrics.json
  figures/
    dose_response.png
    surveillance_heatmap.png
    vsp_threshold_sweep.png
    epidemic_curves.png
    pairwise_exact_match.png
  report.html
```

### `run_summary.csv`

One row per run.

Required columns:

```text
run_id
campaign
platform_id
platform_class
pathogen
pathogen_id
dose_adjustment
density_exponent
immunity_fraction
surveillance_strategy
transport_engine
seed
num_agents
num_epochs
attack_rate
outbreak_occurred              # takeoff vs fizzle (see epidemic_labels)
peak_prevalence
peak_epoch
detection_epoch
confirmation_epoch
detection_lag
total_quarantine_person_epochs
r_effective_at_peak
final_susceptible_fraction
cumulative_cost_usd
cumulative_ois
```

Optional columns parsed when available:

```text
vsp_suspect_threshold
vsp_confirm_threshold
vsp_lockdown_threshold
sick_call_probability
detection_delay_epochs
isolation_compliance
wearable_profile
wastewater_enabled
cascade_enabled
multiplex_enabled
contam_paired_run_id
native_paired_run_id
```

### `epoch_timeseries.parquet`

One row per `(run_id, epoch)`.

Required columns:

```text
run_id
epoch
susceptible
infected
symptomatic
recovered
immune
quarantined
isolated
new_infections
total_pathogen_mass
n_zones_contaminated
max_concentration
max_conc_zone
trigger_status
cumulative_cost_usd
cumulative_ois
```

Joined run factors from `run_summary.csv` should be included or joinable by
`run_id`.

### Pairwise comparison module

Canonical comparisons:

1. `native` vs `contamx`
2. `none_true` vs `syndromic`
3. `syndromic` vs `cascade`
4. `cascade` vs `cascade_mpx`
5. `cascade` vs wearable/wastewater variants

Comparison hierarchy:

1. First compare per-seed, per-epoch trajectories.
2. Then compare run-level scalar summaries.
3. Only then compare aggregate means.

This prevents hiding differences behind mean trajectories.

Outputs:

```text
pairwise_deltas.csv
  comparison_id
  run_id_a
  run_id_b
  platform_id
  pathogen
  dose_adjustment
  seed
  epoch_match_rate_infected
  epoch_match_rate_recovered
  epoch_match_rate_new_infections
  max_abs_delta_infected
  max_abs_delta_recovered
  delta_attack_rate
  delta_peak_prevalence
  delta_peak_epoch
  delta_detection_epoch
  delta_total_quarantine_person_epochs
  mass_ratio_median
  mass_ratio_iqr_low
  mass_ratio_iqr_high
```

## Stan Calibration Layer

### Phase 1b hurdle (engineering default; see lessons)

Zero-heavy campaign outputs motivate a two-stage model:

1. **Stage A** (`norovirus_outbreak.stan`) — Bernoulli-logit on
   **takeoff vs fizzle** (`outbreak_occurred`: VSP fires while incidence is
   still accelerating — `Δ²incidence >= 0` at first SUSPECTED/CONFIRMED;
   otherwise fizzle, including late VSP on a decelerating curve).
2. **Stage B** (`norovirus_trajectory.stan`) — NegBin2 incidence
   **conditional on outbreak**, with `reduce_sum` (no `N×T` transformed
   `log_lambda`) and slim generated quantities (no `y_rep[N,T]`;
   `pred_attack_rate` + `ppc_new_inf_mean` only).

Orchestrator: `python -m picard_framework.analysis.stan.fit_norovirus_hurdle`.

**Field note:** first full-scale Stage A fits used the legacy `ever_infected > 2`
label and diverged heavily. The label is now **VSP + curvature takeoff vs
fizzle** (see `simulation_utils.epidemic_labels`). Re-bundle before re-fitting
Stage A.
Full narrative: [`docs/stan_hurdle_lessons.md`](stan_hurdle_lessons.md).

### Core model: `norovirus_trajectory.stan` (Stage B)

Consumes `epoch_timeseries` and `run_summary` rows for norovirus campaigns
(default: `outbreaks_only=True`).

#### Data

For each run `r` and epoch `t`:

```text
N_runs
T
N_agents[r]
platform[r]             # 1..P
surveillance[r]         # 1..S
dose_adj[r]
vsp_threshold[r]
seed[r]
infected[r,t]
symptomatic[r,t]
recovered[r,t]
new_infections[r,t]
quarantined[r,t]
trigger_state[r,t]       # 0 none, 1 suspected, 2 confirmed/lockdown
```

#### Likelihood

Model per-epoch incidence using a negative binomial observation model:

\[
y_{r,t} \sim \mathrm{NegBinomial2}(\lambda_{r,t}, \phi)
\]

where `y_{r,t} = new_infections[r,t]`.

A simple first model:

\[
\log \lambda_{r,t} =
  \alpha_{platform[r]}
  + \beta_d (d_0 - dose\_adj_r)
  + f(t)
  + \gamma_{platform[r]} g(t)
  - \delta_{surveillance[r]} I(t \ge trigger_r)
  - \eta_{vsp} I(t \ge vsp_r)
  + \log(I_{r,t-1} + 1)
\]

Interpretation:

- `alpha_platform`: latent platform epidemic potential
- `beta_d`: dose-response slope for `dose_adj` (larger dose_adj lowers shedding)
- `f(t)`: shared temporal epidemic curve component
- `gamma_platform`: platform-specific temporal deformation
- `delta_surveillance`: post-trigger intervention suppression by surveillance strategy
- `eta_vsp`: additional compression from VSP threshold response
- `phi`: overdispersion

#### Trigger model

Optionally model `trigger_state` as a discrete-time hazard:

\[
P(trigger_{r,t}=1) = \mathrm{logit}^{-1}
  (a_{surv[r]} + b_s symptomatic\_fraction_{r,t} + b_q quarantined\_fraction_{r,t})
\]

This estimates how sharply each surveillance strategy detects a growing outbreak.

For v1, this can be simplified by treating observed `trigger_epoch` as known.

#### Priors

Use weakly informative priors:

```stan
alpha_platform ~ normal(0, 2);
beta_d ~ normal(0, 1);
delta_surveillance ~ normal(0, 1);
eta_vsp ~ normal(0, 1);
phi ~ exponential(1);
```

For monotonic effects:

- `beta_d > 0` if parameterized as `d0 - dose_adj`
- `eta_vsp > 0`
- stronger surveillance effects constrained non-negative if desired

#### Outputs

Posterior summaries:

```text
posterior/dose_adj_calibration.csv
posterior/platform_effects.csv
posterior/surveillance_effects.csv
posterior/vsp_threshold_effect.csv
posterior/trigger_hazard.csv
posterior/posterior_predictive_ar.csv
posterior/ppc_curves.parquet
```

Key posterior quantities:

- P(dose_adj in [10.4, 10.8]) compatible with VSP target
- Platform latent risk ratio: expedition / mega
- VSP compression factor: uncontrolled AR / observed AR
- Surveillance marginal effect after syndromic
- Posterior predictive curves under alternative thresholds (1%, 3%, 5%, off)

## Phase 1 Implementation Scope

Phase 1 should be deliberately narrow:

1. Build campaign bundle generator.
2. Fit norovirus only.
3. Use C12c and C14 data only.
4. Treat trigger epochs as observed, not latent.
5. Fit incidence and final attack rate jointly or in two linked stages.
6. Produce posterior predictive plots for VSP threshold sweep.

Recommended first analysis dataset:

- `/workspace/c12c_campaign_results.csv` plus C12c zip timeseries
- `/workspace/c14_campaign_results.csv` plus C14 zip timeseries

## Phase 2 Extensions

1. Add respiratory pathogens.
2. Add environmental mass model for wastewater/surface/air sampling calibration.
3. Add latent trigger hazard model.
4. Add approximate Bayesian computation (ABC) option for raw ABM outputs.
5. Add global sensitivity screening (Morris/Sobol) upstream of Stan.
6. Add boundary-condition model for embarkation and turnaround interventions.
   **Status:** Phase 1 pre-boarding wearable decision model implemented as
   `picard_framework/analysis/boundary/` (see
   [preboarding_wearable_decision_model_spec.md](preboarding_wearable_decision_model_spec.md)).
   Consumes k-indexed outbreak surfaces; does not call the ABM. Turnaround
   re-embark wiring remains future work.

## Notes on What Stan Should Not Do

Stan should not:

- call the ABM inside the sampler
- simulate individual agents
- represent all transmission pathways mechanistically
- replace the campaign runner

Stan should:

- consume ABM outputs
- estimate smooth latent response surfaces
- quantify uncertainty and non-identifiability
- produce posterior predictive checks
- turn simulation ensembles into calibrated inference

## Minimal Definition of Done

A successful Phase 1 / 1b PR should:

1. Parse an arbitrary campaign zip directory into `run_summary.csv` and
   `epoch_timeseries.parquet/csv.gz`.
2. Reproduce current C12c/C14 summary metrics from the bundle
   (`outbreak_rate` must survive CSV round-trip via `coerce_bool`).
3. Fit Stage A (`norovirus_outbreak.stan`) and Stage B
   (`norovirus_trajectory.stan`, outbreaks-only by default) via the hurdle CLI.
4. Generate compact posterior predictive summaries (AR / outbreak prob;
   no full `y_rep[N,T]` dumps).
5. Report posterior platform risk ratios and VSP compression factors.
6. Include unit tests for parser, factor extraction, metric definitions, and
   Stan data builders (CmdStan smoke remains opt-in).
