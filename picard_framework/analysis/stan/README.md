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

## Sentinel attribution (single ship)

`sentinel_attribution.stan` estimates a per-port introduction hazard per exposed
person-hour ashore, with an onboard baseline, renewal secondaries at strictly
positive lags, and a sampled `R_onboard` — see
[`docs/sentinel_surveillance_spec.md`](../../../docs/sentinel_surveillance_spec.md).
Exposure hours enter as offsets, so the ports are compared on a denominator
rather than on case counts.

```bash
python3 -m picard_framework.analysis.stan.fit_sentinel_attribution \
  picard_framework/analysis/sentinel/data/example_itinerary.json \
  picard_framework/analysis/sentinel/data/example_observations.json \
  --out sentinel_fit
```

Without a CmdStan toolchain the fit writes `fit_status.json` with
`"status": "skipped"`; `--smoke` instead summarizes the committed fixture
posterior so the data → posterior → `port_hazards.csv` path stays exercised.
Regenerate that fixture after any prior change:

```bash
python3 -m picard_framework.analysis.stan.fit_sentinel_attribution ... \
  --write-fixture picard_framework/analysis/sentinel/fixtures/attribution_posterior.json
```

Exit codes, because a campaign shard reads them instead of the console:

| code | meaning | statuses |
| --- | --- | --- |
| 0 | a posterior was written | `ok`, `smoke`, `fixture` |
| 1 | the fit failed | `error`, or a status nobody wrote |
| 2 | no posterior exists | `skipped` (no CmdStan) |

Code 2 is separate from 1 because the operator response differs — install a
toolchain, or pass `--engine numpy` to sample with the reference walker, versus
debug a model. A caller that deliberately exercises the data path without a
sampler says so with `--allow-skipped-fit`, which turns `skipped` back into 0;
nothing else changes. Sweeps that fit many cells (multiphase, recovery
post-processing) report the worst code they saw, a real failure outranking a
skip.

`_sentinel_reference.py` is a numpy Metropolis sampler over *the same* log
density, which is what lets `tests/test_sentinel_validation.py` assert on a real
posterior in CI. `test_stan_and_numpy_reference_posteriors_agree` pins the two
together and runs whenever CmdStan is installed.

Identifiability, honestly: on one voyage, imported and onboard cases are
separated by onset *timing* alone, so a voyage whose port days are back to back
leaves the import share only partly identified. Sharing ports across voyages is
what sharpens it — that is the fleet hierarchy, not this model.

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
