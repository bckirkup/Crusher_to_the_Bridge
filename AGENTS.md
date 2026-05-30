# Crusher-to-the-Bridge — Agent Instructions

## Cursor Cloud specific instructions

Pure-Python simulation (no databases, Docker, or external APIs). **Python 3.11+** required.

### Running services

| Service | Command | Notes |
|---------|---------|-------|
| Ship simulation (legacy CLI) | `python3 orchestrator.py` | Delegates to Picard `ShipSimulation`; 24 epochs default |
| Picard programmatic API | See `OPERATORS_MANUAL_SHIP.md` | `PicardRunSpec` + `ShipSimulation` |
| Fleet meta-simulation | `python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1` | Fast smoke; default fleet is slower |
| Utility export (external optimizer) | `python3 presidio_runner.py --export-utility-dir presidio/data/experiences/utility_bundles` | Requires `social` block on run spec |
| Action import (external optimizer) | `python3 presidio_runner.py --import-actions-dir <dir>` | Per-epoch `cruise_*_epoch_*_actions.json` |
| Streamlit dashboard | `python3 -m streamlit run dashboard.py --server.headless true` | Run orchestrator first for telemetry |
| Sanity checker | `python3 tools/sanity_checker.py --from-config` | Ship + fleet + Stackelberg social configs |
| Full test suite | `python3 -m pytest tests/ -v --tb=short` | ~330 tests, ~4s |
| Long-read / TAT tests | `python3 -m pytest tests/test_long_read_sequencing.py tests/test_instrument_turnaround.py -v` | Nanopore + turnaround queue |

### Framework layout

| Path | Role |
|------|------|
| `picard_framework/` | Ship run spec, catalog, `ShipSimulation` |
| `decision_engine/` | Policies, Stackelberg round, diffusion, utility I/O |
| `presidio/` + `presidio_runner.py` | Fleet cruises, experience store, economics |
| `orchestrator*.py` | Legacy epoch helpers used by Picard |

### Operator manuals

- Ship / Picard: `OPERATORS_MANUAL_SHIP.md`
- Fleet / Stackelberg: `OPERATORS_MANUAL_GAME_THEORY.md`
- Full legacy reference: `OPERATORS_MANUAL.md`

### CI (replicate locally)

**Main** (`.github/workflows/ci.yml` on `main` PRs): sanity checker → full pytest → Picard/Presidio import hygiene → Presidio smoke → orchestrator import hygiene → dashboard import → 24-epoch `orchestrator.py`.

**Picard/Presidio** (`.github/workflows/picard-presidio.yml`): focused framework tests + Stackelberg schema validation + Presidio smoke.

### Agent skills

| Skill | Use when |
|-------|----------|
| `picard-ship-simulation` | `picard_framework/`, `ShipSimulation` |
| `presidio-fleet-run` | `presidio_runner.py`, fleet configs |
| `stackelberg-utility-export` | Social config, utility bundles, action import |
| `testing-picard-presidio` | Before PRs on framework code |
| `configuring-stackelberg-social` | Adding/editing diffusion, class interactions, profiles |
| `operational-impact-behavioral-policies` | OIS weights, action kinds, ThresholdBeliefPolicy |
| `run-full-test-suite` | Any pre-PR validation |
| `long-read-sequencing` | Long-read params, TAT config, escalation, `LongReadNanoporeSequencing` |

### Important caveats

- Use `python3` (not `python`) on Linux cloud VMs.
- Dashboard reads `telemetry_buffer/simulation_history.json` and `telemetry_buffer/artificial_lab_notebook.json`.
- Observation results in telemetry reflect **delivered** assays (TAT queue), including `pending` long-read runs until `available_epoch`.
- **Law 1:** No hardcoded epoch SOP schedules; Stackelberg `authorize_sop_subset` filters stoplight-eligible SOPs; `activate_sop` can force protocols via `forced_protocol_ids`.
- **OIS:** Fourth ledger dimension in `cost_accounting`; configured via `operational_impact_weights` in `resource_costs.json`.
- Utility **weights and optimization** are out-of-repo; only feature export and action apply are in-repo.
- No flake8/ruff in repo; use `sanity_checker.py` and pytest.
