---
name: preboarding-wearable-decision
description: Run and extend the pre-boarding wearable data-sharing decision model (boundary analysis). Use when editing picard_framework/analysis/boundary/, preboarding schemas, or ROI/policy comparisons for embarkation screening.
---

# Pre-boarding wearable decision model

Ancillary analysis package (like Stan campaign analysis / ship-blueprint
import): **same repo, not the ship epoch loop**.

## When to use

- Estimate ROI of voluntary pre-boarding wearable sharing (policies P0–P5)
- Compare expected cost / P(VSP) vs embarkation prevalence
- Consume CTB Stan/fixture outbreak surfaces keyed by introductions `k`

## Commands

```bash
# Smoke (fixture surface; no CmdStan)
python3 -m picard_framework.analysis.boundary.run_decision_model --smoke

# Default matrix
python3 -m picard_framework.analysis.boundary.run_decision_model \
  --lookup fixture --n-mc 2000 --out boundary_analysis/

# Export empirical outbreak_surface from campaign zips (k = introductions)
python3 -m picard_framework.analysis.boundary.export_outbreak_surface \
  results/c12c_fine_calibration results/results_c14 results/results_c14b \
  --pathogen norovirus \
  --out analysis/analysis_stan_norovirus/hurdle_fit_takeoff/trajectory/outbreak_surface.csv

# Stan/empirical surface when outbreak_surface.{json,csv} exists under the fit dir
python3 -m picard_framework.analysis.boundary.run_decision_model \
  --stan-fit analysis/analysis_stan_norovirus/hurdle_fit_takeoff/trajectory \
  --lookup auto --out boundary_analysis/ --resume
```

## Layout

| Path | Role |
|------|------|
| `picard_framework/analysis/boundary/` | Package (prevalence, screening, costs, lookup, CLI) |
| `fixtures/outbreak_surface.json` | CI/smoke response surfaces |
| `data/scenario_matrix.json` | Full campaign axes |
| `schemas/preboarding_decision_*.schema.json` | Scenario + summary contracts |
| `docs/preboarding_wearable_decision_model_spec.md` | Full spec |
| `tests/test_boundary_decision_model.py` | Golden + sensitivity + CLI smoke |

## Policies

- **P0** baseline (no sharing)
- **P1** advisory only (≈ P0 economically in v1)
- **P2** flag → confirmatory test → deny if positive
- **P3** flag → deny/delay with compensation
- **P4** P2 mechanics + incentivized adoption `a=0.70`
- **P5** crew mandatory + passenger optional; boarding like P2

## Tests

```bash
python3 -m pytest tests/test_boundary_decision_model.py -v --tb=short
```

## Non-goals (Phase 1)

- Do not call `ShipSimulation` or wire `init_multi_pathogen`
- Do not require CmdStan for pytest
- Do not change mid-voyage wearable cascade behavior
