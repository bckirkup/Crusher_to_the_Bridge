# Sentinel Wastewater Operations Parameter Scan
# Campaign + Analysis Design v2

> **Status:** Implemented — earlier spec for the doc above

## Objective

Determine the wastewater sampling operational envelope for port-attributed 
sentinel surveillance. Map the (sampling_frequency × holding_tank_residence) 
space to identify the minimum operational requirements for reliable port 
hazard recovery.

## Design rationale

The v1 recovery showed the clinical-only model is structurally biased 
(18.5% coverage, 100× underestimation). The R_onboard prior fix addresses 
part of this. The remaining question is: under what wastewater operational 
conditions does the additional channel break the residual degeneracy?

The two parameters that dominate signal quality:
- **Sampling frequency** controls temporal resolution (Nyquist limit)
- **Holding tank residence time** controls temporal smearing (convolution blur)

Their ratio determines identifiability: if residence_time > sampling_interval, 
adjacent samples are correlated and temporal attribution degrades. The 
critical regime is residence_time ≈ inter-port interval (~24h).

## Campaign design

### Fixed factors (use the hardest cases)
- Hazard profiles: one_hot, last_port_hot (the two 0% coverage profiles)
  Plus null (false positive control)
- R_onboard: 1.0 (realistic norovirus, tests imported-vs-secondary separation)
- Fleet: fleet_crossed (3 ships, best identifiability geometry)
- Itinerary: standard Caribbean 7-day (same as v1)
- Pathogen: norovirus
- All other sim parameters: identical to v1

### Swept factors

Factor 1 — Sampling frequency (epochs between samples):
  [1, 3, 6, 12, 24] = 5 levels
  1h = maximum resolution (168 samples/voyage)
  24h = daily grab sample (7 samples/voyage)

Factor 2 — Holding tank residence time (hours):
  [0.5, 2, 4, 8, 12] = 5 levels
  0.5h = direct line sampling (near-instantaneous)
  12h = large holding tank with full mixing

Factor 3 — Sequencing depth (total reads per sample):
  [50000, 250000, 1000000] = 3 levels
  50K = rapid/cheap sequencing
  1M = deep sequencing

Factor 4 — Collection points:
  [1, 3] = 2 levels
  1 = single aft main sewer
  3 = aft + midship + forward (spatial resolution)

Plus one control level: wastewater OFF (clinical-only with tight R prior)

### Run matrix
- 3 hazard profiles × 1 R × 1 fleet(3 ships) × sweep
- Wastewater sweep: 5 freq × 5 residence × 3 depth × 2 collection = 150 cells
  Plus 1 control (wastewater off) = 151 cells per hazard profile
- 3 hazard × 151 cells × 3 ships × 10 seeds = 13,590 runs

That's too many. Fractional factorial:

### Reduced design

**Core scan** (frequency × residence — the critical interaction):
- 5 freq × 5 residence = 25 cells
- At fixed depth=250K, collection=1
- 3 hazard × 25 × 3 ships × 15 seeds = 3,375 runs

**Depth sensitivity** (at best frequency × 2 residence levels):
- 3 depth × 2 residence × 1 freq(best) 
- 3 hazard × 6 × 3 ships × 10 seeds = 540 runs

**Collection point sensitivity** (at best operating point):
- 2 collection × 1 best frequency × 1 best residence
- 3 hazard × 2 × 3 ships × 10 seeds = 180 runs

**Control** (wastewater off, tight R prior):
- 3 hazard × 1 × 3 ships × 15 seeds = 135 runs

**Total: 4,230 runs**
~3.5 hours on 200 instances at 10 min/run

### Execution order
1. Core scan first (3,375 runs) — identifies the freq × residence sweet spot
2. Control (135 runs) — baseline without wastewater
3. Depth + collection sensitivity (720 runs) — at the sweet spot from step 1

## Wastewater configuration per run

```json
{
  "wastewater_surveillance": {
    "enabled": true,
    "sampling_interval_epochs": <SWEEP: 1, 3, 6, 12, 24>,
    "holding_tank_residence_hours": <SWEEP: 0.5, 2, 4, 8, 12>,
    "collection_points": <SWEEP: ["aft_main"] or ["aft_main", "midship", "forward"]>,
    "sequencing_depth": <SWEEP: 50000, 250000, 1000000>,
    "pathogen_shedding_to_reads_scale": 1.0,
    "background_read_fraction": 0.9999
  }
}
```

The `holding_tank_residence_hours` acts as a convolution kernel on the 
wastewater signal. At 0.5h, the signal is nearly instantaneous. At 12h, 
a port-call spike is smeared across 12 hours — overlapping with adjacent 
port calls or sea days.

## Analysis design

### Per-cell Stan fitting
For each cell, fit sentinel_attribution.stan with:
- Clinical + wastewater likelihood (beta-binomial on reads)
- Tight R_onboard prior from CTB posterior
- Wastewater shedding kernel = pathogen-specific (norovirus: peak 24-48h)
- Wastewater residence kernel = exponential with mean = configured residence time

### Primary outcome: coverage heatmap
- x-axis: sampling frequency (1h → 24h)
- y-axis: holding tank residence (0.5h → 12h)  
- color: port hazard 90% CI coverage
- Separate panels for one_hot vs last_port_hot

### Secondary outcomes
1. **CI width ratio**: wastewater / clinical-only at each operating point
2. **KYGEC (last port) recovery**: does wastewater specifically help the 
   censored port? Heat map of KYGEC coverage vs freq × residence
3. **Marginal log-likelihood**: per-channel evidence_loglik showing where 
   wastewater actually adds information vs noise
4. **Sampling frequency ROI**: coverage gain per additional sample
5. **Depth sensitivity**: does 1M reads help vs 250K vs 50K?
6. **Spatial resolution**: does 3 collection points help vs 1?

### Key figures for the paper
1. Coverage heatmap (freq × residence × hazard profile)
2. KYGEC-specific recovery heatmap
3. CI width reduction vs operating cost (samples × depth)
4. Wastewater temporal signal examples: read timeseries at 3 operating points
   (fast-clean, moderate, slow-mixed)
5. Operational recommendation curve: minimum sampling frequency for X% coverage 
   as a function of holding tank residence time

## Expected outcomes and paper framing

Best case: there's a clear operational threshold (e.g., "sample every 3h 
with ≤4h residence for ≥80% port coverage"). This becomes a design 
specification for shipboard WBE.

Worst case: even at 1h/0.5h, coverage doesn't exceed 50%. This means 
clinical timing + tight CTB prior is sufficient and wastewater doesn't 
add enough for port attribution. Still publishable — it bounds the value 
of ship WBE for this specific application.

Most likely: coverage improves substantially at freq ≤ 6h and residence ≤ 4h, 
with diminishing returns below 3h frequency. Last-port recovery (KYGEC) is 
the biggest beneficiary because wastewater shedding continues after 
disembarkation while clinical onsets are censored.
