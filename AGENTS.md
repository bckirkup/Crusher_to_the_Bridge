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
| Deck asset precompute | `python3 scripts/precompute_deck_assets.py` | Writes `deck_graphics.geojson`, hull PNG, manifest per platform |
| Sanity checker | `python3 tools/sanity_checker.py --from-config` | Ship + fleet + Stackelberg social configs |
| Full test suite | `python3 -m pytest tests/ -v --tb=short` | ~337 tests, ~4s |
| Long-read / TAT tests | `python3 -m pytest tests/test_long_read_sequencing.py tests/test_instrument_turnaround.py -v` | Nanopore + turnaround queue |

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

- Ship / Picard: `OPERATORS_MANUAL_SHIP.md`
- Fleet / Stackelberg: `OPERATORS_MANUAL_GAME_THEORY.md`
- Full legacy reference: `OPERATORS_MANUAL.md`

### CI (replicate locally)

**Main** (`.github/workflows/ci.yml` on `main` PRs):

1. `python tools/sanity_checker.py --from-config`
2. `pytest tests/ -v --tb=short` (~337 tests)
3. Picard/Presidio/Stackelberg import hygiene
4. Presidio smoke (`smoke_fleet.json`, 1 cruise)
5. Long-read / TAT targeted tests
6. Orchestrator import hygiene (stoplight deduplication)
7. Dashboard import + `apply_lcars_layout` smoke
8. `python orchestrator.py` — 24-epoch smoke
9. OIS fields present in final `cost_accounting`

**Picard/Presidio** (`.github/workflows/picard-presidio.yml` on `main` and `cursor/**`):

- Framework-focused pytest slice (Picard, Presidio, Stackelberg, OIS, behavioral, long-read, enterprise platforms, agent axes, sequencing config)
- Stackelberg + platform JSON schema validation (all `data/platforms/*/`)
- Presidio smoke

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
| `orchestrator-smoke-test` | After orchestrator, engine, or `config.yaml` changes |
| `testing-dashboard` | After `dashboard/` or telemetry field changes |
| `testing-data-contracts` | After JSON config or platform/pathogen edits |
| `testing-agent-classes` | Agent class, gender, duty zone, exempt_classes changes |
| `schema-validation` | Before committing JSON in `data/` or `telemetry_buffer/` |
| `adding-new-platform` | New vessel spatial layout + HVAC |
| `adding-new-pathogen` | New pathogen profile entries |

### Important caveats

- Use `python3` (not `python`) on Linux cloud VMs.
- Dashboard reads `telemetry_buffer/simulation_history.json` and `telemetry_buffer/artificial_lab_notebook.json`.
- Dashboard implementation lives in `dashboard/`; `streamlit run dashboard.py` imports the package.
- Observation results in telemetry reflect **delivered** assays (TAT queue), including `pending` long-read runs until `available_epoch`.
- **Law 1:** No hardcoded epoch SOP schedules; Stackelberg `authorize_sop_subset` filters stoplight-eligible SOPs; `activate_sop` can force protocols via `forced_protocol_ids`.
- **OIS:** Fourth ledger dimension in `cost_accounting`; configured via `operational_impact_weights` in `resource_costs.json`.
- Utility **weights and optimization** are out-of-repo; only feature export and action apply are in-repo.
- Eight ship platforms in `data/platforms/` (including fiction-adapted Enterprise bundles); see `README.md` Platforms table.
- No flake8/ruff in repo; use `sanity_checker.py` and pytest.
