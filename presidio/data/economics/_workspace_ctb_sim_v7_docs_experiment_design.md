
# Crusher_to_the_Bridge Experimental Framework Specification

To move from single-outbreak validation to policy optimization, we need a 
reproducible way to define, run, and analyze multi-cruise fleet experiments 
under different policy and surveillance regimes.

## 1. The Fleet Base-Rate Parameterization

Instead of guaranteeing an outbreak on every cruise, we sample from a 
base-rate distribution reflecting real-world cruise operations.

**Annual Cruise Base Rates (per 100 voyages)**:
- 85% Baseline: Normal sick-call noise, no major pathogens introduced
- 10% Sub-clinical intro: 1 infected agent boards, but stochastic extinction 
  prevents an outbreak (fizzles early)
- 4% Outbreak (Enteric): Norovirus intro that gains traction
- 1% Outbreak (Respiratory): Influenza or SARS-CoV-2 intro

This means an evaluation of a new surveillance technology (e.g., wearables)
is tested against 85 cruises of pure noise, exposing its true false-positive 
burden (the "incidentaloma" effect) alongside its value in the 5% of 
cruises with real outbreaks.

## 2. Experimental Design Structure

An experiment consists of **Regimes** tested across identical **Scenarios**.

**Scenarios** (The physical reality, identical across all regimes):
A fixed list of N generated cruise definitions, pre-seeded with pathogens 
according to the base rates above. e.g. `cruise_00` has 0 cases, `cruise_01` 
has 1 Noro case, etc.

**Regimes** (The policy & technology being evaluated):
1. `Status Quo`: Syndromic (sick-call) + RDT + Current VSP rules
2. `Wastewater Add`: Status Quo + Wastewater sequencing + PPE SOPs
3. `Wearable Add`: Status Quo + Wearables + Triage SOPs
4. `Full Stack`: All modalities active
5. `Policy Relaxation`: Status Quo + relaxed VSP thresholds (e.g., 5% instead of 3%) 
   to offset the increased sensitivity of modern detection

## 3. The `experiment.json` Format

Each experiment is defined by a single JSON file that captures all assumptions
and parameters. This file is committed to the repo, ensuring the experiment 
can be reproduced or tweaked for sensitivity analysis.

```json
{
  "experiment_name": "surveillance_roi_mega_cruise",
  "platform": "mega_cruise_5000",
  "num_agents": 500,
  "epochs_per_cruise": 14,
  "num_cruises": 100,
  "random_seed_base": 4242,

  "base_rates": {
    "none": 0.85,
    "norovirus_gii4_fizzle": 0.10,
    "norovirus_gii4_outbreak": 0.04,
    "sars_cov2_resp_outbreak": 0.01
  },

  "pathogen_parameters": {
    "norovirus_gii4": {"dose_adjustment": 7.0, "initial_time_infected": -2},
    "sars_cov2_resp": {"dose_adjustment": 6.0, "initial_time_infected": -3}
  },

  "regimes": {
    "status_quo": {
      "modalities": {"syndromic": true, "clinical_rdt": true, "wastewater": false, "wearable": false},
      "vsp_threshold": 0.03,
      "sops_enabled": ["SOP-006", "SOP-007", "SOP-008", "SOP-010"]
    },
    "wastewater_added": {
      "modalities": {"syndromic": true, "clinical_rdt": true, "wastewater": true, "wearable": false},
      "vsp_threshold": 0.03,
      "sops_enabled": ["SOP-004", "SOP-005", "SOP-006", "SOP-007", "SOP-008", "SOP-010"]
    }
  },

  "evaluation_metrics": [
    "total_fleet_ois",
    "total_fleet_infections",
    "total_financial_cost",
    "false_positive_quarantine_agent_days",
    "true_positive_detection_lead_time"
  ]
}
```

## 4. Analysis and Policy Implications

By summing costs across the 100-cruise fleet:
1. We measure the "incidentaloma" cost of the technology (e.g., wastewater 
   detects a single case on day 1, triggers PPE/isolation, but that case 
   was going to fizzle anyway. The OIS incurred is a pure loss).
2. We can identify the "CDC Offset": If wastewater increases detection sensitivity 
   by 3x, does the CDC need to raise the VSP reporting threshold to prevent 
   the industry from being shut down by hyper-sensitive environmental noise?
