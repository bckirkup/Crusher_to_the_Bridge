# Stan hurdle lessons (C12c + C14/C14b Step-2)

Operational and scientific notes from the first full-scale Phase‑1b hurdle
attempts on the combined Step‑2 bundle
(`analysis/analysis_stan_norovirus/`, ~9940 norovirus runs).

## What was run

| Stage | Data | MCMC | Outcome |
|-------|------|------|---------|
| A #1 (inside `fit_norovirus_hurdle`) | 9940 runs, 5151 outbreaks (51.8%), P=4, S=23 | 4×1000/1000 | Finished ~9 min sampling; **high divergences** (one chain ~95%); NaN logit warnings during warmup |
| A #2 (independent `fit_norovirus_outbreak`) | same | 4×1000/1000 | Finished; posteriors written; draws still ~**33% divergent** |
| B #1 (hurdle Stage B) | 5151 outbreak runs × T=168, `reduce_sum` | 4×1000/1000, 4 threads/chain | After **~5 h**, one chain ~5%, others ~0% — **killed**; no full-scale Stage B posterior |

Artifacts worth keeping locally (not in git):

- `analysis/analysis_stan_norovirus/` — merged bundle
- `.../hurdle_fit/outbreak/` — Stage A #2 outputs (`posterior/`, `draws.csv`)
- Incomplete Stage B run — discard

## Why Stage A fails to converge cleanly

Not primarily a CmdStan install issue. Geometry / design issues:

1. **Hard dichotomy on a soft continuous outcome (legacy).**  
   Early fits used `outbreak_occurred = ever_infected > 2`, then a 1% size cut.
   **Current definition** (re-bundle to apply): **takeoff** if VSP
   (SUSPECTED/CONFIRMED) fires while incidence is still accelerating
   (`Δ²incidence >= 0` at onset); **fizzle** if no VSP or VSP arrives only
   after the curve is already bending down (`Δ² < 0`) — see
   `simulation_utils.epidemic_labels`. Seed-only signal remains
   `seed_established` (`ever_infected > 2`).

2. **Mixture of campaigns in one logit.**  
   C12c is a fine dose/medical calibration surface (high noro N, different
   surveillance tags). C14/C14b add intervention / VSP / cascade arms. Pooling
   them into one `P(outbreak | …)` with shared coefficients induces
   multimodality and weak identification.

3. **23 surveillance levels.**  
   Sparse arms + independent `delta_surveillance[s]` create a high-dimensional
   funnel. Thin cells → near-nonidentifiable logits → divergences and NaNs when
   proposals push `logit_p` to ±Inf.

4. **Weak dose signal on takeoff.**  
   Posterior `beta_d` for Stage A crossed or hugged zero. If dose mainly changes
   *size given takeoff* rather than *P(takeoff)* under this cutoff, the Bernoulli
   stage is asking the wrong question of the data.

5. **VSP as a coarse binary feature.**  
   Stage A uses “VSP enabled” (`threshold < 1`), not path-dependent trigger
   timing. That is a blunt instrument relative to the ABM.

**Implication:** the hurdle split remains a useful *engineering* idea (don’t fit
NegBin to structural zeros), but the current **binary outbreak label + flat
surveillance effects** is not a clean scientific dichotomy. Prefer:

- ordered / continuous outcomes (e.g. attack-rate hurdle, or `ever_infected`
  categories: none / seed / outbreak),
- hierarchical pooling of surveillance (partial pooling toward a global mean),
- or campaign-stratified Stage A (C12c vs C14) before a joint model,
- plus sampler hardening (`adapt_delta ≥ 0.95`, tighter priors, possibly
  non-centered intercepts).

## Why Stage B is expensive

Even with `reduce_sum` and slim GQ (no `y_rep[N,T]`):

- Likelihood is still **O(N_outbreaks × T)** per leapfrog step.
- 5151 × 168 with 4×1000/1000 and within-chain threading is multi-hour to
  multi-day on a workstation.
- Do **not** burn a full Stage B overnight while Stage A diagnostics are red.
  Stage B does not “inherit” Stage A draws, but the **monograph story** needs a
  trustworthy Stage A first.

Spot instances will **not** resume mid-chain; treat Stage B as On-Demand or
one-chain-per-job with S3 upload of finished chain CSVs.

## Re-bundle before the next Stage A

Existing `run_summary.csv` files may still carry legacy size / `ever_infected > 2`
labels from zip `summary.json`. Recompute takeoff from timeseries + triggers:

```powershell
# Per-campaign (examples)
python -u -m picard_framework.analysis.campaign_bundle results\c12c_fine_calibration --out analysis\c12c_fine_calibration
python -u -m picard_framework.analysis.campaign_bundle results\results_c14 --out analysis\c14
python -u -m picard_framework.analysis.campaign_bundle results\results_c14b --out analysis\c14b
# Then rebuild the Step-2 merge (c12c + c14 + c14b)
python -u scripts\build_stan_step2_bundle.py
```

`build_run_summary_row` now prefers timeseries-derived metrics when epochs are
present, so re-bundling applies takeoff vs fizzle without re-running the ABM.

1. **Keep** merged analysis bundles; they are fine.
2. **Treat** current Stage A posteriors as exploratory only (divergences).
3. **Do not** run full-scale Stage B until Stage A converges (or until Stage B
   is justified as a standalone “size | outbreak” analysis with a fixed label).
4. **Next Stage A iterations** should:
   - **re-bundle** so `outbreak_occurred` uses VSP + curvature takeoff vs fizzle,
   - add hierarchical `delta_surveillance`,
   - use `adapt_delta=0.95`, longer warmup if needed,
   - consider fitting C12c and C14(+b) separately for diagnosis.
5. Stage A alone remains cheap (~10 min at 4×1000 on this dataset) — iterate
   locally; reserve AWS for Stage B.

## Commands (reminder)

```powershell
# Stage A only
python -u -m picard_framework.analysis.stan.fit_norovirus_outbreak `
  analysis\analysis_stan_norovirus `
  --out analysis\analysis_stan_norovirus\hurdle_fit\outbreak `
  --chains 4 --iter-warmup 1000 --iter-sampling 1000 `
  --seed 1701 --d0 10.6 --vsp-ref 0.03 --show-progress

# Stage B only (after Stage A is trustworthy, or as standalone)
python -u -m picard_framework.analysis.stan.fit_norovirus_trajectory `
  analysis\analysis_stan_norovirus `
  --out analysis\analysis_stan_norovirus\hurdle_fit\trajectory `
  --outbreaks-only --chains 4 --threads-per-chain 4 `
  --iter-warmup 1000 --iter-sampling 1000 `
  --seed 1702 --d0 10.6 --vsp-ref 0.03 --show-progress
```

See also `picard_framework/analysis/stan/README.md` and
`docs/stan_analysis_tool_spec.md`.
