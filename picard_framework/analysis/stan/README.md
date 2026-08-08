# Stan calibration layer (Phase 1b — hurdle)

Two-stage Bayesian layer for **norovirus** campaign outputs:

1. **Stage A** — `norovirus_outbreak.stan`: Bernoulli-logit **P(outbreak)**
2. **Stage B** — `norovirus_trajectory.stan`: NegBin2 **trajectory | outbreak**
   with `reduce_sum` (no `N×T` transformed `log_lambda`) and slim GQ
   (no `y_rep[N,T]`; summaries only)

The ABM remains the mechanistic simulator.

## Install

```bash
pip install -e '.[analysis]'
python3 -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'
```

## Fit (recommended)

```bash
# Combined C12c + C14/C14b bundle (or any analysis/ dir with run_summary + epochs)
python3 -m picard_framework.analysis.stan.fit_norovirus_hurdle analysis/analysis_stan_norovirus \
  --out-dir analysis/analysis_stan_norovirus/hurdle_fit \
  --chains-outbreak 4 --chains-trajectory 4 \
  --iter-warmup 1000 --iter-sampling 1000 \
  --seed 1701 --d0 10.6 --vsp-ref 0.03 \
  --threads-per-chain 4 --show-progress
```

Or stages separately:

```bash
python3 -m picard_framework.analysis.stan.fit_norovirus_outbreak analysis/ --out stan_fit_outbreak/
python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit_trajectory/
```

Stage B defaults to `--outbreaks-only` (hurdle). Use `--no-outbreaks-only` for the legacy all-runs trajectory.

## Model notes

- Stage A: run-level **takeoff vs fizzle** (`outbreak_occurred`; see
  `simulation_utils.epidemic_labels`); VSP feature = threshold enabled (`< 1`)
- Stage B: observed triggers; `reduce_sum` + `threads_per_chain` for multi-core
- Outputs under each stage `posterior/`: dose, platform, surveillance, VSP, PPC tables

## Field lessons (Step-2)

First full-scale hurdle attempts on the merged C12c + C14/C14b bundle:

- Stage A (~10 min) completed but with **high divergences** — do not treat as
  monograph-grade without model changes.
- Stage B (5151 outbreaks × 168 epochs, 4×1000/1000) was still near 0–5% after
  ~5 h and was aborted.
- Labels evolved from `ever_infected > 2` → size cut → **VSP + incidence
  curvature** (takeoff only if VSP fires while still accelerating). Re-bundle
  before the next Stage A.

Full write-up: [`docs/stan_hurdle_lessons.md`](../../../docs/stan_hurdle_lessons.md).
