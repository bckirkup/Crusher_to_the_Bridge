---
name: mega-cruise-campaign-local
description: Run and validate the ~17780-run mega cruise campaign locally (smoke, dry-run, tiers, resume, sharding) before AWS Batch. Use when editing campaign_runner.py, tier_iterators.py, campaign_manifest.json, run_campaign scripts, or preparing a Batch submit.
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

In addition, each shard accumulates completed run dirs under
`<output_root>/_shard_runs/<run_id>/` and publishes a coalesced bundle
`<suffix>.zip` (nested `<run_id>/{summary,timeseries,run_spec}.json`) plus
`<suffix>.manifest.json` (`[{run_id, parameters, derived}]` in completion
order), where `<suffix>` is `shard-<i>` with `--shard-count` and `single`
without. Both are re-packed/re-uploaded every `--s3-log-every K` successes and
once at shard end; with an uploader configured each checkpoint prints
`fused <suffix>.zip + manifest (<n> runs) -> s3`.

### Testing the shard bundle locally

- `--output-dir` must resolve under the repo (or another non-world-writable
  root); `simulation_utils.paths` refuses `/tmp`
  ("Refusing to write under publicly writable directory").
- A run with `--platform destroyer_baseline --epochs 2 --num-agents 20` costs
  ~0.5 s, so multi-run + resume scenarios are cheap.
- Exercise the S3 code paths with no AWS by monkeypatching
  `campaign_runner.S3Uploader` with a class implementing
  `upload_file(Path, name)`, `download_file(name, Path) -> bool` (and
  optionally `object_exists`) backed by a local directory, then calling
  `campaign_runner.main([...])`. The resume gate consults the downloaded
  shard manifest, so a fake bucket is enough to test skip/append behavior.
- Running two shard indices into the **same** `--output-dir` lets the later
  shard's pack pick up the earlier shard's `_shard_runs/` entries (its zip
  becomes a superset; manifests stay disjoint). Use a separate output dir per
  shard locally — that matches per-container Batch filesystems.
- On `--resume` **without** `--s3-prefix` the in-memory manifest starts empty,
  so `<suffix>.manifest.json` is rewritten with only the newly executed runs
  while `<suffix>.zip` keeps the union. The `deploy/aws` readers dedupe by
  `run_id` and prefer zip contents, so aggregation is still complete, but do
  not treat a local-only-resume manifest as the full run list.

`generate_tier_runs` in `campaign_runner.py` dispatches `t1`–`t16` and
calibration shorts (`c1`–`c6`, `a2`, `b1`, `b2`) through
`tier_iterators.dispatch_standard_or_calibration` (a plain function that
returns an iterator or `None` — not a generator). `sr*` and `vd*` families
stay in `campaign_runner.py`. Nested cartesian products in new iterators
use `itertools.product` so new functions stay at cognitive complexity ≤15.

## Tests

```bash
python3 -m pytest tests/test_mega_cruise_campaign.py \
  tests/test_tier_iterators.py tests/test_campaign_boundaries.py -v --tb=short
```

`test_mega_cruise_campaign.py` is the behavior lock for dry-run cartesian
counts, surveillance ladder divergence, OA/compliance/immunity sweeps, smoke
zip layout, S3 resume mocks, HVAC OA sensitivity, shard partitioning, and
Campaign v5 T11/T15/T16 generators (decision latency, SOP AR thresholds,
reluctant fraction). `test_tier_iterators.py` locks the extracted iterator
table and seed grading; `test_campaign_boundaries.py` locks HVAC factor
mapping, shard partitions, and unknown-tier `ValueError`.

Outbreak-response knobs: skill `outbreak-response-architecture` +
`docs/tiered_escalation_spec.md`. Also run:

```bash
python3 -m pytest tests/test_outbreak_response_architecture.py -v --tb=short
```

## Natural-history clock

`--natural-history-clock {hours,legacy_epoch_day}` (default omitted = specs
unchanged, engine default is `hours`). The value is merged into every generated
spec's `config_overrides` and surfaced as `summary.json`
`parameters.natural_history_clock`, which `deploy/aws/aggregate_results.py`
flattens to the CSV column `parameters.natural_history_clock`.

`hours` is the supported configuration for new campaigns. The
`legacy_epoch_day` option is retained only to reproduce old runs; it is
retired for new campaigns and its historical numbers are not a reference.

Run IDs are identical across arms, so each arm needs its own `--output-dir`.
The runner drops `natural_history_clock.txt` in the output dir and exits
non-zero on a mismatched arm (this guard is what prevents a "silently skipped
every run via the resume log" empty arm). `--dry-run` does not write the marker.

Fast paired probe (~1.3 s/run; the calibration c1 tiers at 168 epochs are far
too slow for a smoke check):

```bash
R=picard_framework/runs/mega_cruise_campaign/campaign_runner.py
for c in hours legacy_epoch_day; do
  python3 $R --tier t1 --platform destroyer_baseline --epochs 24 \
    --num-agents 60 --limit 2 --natural-history-clock $c \
    --output-dir telemetry_buffer/arm_$c
done
```

At 24 epochs the arms diverge clearly (`hours` peaks ~epoch 17-22 with
`recovered: 0`; `legacy_epoch_day` peaks ~epoch 0-4 and has already recovered).
If matched-seed runs come out identical, the flag is not reaching
`engines/sim_clock.py`.

Caveat: the guard only protects dirs that already have a marker. A dir first
populated *without* the flag has no marker, so a later `--resume` with an arm
flag is accepted and marks it retroactively — the dir then mixes unflagged and
flagged runs (distinguishable in the CSV as empty vs. arm value). Always start
a fresh dir per arm.

AWS wiring: `deploy/aws/batch_job_definition.json` passes
`--natural-history-clock Ref::clock` (parameter default `hours`);
`deploy/aws/submit_array_job.sh` takes `CLOCK=` or a 6th positional arg and
forwards `clock=$CLOCK` in `--parameters`. To verify without submitting, put a
fake executable `aws` that echoes `"$@"` first on `PATH` and run the script.

### Current C1 single-dose refit

`c1_single_dose_hours_v1_manifest.json` is an hourly-only campaign with a
common 11.5–13.0 dose ladder at 0.25 steps, `n_init=1`, both `none_true` and
`syndromic`, and matched seeds 720–759 across four hulls. It enumerates 560
runs per hull and 2,240 total. Run its dry run with
`--natural-history-clock hours`; do not launch a new `legacy_epoch_day` arm.

### Current C1 reported-case hourly refit

`c1_reported_case_refit_v1_manifest.json` is the corrected-model norovirus
refit with four `c1_*` tiers, 720 runs per hull, and 2,880 total. It uses
`dose_adjustment` 12.0–14.0 at 0.25 steps, `n_init=1`, `none_true` plus
`syndromic`, and matched seeds 760–799. Run its hourly-only dry run with:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/c1_reported_case_refit_v1_manifest.json
python3 "$RUNNER" --manifest "$MANIFEST" \
  --tier all --natural-history-clock hours --dry-run
```

The scored `syndromic` endpoint is cumulative reported symptomatic passenger
cases divided by the passenger complement, not infections divided by the
complement. `none_true` is the matched counterfactual. Do not launch a new
`legacy_epoch_day` arm; keep the independent simulation tiers on Spot.

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
3. `tests/test_mega_cruise_campaign.py`, `tests/test_tier_iterators.py`, and
   `tests/test_campaign_boundaries.py` green.
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
