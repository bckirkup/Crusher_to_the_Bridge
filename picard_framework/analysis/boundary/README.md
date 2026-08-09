# Pre-boarding wearable decision model (boundary analysis)

Ancillary Monte Carlo decision model for **voluntary pre-boarding wearable
data sharing**. Distinct from mid-voyage wearable surveillance in the ship
ABM: this package never calls `ShipSimulation`.

It answers whether intercepting infectious passengers before embarkation can
avoid costly onboard outbreaks / VSP escalations under policies P0–P5.

## Quick start

```bash
# CI smoke (fixture outbreak surface, tiny matrix)
python3 -m picard_framework.analysis.boundary.run_decision_model --smoke

# Full default matrix with fixture lookup
python3 -m picard_framework.analysis.boundary.run_decision_model \
  --lookup fixture --n-mc 2000 --seed 1701 --out boundary_analysis/

# Real Stan-adjacent surface (export outbreak_surface.csv under the fit dir)
python3 -m picard_framework.analysis.boundary.run_decision_model \
  --stan-fit analysis/analysis_stan_norovirus/hurdle_fit \
  --lookup auto --out boundary_analysis/
```

Outputs under `--out`:

- `policy_comparison.csv`
- `runs/<scenario_id>.json`
- `figures/*.png` (when matplotlib available)
- `report.md`
- `completed_runs.txt` (resume)

## Stan surface contract

Place one of these under `--stan-fit`:

- `outbreak_surface.json` (same schema as `fixtures/outbreak_surface.json`)
- `outbreak_surface.csv` with columns
  `platform_class,pathogen,baseline_response,k,P_trigger,E_AR,P_accel,E_cost_onboard[,E_peak_epoch]`
- or the same filenames under `posterior/` or `boundary/`

`--lookup auto` uses Stan when present, otherwise the packaged fixture.

## Ship-sim handoff (future)

Phase 1 does **not** wire boarding denials into `init_multi_pathogen`.
A later PR may map `K_board` / denied agent sets into embarkation seeding.

## Spec

See [`docs/preboarding_wearable_decision_model_spec.md`](../../../docs/preboarding_wearable_decision_model_spec.md).
