---
name: run-full-test-suite
description: Run the complete Crusher-to-the-Bridge pytest suite including data contracts, sanity checks, orchestrator tests, law compliance, and all module tests. Use before creating PRs or after any code change.
---

# Run Full Test Suite

## Prerequisites

- Python 3.11+ with dependencies from `requirements.lock.txt` (or `requirements.txt`)
- Working directory: **repo root**

## Devin Secrets Needed

None — all tests run locally.

## Quick Commands

### Run the entire test suite
```bash
python3 -m pytest tests/ -v --tb=short
```
Expected: ~875 tests pass in ~8s.

### Run with coverage reporting
```bash
python3 -m pytest tests/ -v --tb=short --cov --cov-report=term-missing
```
Coverage sources: `engines/`, `crusher_labs/`, `picard_framework/`, `decision_engine/`, `orchestrator_*.py`.

### Run ruff lint (advisory, non-blocking)
```bash
ruff check --select E,F,W,I --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ orchestrator*.py presidio_runner.py
```
Expected: ~65 findings (mostly import ordering). This is advisory — `continue-on-error: true` in CI.

### Run individual test modules
```bash
# Data contract validation (pathogen profiles, spatial layout, airflow, protocols, resource costs)
python3 -m pytest tests/test_data_contracts.py -v --tb=short

# JSON schema validation (all platforms, social configs, fleet configs)
python3 -m pytest tests/test_json_schema_validation.py -v --tb=short

# Sanity checker (pydantic model validation + referential integrity)
python3 -m pytest tests/test_sanity_checker.py -v --tb=short

# Orchestrator integration tests (quarantine, SOP confinement, zone closures)
python3 -m pytest tests/test_orchestrator.py -v --tb=short

# Infection counters and exempt_classes confinement
python3 -m pytest tests/test_infection_counters.py -v --tb=short

# CONTAM physics (HVAC mass-balance, ACH, filter efficiency, natural decay)
python3 -m pytest tests/test_py_contam_bridge.py -v --tb=short

# ContamX seam (SIM reader embedded path nr, AHS bridge, compare/flow tools)
python3 -m pytest tests/test_contamx_solver.py tests/test_contamx_ahs_bridge.py \
  tests/test_contam_flow_compare.py tests/test_contam_engine_compare.py -v --tb=short

# Shedding variance + cabin-mate transmission
python3 -m pytest tests/test_shedding_variance_cabin_mates.py tests/test_cabin_corridor_transmission.py -v --tb=short

# Golden Picard parity (ShipSimulation vs orchestrator SIR comparison)
python3 -m pytest tests/test_golden_picard.py -v --tb=short

# Transmission core + infection dynamics (dose-response, shedding, multi-pathway)
python3 -m pytest tests/test_transmission_infection_expanded.py -v --tb=short

# Food/environmental transmission pools
python3 -m pytest tests/test_transmission_pathways.py -v --tb=short

# Dashboard extended (spatial_viz, deck_geometry, pydeck, fleet_viz, theme)
python3 -m pytest tests/test_dashboard_extended.py -v --tb=short

# Dashboard import and pathway aggregation
python3 -m pytest tests/test_dashboard.py -v --tb=short

# Scripts and GIS tools (blueprint, resolve_column, group_hvac_zones)
python3 -m pytest tests/test_scripts_tools.py -v --tb=short

# Crusher Labs modalities (fidelity, lab_notebook, RDT, sequencing, PCR)
python3 -m pytest tests/test_crusher_labs_modalities.py -v --tb=short

# Protocol engine (stoplight evaluation, SOP activation)
python3 -m pytest tests/test_protocol_engine.py -v --tb=short

# Cost ledger (budget, labor, materials, OIS)
python3 -m pytest tests/test_cost_ledger.py tests/test_operational_impact.py -v --tb=short

# Action envelopes, campaign seams, and Stan fleet columns
python3 -m pytest tests/test_action_applier.py tests/test_behavioral_syndromic.py \
  tests/test_tier_iterators.py tests/test_campaign_boundaries.py \
  tests/test_ship_epoch_helpers.py tests/test_sentinel_fleet_columns.py -v --tb=short

# Law compliance (architectural invariants, extended to picard_framework/crusher_labs/decision_engine)
python3 -m pytest tests/test_law_compliance.py -v --tb=short

# Picard / Presidio / Stackelberg
python3 -m pytest tests/test_picard_framework.py tests/test_decision_engine.py \
  tests/test_presidio_runner.py tests/test_stackelberg.py tests/test_golden_orchestrator.py -v --tb=short

# Telemetry seams (ground truth read/write)
python3 -m pytest tests/test_telemetry_seams.py -v --tb=short

# Agent axes (orthogonal infection/presentation/compliance)
python3 -m pytest tests/test_agent_axes.py -v --tb=short

# Enterprise platform referential integrity
python3 -m pytest tests/test_enterprise_platforms.py -v --tb=short

# Sequencing config wiring (read_depth from config.yaml)
python3 -m pytest tests/test_sequencing_config.py -v --tb=short

# Per-test cost accounting telemetry
python3 -m pytest tests/test_cost_accounting.py -v --tb=short

# Diagnostic cascade (tier progression + smoke)
python3 -m pytest tests/test_diagnostic_cascade.py tests/test_smoke_diagnostic_cascade.py -v --tb=short

# Wearable anomaly scoring + cascade entry fusion
python3 -m pytest tests/test_wearable_anomaly_scorer.py tests/test_cascade_entry.py -v --tb=short

# Enhanced wearable model (multi-device, confounders, chronic disease)
python3 -m pytest tests/test_wearable_enhanced.py tests/test_chronic_disease.py -v --tb=short

# Mega cruise campaign (dry-run, smoke zip, shards, aggregators, T11/T15/T16)
python3 -m pytest tests/test_mega_cruise_campaign.py \
  tests/test_outbreak_response_architecture.py -v --tb=short

# Contam hobbyist PRJ exports + path I/O inviolate
python3 -m pytest tests/test_contam_hobbyist_constitution.py tests/test_contam_hobbyist_destroyer.py \
  tests/test_contam_hobbyist_galaxy.py tests/test_contam_hobbyist_mega.py \
  tests/test_path_io_inviolate.py -v --tb=short

# Schema module (JSON schema validation)
python3 -m pytest tests/test_schema_module.py -v --tb=short
```

### Run the sanity checker directly (CLI)
```bash
python3 tools/sanity_checker.py --from-config
```
Expected: All checks pass with no ERROR findings.

### Run the orchestrator smoke test
```bash
python3 orchestrator.py && \
python3 -c "import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c; print(f'OIS cumulative: {c[\"operational_impact_cumulative\"]}')"
```
Expected: 24-epoch run completes; final epoch includes OIS fields.

## CI Pipeline Equivalence

The full CI pipeline (`.github/workflows/ci.yml`) runs these steps in order:
1. `pip install --only-binary=:all: --require-hashes -r requirements.lock.txt`
2. `ruff check ...` — static analysis (advisory, `continue-on-error: true`)
3. `python3 tools/sanity_checker.py --from-config` — config validation
4. `pytest tests/test_json_schema_validation.py -v --tb=short` — JSON schema validation
5. `pytest tests/ -v --tb=short --cov --cov-report=term-missing` — full suite with coverage (~875 tests)
6. Picard/Presidio/Stackelberg import hygiene
7. Presidio smoke (`presidio_runner.py` smoke fleet)
8. Orchestrator import hygiene (split modules, stoplights, long-read/TAT)
9. Dashboard import check (LCARS package, `apply_lcars_layout`)
10. `python3 orchestrator.py` — 24-epoch smoke test
11. OIS fields present in final `cost_accounting`
12. Campaign Docker image smoke (`docker build` + `docker run … --smoke`) when Docker is available

Framework-focused CI (`.github/workflows/picard-presidio.yml`) runs a ~190+ test pytest slice (Picard/Presidio/Stackelberg/Contam/campaign/cabin/shedding), Stackelberg schema checks, all-platform JSON schema validation, and Presidio smoke.

To replicate main CI locally:
```bash
pip install --only-binary=:all: --require-hashes -r requirements.lock.txt && \
python3 tools/sanity_checker.py --from-config && \
ruff check --select E,F,W,I --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ orchestrator*.py \
  presidio_runner.py || true && \
python3 -m pytest tests/test_json_schema_validation.py -v --tb=short && \
python3 -m pytest tests/ -v --tb=short --cov --cov-report=term-missing && \
PYTHONPATH=. python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1 && \
python3 orchestrator.py && \
python3 -c "import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c"
```

## Test Coverage Map

| Test File | Tests | Module(s) Tested | Focus |
|-----------|-------|-----------------|-------|
| `test_orchestrator.py` | 76 | `orchestrator*.py` | End-to-end simulation flow, quarantine/SOP |
| `test_wearable_enhanced.py` | 40 | `engines/wearable_monitor.py`, `crusher_labs/modalities/wearable.py` | Multi-device, coverage, visibility, confounders, detection profiles, chronic disease devices, glucose channel, config parsing |
| `test_sanity_checker.py` | 40 | `tools/sanity_checker.py` | Pydantic validation, referential integrity, config sections |
| `test_stoplight.py` | 39 | `crusher_labs/stoplight.py` | Ct-to-stoplight mapping, threshold logic |
| `test_mega_cruise_campaign.py` | 30+ | `picard_framework/runs/mega_cruise_campaign/` | Dry-run counts, smoke zip, shards, S3 resume, aggregators, T11/T15/T16 |
| `test_outbreak_response_architecture.py` | 10+ | `orchestrator_init.py`, `syndromic.py`, `protocol_engine.py`, campaign | Attack-rate escalation, decision latency, bimodal compliance, SOP gates |
| `test_diagnostic_cascade.py` | 36 | `crusher_labs/diagnostic_cascade.py` | Tier progression, multiplex panels, cascade telemetry |
| `test_chronic_disease.py` | 31 | `engines/wearable_monitor.py` | Chronic disease device assignments and glucose channel |
| `test_json_schema_validation.py` | 30 | `schemas/*.schema.json` | All platform, social, fleet JSON files validated against schemas |
| `test_protocol_engine.py` | 28 | `crusher_labs/protocol_engine.py` | Stoplight triggers, SOP activation, modifiers |
| `test_transmission_infection_expanded.py` | 27 | `engines/transmission_core.py`, `engines/infection_dynamics_bridge.py` | Dose-response, shedding, KorkinAgent lifecycle, multi-pathway |
| `test_data_contracts.py` | 27 | JSON config files | Schema conformance, uniqueness, bounds |
| `test_telemetry_seams.py` | 22 | `telemetry_buffer/schema.py` | Ground truth serialization round-trip |
| `test_dashboard_extended.py` | 21 | `dashboard/` | zone_metric, color_scale, lcars_rgba, theme, fleet_viz, spatial_viz |
| `test_law_compliance.py` | 20 | All modules | Laws 1-6, extended to picard_framework/, crusher_labs/, decision_engine/ |
| `test_py_contam_bridge.py` | 19 | `engines/py_contam_bridge.py` | HVAC mass conservation, ACH, filter efficiency, decay, path construction |
| `test_contamx_solver.py` | ~17 | `engines/contamx_runner.py`, `contamx_transport.py` | ContamX discovery, `.SIM` reader (embedded path `nr`), transport engine |
| `test_contam_flow_compare.py` | ~6 | `tools/contam_flow_compare.py` | Native vs ContamX path fate / kept-link Flow0 diagnostics |
| `test_contam_engine_compare.py` | ~8 | `tools/contam_engine_compare.py` | Compare suite jobs, path_inventory offline |
| `test_crusher_labs_modalities.py` | 19 | `crusher_labs/modalities/` | Fidelity tiers, lab_notebook, RDT, sequencing CLR, PCR Ct |
| `test_scripts_tools.py` | 14 | `scripts/`, `tools/gis_spatial_bridge.py` | Blueprint shapes, resolve_column, group_hvac_zones, imports |
| `test_decision_engine.py` | 9 | `decision_engine/` | ObservationModel, DecisionRound, ExperienceStore |
| `test_cost_ledger.py` | 9 | `crusher_labs/cost_ledger.py` | Budget tracking, material deductions, OIS |
| `test_wearable_anomaly_scorer.py` | 8 | `engines/wearable_anomaly_scorer.py`, `crusher_labs/cascade_entry.py` | Confounder template matching, fleet downweighting, `infection_score`, cascade entry fusion |
| `test_stackelberg.py` | 8 | `decision_engine/stackelberg/` | Diffusion, contact graph, utility export/import |
| `test_schema_module.py` | 7 | `telemetry_buffer/schema.py` | JSON schema output validation |
| `test_long_read_sequencing.py` | 7 | `crusher_labs/modalities/long_read_sequencing.py` | Nanopore verification, escalation, profiles |
| `test_dashboard.py` | 7 | `dashboard.py` | LCARS dashboard imports, pathway aggregation |
| `test_clinical_correlation.py` | 7 | `crusher_labs/` | Clinical correlation across modalities |
| `test_aitchison_beta_diversity.py` | 7 | `engines/` | Microbiome beta diversity metrics |
| `test_infection_counters.py` | 6 | `orchestrator_epoch.py` | Attack-rate counters, thresholds, exempt_classes |
| `test_cascade_entry.py` | 6 | `crusher_labs/cascade_entry.py`, `crusher_labs/diagnostic_cascade.py` | Sick-call Tier 1 vs wearable Tier 0, `infection_score` alert rules, device fusion |
| `test_simulation_utils_paths.py` | 5 | `engines/` | Simulation utility path resolution |
| `test_sequencing_config.py` | 5 | `crusher_labs/__init__.py` | Read-depth wiring from config.yaml |
| `test_pathogen_overrides.py` | 5 | `data/pathogens/` | Per-pathogen config overrides |
| `test_instrument_turnaround.py` | 5 | `crusher_labs/instrument_turnaround.py` | TAT queue delivery delays |
| `test_enterprise_platforms.py` | 5 | `data/platforms/enterprise_*` | Enterprise HVAC referential integrity |
| `test_smoke_diagnostic_cascade.py` | 4 | `picard_framework/` | 6-epoch cascade smoke (standard + multiplex specs) |
| `test_picard_framework.py` | 4 | `picard_framework/` | PicardRunSpec, ShipSimulation, golden reproducibility |
| `test_cabin_corridor_transmission.py` | 5 | `engines/transmission_core.py` | Cabin-corridor confinement, ventilation, HVAC |
| `test_shedding_variance_cabin_mates.py` | 8 | `engines/infection_dynamics_bridge.py`, `orchestrator_init.py` | Host shedding multiplier, cabin-mate pairing |
| `test_agent_axes.py` | 4 | `telemetry_buffer/agent_axes.py` | Orthogonal infection/presentation/compliance |
| `test_transmission_pathways.py` | 3 | `engines/transmission_core.py` | Food/environmental pool initialization |
| `test_golden_picard.py` | 3 | `picard_framework/`, `orchestrator.py` | Golden SIR parity, cost accounting, Picard vs orchestrator |
| `test_behavioral_syndromic.py` | 3 | `syndromic.py` | Layer-1 sick-call / compliance |
| `test_operational_impact.py` | 2 | `crusher_labs/cost_ledger.py` | OIS weight computation |
| `test_infection_dynamics_bridge.py` | 2 | `engines/infection_dynamics_bridge.py` | Korkin agent lifecycle bridge |
| `test_golden_orchestrator.py` | 2 | `orchestrator.py` | 24-epoch reproducibility via Picard |
| `test_presidio_runner.py` | 1 | `presidio_runner.py` | Fleet smoke, experience store |
| `test_cost_accounting.py` | 1 | `orchestrator_record.py` | Per-test debits and materials telemetry |
| `test_action_applier.py` | 7 | `action_applier.py` | Handler table, missing-ctx no-ops, isolation/stance |
| `test_tier_iterators.py` | 9 | `tier_iterators.py` | Campaign iterator table and seed grading |
| `test_campaign_boundaries.py` | 11 | `campaign_runner.py` | HVAC mapping, shards, unknown-tier errors |
| `test_ship_epoch_helpers.py` | 7 | `ship_simulation.py` | `_merge_applied`, belief clamp |
| `test_sentinel_fleet_columns.py` | 5 | `_sentinel_fleet_reference.py` | 1-based Stan names, WW columns |

## Golden Test Values

Seed-42 / 24-epoch `mega_cruise_5000` baseline (epoch 23) — the default
platform in `crusher_labs/config.yaml`:

| Metric | Expected (epoch 23) |
|--------|-------------------|
| Susceptible | 13 |
| Infected | 0 |
| Symptomatic | 0 |
| Recovered | 3 |
| Immune | 4 |
| Trigger status | BASELINE |
| Total financial USD | > 0 (exact value may differ slightly between Python 3.11 and 3.12) |
| OIS cumulative | shifts with outbreak dynamics |

Golden totals shift when observation, cascade, pathogen wiring, shedding variance,
outbreak-response (escalation / compliance) wiring, or the default platform
changes; update `tests/test_golden_orchestrator.py` and `tests/test_golden_picard.py`
after intentional epidemiological changes. See `docs/SHEDDING_AND_CABINMATES.md`
and `docs/tiered_escalation_spec.md`.
