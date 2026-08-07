---
name: campaign-results-analysis
description: Aggregate mega-cruise campaign result zips, build epidemic curve tables, Stan calibration bundles, and classify AWS Batch array-child failures after S3 sync. Use after a campaign shard upload or local result collection.
---

# Campaign results analysis

Two complementary toolchains:

1. **Standardized analysis bundle + Stan** — `picard_framework/analysis/`
   (preferred for calibration / Bayesian trajectory fits)
2. **Lightweight ops aggregators** — `deploy/aws/` (CSV flatten after S3 sync)

Path I/O is confined to the process CWD via `simulation_utils.paths`
(see `tests/test_path_io_inviolate.py`).

## Prerequisites

- Local directory of `<run_id>.zip` files (from local campaign output or
  `aws s3 sync`)
- For Batch failure classification: AWS CLI + `AWS_PROFILE=picard` (or equivalent)
- For Stan fits: `pip install -e '.[analysis]'` and CmdStan
  (`python3 -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'`)

## Sync from S3 (Batch campaigns)

```bash
AWS_PROFILE=picard aws s3 sync s3://<bucket>/campaign/ ./results/
```

## Analysis bundle + Stan (Phase 1)

Converts zips into `run_summary.csv` + `epoch_timeseries.parquet` (or
`.csv.gz`), pairwise deltas, figures, then optional norovirus Stan fit.

```bash
# Point at local C12c / C14 (or any) zip directory:
python3 -m picard_framework.analysis.campaign_bundle ./results/c12c/ --out analysis/
python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit/
python3 -m picard_framework.analysis.report analysis/ stan_fit/ --out report.html
```

See `picard_framework/analysis/stan/README.md` and
`docs/stan_analysis_tool_spec.md`. CmdStan is not required for the bundle CLI
or default pytest.

## Aggregate scalar summaries (ops)

```bash
python3 deploy/aws/aggregate_results.py ./results/ \
  --out-csv campaign_summary.csv \
  --out-json campaign_summary.json
```

Flattens each zip’s `summary.json` (`parameters.*`, `derived.*`, costs) into one
row per run.

## Epidemic curves / frontiers (ops)

```bash
python3 deploy/aws/analyze_campaign_curves.py ./results/ \
  --out-csv campaign_curves.csv \
  --out-frontiers campaign_frontiers.csv
```

- `--out-csv` — one row per `(run_id, epoch)` with infected/recovered/… plus
  sweep tags (`oa*`, `imm*`, `comp*`, …)
- `--out-frontiers` — one row per run (attack rate, peak prevalence, tags)

## Classify Batch failures

```bash
AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \
  --job-id <parentArrayJobId> --region us-east-1 \
  --out-json failure_report.json

# Or by queue / optional S3 upload of the report
AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \
  --queue picard-campaign-queue --region us-east-1 \
  --s3-uri s3://<bucket>/campaign/_ops/failure_report.json
```

Separates Spot reclaim vs OOM (exit 137) vs timeout vs other so you can decide
whether to escalate Fargate memory or just re-submit Spot.

## Related

- Spec: `docs/stan_analysis_tool_spec.md`
- Local campaign ops: `.agents/skills/mega-cruise-campaign-local/SKILL.md`
- AWS deploy gotchas: `.agents/skills/aws-batch-campaign/SKILL.md`
- Canonical deploy doc: `deploy/aws/README.md`
