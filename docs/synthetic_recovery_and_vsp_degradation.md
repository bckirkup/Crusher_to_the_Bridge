# Synthetic recovery + VSP degradation campaigns

Spot ABM campaigns derived from design specs in
`picard_framework/runs/mega_cruise_campaign/*_design.json`.

| Campaign | Manifest | Runs | S3 prefix |
|----------|----------|------|-----------|
| Synthetic recovery | `synthetic_recovery_v1_manifest.json` | **1200** | `campaign/synthetic_recovery_v1/` |
| VSP degradation | `vsp_degradation_v1_manifest.json` | **6360** | `campaign/vsp_degradation_v1/` |

Generators: tier ids `sr*` / `vd*` in
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`.

## Light validation

```powershell
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian `
  picard_framework/runs/mega_cruise_campaign/synthetic_recovery_v1_manifest.json
# expect total=1200
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
  -Manifest picard_framework/runs/mega_cruise_campaign/vsp_degradation_v1_manifest.json `
  -Prefix campaign/vsp_degradation_v1/ -ShardCount 200
```

## Parameter mapping

| Design | Override |
|--------|----------|
| `dose_adj` | pathogen `dose_adjustment` |
| `alpha_c` | `transmission.density_dependent.exponent` |
| `non_susceptible` | `innate_nonsusceptible_fraction` |
| `vsp_threshold` | `escalation.lockdown_attack_rate` |
| `detection_delay` | `medical_response.detection_delay_epochs` |
| `isolation_compliance` | medical + `fred_behavior.quarantine_compliance`, and **clears** stock `compliance_by_class` so the scalar is not masked by crew/passenger class rates |
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

### Reinterpreting `vsp_degradation_v1` (pre-fix) zips

Stock `fred_behavior.compliance_by_class` **masked** swept
`isolation_compliance` / `quarantine_compliance`. Treat those runs as:

| Axis | Trust? |
|------|--------|
| `vsp_threshold` | yes |
| `detection_delay` | yes (weak effect) |
| `sick_call_probability` | yes |
| `isolation_compliance` | **no** — class table dominated; iso labels are bookkeeping only |

Compliance-affected tiers were re-run under
`campaign/vsp_degradation_compliance_fix_v1/` (manifest
`vsp_degradation_compliance_fix_v1_manifest.json`: FAT iso +
threshold×compliance + worst-case = **3480** runs) after clearing
`compliance_by_class` in `_vsp_degradation_overrides`.

Design checklist (covered by the script):

1. Heatmap `|AR_expedition − AR_mega|` vs (threshold, compliance)
2. Shadow-breaking boundary in degradation space
3. Per-platform AR curves under progressive degradation
4. Thesis test: when does the uncontrolled ~23% vs ~11% gap reappear (>5 pp)
   despite active response?

See also: `.agents/skills/aws-batch-campaign/SKILL.md`,
`docs/boundary_aws_pipeline_lessons.md`.
