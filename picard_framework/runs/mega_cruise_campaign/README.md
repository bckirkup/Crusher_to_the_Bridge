# Mega Cruise 9K Campaign

~9000 Picard runs on `mega_cruise_5000` (default 7000 agents, 240 epochs)
after the HVAC star-topology + analytical mass-balance fixes.

## Tiers

| Tier | What | Dimensions | Runs |
|------|------|-----------|------|
| t1 | Pathogen baselines | 10 pathogens × 30 seeds | 300 |
| t2 | HVAC parameter sweep | 10 × 5 filters × 4 decay × 10 seeds | 2000 |
| t3 | Surveillance strategies | 10 × 4 strategies × 30 seeds | 1200 |
| t4 | Full factorial | 4 × 3 filters × 3 decay × 4 surv × 20 seeds | 2880 |
| t5 | Multi-pathogen | 5 combos × 4 surv × 20 seeds | 400 |
| t6 | Dose-response | 4 × 5 doses × 30 seeds | 600 |
| t7 | Compliance | 4 × 4 surv × 5 compliance × 10 seeds | 800 |
| t8 | Wearables | 4 × 3 configs × 4 surv × 10 seeds | 480 |
| t9 | Slow pathogens (21d) | 4 × 4 surv × 20 seeds | 320 |
| t10 | Population size | 2 × 5 sizes × 10 seeds | 100 |
| **Total** | | | **~9080** |

## Running

From the **repo root**:

```bash
# Dry run (count without executing)
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --dry-run

# Fast local smoke (destroyer, 2 epochs, 20 agents, 1 run)
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --smoke

# One tier
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --tier t1

# Resume after interruption
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --resume --tier t2

# Limit / override for testing
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py \
  --tier t1 --limit 3 --epochs 6 --num-agents 100
```

### Windows (`.bat`)

Double-click or from a prompt at the repo root:

```bat
run_campaign.bat --smoke
run_campaign.bat --tier t1
run_campaign.bat --dry-run
run_campaign.bat --resume --tier t4
```

### Linux / macOS (`.sh`)

```bash
./run_campaign.sh --smoke
./run_campaign.sh --tier t1 --resume
```

## Output

Each successful run writes:

`telemetry_buffer/mega_cruise_campaign/<run_id>.zip`

containing at least `run_spec.json` and `summary.json` (final SIR + costs + trigger).

Use `--full-telemetry` to also pack history / lab notebook / ground truth
(much larger and slower).

Progress for `--resume` is appended to:

`telemetry_buffer/mega_cruise_campaign/completed_runs.txt`

## Sharding & S3 (AWS Batch / distributed runs)

The runner can split the run list into disjoint shards and upload results to S3,
so the campaign can run as one AWS Batch array job of many Fargate Spot
containers. See [`deploy/aws/`](../../../deploy/aws/README.md) for the full
ECR + Batch workflow.

| Flag | Meaning |
|------|---------|
| `--shard-count N` | Total number of shards. A run executes only when `global_index % N == shard_index`, where `global_index` is its position in the full flattened, ordered run list across the selected tiers. |
| `--shard-index i` | This shard's index in `[0, N)`. Defaults to the `AWS_BATCH_JOB_ARRAY_INDEX` env var when present (so Batch array child *i* runs shard *i*). |
| `--s3-prefix s3://bucket/path` | After each run's zip is written to `telemetry_buffer/mega_cruise_campaign/<run_id>.zip`, upload it to `<s3-prefix>/<run_id>.zip`. The shard's `completed_runs.txt` is uploaded periodically to `<s3-prefix>/_resume/` (and at the end) so an interrupted Spot container resumes correctly on retry. Requires `boto3`. |
| `--s3-log-every K` | Upload `completed_runs.txt` every `K` successful runs (default 25). |

```bash
# Shard 3 of 200, uploading to S3, resumable:
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py \
  --shard-count 200 --shard-index 3 \
  --s3-prefix s3://my-bucket/campaign/ --resume

# Count how many runs a shard would execute:
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py \
  --dry-run --shard-count 200 --shard-index 3
```

Sharding composes with `--tier`, `--limit`, `--resume`, and `--dry-run`:
the global index is computed over exactly the tiers selected by `--tier`, so a
shard is stable regardless of which shard is running.

## Estimated time

At ~3 min/run for the full mega cruise, the campaign is ~450 hours wall-clock
serially. Parallelize by launching different `--tier` values on different machines,
or run one AWS Batch array job of N Fargate Spot children with
`--shard-count N` (~450/N hours wall-clock; e.g. N=200 ≈ 2.3 hours).
Tier 1 alone: ~15 hours (300 × 3 min).

## Files

| File | Role |
|------|------|
| `campaign_manifest.json` | Tier matrix, pathogen/combo/surveillance configs |
| `campaign_runner.py` | Spec generator + Picard executor (sharding + S3 upload) |
| `README.md` | This file |
| [`deploy/aws/`](../../../deploy/aws/README.md) | Dockerfile is at repo root; ECR + AWS Batch array-job deployment using IAM **role assumption** (short-lived creds) — bootstrap user → `picard-deploy-role`; containers use Batch execution/job roles |
