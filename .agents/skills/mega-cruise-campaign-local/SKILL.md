---
name: mega-cruise-campaign-local
description: Run and validate the ~17780-run mega cruise campaign locally (smoke, dry-run, tiers, resume, sharding) before AWS Batch. Use when editing campaign_runner.py, campaign_manifest.json, run_campaign scripts, or preparing a Batch submit.
---

# Mega cruise campaign (local)

Canonical ops doc: `picard_framework/runs/mega_cruise_campaign/README.md`.
AWS Batch deploy: `.agents/skills/aws-batch-campaign/SKILL.md` + `deploy/aws/README.md`.
Post-run analysis: `.agents/skills/campaign-results-analysis/SKILL.md`.

## Prerequisites

- Python 3.11+; install from `requirements.lock.txt` (or `requirements.txt` for editable local work)
- Working directory: **repo root**
- Platform data for `mega_cruise_5000` under `data/platforms/`

## Quick commands

```bash
RUNNER=picard_framework/runs/mega_cruise_campaign/campaign_runner.py

# Count full matrix without executing (~17780)
python3 "$RUNNER" --dry-run

# Fast smoke (destroyer, 2 epochs, 20 agents, 1 run) — writes a result zip
python3 "$RUNNER" --smoke

# One tier / resume / limits
python3 "$RUNNER" --tier t1
python3 "$RUNNER" --resume --tier t2
python3 "$RUNNER" --tier t1 --limit 3 --epochs 6 --num-agents 100

# Local shard simulation (disjoint partitions)
python3 "$RUNNER" --dry-run --shard-count 4 --shard-index 0
python3 "$RUNNER" --dry-run --shard-count 4 --shard-index 1

# Wrapper scripts
./run_campaign.sh --smoke
./run_campaign.sh --dry-run
run_campaign.bat --smoke
```

## Output layout

Successful runs write:

`telemetry_buffer/mega_cruise_campaign/<run_id>.zip`

containing `run_spec.json`, `summary.json` (SIR + costs + `parameters` + `derived`),
and compact `timeseries.json`. Use `--full-telemetry` only when you need history /
lab notebook / ground truth (much larger).

## Tests

```bash
python3 -m pytest tests/test_mega_cruise_campaign.py -v --tb=short
```

Covers dry-run counts, surveillance ladder divergence, OA/compliance/immunity
sweeps, smoke zip layout, S3 resume mocks, HVAC OA sensitivity, shard
partitioning, and Campaign v5 T11/T15/T16 generators
(decision latency, SOP AR thresholds, reluctant fraction).

Outbreak-response knobs: skill `outbreak-response-architecture` +
`docs/tiered_escalation_spec.md`. Also run:

```bash
python3 -m pytest tests/test_outbreak_response_architecture.py -v --tb=short
```

## Calibration tiers (density + multi-pathogen)

Manifest: `picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json`.

| Tier | Focus |
|------|--------|
| `c5_density_calibration` | Density-dependent α × dose × platforms (~3600 runs) |
| `c6_heterogeneous_sensitivity` | Density vs `heterogeneous_zone_dose` — **deferred** until needed |

Dining/free rotation stays off in default `config.yaml` (`dining_rotation_probability: 0.0`).
Raise via campaign `config_overrides` when testing venue mixing vs platform
`dose_adjustment` gaps. Specs: `docs/density_contact_spec.md`,
`docs/multi_pathogen_model_changes_spec.md`.

```bash
python3 -m pytest tests/test_density_contact.py \
  tests/test_multi_pathogen_model_phase_a.py \
  tests/test_multi_pathogen_model_phase_b.py -v --tb=short
```

## Pre-AWS checklist

1. `--dry-run` count matches README (~17,780) for the current manifest.
2. `--smoke` produces a valid zip under `telemetry_buffer/mega_cruise_campaign/`.
3. `tests/test_mega_cruise_campaign.py` green.
4. Docker image smoke (optional locally, required in main CI when Docker available):

```bash
docker build -t picard-campaign .
docker run --rm picard-campaign --smoke
```

5. Then follow `aws-batch-campaign` for ECR push + array submit.

## Synthetic recovery + VSP degradation

Design specs + runnable manifests for Ridge recovery (1200) and VSP shadow
stress (6360). Ops: `docs/synthetic_recovery_and_vsp_degradation.md`.

```bash
python3 -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian \
  picard_framework/runs/mega_cruise_campaign/synthetic_recovery_v1_manifest.json
python3 -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian \
  picard_framework/runs/mega_cruise_campaign/vsp_degradation_v1_manifest.json
```
