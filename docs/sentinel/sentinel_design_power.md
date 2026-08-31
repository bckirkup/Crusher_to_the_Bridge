# Sentinel design-stage power and precision projection

> **Status:** Implemented

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
  regional claims use the Engine A ceiling with a conservative adjustment:
  posterior-width ratios below one never reduce the ceiling MDHR.

The geometries come from the stakeholder brief. `lambda_background`, `r_onboard`,
and ascertainment are anchored assumptions, not tuned parameters.

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
4. Regional-scale numbers are extrapolations: full-scale claims rest on Engine A. The pilot-scale sampler comparison produced narrower intervals with ratio coverage 0.6 versus 0.9 nominal, so it cannot certify calibration and no downward adjustment is applied.
5. `lambda_background`, `r_onboard`, and ascertainment are assumptions, not fitted from data; MDHR scales roughly as 1/sqrt(expected observed imported cases), so halving assumed ascertainment inflates MDHR accordingly.
6. The one-week information scaling shortcut is approximately 7-9% optimistic versus explicitly building three weeks in the measured pilot and Alaska checks.

## What drives detection

Precision scales as `1/sqrt(ship-weeks)`: multiplying ships by 16 gives
approximately four times narrower intervals. Calls per ship-week are a
near-flat lever (spread under 12% and not monotone), because extra calls spread
the same passengers over more ports. The governing quantity is voyage-calls per
port: Caribbean 36, Alaska 25, Mediterranean 16, and Pilot 8. This is why the
60-port Mediterranean is less precise than 10-port Alaska despite four times
the ships.

At pilot scale, the measured Engine B ratio coverage was 0.6 against the 0.9
nominal target. Together with a posterior-width ratio below one, this indicates
that the reference sampler intervals are too narrow or mis-calibrated, not that
the design is more informative than the likelihood ceiling. Engine B
power/coverage results are therefore indicative only; a real deployment claim
requires a calibrated NUTS fit.

## Results

The following table is populated from the projection run attached to the PR.

| Design | Voyages | Engine | sd(log lambda_hot) | 90% width | sd(log ratio) | MDHR |
|---|---:|---|---:|---:|---:|---:|
| Caribbean | 1440 | A ceiling | 0.1200 | 0.3949 | 0.1259 | 1.4665 |
| Mediterranean | 960 | A ceiling | 0.1757 | 0.5780 | 0.1809 | 1.6539 |
| Alaska | 250 | A ceiling | 0.1622 | 0.5335 | 0.2005 | 1.7144 |
| Pilot | 48 | A ceiling | 0.3260 | 1.0726 | 0.4705 | 2.8299 |

Caribbean Engine A sweeps (sd_log_hot / sd_log_ratio / MDHR):

| Dimension | Values |
|---|---|
| Ships | 15: 0.3519 / 0.3662 / 2.3498; 30: 0.2261 / 0.2381 / 1.8520; 60: 0.1698 / 0.1781 / 1.6442; 120: 0.1200 / 0.1259 / 1.4665; 240: 0.0849 / 0.0890 / 1.3383 |
| Weeks | 4: 0.2079 / 0.2181 / 1.7819; 12: 0.1200 / 0.1259 / 1.4665; 26: 0.0816 / 0.0855 / 1.3260; 52: 0.0577 / 0.0605 / 1.2355 |
| Calls/ship-week | 2: 0.1314 / 0.1367 / 1.4991; 3: 0.1176 / 0.1238 / 1.4584; 4: 0.1221 / 0.1277 / 1.4730; 5: 0.1194 / 0.1253 / 1.4656 |

At the pilot-scale design and assumed hot ratio 2.0, the measured Engine B
detection power was 0.0. The reduced-fit graded-power run below is the
signal-response check; it uses 4 ships, 2 weeks, 4 ports, 120 draws, 400
warmup steps, and 3 replicates per ratio.

| True hot ratio | Detection power | Mean ratio 90% width | Ratio coverage | Pooled hot coverage | Pooled background coverage |
|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.000 | 2.864 | 1.000 | 1.000 | 1.000 |
| 2.0 | 0.000 | 2.633 | 1.000 | 1.000 | 1.000 |
| 4.0 | 0.000 | 1.930 | 0.667 | 0.667 | 1.000 |
| 8.0 | 0.000 | 2.827 | 0.667 | 0.333 | 1.000 |
| 16.0 | 0.333 | 2.201 | 0.333 | 0.333 | 1.000 |
