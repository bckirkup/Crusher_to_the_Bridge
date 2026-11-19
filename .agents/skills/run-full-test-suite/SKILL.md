---
name: run-full-test-suite
description: Run the complete Crusher-to-the-Bridge pytest suite including data contracts, sanity checks, orchestrator tests, law compliance, and all module tests. Use before creating PRs or after any code change.
---

# Run Full Test Suite

## Prerequisites

- Python 3.11+ with dependencies from `uv.lock` (see Setup in `AGENTS.md`)
- Working directory: **repo root**

## Devin Secrets Needed

None — all tests run locally.

## Quick Commands

### Run the entire test suite
```bash
python3 -m pytest tests/ -v --tb=short
```
Main CI uses `python3 -m pytest tests/ -m 'not slow'`. Use `--collect-only -q`
to inspect the current selection without executing tests.

### Run with coverage reporting
```bash
python3 -m pytest tests/ -v --tb=short --cov --cov-report=term-missing
```
Coverage scope and exclusions are defined in `pyproject.toml` under `[tool.coverage.run]`.

### Run blocking Ruff lint

Use the production package list and flags in [AGENTS.md](../../../AGENTS.md#validation).
An exit other than zero is a failure; do not suppress lint errors.

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

## CI pipeline

[Main CI](../../../.github/workflows/ci.yml) runs the fast pytest tier on both
supported interpreters and combines coverage from the Python 3.12 shards.
[Nightly](../../../.github/workflows/nightly.yml) includes slow tests by default.
[Picard/Presidio](../../../.github/workflows/picard-presidio.yml) checks sanity,
imports, schemas and a fleet smoke; it does not repeat the pytest suite.
See [root validation](../../../AGENTS.md#validation) for local commands.

## Selected test modules

| Test File | Module(s) Tested | Focus |
|-----------|-----------------|-------|
| `test_orchestrator.py` | `orchestrator*.py` | End-to-end simulation flow, quarantine/SOP |
| `test_wearable_enhanced.py` | `engines/wearable_monitor.py`, `crusher_labs/modalities/wearable.py` | Multi-device, coverage, visibility, confounders, detection profiles, chronic disease devices, glucose channel, config parsing |
| `test_sanity_checker.py` | `tools/sanity_checker.py` | Pydantic validation, referential integrity, config sections |
| `test_stoplight.py` | `crusher_labs/stoplight.py` | Ct-to-stoplight mapping, threshold logic |
| `test_mega_cruise_campaign.py` | `picard_framework/runs/mega_cruise_campaign/` | Dry-run counts, smoke zip, shards, S3 resume, aggregators, T11/T15/T16 |
| `test_outbreak_response_architecture.py` | `orchestrator_init.py`, `syndromic.py`, `protocol_engine.py`, campaign | Attack-rate escalation, decision latency, bimodal compliance, SOP gates |
| `test_diagnostic_cascade.py` | `crusher_labs/diagnostic_cascade.py` | Tier progression, multiplex panels, cascade telemetry |
| `test_chronic_disease.py` | `engines/wearable_monitor.py` | Chronic disease device assignments and glucose channel |
| `test_json_schema_validation.py` | `schemas/*.schema.json` | All platform, social, fleet JSON files validated against schemas |
| `test_protocol_engine.py` | `crusher_labs/protocol_engine.py` | Stoplight triggers, SOP activation, modifiers |
| `test_transmission_infection_expanded.py` | `engines/transmission_core.py`, `engines/infection_dynamics_bridge.py` | Dose-response, shedding, KorkinAgent lifecycle, multi-pathway |
| `test_data_contracts.py` | JSON config files | Schema conformance, uniqueness, bounds |
| `test_telemetry_seams.py` | `telemetry_buffer/schema.py` | Ground truth serialization round-trip |
| `test_dashboard_extended.py` | `dashboard/` | zone_metric, color_scale, lcars_rgba, theme, fleet_viz, spatial_viz |
| `test_law_compliance.py` | All modules | Laws 1-6, extended to picard_framework/, crusher_labs/, decision_engine/ |
| `test_py_contam_bridge.py` | `engines/py_contam_bridge.py` | HVAC mass conservation, ACH, filter efficiency, decay, path construction |
| `test_contamx_solver.py` | `engines/contamx_runner.py`, `contamx_transport.py` | ContamX discovery, `.SIM` reader (embedded path `nr`), transport engine |
| `test_contam_flow_compare.py` | `tools/contam_flow_compare.py` | Native vs ContamX path fate / kept-link Flow0 diagnostics |
| `test_contam_engine_compare.py` | `tools/contam_engine_compare.py` | Compare suite jobs, path_inventory offline |
| `test_crusher_labs_modalities.py` | `crusher_labs/modalities/` | Fidelity tiers, lab_notebook, RDT, sequencing CLR, PCR Ct |
| `test_scripts_tools.py` | `scripts/`, `tools/gis_spatial_bridge.py` | Blueprint shapes, resolve_column, group_hvac_zones, imports |
| `test_decision_engine.py` | `decision_engine/` | ObservationModel, DecisionRound, ExperienceStore |
| `test_cost_ledger.py` | `crusher_labs/cost_ledger.py` | Budget tracking, material deductions, OIS |
| `test_wearable_anomaly_scorer.py` | `engines/wearable_anomaly_scorer.py`, `crusher_labs/cascade_entry.py` | Confounder template matching, fleet downweighting, `infection_score`, cascade entry fusion |
| `test_stackelberg.py` | `decision_engine/stackelberg/` | Diffusion, contact graph, utility export/import |
| `test_schema_module.py` | `telemetry_buffer/schema.py` | JSON schema output validation |
| `test_long_read_sequencing.py` | `crusher_labs/modalities/long_read_sequencing.py` | Nanopore verification, escalation, profiles |
| `test_dashboard.py` | `dashboard.py` | LCARS dashboard imports, pathway aggregation |
| `test_clinical_correlation.py` | `crusher_labs/` | Clinical correlation across modalities |
| `test_aitchison_beta_diversity.py` | `engines/` | Microbiome beta diversity metrics |
| `test_infection_counters.py` | `orchestrator_epoch.py` | Attack-rate counters, thresholds, exempt_classes |
| `test_cascade_entry.py` | `crusher_labs/cascade_entry.py`, `crusher_labs/diagnostic_cascade.py` | Sick-call Tier 1 vs wearable Tier 0, `infection_score` alert rules, device fusion |
| `test_simulation_utils_paths.py` | `engines/` | Simulation utility path resolution |
| `test_sequencing_config.py` | `crusher_labs/__init__.py` | Read-depth wiring from config.yaml |
| `test_pathogen_overrides.py` | `data/pathogens/` | Per-pathogen config overrides |
| `test_instrument_turnaround.py` | `crusher_labs/instrument_turnaround.py` | TAT queue delivery delays |
| `test_enterprise_platforms.py` | `data/platforms/enterprise_*` | Enterprise HVAC referential integrity |
| `test_smoke_diagnostic_cascade.py` | `picard_framework/` | 6-epoch cascade smoke (standard + multiplex specs) |
| `test_picard_framework.py` | `picard_framework/` | PicardRunSpec, ShipSimulation, golden reproducibility |
| `test_cabin_corridor_transmission.py` | `engines/transmission_core.py` | Cabin-corridor confinement, ventilation, HVAC |
| `test_shedding_variance_cabin_mates.py` | `engines/infection_dynamics_bridge.py`, `orchestrator_init.py` | Host shedding multiplier, cabin-mate pairing |
| `test_agent_axes.py` | `telemetry_buffer/agent_axes.py` | Orthogonal infection/presentation/compliance |
| `test_transmission_pathways.py` | `engines/transmission_core.py` | Food/environmental pool initialization |
| `test_golden_picard.py` | `picard_framework/`, `orchestrator.py` | Golden SIR parity, cost accounting, Picard vs orchestrator |
| `test_behavioral_syndromic.py` | `syndromic.py` | Layer-1 sick-call / compliance |
| `test_operational_impact.py` | `crusher_labs/cost_ledger.py` | OIS weight computation |
| `test_infection_dynamics_bridge.py` | `engines/infection_dynamics_bridge.py` | Korkin agent lifecycle bridge |
| `test_golden_orchestrator.py` | `orchestrator.py` | 24-epoch reproducibility via Picard |
| `test_presidio_runner.py` | `presidio_runner.py` | Fleet smoke, experience store |
| `test_cost_accounting.py` | `orchestrator_record.py` | Per-test debits and materials telemetry |
| `test_action_applier.py` | `action_applier.py` | Handler table, missing-ctx no-ops, isolation/stance |
| `test_tier_iterators.py` | `tier_iterators.py` | Campaign iterator table and seed grading |
| `test_campaign_boundaries.py` | `campaign_runner.py` | HVAC mapping, shards, unknown-tier errors |
| `test_ship_epoch_helpers.py` | `ship_simulation.py` | `_merge_applied`, belief clamp |
| `test_sentinel_fleet_columns.py` | `_sentinel_fleet_reference.py` | 1-based Stan names, WW columns |

## What the golden tests assert

`tests/test_golden_orchestrator.py` checks conservation, repeatability and
cost accounting. `tests/test_golden_picard.py` checks parity between entry
points. Neither pins a particular final case count.

## Hull cells: invariants + determinism, not pins

`tests/test_covid_hull_change_detector.py` used to pin each hull cell's
five-field witness tuple per interpreter and fail on any move. At the merge
rate of late 2026 (~8 PRs/day) every mechanism touching the shared RNG
stream re-rolled both cells, nightly went red for days at a stretch, and
the repin/attribution loop cost more than the drift signal was worth. The
pins are retired. The module now asserts:

* structural invariants — channel ordering, split-day partition
  conservation, counts bounded by aboard complement, share domains;
* identity echoes (scenario/theta/seed it was asked to run);
* same-seed determinism on the fast Greg Mortimer cell — a second run
  must reproduce the first witness tuple exactly. This is the part of the
  old pin worth keeping: it still catches unseeded draws and stream
  nondeterminism. Diamond Princess is exempt (a second ~20-minute replay
  per interpreter is not worth the nightly wall time).

A legitimate mechanism move is free to re-roll these cells; only a
structurally impossible or nondeterministic reading fails. The last pinned
tuples live in `LAST_KNOWN_READINGS` in the test file as investigation
references (NOT asserted); the per-merge attribution history is in the
file's git history. If the determinism test fails, that is a real finding —
unseeded draw or iteration-order dependence — not a pin to bump.

Historical context on interpreter divergence: CPython 3.12's compensated
`sum()` association order means the same seed can follow a different
Bernoulli path on 3.12 than on 3.11 — e.g. HOST-AGE-01 moved the GM cell
to (34,17,217,56,22) on 3.12 vs (43,25,217,60,19) on 3.11. Both
interpreters are deterministic on their own; never expect cross-interpreter
equality of exact counts, and never copy one leg's reading into the
other's notes as "the" value.

## CI infrastructure flakes

The `astral-sh/setup-uv` step occasionally dies at "Activating python
venv..." with exit 1 before repo code runs — an infra hiccup that killed
whole jobs (smoke, schema validation, shards) indiscriminately. Every
`Set up uv` step is now `continue-on-error` with an `id`, and a
`Set up uv (fallback installer)` step runs only when the action's outcome
is `failure` (direct `install.sh` fetch + `uv python install`, pinned to
the same 0.7.9); `uv sync` retries once after 10s. If jobs still die
before repo code runs, look at the fallback step's log, not the code.
