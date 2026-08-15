# Synthetic recovery + VSP degradation campaigns

Spot ABM campaigns derived from design specs in
`picard_framework/runs/mega_cruise_campaign/*_design.json`.

| Campaign | Manifest | Runs | S3 prefix |
|----------|----------|------|-----------|
| Synthetic recovery | `synthetic_recovery_v1_manifest.json` | **1200** | `campaign/synthetic_recovery_v1/` |
| Sentinel port recovery | `sentinel_synthetic_recovery_v1_manifest.json` | **3360** | `campaign/sentinel_synthetic_recovery_v1/` |
| VSP degradation | `vsp_degradation_v1_manifest.json` | **6360** | `campaign/vsp_degradation_v1/` |

Generators: tier ids `sr*` / `sr_*` (sentinel) / `vd*` in
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`.

## Sentinel: the manifest is generated, not authored

`sentinel_synthetic_recovery_v1_manifest.json` is expanded from
`sentinel_synthetic_recovery_v1_design.json`
(schema: `schemas/sentinel_recovery_design.schema.json`). The design spec holds
the port registry, itinerary templates, hazard profiles, `R_onboard` levels,
fleet configurations and seeds; the expander crosses hazard profiles with fleet
configurations into `sr_<hazard>_<fleet>` tiers and resolves each template into
voyage day slots that `campaign_runner` stamps hazards onto. A new region or
port rotation is therefore a design-spec edit, not a code edit.

`port_hazards` are per-epoch (hourly) infection probabilities for a person
ashore, so a value must be read against the ~10-epoch ashore window: 1e-4 is
~0.1% attack among shore-goers per call, 1e-3 ~1%, and 0.015 ~14% — hundreds of
imported cases on a mega-cruise call, i.e. an outbreak rather than a quiet
voyage. The grid therefore sits in the 1e-4 to 1e-3 decade, which is where the
sentinel question ("can a port be seen at all when almost nothing happens")
lives, and keeps outbreak scale only in `last_port_hot`, whose purpose is to
stress the right-censoring correction.

```bash
# regenerate the manifest after editing the design
python3 -m picard_framework.runs.mega_cruise_campaign.expand_design \
  --design picard_framework/runs/mega_cruise_campaign/sentinel_synthetic_recovery_v1_design.json

# fail on drift (also asserted by tests/test_sentinel_design_expansion.py)
python3 -m picard_framework.runs.mega_cruise_campaign.expand_design \
  --design picard_framework/runs/mega_cruise_campaign/sentinel_synthetic_recovery_v1_design.json \
  --check
```

Population note: earlier hand-written sentinel experiment JSON listed
`default_num_agents: 5000`, matching the `mega_cruise_5000` *berth* name rather
than its agent count. Populations come from `_PLATFORM_DEFAULT_AGENTS` in
`campaign_runner.py` (mega 7000 = passengers + crew, spirit 3000, classic 1910);
`default_num_agents` in the design is only the fallback for platforms absent
from that table, and is kept at 7000 so the run set is unchanged.

## Light validation

```powershell
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian `
  picard_framework/runs/mega_cruise_campaign/synthetic_recovery_v1_manifest.json
# expect total=1200
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian `
  picard_framework/runs/mega_cruise_campaign/sentinel_synthetic_recovery_v1_manifest.json
# expect total=3360
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian `
  picard_framework/runs/mega_cruise_campaign/vsp_degradation_v1_manifest.json
# expect total=6360
python picard_framework/runs/mega_cruise_campaign/campaign_runner.py --smoke
```

## Spot submit

Rebuild/push `picard-campaign` after adding manifests, ensure ACTIVE job def
uses `:latest`, then:

```powershell
.\deploy\aws\submit_campaign_manifest.ps1 `
  -Manifest picard_framework/runs/mega_cruise_campaign/synthetic_recovery_v1_manifest.json `
  -Prefix campaign/synthetic_recovery_v1/ -ShardCount 200

.\deploy\aws\submit_campaign_manifest.ps1 `
  -Manifest picard_framework/runs/mega_cruise_campaign/sentinel_synthetic_recovery_v1_manifest.json `
  -Prefix campaign/sentinel_synthetic_recovery_v1/ -ShardCount 200

.\deploy\aws\submit_campaign_manifest.ps1 `
  -Manifest picard_framework/runs/mega_cruise_campaign/vsp_degradation_v1_manifest.json `
  -Prefix campaign/vsp_degradation_v1/ -ShardCount 200
```

## Parameter mapping

| Design | Override |
|--------|----------|
| `dose_adj` | pathogen `dose_adjustment` |
| `alpha_c` | `transmission.density_dependent.exponent` |
| `non_susceptible` | `innate_nonsusceptible_fraction` |
| `λ_p` (sentinel) | itinerary `shore_infection_probability` per `port_id` |
| `R_onboard` (sentinel) | day-type `contact_rate_multiplier` scale (1.0 = nominal) |
| `vsp_threshold` | `escalation.lockdown_attack_rate` |
| `detection_delay` | `medical_response.detection_delay_epochs` |
| `isolation_compliance` | `medical_response.isolation_compliance` + `fred_behavior.quarantine_compliance` |
| `sick_call_probability` | medical + syndromic |

Synthetic recovery pins `initial_infected=3`. VSP degradation pins
`dose_adjustment=10.6`, `density_exponent=0.75`, `initial_infected=3`.

## Post-processing

**Synthetic recovery** (local; ~1200 zips is fine on a laptop):

```powershell
python -m picard_framework.analysis.synthetic_recovery_postprocess `
  results/synthetic_recovery_v1/zips `
  --out results/synthetic_recovery_v1/analysis
```

Writes `run_summary.csv`, aggregates, Stage A Bernoulli + Stage B Beta-AR
pooled fits, per-vector latent recovery, figures, and `report.md`. Uses CmdStan
when `mingw32-make` is available; otherwise a NumPy Metropolis fallback.

**VSP degradation** (local; streams `run_zips.tar`):

```powershell
python -m picard_framework.analysis.vsp_degradation_postprocess `
  results/vsp_degradation_v1 `
  --out results/vsp_degradation_v1/analysis
```

Writes aggregates, `|AR_expedition − AR_mega|` heatmaps, FAT AR curves, shadow-break
thesis summary (`>5 pp`), and `report.md`.

Design checklist (covered by the script):

1. Heatmap `|AR_expedition − AR_mega|` vs (threshold, compliance)
2. Shadow-breaking boundary in degradation space
3. Per-platform AR curves under progressive degradation
4. Thesis test: when does the uncontrolled ~23% vs ~11% gap reappear (>5 pp)
   despite active response?

See also: `.agents/skills/aws-batch-campaign/SKILL.md`,
`docs/boundary_aws_pipeline_lessons.md`.
