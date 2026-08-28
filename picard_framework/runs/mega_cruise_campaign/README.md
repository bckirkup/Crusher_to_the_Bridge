# Mega Cruise Campaign

~17,780 Picard runs on `mega_cruise_5000` (default 7000 agents, 240 epochs)
after the HVAC star-topology + analytical mass-balance fixes.

## Tiers

Legacy v4 matrix (~17,780) is t1–t10. Campaign v5 adds outbreak-response
sweeps (see `docs/tiered_escalation_spec.md`):

| Tier | What | Dimensions | Runs (approx) |
|------|------|-----------|------|
| t1 | Pathogen baselines | 10 pathogens × 30 seeds | 300 |
| t2 | HVAC parameter sweep | 4 × 5 filters × 5 OA × 3 decay × 15 seeds | 4500 |
| t3 | Surveillance strategies | 10 × 4 strategies × 30 seeds | 1200 |
| t4 | Full factorial | 4 × 3 filters × 3 decay × 4 surv × 20 seeds | 2880 |
| t5 | Multi-pathogen | 5 combos × 4 surv × 20 seeds | 400 |
| t6 | Dose-response | 4 × 6 doses × 5 immunity × 30 seeds | 3600 |
| t7 | Compliance | 4 × 4 surv × 5 compliance × 5 immunity × 10 seeds | 4000 |
| t8 | Wearables | 4 × 3 configs × 4 surv × 10 seeds | 480 |
| t9 | Slow pathogens (21d) | 4 × 4 surv × 20 seeds | 320 |
| t10 | Population size | 2 × 5 sizes × 10 seeds | 100 |
| t11 | Decision latency | 4 pathogens × 5 latency × 2 surv × 2 compliance × 5 seeds | 400 |
| t15 | SOP AR thresholds | 4 × 4 suspect_AR × 4 lockdown_AR × 5 seeds | 320 |
| t16 | Reluctant fraction | 4 × 3 reluctant_frac × 4 delay × 5 seeds | 240 |

## Multi-platform calibration (`calibration_manifest_v1.json`)

Separate campaign (~6,360 runs if all tiers; **wave-1 default ~5,960**
without deferred C2). CDC VSP AGE rate matching via `dose_adjustment`
sweeps across `expedition_cruise_450` / `classic_cruise_1900` /
`spirit_cruise_3000` / `mega_cruise_5000`. Agent counts come from the
runner’s platform table (450 / 1910 / 3000 / 7000), not
`default_num_agents`.

| Tier | What | Runs |
|------|------|------|
| c1_* (4) | Norovirus dose × init infected × surveillance | 1820 |
| c2 | Immunity × platforms — **deferred** until C1 pins `dose_adjustment` | 400 |
| c3 | SARS-CoV-2 dose × platforms (Diamond Princess cross-check) | 360 |
| c4 | Voyage duration (72/168/336 epochs) × dose | 180 |
| c5 | Density-dependent contact α × dose × platforms × immunity × surv | 3600 |
| c6 | Density vs heterogeneous_zone_dose sensitivity (pinned α/dose) — **deferred** | 160 |

Dining / free-zone rotation (`agent_behavior.dining_rotation_probability`) is
off by default in `crusher_labs/config.yaml`. Raise it in campaign
`config_overrides` when testing whether venue mixing shrinks platform
`dose_adjustment` gaps (see `docs/multi_pathogen_model_changes_spec.md`).

Follow-on sensitivity waves reuse the same multi-platform generator under
short prefix `a2` (e.g. Downloads `sensitivity_a2_phase1_manifest.json`:
fine `dose_adjustments` × FUT2 `pre_immunity_fractions` at a pinned
`density_exponents` value). `--tier a2` selects all `a2_*` tiers.

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json
RUNNER=picard_framework/runs/mega_cruise_campaign/campaign_runner.py

# Wave 1 (skips deferred c2)
python3 "$RUNNER" --manifest "$MANIFEST" --dry-run
python3 "$RUNNER" --manifest "$MANIFEST" --tier c1 --limit 1 --epochs 6 --num-agents 50

# After C1 analysis: edit c2 with dose_adjustment, then
python3 "$RUNNER" --manifest "$MANIFEST" --tier c2 --dry-run
```

Use a distinct S3 prefix for Batch (e.g. `s3://…/campaign/calibration_v1/`).

### Natural-history clock selection

The campaign runner accepts `--natural-history-clock hours` or
`--natural-history-clock legacy_epoch_day`. The flag is optional, leaves
existing generated specs unchanged when absent, and records the selected arm
in `parameters.natural_history_clock` for aggregation. `hours` is the
supported configuration for new campaigns. `legacy_epoch_day` is retired and
is retained only to reproduce old runs; it is not a reference or a supported
new-campaign arm.

Historical paired calibration arrays used separate S3 prefixes so their
unchanged run IDs and resume logs could not collide:

```bash
CLOCK=hours ./deploy/aws/submit_array_job.sh 80 \
  s3://bucket/calibration_hours/ picard-campaign-queue picard-campaign \
  "$MANIFEST"
CLOCK=legacy_epoch_day ./deploy/aws/submit_array_job.sh 80 \
  s3://bucket/calibration_legacy/ picard-campaign-queue picard-campaign \
  "$MANIFEST"
```

The local output directory records its selected arm in
`natural_history_clock.txt`; requesting a different arm against that directory
fails clearly. An invocation without the flag remains compatible with an
existing marked directory and does not hard-fail.

### Historical C1 VSP refit paired arms

`clock_arm_c1_v1_manifest.json` is the focused C1 norovirus VSP refit manifest.
It contains four simulation tiers: 480 expedition runs and 640 runs for each
of classic, spirit, and mega, or 2,400 runs when selecting `--tier all`.
This paired-arm campaign is historical. The legacy arm is retired; reproduce
an old result only when needed, always using separate S3 prefixes:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/clock_arm_c1_v1_manifest.json
AWS_PROFILE=picard CLOCK=hours ./deploy/aws/submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/clock_hours/" picard-campaign-queue \
  picard-campaign "$MANIFEST"

AWS_PROFILE=picard CLOCK=legacy_epoch_day ./deploy/aws/submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/clock_legacy/" picard-campaign-queue \
  picard-campaign "$MANIFEST"
```

The two arms intentionally have identical run IDs. A shared prefix would
silently mix the two models in one shard bundle, and the resume log would make
the second arm's runs appear already complete. The shell submitter and default
job definition do not provide `--tier`; for one tier, use a dedicated manifest
or the PowerShell submitter's `-Tier` container override. Submit only the
independent, checkpointed simulation tiers to Fargate Spot. Stan and Sentinel
inference tiers must run on a non-Spot path because their fits do not survive
an interruption.

### Current C1 single-dose hourly refit

`c1_single_dose_hours_v1_manifest.json` is the current hourly-only
single-dose norovirus VSP test. It uses the same 11.5–13.0
`dose_adjustment` ladder at 0.25 steps, `n_init=1`, both `none_true` and
`syndromic`, and matched seeds 720–759 across all four hulls. Each hull
enumerates 560 runs, for 2,240 runs with `--tier all`:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/c1_single_dose_hours_v1_manifest.json
python3 "$RUNNER" --manifest "$MANIFEST" \
  --tier all --natural-history-clock hours --dry-run
```

This campaign is hourly-only. `legacy_epoch_day` is retired and is not run
here; its historical numbers are not a reference. Use a distinct S3 prefix
from the historical C1 refit campaign, and keep only the independent,
checkpointed simulation tiers on the Spot path.

### Current C1 reported-case hourly refit

`c1_reported_case_refit_v1_manifest.json` is the corrected-model norovirus
refit. It uses a common 12.0–14.0 `dose_adjustment` ladder at 0.25 steps,
`n_init=1`, both `none_true` and `syndromic`, and matched seeds 760–799 across
all four hulls. Each hull enumerates 720 runs, for 2,880 runs with
`--tier all`:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/c1_reported_case_refit_v1_manifest.json
python3 "$RUNNER" --manifest "$MANIFEST" \
  --tier all --natural-history-clock hours --dry-run
```

The scored endpoint is cumulative reported symptomatic **passenger** cases
divided by the passenger complement on the `syndromic` branch, not infections
divided by the complement. The `none_true` runs are the matched
counterfactual. This campaign is hourly-only; do not run a new
`legacy_epoch_day` arm, and keep its independent simulation tiers on the Spot
path rather than Stan inference.

Mega-cruise runs inject `escalation.lockdown_attack_rate: 0.05` (default
`config.yaml` uses `never` for small smokes).

### T11 intervention timing

Two generator modes (pick one key in the tier):

| Manifest key | What it sweeps | Optional cross |
|--------------|----------------|----------------|
| `decision_latency_levels` | Organizational SOP delay (`escalation.decision_latency`) | `compliance_levels` → run ids `…_lat{N}_comp{pct}_s{seed}` |
| `surveillance_delay_epochs` | Surveillance activation delay (`activation_delay_hours` on syndromic + cascade) | `compliance_levels` → run ids `…_delay{N}_comp{pct}_s{seed}` |

If `compliance_levels` is omitted, both modes keep the previous single-compliance
run-id shape (no `_comp` tag). Campaign v6 controllable manifests use the
legacy delay key with an explicit compliance grid.

## Surveillance presets

Named overrides live under `surveillance_configs` in `campaign_manifest.json`.
Existing tiers keep using soft `"none"` (sick-call / cascade off only). New
campaigns can select the stronger presets or compose the switches directly via
`config_overrides`:

| Preset | Sick-call / cascade | Env observation (air/swab/WW/PCR/seq) | Wearables | VSP counter confinement |
|--------|---------------------|--------------------------------------|-----------|-------------------------|
| `none` | off | on | on | on |
| `none_env` | off | off (`observation.enabled: false`) | on | on |
| `none_true` | off | off | off | off (`counter_confinement_enabled: false`) |
| `syndromic` | cascade off; sick-call default | on | on | on |
| `cascade` / `cascade_mpx` | cascade on | on | on | on |

Composable switches (defaults preserve current behavior):

- `observation.enabled` — master gate for environmental + clinical sampling and Picard PCR/seq cadence
- `ship_graph.counter_confinement_enabled` — when false, infection counters still log but do not confine
- `wearable_monitoring.enabled` — existing wearable off switch

Example for a true-off baseline tier: `"surveillance": "none_true"` or
`"surveillance_strategies": ["none_true", "syndromic", "cascade"]`.

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

containing `run_spec.json`, `summary.json` (final SIR + costs + trigger +
`parameters` factor block + `derived` metrics: attack rate, peak
prevalence/epoch, detection/confirmation lag, quarantine person-epochs,
R_eff at peak, …), and `timeseries.json` (a compact per-epoch epidemic /
contamination / trigger / cost series, ~50 KB).

`summary.json` is the bookkeeping unit: structured `parameters` (tier,
pathogen, seed, HVAC/OA/decay/surveillance/compliance/… labels and resolved
numerics) sit next to outcomes so results are self-describing without parsing
`run_id` or reloading the manifest. `deploy/aws/aggregate_results.py`
flattens `parameters.*` into CSV columns alongside `derived.*`.

For standardized calibration tables and Stan trajectory fits, use the adjacent
analysis package (see `docs/stan_analysis_tool_spec.md`):

```bash
python3 -m picard_framework.analysis.campaign_bundle ./results/ --out analysis/
python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit/
python3 -m picard_framework.analysis.report analysis/ stan_fit/ --out report.html
```

Use `--full-telemetry` to force `history_retention=full` and also pack history
/ lab notebook / ground truth (much larger and slower).

### Memory isolation

Two layers:

1. **Within a run** — campaign specs default to `run.history_retention=compact`,
   so epoch history keeps only summary / spaces / cost scalars (no per-agent
   snapshots, contact-tracing matrices, or raw assay payloads). That stops
   RSS from growing roughly linearly with epochs. Full telemetry is opt-in via
   `--full-telemetry`.
2. **Across runs** — each run executes in a fresh subprocess so the OS
   reclaims all RSS on exit. Repeated 7000-agent runs otherwise leak via
   CPython/`pymalloc` and exceed Fargate after ~20–40 in-process runs. Pass
   `--in-process` to run in the parent (faster for debugging; leaks across
   many large runs), and `--timeout SECONDS` to bound each subprocess
   (default **3600**; ~30 min 7000-agent runs need more than the old 600s cap).
   Failed/successful runs write `{run_id}.resource.json` (peak RSS via
   Linux `VmHWM`); failures also write `{run_id}.failure.json`.

Default Fargate sizing is **1 vCPU / 2048 MB** (see `deploy/aws/`). Escalate
via `classify_batch_failures.py` if OOM (exit 137) appears.

Progress for `--resume` is appended to:

`telemetry_buffer/mega_cruise_campaign/completed_runs.txt`

Failed run_ids are appended to `failed_runs.txt`. Use `--retry-failed` to
re-run only those ids (clears leftover workdirs / stderr first; still skips
completed runs).

## Sharding & S3 (AWS Batch / distributed runs)

The runner can split the run list into disjoint shards and upload results to S3,
so the campaign can run as one AWS Batch array job of many Fargate Spot
containers. See [`deploy/aws/`](../../../deploy/aws/README.md) for the full
ECR + Batch workflow.

Each shard periodically refreshes one fused zip and one JSON manifest. The zip
contains every completed run under `<run_id>/`, while the manifest lists each
run's parameters and derived metrics. Terminal progress is tracked by the
shard-scoped resume-log line counts; for example:

```bash
aws s3 sync s3://$BUCKET/$PREFIX/_resume/ ./_resume/ && cat ./_resume/completed_runs.shard-*.txt | wc -l
```

| Flag | Meaning |
|------|---------|
| `--shard-count N` | Total number of shards. A run executes only when `global_index % N == shard_index`, where `global_index` is its position in the full flattened, ordered run list across the selected tiers. |
| `--shard-index i` | This shard's index in `[0, N)`. Defaults to the `AWS_BATCH_JOB_ARRAY_INDEX` env var when present (so Batch array child *i* runs shard *i*). |
| `--s3-prefix s3://bucket/path` | Upload one periodically refreshed `<suffix>.zip` and `<suffix>.manifest.json` per shard (`shard-3.*`, or `single.*`), plus the shard's resume log. With `--resume`, both shard artifacts and the resume log are downloaded from `<s3-prefix>` before skipping. Requires `boto3`. |
| `--s3-log-every K` | Upload the fused shard zip, JSON manifest, and resume log every `K` successful runs (default 25). |
| `--retry-failed` | Re-run only ids in `failed_runs.txt` (clears their leftover artifacts first). |

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

At ~3 min/run for the full mega cruise, the campaign is ~890 hours wall-clock
serially (~17,780 runs). Parallelize by launching different `--tier` values on
different machines, or run one AWS Batch array job of N Fargate Spot children
with `--shard-count N` (~890/N hours wall-clock; e.g. N=200 ≈ 4.5 hours).
Tier 1 alone: ~15 hours (300 × 3 min).

## Files

| File | Role |
|------|------|
| `campaign_manifest.json` | Mega-cruise tier matrix (~17,780) |
| `calibration_manifest_v1.json` | Multi-platform calibration matrix (c1–c4) |
| `clock_arm_c1_v1_manifest.json` | Historical paired-clock C1 VSP refit |
| `c1_single_dose_hours_v1_manifest.json` | Hourly-only single-dose C1 VSP refit |
| `c1_reported_case_refit_v1_manifest.json` | Corrected-model reported-case C1 refit |
| `tier_iterators.py` | `t1`–`t16` and calibration (`c1`–`c6`, `a2`, `b1`, `b2`) cartesian generators; `dispatch_standard_or_calibration` |
| `campaign_runner.py` | Spec generator + Picard executor (sharding + S3 upload); `sr*` / `vd*` families stay here |
| `README.md` | This file |
| [`deploy/aws/`](../../../deploy/aws/README.md) | Dockerfile is at repo root; ECR + AWS Batch array-job deployment using IAM **role assumption** (short-lived creds) — bootstrap user → `picard-deploy-role`; containers use Batch execution/job roles |
