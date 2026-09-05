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

- Local directory of campaign artifacts: local runs may be individual
  `<run_id>.zip` files, while AWS Batch results are nested shard zips plus
  shard manifests (from `aws s3 sync`)
- For Batch failure classification: AWS CLI + `AWS_PROFILE=picard` (or equivalent)
- For Stan fits: `pip install -e '.[analysis]'` and CmdStan
  (`python3 -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'`)

## Sync from S3 (Batch campaigns)

```bash
AWS_PROFILE=picard aws s3 sync s3://<bucket>/campaign/ ./results/
```

## Analysis bundle + Stan hurdle (Phase 1b)

Converts zips into `run_summary.csv` + `epoch_timeseries.parquet` (or
`.csv.gz`), then fits a **two-stage** norovirus model:

1. **Stage A** — `P(outbreak)` (`norovirus_outbreak.stan`)
2. **Stage B** — trajectory | outbreak (`norovirus_trajectory.stan` with
   `reduce_sum`, slim GQ)

```bash
# Per-campaign bundle
python3 -m picard_framework.analysis.campaign_bundle ./results/c12c_fine_calibration/ \
  --out analysis/c12c_fine_calibration/

# Optional: merge C12c + C14/C14b for Step-2 monograph fit
python3 -u scripts/build_stan_step2_bundle.py

# Two-stage hurdle (recommended)
python3 -m picard_framework.analysis.stan.fit_norovirus_hurdle \
  analysis/analysis_stan_norovirus \
  --out-dir analysis/analysis_stan_norovirus/hurdle_fit \
  --chains-outbreak 4 --chains-trajectory 4 \
  --iter-warmup 1000 --iter-sampling 1000 \
  --seed 1701 --d0 10.6 --vsp-ref 0.03 \
  --threads-per-chain 4 --show-progress

# Report (bundle + optional stage dirs)
python3 -m picard_framework.analysis.report \
  analysis/analysis_stan_norovirus \
  analysis/analysis_stan_norovirus/hurdle_fit/trajectory \
  --out analysis/analysis_stan_norovirus/report.html
```

Stages can also be fit separately via
`fit_norovirus_outbreak` / `fit_norovirus_trajectory`.
See `picard_framework/analysis/stan/README.md` and
`docs/stan_analysis_tool_spec.md`. CmdStan is not required for the bundle CLI
or default pytest.

**Note:** `aggregate_metrics.outbreak_rate` uses `coerce_bool` so CSV-reloaded
`"False"` strings are not treated as truthy.

**Field lessons:** first full-scale Stage A fits diverged heavily; Stage B at
full outbreak N is multi-day. See `docs/stan_hurdle_lessons.md` before burning
a long Stage B run.

## Aggregate scalar summaries (ops)

```bash
python3 deploy/aws/aggregate_results.py ./results/ \
  --out-csv campaign_summary.csv \
  --out-json campaign_summary.json
```

Flattens each zip’s `summary.json` (`parameters.*`, `derived.*`, costs) into one
row per run.

## Check the swept axis resolved (do this first)

```bash
python3 -m picard_framework.analysis.sweep_degeneracy campaign_summary.csv \
  --axis parameters.dose_adjustment \
  --outputs derived.infection_attack_rate_passenger \
            derived.reported_case_attack_rate_passenger \
            derived.peak_prevalence \
  --group parameters.platform_id --group parameters.surveillance \
  --replicate parameters.seed --fail-on-degenerate
```

Reports which rungs of the axis produced identical output at every shared seed,
and the fraction of rungs that are distinguishable at all. A resolved fraction
below 1.0 means part of the ladder is replication rather than design, and any
interval read across that stretch is an artefact of the replication.

Read it before scoring, and run it on a two-rung local probe before submitting a
campaign: C1 spent 2,880 Batch runs on nine rungs that were one design point
(`docs/norovirus/c1_reported_case_bracket_result.md`).

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
- Fleet Stan column builders: `picard_framework/analysis/stan/_sentinel_fleet_reference.py`
  and `_sentinel_fleet_data.py`; lock with `tests/test_sentinel_fleet_columns.py`
