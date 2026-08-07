# Stan calibration layer (Phase 1)

Bayesian trajectory model for **norovirus** campaign outputs. The ABM remains
the mechanistic simulator; Stan consumes bundle tables
(`run_summary.csv` + `epoch_timeseries.*`) and estimates posterior uncertainty
over dose response, platform effects, surveillance suppression, and VSP
compression.

## Install

```bash
pip install -e '.[analysis]'
python3 -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'
```

CmdStan is **not** required for the campaign bundle CLI or for default pytest.
Fit tests skip when CmdStan is absent.

## Fit

```bash
# 1) Build the analysis bundle from campaign zips
python3 -m picard_framework.analysis.campaign_bundle ./results/c12c/ --out analysis/

# 2) Fit norovirus trajectory model
python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit/

# 3) Report
python3 -m picard_framework.analysis.report analysis/ stan_fit/ --out report.html
```

Recommended first datasets (local, not in-repo): C12c and C14 campaign zip
directories. Point `campaign_bundle` at each results dir separately or a parent
folder that contains both.

## Model notes

- Likelihood: NegBin2 on per-epoch `new_infections`
- Triggers treated as **observed** (`trigger_state`); no latent hazard in v1
- Priors: weakly informative; `beta_d`, `eta_vsp`, `delta_surveillance` ≥ 0
- Outputs under `stan_fit/posterior/`:
  - `dose_adj_calibration.csv`
  - `platform_effects.csv` (includes expedition/mega risk ratio when both present)
  - `surveillance_effects.csv`
  - `vsp_threshold_effect.csv`
  - `posterior_predictive_ar.csv`
  - `ppc_curves.*` / `vsp_threshold_ppc_sweep.csv`

## What Stan does not do

Stan does not call the ABM, simulate agents, or replace `campaign_runner.py`.
