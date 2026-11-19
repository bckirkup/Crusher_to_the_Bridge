# Crusher-to-the-Bridge — Agent Instructions

[Docs and skill index](docs/AGENTS.md) · [Human docs map](docs/README.md)

## Setup

Use Python 3.11+ and uv. The `pre-commit` CLI is a separate developer tool;
install it if it is not already on your PATH.

```bash
uv sync --locked --all-extras --no-install-project --no-build
source .venv/bin/activate
pre-commit install
```

## Before Editing

Read `.agents/skills/sonar-quality/SKILL.md` before changing code or workflows.

Before changing any epidemiological constant — transmission rates, transfer
fractions, contact kernels, decay rates, titres, areas, deposition fractions —
read `.agents/skills/model-parameter-provenance/SKILL.md`. Constants carry a
source and an evidence grade at their definition, and none of them may be
chosen to make VSP, Park, or the passenger/crew ratio come out right.

`docs/norovirus/norovirus_open_ledger.md` records what is currently withdrawn. **Every
dose figure in the repository is void pending a refit** — check the ledger
before quoting one.

Crusher's local Ruff pre-commit hook uses the repository `C901` ceiling of 56.
Sonar's new-code gate holds new functions to cognitive complexity 15. Dedicated
complexity-backlog splits are allowed as their own change; do not mix them into
Sentinel analysis. The last documented official `S3776` count was 27, taken from
a live Sonar scan on 2026-09-29 — update it only from a live Sonar scan. The
ceiling only ever ratchets downward.

## Validation

```bash
# After staging changes, run hooks on those files (use --files for unstaged paths).
pre-commit run
# Check tracked Python sources as well as workflows and configuration:
git ls-files -z -- '*.py' ':!tests' ':!.agents' | xargs -0 python3 scripts/sonar_guard.py
git ls-files -z -- '*.py' ':!tests' ':!.agents' | xargs -0 python3 scripts/clock_guard.py
python3 scripts/sonar_guard.py --workflows .github/workflows
python3 scripts/clock_guard.py --configs
ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311 \
  api/ engines/ crusher_labs/ picard_framework/ decision_engine/ \
  orchestrator*.py presidio_runner.py deploy/aws/
python3 -m pytest tests/ -m 'not slow' -v --tb=short --cov --cov-report=xml
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

`-m 'not slow'` is the fast tier that [CI](.github/workflows/ci.yml) runs on PRs
to `main` and pushes to `main`. It uses four shards each on Python 3.11 and 3.12
(`--ci-shard-count`/`--ci-shard-index` in `tests/conftest.py`), with
`pytest -n auto` inside each; add `-n auto` locally to use every core. The
`slow` marker covers the posterior-recovery fits — all of
`tests/test_sentinel_fleet_validation.py`, the three long wastewater fits in
`tests/test_sentinel_wastewater.py`, plus a few reference-walker and campaign
cases. [Nightly](.github/workflows/nightly.yml) runs the full suite by default
on cron or manual dispatch, in two shards per interpreter. The separate
[framework workflow](.github/workflows/picard-presidio.yml) checks imports,
schemas, sanity and the fleet smoke; it does not repeat pytest.
Run `python3 -m pytest tests/ -v --tb=short`
locally before changing anything under `picard_framework/analysis/stan/`.

Docker campaign smoke is optional when Docker is unavailable:

```bash
docker build -t picard-campaign .
docker run --rm picard-campaign --smoke
```

## Scope Rules

- Do not modify tests to make them pass. When a model change legitimately moves
  a numeric expectation, attribute the move to a specific part of your diff
  before updating it; an unattributed baseline move is a possible defect.
- Do not fit a physical constant to an anchor the model is scored against.
- Update the relevant open ledger — one per pathogen home:
  `docs/norovirus/norovirus_open_ledger.md`, `docs/covid/covid_open_ledger.md`,
  `docs/flu/flu_open_ledger.md` — in the same change as anything that
  invalidates a measurement recorded there; new defect/measurement entries are
  one file each under `docs/ledger/<ID>.md` (see its README) with Pathogens and
  Commit SHA. Every pathogen arm, including fictional bundles, gets a docs home
  (`docs/<name>/` plus `<name>_open_ledger.md`) in the change the arm lands;
  register it in `docs/README.md` and `docs/ledger/README.md`.
- New campaigns register under `campaigns/<pathogen>/<name>/` and submit
  through `scripts/campaign`; the bespoke `deploy/aws/*_entrypoint.py`,
  `submit_*.sh`, `batch_job_definition_*.json` and `Dockerfile.*` files are the
  frozen legacy layout — do not add new ones, and migrate a legacy campaign's
  spec the next time it is touched. A file named in a registered jobdef's
  argv[0] stays put until that campaign's array work is done.
- Preserve the locked `uv sync` installation (`--locked --no-build`, wheels only
  from `uv.lock`) and the CI workflows. Regenerate `uv.lock` only with
  `uv lock` after changing `pyproject.toml`.
- Keep substantive Sentinel work under `picard_framework/analysis/stan/` and
  `picard_framework/runs/` separate from mechanical maintenance.
