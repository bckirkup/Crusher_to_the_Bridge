The Prime Directive: Fix it, improve it, have fun.

We don't do "processes." We do engineering. If you see a way to make the shipboard agent-based model run faster or the biosurveillance logic sharper, open a Pull Request.

Rule 0: If you find a bug, don't just report it—patch it. Run CI tests.

Rule 1: Documentation is a courtesy and brevity is valuable.

## First run

```bash
pip install -r requirements.txt
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py
python3 -m pytest tests/ -v --tb=short
```

Docs map: [docs/README.md](docs/README.md). Agent runbook: [docs/AGENTS.md](docs/AGENTS.md).

## Before opening a PR

1. `python3 tools/sanity_checker.py --from-config`
2. Targeted pytest for what you touched (or full `tests/`)
3. If you changed JSON under `data/` or `telemetry_buffer/`, validate schemas (`schemas/README.md` / `schema-validation` skill)

## Where documentation lives

| Need | Start here |
|------|------------|
| Run a ship or fleet | `docs/OPERATORS_MANUAL_SHIP.md`, `docs/OPERATORS_MANUAL_GAME_THEORY.md` |
| ContamX / HVAC | `docs/CONTAM_INTEROP.md` |
| Agent skills | `.agents/skills/` |
| Doc index | `docs/README.md` |

When behavior changes, update the matching operator section **and** the skill in the same PR so humans and agents do not drift.
