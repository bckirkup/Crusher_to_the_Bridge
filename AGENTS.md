# Crusher-to-the-Bridge — Agent Instructions

## Cursor Cloud specific instructions

This is a pure-Python simulation project with no external services (no databases, Docker, or network APIs). Python 3.11+ is required.

### Running services

| Service | Command | Notes |
|---------|---------|-------|
| Orchestrator simulation | `python3 orchestrator.py` | Runs 24 epochs by default; override with `--epochs N` |
| Streamlit dashboard | `python3 -m streamlit run dashboard.py --server.headless true` | Requires simulation output in `telemetry_buffer/` |
| Sanity checker | `python3 tools/sanity_checker.py --from-config` | Validates all JSON configs + `crusher_labs/config.yaml` |
| Test suite | `python3 -m pytest tests/ -v --tb=short` | 259 tests, runs in ~2s |

### Important caveats

- Use `python3` (not `python`) — the VM does not alias `python` to `python3`.
- The dashboard reads from `telemetry_buffer/simulation_history.json` and `telemetry_buffer/artificial_lab_notebook.json`. Run the orchestrator first to generate these files.
- All standard commands are documented in the README Quick Start section and `.github/workflows/ci.yml`.
- The CI workflow validates: sanity checker → pytest → import hygiene → dashboard import → 24-epoch run.
- No linter (flake8/ruff/pylint) is configured in the repo; validation is done via `sanity_checker.py` and the test suite.
