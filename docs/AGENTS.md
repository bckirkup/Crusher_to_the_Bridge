# Crusher-to-the-Bridge — Agent Instructions

> See also the human docs map: [README.md](README.md).

## Cursor Cloud specific instructions

Pure-Python simulation (no databases or external APIs for local dev). **Python 3.11+** required. Docker is used only to package the mega cruise campaign for AWS Batch (see `deploy/aws/`); it is not needed for local development.

### Running services

| Service | Command | Notes |
|---------|---------|-------|
| Ship simulation (legacy CLI) | `python3 orchestrator.py` | Standalone epoch loop; 24 epochs default |
| Picard programmatic API | See `docs/OPERATORS_MANUAL_SHIP.md` | `PicardRunSpec` + `ShipSimulation` |
| Fleet meta-simulation | `python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1` | Fast smoke; default fleet is slower |
| Utility export (external optimizer) | `python3 presidio_runner.py --export-utility-dir presidio/data/experiences/utility_bundles` | Requires `social` block on run spec |
| Action import (external optimizer) | `python3 presidio_runner.py --import-actions-dir <dir>` | Per-epoch `cruise_*_epoch_*_actions.json` |
| Streamlit dashboard | `python3 -m streamlit run dashboard.py --server.headless true` | Run orchestrator first for telemetry |
| Deck asset precompute | `python3 scripts/precompute_deck_assets.py` | Writes `deck_graphics.geojson`, hull PNG, manifest per platform |
| Sanity checker | `python3 tools/sanity_checker.py --from-config` | Ship + fleet + Stackelberg social configs |
| Full test suite | `python3 -m pytest tests/ -v --tb=short` | ~875 tests, ~8s |
| Wearable anomaly scoring | `python3 -m pytest tests/test_wearable_anomaly_scorer.py tests/test_cascade_entry.py -v` | Confounder-aware infection_score + cascade entry fusion |
| Diagnostic cascade smoke | `python3 -m pytest tests/test_smoke_diagnostic_cascade.py -v` | 6-epoch runs with cascade enabled (standard + multiplex specs) |
| Long-read / TAT tests | `python3 -m pytest tests/test_long_read_sequencing.py tests/test_instrument_turnaround.py -v` | Nanopore + turnaround queue |
| Mega cruise campaign | `./run_campaign.sh --smoke` or `run_campaign.bat --smoke` | Full matrix ~17,780 runs: `picard_framework/runs/mega_cruise_campaign/` |
| Campaign (sharded) | `python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --shard-count N --shard-index i --s3-prefix s3://bucket/campaign/ --resume` | `--shard-index` defaults to `AWS_BATCH_JOB_ARRAY_INDEX`; uploads each `<run_id>.zip` + `completed_runs.txt` to S3 (needs `boto3`) |
| Campaign Docker image | `docker build -t picard-campaign . && docker run --rm picard-campaign --smoke` | Root `Dockerfile`; ECR + AWS Batch array-job flow in `deploy/aws/README.md` |
| Campaign deploy (AWS) | `AWS_PROFILE=picard ./deploy/aws/submit_array_job.sh N s3://<bucket>/campaign/` | **Role-assumption creds**: a minimal `devin-bootstrap` user only `sts:AssumeRole`s `picard-deploy-role` (ExternalId, 1h sessions) via a `~/.aws/config` profile; containers use Batch execution/job roles. IAM JSON + full flow in `deploy/aws/README.md` |

### Framework layout

| Path | Role |
|------|------|
| `picard_framework/` | Ship run spec, catalog, `ShipSimulation` |
| `decision_engine/` | Policies, Stackelberg round, diffusion, utility I/O |
| `presidio/` + `presidio_runner.py` | Fleet cruises, experience store, economics |
| `orchestrator*.py` | Legacy epoch helpers used by Picard |
| `dashboard/` | LCARS Streamlit package (`dashboard.py` is the entry script) |
| `scripts/` | Enterprise platform builder, deck graphics, asset precompute |
| `telemetry_buffer/agent_axes.py` | Canonical orthogonal agent state literals |

### Operator manuals

- Ship / Picard: `docs/OPERATORS_MANUAL_SHIP.md`
- Fleet / Stackelberg: `docs/OPERATORS_MANUAL_GAME_THEORY.md`
- Full legacy reference: `docs/OPERATORS_MANUAL.md`

### CI (replicate locally)

Install from the hash-pinned lockfile: `pip install --only-binary=:all: --require-hashes -r requirements.lock.txt`.

**Main** (`.github/workflows/ci.yml` on `main` PRs):

1. `ruff check` — **F-rules blocking**; E/W/I advisory
2. `python3 tools/sanity_checker.py --from-config`
3. `pytest tests/test_json_schema_validation.py -v --tb=short`
4. `pytest tests/ -v --tb=short --cov --cov-report=term-missing` (~875 tests)
5. Picard/Presidio/Stackelberg import hygiene
6. Presidio smoke (`smoke_fleet.json`, 1 cruise)
7. Orchestrator import hygiene (stoplight deduplication)
8. Dashboard import + `apply_lcars_layout` smoke
9. `python3 orchestrator.py` — 24-epoch smoke
10. OIS fields present in final `cost_accounting`
11. Campaign Docker image smoke (`docker build` + `docker run … --smoke`) when Docker is available

**Picard/Presidio** (`.github/workflows/picard-presidio.yml` on `main` and `cursor/**`):

- Framework-focused pytest slice (~190+ tests: Picard, Presidio, Stackelberg, OIS, behavioral, long-read, TAT, enterprise platforms, agent axes, sequencing config, wearable scoring, cascade entry, ContamX subset, mega-cruise campaign, campaign/ship/Stan boundary tests, outbreak response, golden Picard, cabin/shedding, pathogen overrides, density contact, multi-pathogen Phase A/B)
- Stackelberg + platform JSON schema validation (all `data/platforms/*/`)
- Presidio smoke

### Agent skills

| Skill | Use when |
|-------|----------|
| `picard-ship-simulation` | `picard_framework/`, `ShipSimulation` |
| `presidio-fleet-run` | `presidio_runner.py`, fleet configs |
| `stackelberg-utility-export` | Social config, utility bundles, action import |
| `testing-picard-presidio` | Before PRs on framework code |
| `sonar-quality` | Before source/workflow edits; complexity-backlog splits (C901 117, new-code 15) |
| `configuring-stackelberg-social` | Adding/editing diffusion, class interactions, profiles |
| `operational-impact-behavioral-policies` | OIS weights, action kinds, ThresholdBeliefPolicy |
| `outbreak-response-architecture` | Escalation levels, decision latency, bimodal compliance, T11/T15/T16 |
| `run-full-test-suite` | Any pre-PR validation |
| `ci-test-design` | Designing golden-value + config-sensitivity tests |
| `long-read-sequencing` | Long-read params, TAT config, escalation, `LongReadNanoporeSequencing` |
| `orchestrator-smoke-test` | After orchestrator, engine, or `config.yaml` changes |
| `wearable-anomaly-scoring` | `wearable_anomaly_scorer.py`, `anomaly_detection` config, cascade entry `infection_score` rules |
| `diagnostic-cascade` | Tier 0–3 cascade configs, multiplex specs, SOP gating |
| `testing-dashboard` | After `dashboard/` or telemetry field changes |
| `testing-data-contracts` | After JSON config or platform/pathogen edits |
| `testing-agent-classes` | Agent class, gender, duty zone, exempt_classes changes |
| `schema-validation` | Before committing JSON in `data/` or `telemetry_buffer/` |
| `adding-new-platform` | New vessel spatial layout + HVAC |
| `importing-naval-blueprint` | GA PDF/image → ShipDigest + SVG overlay → platform JSON |
| `adding-new-pathogen` | New pathogen profile entries |
| `contamx-interop` | ContamX SIM reader, AHS bridge, compare suite, flow diagnostics |
| `mega-cruise-campaign-local` | Local `--smoke` / `--dry-run` / shard hygiene; synthetic recovery + VSP degradation (`docs/synthetic_recovery_and_vsp_degradation.md`) |
| `campaign-results-analysis` | Analysis bundle + two-stage Stan hurdle (outbreak + trajectory); see `docs/stan_hurdle_lessons.md` for Step-2 field notes |
| `preboarding-wearable-decision` | Pre-boarding wearable ROI / policy Monte Carlo (`picard_framework/analysis/boundary/`); fixture or Stan `outbreak_surface` lookup |
| `boundary-aws-pipeline` | `boundary_surface_v1` Spot campaign + On-Demand surface/Stan/MC (`deploy/aws/`, Bernoulli+Beta-AR) |
| `aws-batch-campaign` | Running large Crusher simulation batches on AWS Batch / Fargate Spot |
| `managing-github-issues` | Issue triage, batching, PR lifecycle |
| `download-deepwiki` | Offline DeepWiki export for a public GitHub repo |

### Important caveats

- Use `python3` (not `python`) on Linux cloud VMs.
- Dashboard reads `telemetry_buffer/simulation_history.json` and `telemetry_buffer/artificial_lab_notebook.json`.
- Dashboard implementation lives in `dashboard/`; `streamlit run dashboard.py` imports the package.
- Observation results in telemetry reflect **delivered** assays (TAT queue), including `pending` long-read runs until `available_epoch`.
- **Law 1:** No hardcoded epoch SOP schedules; Stackelberg `authorize_sop_subset` filters stoplight-eligible SOPs; `activate_sop` can force protocols via `forced_protocol_ids`.
- **OIS:** Fourth ledger dimension in `cost_accounting`; configured via `operational_impact_weights` in `resource_costs.json`.
- Utility **weights and optimization** are out-of-repo; only feature export and action apply are in-repo.
- Nine ship platforms in `data/platforms/` (including fiction-adapted Enterprise bundles and legacy `messy_cruise_500`); see `README.md` Platforms table.
- **Wearable cascade entry** uses confounder-aware `infection_score` (not raw `anomaly_count`) via `diagnostic_cascade.entry.wearable_alert_fusion` or defaults in `data/config/diagnostic_cascade*.json`. Fleet stoplight SOPs (SOP-013/014) still use shipwide `anomaly_rate`.
- **Complexity backlog:** new functions stay at cognitive complexity ≤15. Campaign `t1`–`t16` / calibration iterators live in `tier_iterators.py`; `ShipSimulation.step` is `_begin_epoch` plus `_step_*` phases. See skill `sonar-quality`.
- **Outbreak response architecture:** SOP policy (attack-rate escalation + `min_escalation_status`), organizational decision latency (`escalation.decision_latency` / SOP `activation_delay_epochs`), and bimodal compliance (compliant/reluctant/defiant) are separate systems — see `docs/tiered_escalation_spec.md` and skill `outbreak-response-architecture`. Default `lockdown_attack_rate: never` for n=20 smokes; mega-cruise campaign injects `0.05`.
- **Shedding variance:** `shedding_variance_log10` on pathogen profiles draws a persistent per-agent multiplier at infection (`docs/SHEDDING_AND_CABINMATES.md`).
- **Cabin-mates:** `mega_cruise_5000` `Cabin_Corridor` zones pair agents into staterooms at init; confinement direct contact is cabin-mate-aware (`assign_cabin_mates` in `orchestrator_init.py`).
- **Contact mode:** default `transmission.contact_mode: density_dependent` (`docs/density_contact_spec.md`); `legacy` and opt-in `heterogeneous_zone_dose` available.
- **Multi-pathogen calibration knobs:** `transmission_route_weights`, log10 `dose_adjustment`, `innate_nonsusceptible_fraction`, `agent_behavior` dining/free rotation (default off), Dining `food_contamination_multiplier` / `dining_service_type`, env `source_zones` — see `docs/multi_pathogen_model_changes_spec.md`.
- Ruff lint: **F-rules are blocking** in main CI; E/W/I remain advisory (`continue-on-error` / `|| true`). Keep unused-import and undefined-name findings clean before campaigns.
- **SonarCloud** uses GitHub-app Automatic Analysis (Autoscan). Configure analysis via in-repo `.sonarcloud.properties` (`sonar.python.version`, `sonar.tests`, exclusions) — not `sonar-project.properties` (that file is ignored while Autoscan is on). Agents still rely on ruff, `tests/test_path_io_inviolate.py`, and pytest for local gates; do not block on live Sonar MCP/CLI unless explicitly integrating.
