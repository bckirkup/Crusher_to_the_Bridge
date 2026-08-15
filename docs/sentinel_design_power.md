# Sentinel design-stage power and precision projection

This projection evaluates the stakeholder-brief sentinel fleet geometries without
running the Crusher ABM. It reuses the sentinel fleet forward model and its
numpy reference posterior.

## Two engines

* **Engine A (`ceiling`)** numerically differentiates the existing forward model
  and computes the independent-Poisson Fisher information. It is an optimistic
  information ceiling: all other parameters are known and one exchangeable
  week is scaled by the number of weeks.
* **Engine B (`fit`)** simulates Poisson onsets and fits the existing
  `fleet_reference_posterior` at the configured fit scale. The sampler cannot
  be run at Caribbean scale (1,440 voyages) in a practical projection, so
  regional claims are Engine A curves multiplied by the pilot-scale inflation
  factor.

The geometries come from the stakeholder brief. `lambda_background` is an
assumption anchored so one call of one 2,800-passenger ship yields approximately
0.5 imported infections; it is not tuned to make results look good.

Run a regional ceiling and the fit-scale calibration with:

```bash
python3 -m picard_framework.analysis.sentinel.run_design_power \
  --preset caribbean --engine both --out tmp_design_power_out
```

Use `--smoke` for two short reference-sampler replicates.

## Caveats

1. Pooled `lambda_port` is identified only up to the fleet-time effect; per-visit hazards are the reportable per-call number (cite `summarize_fleet_hazards` / `summarize_visit_hazards`). The hot/background *ratio* is the fleet-time-free quantity.
2. The numpy reference sampler is not NUTS; its intervals are indicative, not calibrated. Any coverage/power number from Engine B inherits that.
3. Engine A is an information ceiling: other parameters treated as known, no week-to-week `fleet_time` variation -> widths are optimistic, MDHRs are best case.
4. Regional-scale numbers are extrapolations: the sampler cannot be run at 1,440 voyages, so full-scale claims rest on Engine A plus a pilot-scale inflation factor.
5. `lambda_background`, `r_onboard`, and ascertainment are assumptions, not fitted from data; MDHR scales roughly as 1/sqrt(expected observed imported cases), so halving assumed ascertainment inflates MDHR accordingly.

## Results

The following table is populated from the projection run attached to the PR.

| Design | Engine | sd(log lambda_hot) | 90% width | sd(log ratio) | MDHR |
|---|---|---:|---:|---:|---:|
| Caribbean | A ceiling | — | — | — | — |
| Mediterranean | A ceiling | — | — | — | — |
| Alaska | A ceiling | — | — | — | — |
| Pilot | A ceiling | — | — | — | — |
